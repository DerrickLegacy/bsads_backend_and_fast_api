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
# Advisory templates — the lookup table that drives alert text + severity
# ---------------------------------------------------------------------------
_ADVISORY_TEMPLATES = [
    dict(
        prediction_code=0,
        hive_state="normal",
        condition_label="Normal Colony Activity",
        advisory_text=(
            "The colony is operating normally. No intervention required. "
            "Continue routine monitoring and maintain hive hygiene standards."
        ),
        advisory_type="Preventive",
        severity="info",
    ),
    dict(
        prediction_code=1,
        hive_state="pre_swarm",
        condition_label="Pre-Swarm Activity Detected",
        advisory_text=(
            "Acoustic signatures indicate pre-swarm behaviour. Inspect the hive within "
            "24 hours for queen cells and signs of congestion. Consider adding a super or "
            "performing a nucleus split to relieve population pressure."
        ),
        advisory_type="Reactive",
        severity="medium",
    ),
    dict(
        prediction_code=2,
        hive_state="swarm",
        condition_label="Active Swarm Event",
        advisory_text=(
            "Swarm activity is in progress or imminent. Dispatch a team immediately. "
            "Locate the swarm cluster and capture it to retain the colony. Inspect the "
            "parent hive for remaining queen cells and population stability."
        ),
        advisory_type="Reactive",
        severity="critical",
    ),
    dict(
        prediction_code=3,
        hive_state="abscondment",
        condition_label="Colony Abscondment",
        advisory_text=(
            "The colony appears to have absconded. Inspect the hive immediately to confirm. "
            "If absconded, identify the cause (pests, disease, poor conditions) before "
            "re-hiving to prevent recurrence."
        ),
        advisory_type="Reactive",
        severity="critical",
    ),
    dict(
        prediction_code=4,
        hive_state="missing_queen",
        condition_label="Queen Loss Detected",
        advisory_text=(
            "The queen bee appears to be absent. Inspect the hive for eggs and young "
            "larvae within 48 hours. If queenless is confirmed, introduce a new mated "
            "queen or allow the colony to raise an emergency queen from existing young larvae."
        ),
        advisory_type="Reactive",
        severity="high",
    ),
    dict(
        prediction_code=5,
        hive_state="queenbee_present",
        condition_label="Queen Bee Confirmed Present",
        advisory_text=(
            "The queen bee is confirmed present and active. Colony is stable. "
            "Monitor brood pattern at next scheduled inspection."
        ),
        advisory_type="Preventive",
        severity="info",
    ),
    dict(
        prediction_code=6,
        hive_state="pest_infested",
        condition_label="Pest or Mite Infestation Detected",
        advisory_text=(
            "Acoustic patterns suggest pest pressure (mites, small hive beetle, or similar). "
            "Perform a mite wash or sugar roll count. If Varroa count exceeds 3%, initiate "
            "an approved treatment protocol immediately."
        ),
        advisory_type="Reactive",
        severity="high",
    ),
    dict(
        prediction_code=7,
        hive_state="external_noise",
        condition_label="External Noise in Recording",
        advisory_text=(
            "The audio recording contains significant non-bee noise (wind, rain, machinery). "
            "Classification confidence is reduced. Re-record when ambient noise is lower, "
            "or check sensor placement and housing."
        ),
        advisory_type="Preventive",
        severity="low",
    ),
    dict(
        prediction_code=8,
        hive_state="uncertain",
        condition_label="Uncertain Classification",
        advisory_text=(
            "The model could not confidently classify this audio sample. This may be caused "
            "by poor audio quality, unusual colony behaviour, or a state not well represented "
            "in training data. Re-record and resubmit, or schedule a manual hive inspection."
        ),
        advisory_type="Preventive",
        severity="low",
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
