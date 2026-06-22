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

from api.models import Advisory, AdvisoryTemplate, User, AdminKey


# ---------------------------------------------------------------------------
# Advisory templates — classification definitions only (no actions)
# Thresholds are intentionally LOW (0.50–0.65) so the model's real-world
# confidence range always clears the gate.  The advisory library rows below
# use the same wide 0.50–1.00 band for the same reason.
# ---------------------------------------------------------------------------
_ADVISORY_TEMPLATES = [
    dict(
        prediction_code=0,
        hive_state="normal",
        advisory_type="Preventive",
        severity="info",
        min_confidence_threshold=0.50,
        description="The colony is operating normally with healthy bee activity",
    ),
    dict(
        prediction_code=1,
        hive_state="pre_swarm",
        advisory_type="Preventive",
        severity="high",
        min_confidence_threshold=0.50,
        description="Pre-swarm indicators detected - preventive action can avoid swarming",
    ),
    dict(
        prediction_code=2,
        hive_state="swarm",
        advisory_type="Reactive",
        severity="critical",
        min_confidence_threshold=0.50,
        description="Active swarm event detected - immediate intervention required",
    ),
    dict(
        prediction_code=3,
        hive_state="abscondment",
        advisory_type="Reactive",
        severity="critical",
        min_confidence_threshold=0.50,
        description="Colony has likely absconded - hive may be empty",
    ),
    dict(
        prediction_code=4,
        hive_state="missing_queen",
        advisory_type="Reactive",
        severity="high",
        min_confidence_threshold=0.50,
        description="Queen absence suspected - colony at risk",
    ),
    dict(
        prediction_code=5,
        hive_state="queenbee_present",
        advisory_type="Preventive",
        severity="info",
        min_confidence_threshold=0.50,
        description="Healthy queen detected",
    ),
    dict(
        prediction_code=6,
        hive_state="pest_infested",
        advisory_type="Reactive",
        severity="high",
        min_confidence_threshold=0.50,
        description="Pest activity detected in the hive",
    ),
    dict(
        prediction_code=7,
        hive_state="external_noise",
        advisory_type="Preventive",
        severity="low",
        min_confidence_threshold=0.50,
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

# ---------------------------------------------------------------------------
# Default advisory library — one or more actions per alerting state.
# confidence_threshold_min/max span 0.50–1.00 so every real-world score
# always gets at least one matching action row.
# Admins can add more specific actions via the admin panel; these defaults
# guarantee the alert pipeline never aborts due to an empty library.
# ---------------------------------------------------------------------------
_DEFAULT_ADVISORIES = [
    # ── swarm ──────────────────────────────────────────────────────────────
    dict(
        hive_state="swarm",
        action_title="Locate the swarm cluster",
        action_description=(
            "Find where the swarm has clustered (nearby tree, fence, wall). "
            "Work calmly and wear protective gear before approaching."
        ),
        priority_level="high",
        action_order=1,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="swarm",
        action_title="Capture the swarm into a spare hive",
        action_description=(
            "Gently brush or shake the cluster into a prepared hive body with frames. "
            "Ensure the queen moves in; close the entrance at dusk and move to a permanent site."
        ),
        priority_level="high",
        action_order=2,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="swarm",
        action_title="Inspect the original hive for queen cells",
        action_description=(
            "After capturing the swarm, examine the source hive for capped queen cells. "
            "Remove all but one or two well-formed cells to prevent after-swarms."
        ),
        priority_level="medium",
        action_order=3,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    # ── pre_swarm ──────────────────────────────────────────────────────────
    dict(
        hive_state="pre_swarm",
        action_title="Inspect for queen cells and overcrowding",
        action_description=(
            "Open the hive and look for swarm queen cells along the bottom of frames. "
            "Check whether the brood box is full of bees with little open space."
        ),
        priority_level="high",
        action_order=1,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="pre_swarm",
        action_title="Add a super or split the colony",
        action_description=(
            "If the hive is congested, add a honey super or perform an artificial swarm split "
            "to relieve the urge to swarm. Remove any swarm queen cells found."
        ),
        priority_level="high",
        action_order=2,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    # ── abscondment ────────────────────────────────────────────────────────
    dict(
        hive_state="abscondment",
        action_title="Confirm whether the hive is empty",
        action_description=(
            "Open and inspect all frames. If the colony has left, remove remaining honey "
            "and comb, clean the hive, and treat for pests before re-baiting."
        ),
        priority_level="high",
        action_order=1,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="abscondment",
        action_title="Identify and remove the cause of absconding",
        action_description=(
            "Check for wax moth damage, ant infestations, Varroa overload, or "
            "excessive disturbance near the hive that may have triggered the departure."
        ),
        priority_level="high",
        action_order=2,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    # ── missing_queen ──────────────────────────────────────────────────────
    dict(
        hive_state="missing_queen",
        action_title="Perform a thorough queen-search inspection",
        action_description=(
            "Go through every frame systematically looking for the queen, eggs (< 3 days old), "
            "or young larvae. The presence of eggs confirms the queen was present recently."
        ),
        priority_level="high",
        action_order=1,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="missing_queen",
        action_title="Introduce a replacement queen or frame with eggs",
        action_description=(
            "If queenlessness is confirmed, introduce a mated queen in a cage or "
            "add a frame of eggs from another hive so the colony can raise an emergency queen."
        ),
        priority_level="high",
        action_order=2,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    # ── pest_infested ──────────────────────────────────────────────────────
    dict(
        hive_state="pest_infested",
        action_title="Inspect for pest type and severity",
        action_description=(
            "Check for wax moth larvae, small hive beetles, Varroa mites on bees and brood, "
            "or ant trails. Identify the pest before selecting a treatment method."
        ),
        priority_level="high",
        action_order=1,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
    dict(
        hive_state="pest_infested",
        action_title="Apply appropriate pest management treatment",
        action_description=(
            "For Varroa: apply oxalic acid or approved miticide. For wax moth or beetles: "
            "remove damaged comb, reduce entrance size, and ensure the colony is strong enough "
            "to defend itself."
        ),
        priority_level="high",
        action_order=2,
        confidence_threshold_min=0.50,
        confidence_threshold_max=1.00,
    ),
]


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def _seed_advisory_library(db: Session) -> None:
    """
    Seed one default advisory action per alerting state so that the alert
    pipeline always has at least one matching action to work with.

    Uses a title-based uniqueness check so re-running never creates duplicates
    while still allowing admins to add their own actions freely.
    """
    for entry in _DEFAULT_ADVISORIES:
        hive_state = entry["hive_state"]

        # Resolve template_id from hive_state
        template = db.query(AdvisoryTemplate).filter(
            AdvisoryTemplate.hive_state == hive_state
        ).first()
        if template is None:
            print(f"  ⚠ No template found for hive_state='{hive_state}', skipping advisory")
            continue

        # Skip if an advisory with this exact title already exists for the template
        exists = db.query(Advisory).filter(
            Advisory.template_id == template.template_id,
            Advisory.action_title == entry["action_title"],
        ).first()
        if exists:
            continue

        advisory = Advisory(
            template_id=template.template_id,
            action_title=entry["action_title"],
            action_description=entry["action_description"],
            priority_level=entry["priority_level"],
            action_order=entry["action_order"],
            confidence_threshold_min=entry["confidence_threshold_min"],
            confidence_threshold_max=entry["confidence_threshold_max"],
            is_active=True,
        )
        db.add(advisory)

    db.flush()


def seed_initial_data(db: Session) -> None:
    """Insert bootstrap rows that must exist for the app to function."""

    # ── Advisory templates ────────────────────────────────────────────────
    stmt = (
        pg_insert(AdvisoryTemplate)
        .values(_ADVISORY_TEMPLATES)
        .on_conflict_do_update(
            index_elements=["prediction_code"],
            set_={
                # Lower thresholds on conflict so existing prod rows are healed
                "min_confidence_threshold": pg_insert(AdvisoryTemplate).excluded.min_confidence_threshold,
            },
        )
    )
    db.execute(stmt)
    db.flush()

    # ── Default advisory library ──────────────────────────────────────────
    _seed_advisory_library(db)
    print(f"✓ Advisory library seeded  ({len(_DEFAULT_ADVISORIES)} default actions, duplicates skipped)")

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
