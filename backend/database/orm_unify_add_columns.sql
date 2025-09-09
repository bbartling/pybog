-- Add missing non-breaking columns to sessions without modifying PK
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='sessions') THEN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='metadata') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN metadata JSONB DEFAULT ''{}''::jsonb';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='name') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT ''New Session''';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='last_activity') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN last_activity TIMESTAMPTZ DEFAULT NOW()';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='state') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN state VARCHAR(50) DEFAULT ''idle''';
    END IF;
  END IF;
END $$;
