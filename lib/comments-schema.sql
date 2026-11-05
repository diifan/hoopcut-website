CREATE TABLE IF NOT EXISTS hc_comments (
 id uuid PRIMARY KEY, video_id text NOT NULL, parent_id uuid REFERENCES hc_comments(id),
 author_hash text NOT NULL, body text NOT NULL CHECK(char_length(body)<=2000),
 created_at timestamptz(3) NOT NULL DEFAULT now(), deleted_at timestamptz,
 request_id uuid NOT NULL, UNIQUE(author_hash,request_id)
);
CREATE INDEX IF NOT EXISTS hc_comments_video_time ON hc_comments(video_id,parent_id,created_at,id);
CREATE TABLE IF NOT EXISTS hc_comment_rates (
 bucket text NOT NULL, window_start bigint NOT NULL, count integer NOT NULL,
 PRIMARY KEY(bucket,window_start)
);
CREATE TABLE IF NOT EXISTS hc_comment_reports (
 comment_id uuid REFERENCES hc_comments(id), reporter_hash text NOT NULL,
 reason text NOT NULL, created_at timestamptz(3) NOT NULL DEFAULT now(),
 PRIMARY KEY(comment_id,reporter_hash)
);
CREATE TABLE IF NOT EXISTS hc_comment_actions (
 id bigserial PRIMARY KEY, comment_id uuid NOT NULL, action text NOT NULL,
 created_at timestamptz(3) NOT NULL DEFAULT now()
);

ALTER TABLE hc_comments ALTER COLUMN created_at TYPE timestamptz(3);
