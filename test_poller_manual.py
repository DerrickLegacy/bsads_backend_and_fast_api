#!/usr/bin/env python3
"""
Manual test script for conditions poller
Run this to test the poller immediately without waiting for scheduler
"""

import sys
sys.path.insert(0, '.')

from api.conditions_poller import poll_and_process_conditions

print("=" * 60)
print("Testing Conditions Poller Manually")
print("=" * 60)
print()

try:
    poll_and_process_conditions()
    print()
    print("=" * 60)
    print("✓ Poller completed successfully!")
    print("=" * 60)
    print()
    print("Now check the database:")
    print("  PGPASSWORD=bee_user psql -h localhost -U bee_user -d bee_db -c \"SELECT * FROM hive_conditions ORDER BY created_at DESC LIMIT 5;\"")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
