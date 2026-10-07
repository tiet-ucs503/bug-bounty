---
abstract: |
  Step 4 of tutorial 5: what makes the eighteen tests
  pass. The migration that makes the notes and brings
  their permissions; py-api's four routes over its
  accessors; the manifest's entries; and the two pages
  that document them.
date: 2026-10-07
keywords:
- tutorial
- notes
- py-api
- db
- migration
kind: tutorial
sources:
- services/py-api/main.py
- migrations/.squawk.toml
- Makefile
status: draft
subtitle: Step 4, the code
title: "5.4 Notes: the Implementation"
version: v0.1.0
---

## 1 Before You Start

- [The contract](2-contract.md): every file, function
  and route below is one of its entries
- [The tests](3-tests.md), saved as `test-5.sql` and
  `test-5.sh`, run once and failing

The database first, then the service: the routes call
accessors that must exist. Run the tests after any
step, if you like: the count of passes only grows.

## 2 The Migration

py-api's prefix, py-api's file. Expect the new file's
path:

``` sh
make db-new PREFIX=py_api NAME=create_notes
```

Then the whole of it. In the up, in order:

- **The table.** The owner is a `sub`, kept and never
  shown; the `CHECK` holds a body to 1 to 10,000
  characters whoever writes (N5, T5.11). No foreign key
  to `users_people`: that is the users unit's table,
  and no unit touches another's
- **The accessors,** each asking `users_may` first (N2
  to N4, T5.3 to T5.10, T5.12). `py_api_notes_all`
  answers `mine`, a comparison, so the owner never
  leaves the database (N3, T5.6, T5.7). Edit and delete
  match the owner in their `WHERE`; when nothing
  matched, they ask why, so another's note and no note
  answer differently (N4, T5.8, T5.10)
- **The permissions,** last, by the users unit's
  published door, never by its tables (N1, T5.1, T5.2)

The down takes the permissions away first, then drops
what the up made:

``` sql
-- py-api's notes, (u=rw, a=r): everyone with notes.read reads every
-- note; the owner alone changes theirs, and only while they hold
-- notes.write (docs/tutorials/5-notes/). Each accessor takes the caller
-- first and asks users_may before it acts; the permissions are brought
-- by users_permission_add, the users unit's published door.

-- migrate:up
SET lock_timeout = '2s';
SET statement_timeout = '30s';

-- The notes. The owner is a sub, never shown: only whether it is the
-- caller's
CREATE TABLE IF NOT EXISTS py_api_notes (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  owner text NOT NULL,
  body text NOT NULL CHECK (length(body) BETWEEN 1 AND 10000),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz
);
CREATE INDEX IF NOT EXISTS py_api_notes_owner_idx ON py_api_notes (owner, id);

-- A new note, the caller its owner: notes.write
CREATE OR REPLACE FUNCTION py_api_note_new(p_caller text, p_body text) RETURNS bigint
  LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  INSERT INTO py_api_notes (owner, body) VALUES (p_caller, p_body) RETURNING id INTO v_id;
  RETURN v_id;
END
$$;

-- Every note, newest first, a page at a time: notes.read. Not who
-- owns each, only whether the caller does
CREATE OR REPLACE FUNCTION py_api_notes_all(p_caller text, p_before bigint DEFAULT NULL, p_limit int DEFAULT 50)
  RETURNS TABLE (id bigint, body text, mine boolean, created_at timestamptz, updated_at timestamptz)
  LANGUAGE plpgsql STABLE AS $$
#variable_conflict use_column
BEGIN
  IF NOT users_may(p_caller, 'notes.read') THEN
    RAISE EXCEPTION 'notes.read needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN QUERY
    SELECT n.id, n.body, n.owner = p_caller, n.created_at, n.updated_at FROM py_api_notes n
    WHERE p_before IS NULL OR n.id < p_before ORDER BY n.id DESC LIMIT least(p_limit, 200);
END
$$;

-- The owner's change to their note: notes.write, and theirs
CREATE OR REPLACE FUNCTION py_api_note_edit(p_caller text, p_id bigint, p_body text) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  UPDATE py_api_notes SET body = p_body, updated_at = now() WHERE id = p_id AND owner = p_caller;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM py_api_notes WHERE id = p_id) THEN
      RAISE EXCEPTION 'not your note' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RAISE EXCEPTION 'no such note' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;

-- The owner's removal of their note: notes.write, and theirs
CREATE OR REPLACE FUNCTION py_api_note_drop(p_caller text, p_id bigint) RETURNS void
  LANGUAGE plpgsql AS $$
BEGIN
  IF NOT users_may(p_caller, 'notes.write') THEN
    RAISE EXCEPTION 'notes.write needed' USING ERRCODE = 'insufficient_privilege';
  END IF;
  DELETE FROM py_api_notes WHERE id = p_id AND owner = p_caller;
  IF NOT FOUND THEN
    IF EXISTS (SELECT 1 FROM py_api_notes WHERE id = p_id) THEN
      RAISE EXCEPTION 'not your note' USING ERRCODE = 'insufficient_privilege';
    END IF;
    RAISE EXCEPTION 'no such note' USING ERRCODE = 'no_data_found';
  END IF;
END
$$;

-- The notes' two permissions, and the roles that start with them
SELECT users_permission_add('notes.read', 'reads every note', '{reader,member}'),
       users_permission_add('notes.write', 'writes notes, and changes their own', '{member}');

-- migrate:down
SET lock_timeout = '2s';
SET statement_timeout = '30s';
SELECT users_permission_drop('notes.write'), users_permission_drop('notes.read');
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_drop(text, bigint);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_edit(text, bigint, text);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_notes_all(text, bigint, int);
-- squawk-ignore ban-drop-function
DROP FUNCTION IF EXISTS py_api_note_new(text, text);
-- squawk-ignore ban-drop-table
DROP TABLE IF EXISTS py_api_notes;
```

## 3 Lint, and Apply

Expect `Found 0 issues`, then `Applied:` for the notes:

``` sh
make db-lint
make db CMD=up
```

On the native stack, dbmate itself, as the migrator:

``` sh
dbmate --url "${MIGRATOR_URL}" -d migrations/sql --no-dump-schema up
```

Run `test-5.sh` now, if you like: the twelve database
tests pass, and the six through nginx still answer
`404`.

## 4 The Routes, in py-api

The accessors of §2, called by py-api. If you took
Python in tutorial 4, py-api has its database already:
the psycopg lines, the imports and the block below are
there, and only `pydantic`'s import and the routes are
new. If you took JavaScript, add them all now, starting
with the three psycopg lines of [the Python
page](../4-users/4-implementation-python.md) §2 in
`services/py-api/requirements.txt`.

In `services/py-api/main.py`, these imports beside the
starter's:

``` python
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Header, Request
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout
from pydantic import BaseModel, Field
```

The database, as tutorial 4 gives py-api, before the
line that makes `app`; and `app` made with its
`lifespan`, so the pool opens with the service:

``` python
# The project's database, as its app login. Opened without waiting, so
# the service starts, and answers /health, whether or not it is up
pool = ConnectionPool(os.environ.get("DATABASE_URL", ""), min_size=1, max_size=4, open=False,
                      kwargs={"row_factory": dict_row, "autocommit": True})


def query(sql: str, args: tuple = ()) -> list[dict]:
    """One statement, its rows; the tests replace it"""
    with pool.connection(timeout=5) as conn:
        return conn.execute(sql, args).fetchall()


# The database's refusals, by SQLSTATE, as HTTP
STATUS = {"42501": 403, "P0002": 404, "23001": 409, "23514": 400, "22001": 400}
NOSTORE = {"Cache-Control": "no-store"}


def answer(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status, headers=NOSTORE)


def signed_out() -> JSONResponse:
    return JSONResponse({"error": "sign in first"}, 401, headers={**NOSTORE, "WWW-Authenticate": 'Bearer realm="py-api"'})


def run(sql: str, args: tuple) -> JSONResponse | list[dict]:
    """The accessor's rows, times as ISO 8601; or its refusal as an
    answer"""
    try:
        out = query(sql, args)
    except psycopg.Error as e:
        if e.sqlstate in STATUS:
            return answer({"error": e.diag.message_primary or str(e)}, STATUS[e.sqlstate])
        raise
    except PoolTimeout:
        return answer({"error": "the database is not answering"}, 503)
    for r in out:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return out


@asynccontextmanager
async def lifespan(_app):
    if pool.conninfo:
        pool.open(wait=False)
    yield
    pool.close()
```

``` python
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
```

And the routes, at the end. pydantic's `Field` holds a
note's body to 1 to 10,000 characters, and answers
`422` outside that before the database is asked (N5,
T5.18):

``` python
class Note(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


# Sync routes: FastAPI runs each in its thread pool, so the token check
# and the database may block
@app.get("/notes")
def notes(before: int | None = None, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT * FROM py_api_notes_all(%s, %s)", (who["sub"], before))
    return r if isinstance(r, JSONResponse) else answer(r)


@app.post("/notes")
def note_new(note: Note, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT py_api_note_new(%s, %s) AS id", (who["sub"], note.body))
    return r if isinstance(r, JSONResponse) else answer({"id": r[0]["id"]}, 201)


@app.put("/notes/{id}")
def note_edit(id: int, note: Note, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT py_api_note_edit(%s, %s, %s)", (who["sub"], id, note.body))
    return r if isinstance(r, JSONResponse) else answer({"id": id})


@app.delete("/notes/{id}")
def note_drop(id: int, authorization: str | None = Header(default=None)):
    who = caller(authorization)
    if who is None:
        return signed_out()
    r = run("SELECT py_api_note_drop(%s, %s)", (who["sub"], id))
    return r if isinstance(r, JSONResponse) else answer({"id": id})
```

**Its own tests.** The routes, with the database
replaced by the accessors' answers, so no database is
needed. In `services/py-api/test/test_main.py`,
`import psycopg` beside `import jwt`, and after the
last test:

``` python
    # The database replaced by the accessors' answers; a refusal raised
    # as psycopg raises one
    def database(self, sql, args):
        if sql.startswith("SELECT * FROM py_api_notes_all"):
            return [{"id": 1, "body": "hi", "mine": True, "created_at": None, "updated_at": None}]
        if sql.startswith("SELECT py_api_note_edit"):
            raise psycopg.errors.lookup("42501")("not your note")
        if sql.startswith("SELECT py_api_note_drop"):
            raise psycopg.errors.lookup("P0002")("no such note")
        raise AssertionError(sql)

    def bearer(self):
        return {"Authorization": f"Bearer {self.sign(token_use='access', client_id='ui-client')}"}

    def test_notes_by_the_databases_answers(self):
        self.main.query = self.database
        self.assertEqual(self.client.get("/notes").status_code, 401)
        self.assertEqual(self.client.get("/notes", headers=self.bearer()).json()[0]["body"], "hi")
        self.assertEqual(self.client.put("/notes/1", headers=self.bearer(), json={"body": "x"}).status_code, 403)
        self.assertEqual(self.client.delete("/notes/9", headers=self.bearer()).status_code, 404)
        self.assertEqual(self.client.post("/notes", headers=self.bearer(), json={"body": ""}).status_code, 422)
```

Expect `OK`, then restart the stack, `make dev`, or the
native `stop` and `start`:

``` sh
make test
```

## 5 The Manifest's Routes

In `box/project.json`, the four routes of [the
contract](2-contract.md) §5, after the others in
py-api's `routes`. `make check` reads them, and nginx
passes them and nothing else.

## 6 Document Them

In `docs/py-api/api.md`, after the routes already in
§2, the entries from [the contract](2-contract.md) §4,
in the page's own form:

``` markdown
GET /notes
: `notes.read`. `?before=<id>` pages back. `200` and a
  list of `{id, body, mine, created_at, updated_at}`,
  newest first, 50 at most. `403` without it

POST /notes
: `notes.write`. `{body}`, 1 to 10,000 characters.
  `201` and `{id}`. `403` without it; `422` for a body
  out of bounds

PUT /notes/{id}
: `notes.write`, and the note your own. `{body}`, as
  for `POST`. `200` and `{id}`. `403`, `not your note`
  or without it; `404` for no such note; `422`

DELETE /notes/{id}
: As `PUT /notes/{id}`, without a body. `200` and
  `{id}`
```

**A page of their own.** The entries say what each
route does; nothing yet says what a note is, who may do
what with one, or how they change. Save this as
`docs/py-api/notes.md`, and add it to the map in
`docs/README.md`, under py-api:

``` markdown
---
abstract: |
  py-api's notes as the project keeps them: what a note
  is, who may do what with one, the accessors in the
  database and the routes over them, and how they
  change.
date: 2026-10-07
keywords:
- notes
- py-api
- db
kind: reference
sources:
- migrations/sql/20261006130300_py_api_create_notes.sql
- services/py-api/main.py
status: draft
subtitle: What they are, and who may do what
title: py-api's Notes
version: v0.1.0
---

## 1 What a Note Is

A body of 1 to 10,000 characters, its owner's `sub`,
and when it was made and last changed. A unit of
py-api's, every name under `py_api_`, made by the
migration `py_api_create_notes`.

## 2 Who May Do What

(u=rw, a=r): the owner reads and writes; everyone with
`notes.read` reads.

- **`notes.read`,** held by `reader` and `member`:
  every note, and whether each is one's own, never
  whose
- **`notes.write`,** held by `member`: a new note, and
  changes to one's own

The users unit's matrix holds both; its admin changes
who holds them. Changing a note needs the owner and
`notes.write`; another's note is `403`, no note `404`.

## 3 In the Database

Each takes the caller first and asks `users_may` before
it acts:

- `py_api_note_new(caller, body)`
- `py_api_notes_all(caller, before, limit)`
- `py_api_note_edit(caller, id, body)`
- `py_api_note_drop(caller, id)`

None is published; another unit asks py-api, by its
routes.

## 4 Over HTTP

`GET`, `POST`, `PUT` and `DELETE` on `/notes`, as [the
API](api.md) §2 gives them.

## 5 How They Change

By a new migration, beside the old: a released
accessor's signature is a promise ([the
cycle](../conduct/the-cycle/README.md) §2). A new
permission is brought by `users_permission_add`, in the
migration that needs it.
```

Its `sources` name your migration's file: its version
is the one `make db-new` gave it. A later change to the
notes changes this page in the same commit.

## 7 Write the Schema, and Commit

Expect `Writing:`:

``` sh
make db CMD=dump
```

On the native stack,
`dbmate --url "${MIGRATOR_URL}" -d migrations/sql -s migrations/schema.sql dump`.

Run [the tests](3-tests.md) once more; expect
`18 of 18 pass`. Then commit the migration,
`schema.sql`, `box/project.json`, py-api's `main.py`,
the two pages and the two test files together.

## 8 See Also

- [The refinement](5-refinement.md): next
- [Write a
  migration](../../migrations/write-a-migration.md):
  the next change to the notes
