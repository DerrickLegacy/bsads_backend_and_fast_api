"""
Seed the database with required bootstrap data.

Called once at FastAPI startup (after create_all).  Every INSERT uses
ON CONFLICT DO NOTHING so re-running is always safe — existing data is
never overwritten.

Default admin credentials (used only when NO admin exists):
    email    : admin@bsads.ug
    password : Admin1234
"""

import bcrypt
import os
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.models import AdvisoryTemplate, User, AdminKey


# ---------------------------------------------------------------------------
# Advisory templates — classification definitions only (no actions)
# ---------------------------------------------------------------------------
_ADVISORY_TEMPLATES = [
    dict(
        prediction_code=0,
        hive_state="normal",
        advisory_type="Preventive",
        severity="info",
        min_confidence_threshold=0.60,
        description="The colony is operating normally with healthy bee activity",
    ),
    dict(
        prediction_code=1,
        hive_state="pre_swarm",
        advisory_type="Preventive",
        severity="high",
        min_confidence_threshold=0.70,
        description="Pre-swarm indicators detected - preventive action can avoid swarming",
    ),
    dict(
        prediction_code=2,
        hive_state="swarm",
        advisory_type="Reactive",
        severity="critical",
        min_confidence_threshold=0.80,
        description="Active swarm event detected - immediate intervention required",
    ),
    dict(
        prediction_code=3,
        hive_state="abscondment",
        advisory_type="Reactive",
        severity="critical",
        min_confidence_threshold=0.85,
        description="Colony has likely absconded - hive may be empty",
    ),
    dict(
        prediction_code=4,
        hive_state="missing_queen",
        advisory_type="Reactive",
        severity="high",
        min_confidence_threshold=0.75,
        description="Queen absence suspected - colony at risk",
    ),
    dict(
        prediction_code=5,
        hive_state="queenbee_present",
        advisory_type="Preventive",
        severity="info",
        min_confidence_threshold=0.65,
        description="Healthy queen detected",
    ),
    dict(
        prediction_code=6,
        hive_state="pest_infested",
        advisory_type="Reactive",
        severity="high",
        min_confidence_threshold=0.70,
        description="Pest activity detected in the hive",
    ),
    dict(
        prediction_code=7,
        hive_state="external_noise",
        advisory_type="Preventive",
        severity="low",
        min_confidence_threshold=0.60,
        description="External interference detected in recording",
    ),
    dict(
        prediction_code=8,
        hive_state="uncertain",
        advisory_type="Preventive",
        severity="low",
        min_confidence_threshold=0.50,
        description="Classification uncertain - manual inspection recommended",
    ),
]


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def seed_initial_data(db: Session) -> None:
    """Insert bootstrap rows that must exist for the app to function."""

    # ── Advisory templates ────────────────────────────────────────────────
    stmt = (
        pg_insert(AdvisoryTemplate)
        .values(_ADVISORY_TEMPLATES)
        .on_conflict_do_nothing(index_elements=["prediction_code"])
    )
    db.execute(stmt)

    # ── Guaranteed admin account ──────────────────────────────────────────
    # admin@bsads.ug / Admin1234 is always seeded so there is always a
    # working credential even if the DB is brand new or the password for
    # other admin accounts has been forgotten.
    existing = db.query(User).filter(User.email == "admin@bsads.ug").first()
    if not existing:
        admin = User(
            full_name="BSADS Admin",
            email="admin@bsads.ug",
            password_hash=_hash_password("Admin1234"),
            role="admin",
        )
        db.add(admin)
        print("✓ Seeded admin account   →  admin@bsads.ug / Admin1234")
    else:
        print("✓ Seeded admin present   →  admin@bsads.ug")

    # ── Admin Key for Simulation Server ───────────────────────────────────
    # Try to load ADMIN_KEY from the simulation server's .env file
    # This allows automatic seeding without manual intervention
    simulation_env_path = Path(__file__).parent.parent.parent / "bsads_farmer_external_data_source_simulation" / ".env"
    
    admin_key_value = None
    
    # Try to get from simulation .env file
    if simulation_env_path.exists():
        try:
            with open(simulation_env_path, 'r') as f:
                for line in f:
                    if line.startswith('ADMIN_KEY='):
                        admin_key_value = line.split('=', 1)[1].strip()
                        break
        except Exception as e:
            print(f"⚠ Could not read simulation .env: {e}")
    
    # Fallback to environment variable
    if not admin_key_value:
        admin_key_value = os.getenv("SIMULATION_ADMIN_KEY")
    
    # Seed the admin key if we found it
    if admin_key_value:
        existing_key = db.query(AdminKey).filter(AdminKey.admin_key == admin_key_value).first()
        if not existing_key:
            key = AdminKey(
                server_name="Farmer Data Source Simulation",
                server_url=None,
                admin_key=admin_key_value,
                description="Default admin key for farmer external data source simulation server",
                is_active=True,
                created_by=None
            )
            db.add(key)
            print(f"✓ Seeded simulation admin key  →  {admin_key_value[:20]}...")
        else:
            print(f"✓ Simulation admin key present  →  {admin_key_value[:20]}...")
    else:
        print("⚠ Simulation admin key not found - admins can add it manually via /admin/keys")

    db.commit()
    print(f"✓ Advisory templates seeded  ({len(_ADVISORY_TEMPLATES)} rows, duplicates skipped)")
