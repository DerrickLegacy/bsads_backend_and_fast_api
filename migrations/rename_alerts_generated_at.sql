-- Rename legacy column if the DB was created from an older schema
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'alerts' AND column_name = 'generated_at'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'alerts' AND column_name = 'alert_timestamp'
  ) THEN
    ALTER TABLE alerts RENAME COLUMN generated_at TO alert_timestamp;
  END IF;
END $$;
