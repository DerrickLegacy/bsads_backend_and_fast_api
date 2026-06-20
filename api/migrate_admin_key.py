"""
Migration script to populate admin_keys table with the existing ADMIN_KEY
from the farmer external data source simulation server.

Run this once after creating the admin_keys table:
    python -m api.migrate_admin_key
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from api.database import SessionLocal
from api.models import AdminKey


def migrate_admin_key():
    """Add the existing ADMIN_KEY from simulation server to the database."""
    
    # Load the .env from the simulation server
    simulation_env_path = Path(__file__).parent.parent.parent / "bsads_farmer_external_data_source_simulation" / ".env"
    
    if not simulation_env_path.exists():
        print(f"❌ Simulation .env file not found at: {simulation_env_path}")
        print("Please provide the path to the simulation server .env file or set SIMULATION_ADMIN_KEY environment variable")
        return
    
    # Load environment variables from the simulation server
    load_dotenv(simulation_env_path)
    
    admin_key = os.getenv("ADMIN_KEY")
    
    if not admin_key:
        print("❌ ADMIN_KEY not found in simulation server .env file")
        return
    
    db = SessionLocal()
    try:
        # Check if this key already exists
        existing = db.query(AdminKey).filter(AdminKey.admin_key == admin_key).first()
        
        if existing:
            print(f"✓ Admin key already exists in database:")
            print(f"  - Server Name: {existing.server_name}")
            print(f"  - Admin Key: {existing.admin_key}")
            print(f"  - Active: {existing.is_active}")
            return
        
        # Create new admin key record
        new_key = AdminKey(
            server_name="Farmer Data Source Simulation",
            server_url=None,  # Can be updated later via API
            admin_key=admin_key,
            description="Default admin key for farmer external data source simulation server",
            is_active=True,
            created_by=None  # System migration
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        print("✓ Admin key migrated successfully!")
        print(f"  - Admin Key ID: {new_key.admin_key_id}")
        print(f"  - Server Name: {new_key.server_name}")
        print(f"  - Admin Key: {new_key.admin_key}")
        print(f"  - Created At: {new_key.created_at}")
        print("\n📝 Admins can now access this key via the /admin/keys API endpoint")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error migrating admin key: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🔐 Migrating ADMIN_KEY to database...")
    print("=" * 60)
    migrate_admin_key()
    print("=" * 60)
