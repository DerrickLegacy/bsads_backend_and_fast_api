# Poller Scalability Analysis & Recommendations

## Current Architecture

### Discovery Poller (every 30s)
- Scans ALL active FarmerDataSource records
- For each source: HTTP API call to list recordings
- Registers new files as pending AudioSource records
- **Sequential processing** - one source at a time

### Inference Poller (every 30s)
- Fetches ALL pending AudioSource records
- For each: downloads audio bytes, sends to HuggingFace API
- **Sequential processing** - one audio file at a time
- **Blocking** - waits for each inference to complete

## Scalability Issues at Scale

### 🔴 CRITICAL ISSUES

#### 1. **Sequential Processing Bottleneck**
**Problem:** Both pollers process records one-by-one
- With 1,000 hives: Discovery takes 1,000 × ~200ms = **3+ minutes**
- With 100 pending audio files: Inference takes 100 × ~35s = **58+ minutes**
- Pollers will overlap and skip runs (max_instances=1)

**Impact:** 
- Audio files sit in "pending" for hours
- Real-time alerts become delayed alerts
- Farmers miss critical swarming events

#### 2. **Single-Threaded Execution**
**Problem:** BackgroundScheduler runs in a single thread
- Only one HTTP request at a time
- CPU sits idle while waiting for network I/O
- Cannot utilize multiple cores

**Impact:**
- Poor resource utilization
- Slow throughput even with powerful hardware

#### 3. **Memory Growth**
**Problem:** `scan_all_sources()` loads ALL active sources into memory
```python
sources = db.query(FarmerDataSource).filter(...).all()  # Loads everything
```

**Impact:**
- With 10,000 hives: ~10MB+ of data loaded every 30s
- Memory pressure on long-running processes
- Potential OOM on constrained environments

#### 4. **No Prioritization**
**Problem:** All hives treated equally
- Critical hives (already showing pre-swarm) processed same as healthy hives
- No way to fast-track urgent audio files

#### 5. **HuggingFace API Rate Limits**
**Problem:** Free tier has limits
- Concurrent request limits
- Daily inference quotas
- No backoff/retry strategy

**Impact:**
- Inference failures at scale
- Wasted API calls on transient errors

### 🟡 MODERATE ISSUES

#### 6. **Database Connection Pool Exhaustion**
**Problem:** Each poller run opens/closes DB sessions
- At scale: hundreds of connections per minute
- Default pool size: 5-10 connections

#### 7. **No Dead Letter Queue**
**Problem:** Failed audio files marked as "failed" and forgotten
- No automatic retry
- No visibility into failure patterns

#### 8. **Duplicate Work**
**Problem:** If server restarts mid-processing
- "processing" records stuck forever
- No recovery mechanism

## Recommended Solutions

### 🎯 SHORT-TERM FIXES (Implement Now)

#### 1. **Batch Processing with Concurrency**
Replace sequential loops with concurrent processing:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def scan_all_sources_concurrent():
    """Scan multiple sources concurrently."""
    db = SessionLocal()
    try:
        sources = db.query(FarmerDataSource).filter(...).all()
        
        # Process 10 sources at a time
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, _scan_http_api, source, db)
                for source in sources
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        db.close()
```

**Benefit:** 10x-20x faster discovery at scale

#### 2. **Pagination for Large Queries**
Process records in batches:

```python
def process_pending_sources_batched():
    """Process pending audio in batches of 50."""
    batch_size = 50
    offset = 0
    
    while True:
        db = SessionLocal()
        try:
            pending = (
                db.query(AudioSource)
                .filter(AudioSource.status == "pending")
                .limit(batch_size)
                .offset(offset)
                .all()
            )
            
            if not pending:
                break
            
            # Process batch concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(_process_one_audio, record, db)
                    for record in pending
                ]
                # Wait for batch to complete
                for future in futures:
                    future.result()
            
            offset += batch_size
        finally:
            db.close()
```

**Benefit:** Controlled memory usage, better throughput

#### 3. **Add Retry Logic with Exponential Backoff**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True
)
def list_recordings_with_retry(config, hive_name):
    """List recordings with automatic retry on transient failures."""
    return list_recordings(config, hive_name=hive_name)
```

**Benefit:** Resilience to transient network errors

#### 4. **Stuck Record Recovery**

```python
def recover_stuck_records():
    """Reset 'processing' records older than 10 minutes."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        stuck = (
            db.query(AudioSource)
            .filter(
                AudioSource.status == "processing",
                AudioSource.ingestion_timestamp < cutoff
            )
            .all()
        )
        
        for record in stuck:
            record.status = "pending"
            log_standalone("warning", "poller",
                          f"Reset stuck record {record.audio_id}")
        
        db.commit()
    finally:
        db.close()

# Add as a job that runs every 5 minutes
_scheduler.add_job(recover_stuck_records, "interval", minutes=5)
```

**Benefit:** Automatic recovery from crashes

### 🚀 MEDIUM-TERM IMPROVEMENTS (Next Sprint)

#### 5. **Move to Celery + Redis**
Replace BackgroundScheduler with a proper task queue:

```python
# celery_app.py
from celery import Celery

celery_app = Celery(
    "bsads",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

@celery_app.task(bind=True, max_retries=3)
def process_audio_task(self, audio_id, hive_id):
    """Process one audio file as a Celery task."""
    try:
        # Fetch audio bytes
        # Run inference
        # Save results
        pass
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

**Benefits:**
- Horizontal scaling (multiple workers)
- Built-in retry logic
- Task prioritization
- Monitoring & observability

#### 6. **Priority Queue for Critical Hives**

```python
# High priority for hives already showing warning signs
if hive.current_state in ["pre_swarm", "missing_queen"]:
    process_audio_task.apply_async(
        args=[audio_id, hive_id],
        priority=9  # High priority
    )
else:
    process_audio_task.apply_async(
        args=[audio_id, hive_id],
        priority=5  # Normal priority
    )
```

#### 7. **Rate Limiting for HuggingFace API**

```python
from redis import Redis
from ratelimit import limits, sleep_and_retry

redis_client = Redis()

@sleep_and_retry
@limits(calls=100, period=60)  # 100 calls per minute
def predict_from_bytes_rate_limited(audio_bytes):
    """Rate-limited inference calls."""
    return predict_from_bytes(audio_bytes)
```

### 🏗️ LONG-TERM ARCHITECTURE (Production Scale)

#### 8. **Microservices Architecture**

```
┌─────────────────┐
│   FastAPI API   │  (Handles HTTP requests)
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Redis   │  (Message broker + cache)
    └────┬─────┘
         │
    ┌────▼──────────────────────┐
    │  Celery Workers (×10)     │  (Process audio files)
    │  - Worker 1: Discovery    │
    │  - Worker 2-9: Inference  │
    │  - Worker 10: Cleanup     │
    └───────────────────────────┘
         │
    ┌────▼─────┐
    │ PostgreSQL│  (Persistent storage)
    └──────────┘
```

#### 9. **Batch Inference API**
Instead of 1 audio → 1 API call, batch multiple:

```python
def predict_batch(audio_files: list[bytes]) -> list[PredictionResult]:
    """Send multiple audio files in one API call."""
    # HuggingFace Inference API supports batching
    # Reduces network overhead by 10x
    pass
```

#### 10. **Caching Layer**

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_hive_name(hive_id: str) -> str:
    """Cache hive names to reduce DB queries."""
    db = SessionLocal()
    try:
        hive = db.query(Hive).filter(Hive.hive_id == hive_id).first()
        return hive.hive_name if hive else None
    finally:
        db.close()
```

## Performance Projections

### Current Architecture
| Hives | Audio/Day | Processing Time | Delay |
|-------|-----------|-----------------|-------|
| 10    | 100       | ~5 min          | <1 min |
| 100   | 1,000     | ~50 min         | ~10 min |
| 1,000 | 10,000    | ~8 hours        | **Hours** |
| 10,000| 100,000   | **Impossible**  | **Days** |

### With Short-Term Fixes (Concurrent Processing)
| Hives | Audio/Day | Processing Time | Delay |
|-------|-----------|-----------------|-------|
| 10    | 100       | ~30 sec         | <30 sec |
| 100   | 1,000     | ~5 min          | ~1 min |
| 1,000 | 10,000    | ~50 min         | ~10 min |
| 10,000| 100,000   | ~8 hours        | **Hours** |

### With Celery + Redis (10 Workers)
| Hives | Audio/Day | Processing Time | Delay |
|-------|-----------|-----------------|-------|
| 10    | 100       | ~10 sec         | <10 sec |
| 100   | 1,000     | ~1 min          | ~30 sec |
| 1,000 | 10,000    | ~10 min         | ~2 min |
| 10,000| 100,000   | ~100 min        | ~20 min |

### With Full Microservices (50 Workers + Batching)
| Hives | Audio/Day | Processing Time | Delay |
|-------|-----------|-----------------|-------|
| 10    | 100       | ~5 sec          | <5 sec |
| 100   | 1,000     | ~30 sec         | ~10 sec |
| 1,000 | 10,000    | ~5 min          | ~1 min |
| 10,000| 100,000   | ~50 min         | ~10 min |

## Immediate Action Items

### Priority 1 (This Week)
1. ✅ Fix hive_name mapping (DONE)
2. ✅ Add label normalization (DONE)
3. 🔲 Add concurrent processing to discovery poller
4. 🔲 Add stuck record recovery job
5. 🔲 Add retry logic with exponential backoff

### Priority 2 (Next Week)
6. 🔲 Implement batch processing for inference
7. 🔲 Add database connection pooling config
8. 🔲 Add monitoring/metrics (Prometheus + Grafana)

### Priority 3 (Next Month)
9. 🔲 Migrate to Celery + Redis
10. 🔲 Implement priority queue
11. 🔲 Add rate limiting

## Monitoring Recommendations

Add these metrics to track poller health:

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
discovery_duration = Histogram("discovery_poller_duration_seconds", "Time to scan all sources")
inference_duration = Histogram("inference_duration_seconds", "Time to process one audio file")
pending_audio_count = Gauge("pending_audio_count", "Number of pending audio files")
failed_audio_count = Counter("failed_audio_total", "Total failed audio files")
```

## Conclusion

**Current Status:** ✅ Works for small scale (10-100 hives)

**Scalability:** ⚠️ Will struggle beyond 500 hives without changes

**Recommended Path:**
1. Implement short-term fixes NOW (1-2 days work)
2. Plan Celery migration for next sprint (1 week work)
3. Monitor and optimize based on real usage patterns

**Critical Threshold:** ~500 active hives with 5-10 audio files/day each
- Beyond this, you MUST implement concurrent processing
- Beyond 2,000 hives, you MUST migrate to Celery

