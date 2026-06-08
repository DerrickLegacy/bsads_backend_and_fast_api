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
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.models import AdvisoryTemplate, User


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

    db.commit()
    print(f"✓ Advisory templates seeded  ({len(_ADVISORY_TEMPLATES)} rows, duplicates skipped)")
