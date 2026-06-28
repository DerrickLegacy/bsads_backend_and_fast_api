#!/usr/bin/env python3
"""
Script to set up test farmers and hives for importing local condition data
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, '.')

from api.database import SessionLocal
from api.models import User, Hive
from api.seed import _hash_password

def setup_test_data():
    """
    Set up test farmers and hives based on the local directory structure
    """
    print("=" * 60)
    print("Setting Up Test Data")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # Path to the local hive conditions directory
        local_conditions_dir = Path("bsads_farmer_external_data_source_simulation/hive_conditions")
        
        if not local_conditions_dir.exists():
            print(f"✗ Directory not found: {local_conditions_dir}")
            return

        # Iterate through each API key directory
        for api_key_dir in local_conditions_dir.iterdir():
            if not api_key_dir.is_dir():
                continue

            api_key = api_key_dir.name
            print(f"\nProcessing API key: {api_key}")

            # Check if user already exists
            user = db.query(User).filter(User.api_key == api_key).first()
            
            if not user:
                # Create a test farmer user
                user = User(
                    full_name=f"Test Farmer {api_key[:8]}",
                    email=f"farmer_{api_key[:8]}@test.com",
                    password_hash=_hash_password("Test1234"),
                    role="farmer",
                    server_url="http://localhost:8086",  # Default simulation server URL
                    api_key=api_key
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"  ✓ Created farmer: {user.email}")
            else:
                print(f"  ✓ Farmer already exists: {user.email}")

            # Iterate through each hive directory
            for hive_dir in api_key_dir.iterdir():
                if not hive_dir.is_dir():
                    continue

                hive_name = hive_dir.name
                print(f"\n  Processing hive: {hive_name}")

                # Check if hive already exists
                hive = db.query(Hive).filter(
                    Hive.hive_name == hive_name,
                    Hive.owner_id == user.user_id,
                    Hive.is_deleted == False
                ).first()

                if not hive:
                    # Create a test hive
                    hive = Hive(
                        owner_id=user.user_id,
                        hive_name=hive_name,
                        hive_location=f"Test Location for {hive_name}",
                        hive_type="Langstroth",
                        current_state="normal"
                    )
                    db.add(hive)
                    db.commit()
                    db.refresh(hive)
                    print(f"    ✓ Created hive: {hive.hive_id}")
                else:
                    print(f"    ✓ Hive already exists: {hive.hive_id}")

        print("\n" + "=" * 60)
        print("✓ Test data setup complete!")
        print("=" * 60)
        print("\nNow you can run:")
        print("  python import_local_conditions.py")
        print("\nto import the CSV condition data.")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    setup_test_data()
