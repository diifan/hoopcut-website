BEGIN;
CREATE SCHEMA IF NOT EXISTS tiktok_publisher;
REVOKE ALL ON SCHEMA tiktok_publisher FROM PUBLIC;
CREATE TABLE IF NOT EXISTS tiktok_publisher.invites(hash text PRIMARY KEY,label text NOT NULL,expires_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS tiktok_publisher.states(hash text PRIMARY KEY,browser_hash text NOT NULL,label text NOT NULL,expires_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS tiktok_publisher.accounts(app_id text NOT NULL,open_id text NOT NULL,label text NOT NULL,credentials text NOT NULL,scopes text NOT NULL,expires_at timestamptz NOT NULL,refresh_expires_at timestamptz NOT NULL,status text NOT NULL,updated_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(app_id,open_id));
REVOKE ALL ON ALL TABLES IN SCHEMA tiktok_publisher FROM PUBLIC;
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
 REVOKE ALL ON SCHEMA tiktok_publisher FROM anon;
 REVOKE ALL ON ALL TABLES IN SCHEMA tiktok_publisher FROM anon;
 END IF;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
 REVOKE ALL ON SCHEMA tiktok_publisher FROM authenticated;
 REVOKE ALL ON ALL TABLES IN SCHEMA tiktok_publisher FROM authenticated;
 END IF;
END $$;
ALTER TABLE tiktok_publisher.invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE tiktok_publisher.states ENABLE ROW LEVEL SECURITY;
ALTER TABLE tiktok_publisher.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tiktok_publisher.accounts ADD COLUMN IF NOT EXISTS refresh_failures integer NOT NULL DEFAULT 0;

GRANT USAGE ON SCHEMA tiktok_publisher TO hoopcut_comments_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tiktok_publisher TO hoopcut_comments_runtime;
DROP POLICY IF EXISTS publisher_runtime ON tiktok_publisher.invites;
CREATE POLICY publisher_runtime ON tiktok_publisher.invites TO hoopcut_comments_runtime USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS publisher_runtime ON tiktok_publisher.states;
CREATE POLICY publisher_runtime ON tiktok_publisher.states TO hoopcut_comments_runtime USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS publisher_runtime ON tiktok_publisher.accounts;
CREATE POLICY publisher_runtime ON tiktok_publisher.accounts TO hoopcut_comments_runtime USING (true) WITH CHECK (true);
COMMIT;
