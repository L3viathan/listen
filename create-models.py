import psycopg

with psycopg.connect("dbname=listen user=jo") as conn:
    conn.execute(
        """
        DROP TYPE IF EXISTS itemtype CASCADE;
        CREATE TYPE itemtype AS ENUM ('each', 'once');

        DROP TABLE IF EXISTS runbooks CASCADE;
        CREATE TABLE runbooks (
          id SERIAL PRIMARY KEY,
          name TEXT
        );

        DROP TABLE IF EXISTS sections CASCADE;
        CREATE TABLE sections (
          id SERIAL PRIMARY KEY,
          runbook_id INTEGER REFERENCES runbooks (id) ON DELETE CASCADE,
          name TEXT,
          rank INTEGER  -- at which position in the runbook is it?
        );

        DROP TABLE IF EXISTS items CASCADE;
        CREATE TABLE items (
          id SERIAL PRIMARY KEY,
          section_id INTEGER REFERENCES sections (id) ON DELETE CASCADE,
          name TEXT,
          type itemtype DEFAULT 'once',
          rank INTEGER  -- at which position in the section is it?
        );

        DROP TABLE IF EXISTS runs CASCADE;
        CREATE TABLE runs (
          id SERIAL PRIMARY KEY,
          runbook_id INTEGER REFERENCES runbooks (id) ON DELETE CASCADE,
          name TEXT
        );

        DROP TABLE IF EXISTS targets CASCADE;
        CREATE TABLE targets (
          id SERIAL PRIMARY KEY,
          run_id INTEGER REFERENCES runs (id) ON DELETE CASCADE,
          name VARCHAR(16)
        );

        DROP TABLE IF EXISTS checkmarks CASCADE;
        CREATE TABLE checkmarks (
          id SERIAL PRIMARY KEY,
          run_id INTEGER REFERENCES runs (id) ON DELETE CASCADE,
          item_id INTEGER REFERENCES items (id) ON DELETE CASCADE,
          target_id INTEGER REFERENCES targets (id) ON DELETE CASCADE
        );

        INSERT INTO runbooks (name)
            VALUES ('Packliste');

        INSERT INTO sections (runbook_id, name, rank)
            VALUES (1, 'Section One', 1), (1, 'Section Two', 2);

        INSERT INTO items (section_id, name, rank)
            VALUES (1, 'Item #1', 1), (1, 'Item #2', 2), (2, 'Item #3', 1);

        INSERT INTO runs (runbook_id, name)
            VALUES (1, 'Tirol 2024');
    """
    )
