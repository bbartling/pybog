-- PyBOG ORM Unification Upgrade (safe alter-only)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
  -- Add id column if missing
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='sessions') THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_name='sessions' AND column_name='id'
    ) THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN id UUID';
      IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='gen_random_uuid') THEN
        EXECUTE 'UPDATE sessions SET id = gen_random_uuid() WHERE id IS NULL';
      ELSIF EXISTS (SELECT 1 FROM pg_proc WHERE proname='uuid_generate_v4') THEN
        EXECUTE 'UPDATE sessions SET id = uuid_generate_v4() WHERE id IS NULL';
      END IF;
    END IF;

    -- Drop PK if it's on session_id
    IF EXISTS (
      SELECT 1 FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name
      WHERE tc.table_name='sessions' AND tc.constraint_type='PRIMARY KEY' AND kcu.column_name='session_id'
    ) THEN
      EXECUTE (
        SELECT 'ALTER TABLE sessions DROP CONSTRAINT ' || tc.constraint_name
        FROM information_schema.table_constraints tc
        WHERE tc.table_name='sessions' AND tc.constraint_type='PRIMARY KEY'
        LIMIT 1
      );
    END IF;

    -- Ensure PK on id
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.table_constraints tc
      WHERE tc.table_name='sessions' AND tc.constraint_type='PRIMARY KEY'
    ) THEN
      EXECUTE 'ALTER TABLE sessions ADD PRIMARY KEY (id)';
    END IF;

    -- Ensure unique on session_id
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes WHERE tablename='sessions' AND indexname='uq_sessions_session_id'
    ) THEN
      EXECUTE 'CREATE UNIQUE INDEX uq_sessions_session_id ON sessions(session_id)';
    END IF;

    -- Add columns if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='name') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT ''New Session''';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='last_activity') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN last_activity TIMESTAMPTZ DEFAULT NOW()';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='state') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN state VARCHAR(50) DEFAULT ''idle''';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='metadata') THEN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN metadata JSONB DEFAULT ''{}''::jsonb';
    END IF;
  END IF;
END $$;

-- Related indexes/triggers again (idempotent)
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
