\set ON_ERROR_STOP on
CREATE TABLE person_seed (id integer PRIMARY KEY, name text NOT NULL, nickname text);
INSERT INTO person_seed VALUES
  (1, 'Ada Lovelace', NULL), (2, 'Grace Hopper', 'Amazing Grace'), (3, 'José García', '');
CREATE TABLE existing_sentinel (id integer PRIMARY KEY, note text NOT NULL);
INSERT INTO existing_sentinel VALUES (77, 'keep this value');

-- Test-only delay, configured per connection. The consumer query stays ordinary SQL.
CREATE VIEW person_directory AS
WITH delay AS MATERIALIZED (
  SELECT pg_sleep(COALESCE(current_setting('reader_test.delay_seconds', true), '0')::double precision)
)
SELECT p.* FROM person_seed p CROSS JOIN delay;
