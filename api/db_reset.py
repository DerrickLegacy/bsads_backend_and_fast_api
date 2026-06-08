"""
Database reset utility for development.

This module provides functionality to drop all tables and recreate them
with fresh schema and seed data. USE WITH CAUTION - this deletes all data!

Usage:
    Set RESET_DATABASE=true in .env file to auto-reset on startup
    Or run manually: python -m api.db_reset
"""
import logging
from sqlalchemy import text
from api.database import engine, Base, SessionLocal
from api.seed import seed_initial_data

logger = logging.getLogger("bsads.db_reset")


def reset_database():
    """
    Drop all tables and recreate them with the current schema.
    Then seed initial data.
    
    WARNING: This destroys all existing data!
    """
    logger.warning("=" * 60)
    logger.warning("⚠️  DATABASE RESET INITIATED")
    logger.warning("⚠️  ALL DATA WILL BE DELETED!")
    logger.warning("=" * 60)
    
    try:
        # Drop all tables by dropping them in reverse dependency order
        logger.info("Dropping all tables with CASCADE...")
        with engine.begin() as conn:
            # Drop all tables in the database by querying the schema
            # This query gets all tables and drops them with CASCADE
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            tables = [row[0] for row in result]
            
            for table in tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    logger.info(f"  ✓ Dropped table: {table}")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not drop table {table}: {e}")
            
            # Drop all sequences
            result = conn.execute(text("""
                SELECT sequence_name FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            """))
            sequences = [row[0] for row in result]
            
            for seq in sequences:
                try:
                    conn.execute(text(f"DROP SEQUENCE IF EXISTS {seq} CASCADE"))
                    logger.info(f"  ✓ Dropped sequence: {seq}")
                except Exception as e:
                    logger.warning(f"  ⚠ Could not drop sequence {seq}: {e}")
                    
        logger.info("✓ All tables and sequences dropped")
        
        # Recreate all tables
        logger.info("Creating tables from current models...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ All tables created")
        
        # Seed initial data
        logger.info("Seeding initial data...")
        db = SessionLocal()
        try:
            seed_initial_data(db)
            logger.info("✓ Initial data seeded")
        finally:
            db.close()
        
        logger.warning("=" * 60)
        logger.warning("✓ DATABASE RESET COMPLETE")
        logger.warning("=" * 60)
        
    except Exception as e:
        logger.error(f"✗ Database reset failed: {e}")
        raise


def verify_schema():
    """
    Verify that the database schema matches the current models.
    Returns True if schema is up to date, False otherwise.
    """
    try:
        with engine.connect() as conn:
            # Try a simple query to check if basic tables exist
            result = conn.execute(text("SELECT COUNT(*) FROM advisory_templates"))
            
            # Check if min_confidence_threshold column exists (from restructure migration)
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'advisory_templates' AND column_name = 'min_confidence_threshold'"
            ))
            if not result.fetchone():
                logger.warning("Schema is outdated: min_confidence_threshold column missing")
                return False
                
            return True
    except Exception as e:
        logger.warning(f"Schema verification failed: {e}")
        return False


if __name__ == "__main__":
    # Allow running directly: python -m api.db_reset
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    reset_database()
