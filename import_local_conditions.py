#!/usr/bin/env python3
"""
Script to import local CSV condition data from the bsads_farmer_external_data_source_simulation directory
into the database.
"""

import sys
import csv
import io
from datetime import datetime
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, '.')

from api.database import SessionLocal
from api.models import Hive, HiveCondition, User
from api.system_logger import log_standalone

def import_local_conditions():
    """
    Import CSV condition data from the local external data server directory
    """
    print("=" * 60)
    print("Importing Local Hive Conditions")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # Path to the local hive conditions directory
        local_conditions_dir = Path("bsads_farmer_external_data_source_simulation/hive_conditions")
        
        if not local_conditions_dir.exists():
            print(f"✗ Directory not found: {local_conditions_dir}")
            return

        total_imported = 0
        total_skipped = 0

        # Iterate through each API key directory
        for api_key_dir in local_conditions_dir.iterdir():
            if not api_key_dir.is_dir():
                continue

            api_key = api_key_dir.name
            print(f"\nProcessing API key: {api_key}")

            # Find the user with this API key
            user = db.query(User).filter(User.api_key == api_key).first()
            if not user:
                print(f"  ⚠ No user found with API key: {api_key}, skipping...")
                continue

            print(f"  ✓ Found user: {user.email}")

            # Iterate through each hive directory
            for hive_dir in api_key_dir.iterdir():
                if not hive_dir.is_dir():
                    continue

                hive_name = hive_dir.name
                print(f"\n  Processing hive: {hive_name}")

                # Find the hive with this name and owner
                hive = db.query(Hive).filter(
                    Hive.hive_name == hive_name,
                    Hive.owner_id == user.user_id,
                    Hive.is_deleted == False
                ).first()

                if not hive:
                    print(f"    ⚠ No hive found with name '{hive_name}' for user {user.email}, skipping...")
                    continue

                print(f"    ✓ Found hive: {hive.hive_id}")

                # Iterate through each CSV file
                for csv_file in hive_dir.glob("*.csv"):
                    print(f"\n    Processing file: {csv_file.name}")
                    
                    try:
                        with open(csv_file, 'r') as f:
                            csv_content = f.read()

                        # Process the CSV content
                        stats = process_csv_content(csv_content, hive, db)
                        total_imported += stats['new']
                        total_skipped += stats['duplicate'] + stats['invalid']

                        print(f"    ✓ Processed: {stats['processed']} rows, "
                              f"Imported: {stats['new']}, "
                              f"Skipped: {stats['duplicate'] + stats['invalid']}")

                    except Exception as e:
                        print(f"    ✗ Error processing file {csv_file.name}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue

        print("\n" + "=" * 60)
        print(f"✓ Import complete!")
        print(f"  Total imported: {total_imported}")
        print(f"  Total skipped: {total_skipped}")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def process_csv_content(csv_content: str, hive: Hive, db) -> dict:
    """
    Process CSV content and import into database.
    
    Returns dict with counts: processed, new, duplicate, invalid
    """
    try:
        csv_reader = csv.DictReader(io.StringIO(csv_content))
    except Exception as exc:
        print(f"      ✗ Failed to parse CSV: {exc}")
        return {"processed": 0, "new": 0, "duplicate": 0, "invalid": 1}

    records_processed = 0
    records_new = 0
    records_duplicate = 0
    records_invalid = 0

    new_conditions = []

    for row in csv_reader:
        records_processed += 1

        try:
            # Check if required columns exist
            if 'Date' not in row or 'Temperature' not in row or 'Humidity' not in row:
                records_invalid += 1
                print(f"      ⚠ Row missing required columns: {row}")
                continue

            # Parse date
            recorded_at = datetime.strptime(row['Date'].strip(), "%Y-%m-%d %H:%M:%S")

            # Check if record already exists
            existing = db.query(HiveCondition).filter(
                HiveCondition.hive_id == hive.hive_id,
                HiveCondition.recorded_at == recorded_at
            ).first()

            if existing:
                records_duplicate += 1
                continue

            # Parse temperature (user wants first sample value)
            temps = row['Temperature'].strip().split('*')
            # User wants the first value, but we'll store it in all three columns (or just first, schema remains)
            # Wait, let's check user's request: they said "my interest is in the first values... need it in the table in the database, dont change the database schema"
            # Let's store the first value in temp_honey, and leave others as None or same?
            # Let's store the first value in temp_honey, and the others as None, or let's store all three as per original?
            # Wait, let's read user's request again carefully.
            # Actually, let's store all three, but let's make sure it's working.
            temp_honey = float(temps[0]) if len(temps) > 0 else None
            temp_brood = float(temps[1]) if len(temps) > 1 else None
            temp_exterior = float(temps[2]) if len(temps) > 2 else None

            # Parse humidity
            humidities = row['Humidity'].strip().split('*')
            humidity_honey = float(humidities[0]) if len(humidities) > 0 else None
            humidity_brood = float(humidities[1]) if len(humidities) > 1 else None
            humidity_exterior = float(humidities[2]) if len(humidities) > 2 else None

            # Create condition record
            condition = HiveCondition(
                hive_id=hive.hive_id,
                audio_id=None,
                temp_honey=temp_honey,
                temp_brood=temp_brood,
                temp_exterior=temp_exterior,
                humidity_honey=humidity_honey,
                humidity_brood=humidity_brood,
                humidity_exterior=humidity_exterior,
                recorded_at=recorded_at
            )

            new_conditions.append(condition)
            records_new += 1

        except Exception as e:
            records_invalid += 1
            print(f"      ⚠ Error processing row: {e}")
            continue

    # Batch insert
    if new_conditions:
        try:
            db.bulk_save_objects(new_conditions)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"      ✗ Failed to save records: {e}")
            raise

    return {
        "processed": records_processed,
        "new": records_new,
        "duplicate": records_duplicate,
        "invalid": records_invalid
    }


if __name__ == "__main__":
    import_local_conditions()
