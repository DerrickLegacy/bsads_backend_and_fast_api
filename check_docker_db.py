#!/usr/bin/env python3
"""Check Docker database (port 5433)"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models import Alert, User, Hive

# Docker database URL
docker_db_url = "postgresql://bee_user:bee_user@localhost:5433/bee_db"

engine = create_engine(docker_db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("=" * 80)
print("DOCKER DATABASE CHECK (port 5433)")
print("=" * 80)

try:
    # Check users
    user_count = db.query(User).count()
    print(f"\nUsers: {user_count}")
    
    # Check hives
    hive_count = db.query(Hive).filter(Hive.is_deleted == False).count()
    print(f"Hives: {hive_count}")
    
    # Check alerts
    alert_count = db.query(Alert).count()
    print(f"Alerts: {alert_count}")
    
    # List some hives
    if hive_count > 0:
        print("\nHive Names:")
        hives = db.query(Hive).filter(Hive.is_deleted == False).limit(10).all()
        for hive in hives:
            print(f"  - {hive.hive_name} ({hive.hive_id})")
    
    # Check the specific alert
    alert_id = "d3f24b2f-128d-480d-9499-5537098b8114"
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    
    if alert:
        print(f"\n✅ Alert {alert_id} found in Docker database!")
    else:
        print(f"\n❌ Alert {alert_id} NOT in Docker database")
    
except Exception as e:
    print(f"\n❌ Error connecting to Docker database: {e}")
    print("Make sure Docker is running: docker compose up")

finally:
    db.close()

print("=" * 80)
