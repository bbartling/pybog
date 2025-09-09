-- PyBOG ORM Unification Upgrade
-- Align existing database to SQLAlchemy models while preserving legacy compatibility.

-- 0) UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Sessions table: ensure ORM-friendly primary key and columns
DO $$
BEGIN
  -- Add id column if missing
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='sessions' AND column_name='id'
  ) THEN
    BEGIN
      EXECUTE 'ALTER TABLE sessions ADD COLUMN id UUID';
      -- Fill id for existing rows
      IF EXISTS (SELECT 1 FROM pg_proc WHERE proname='gen_random_uuid') THEN
        EXECUTE 'UPDATE sessions SET id = gen_random_uuid() WHERE id IS NULL';
      ELSIF EXISTS (SELECT 1 FROM pg_proc WHERE proname='uuid_generate_v4') THEN
        EXECUTE 'UPDATE sessions SET id = uuid_generate_v4() WHERE id IS NULL';
      ELSE
        -- fallback: cast md5
        EXECUTE 'UPDATE sessions SET id = (''00000000-0000-4000-8000-'' || right(md5(session_id),12))::uuid WHERE id IS NULL';
      END IF;
    EXCEPTION WHEN undefined_table THEN
      -- Table does not exist; create with full schema
      EXECUTE $$
        CREATE TABLE IF NOT EXISTS sessions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          session_id VARCHAR(255) UNIQUE NOT NULL,
          name VARCHAR(255) NOT NULL DEFAULT 'New Session',
          created_at TIMESTAMPTZ DEFAULT NOW(),
          updated_at TIMESTAMPTZ DEFAULT NOW(),
          last_activity TIMESTAMPTZ DEFAULT NOW(),
          state VARCHAR(50) DEFAULT 'idle',
          metadata JSONB DEFAULT '{}'::jsonb
        );
      $$;
      RETURN;
    END;
  END IF;

  -- Drop existing PK if it's on session_id
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

  -- Add PK on id if not present
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

  -- Add/ensure other columns
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

END$$;

-- 2) Create ORM tables if missing
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  type VARCHAR(50) NOT NULL,
  message_type VARCHAR(50),
  content TEXT NOT NULL,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  filename VARCHAR(255) NOT NULL,
  file_type VARCHAR(100),
  file_size BIGINT,
  storage_path TEXT,
  upload_time TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  analysis_data JSONB NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bog_files (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bog_id VARCHAR(255) UNIQUE NOT NULL,
  session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  message_id VARCHAR(255),
  filename VARCHAR(255) NOT NULL,
  file_path TEXT,
  download_url TEXT,
  content JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

-- 3) Useful indexes
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_files_session_id ON files(session_id);
CREATE INDEX IF NOT EXISTS idx_analysis_session_id ON analysis_results(session_id);
CREATE INDEX IF NOT EXISTS idx_bog_files_session_id ON bog_files(session_id);

-- 4) updated_at triggers
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

DROP TRIGGER IF EXISTS update_analysis_updated_at ON analysis_results;
CREATE TRIGGER update_analysis_updated_at BEFORE UPDATE ON analysis_results
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
