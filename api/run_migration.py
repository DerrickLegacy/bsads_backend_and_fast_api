"""
Run SQL migrations on the database.

Usage:
    python -m api.run_migration
"""

from pathlib import Path
from api.database import engine
from sqlalchemy import text


def run_migrations():
    """Run all SQL migration files in the migrations directory."""
    
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        print("❌ Migrations directory not found")
        return
    
    # Get all .sql files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("✓ No migration files found")
        return
    
    print(f"Found {len(migration_files)} migration file(s)")
    print("=" * 60)
    
    with engine.connect() as conn:
        for migration_file in migration_files:
            print(f"\n📝 Running: {migration_file.name}")
            
            try:
                # Read the migration SQL
                sql = migration_file.read_text()
                
                # Execute the migration
                conn.execute(text(sql))
                conn.commit()
                
                print(f"✓ {migration_file.name} completed successfully")
                
            except Exception as e:
                print(f"❌ Error running {migration_file.name}: {e}")
                conn.rollback()
                raise
    
    print("\n" + "=" * 60)
    print("✓ All migrations completed successfully!")


if __name__ == "__main__":
    print("🔄 Running database migrations...")
    print("=" * 60)
    run_migrations()
