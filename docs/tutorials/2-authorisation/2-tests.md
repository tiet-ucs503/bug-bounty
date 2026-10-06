---
abstract: |
  Step 2 of tutorial 2: the concept's nine rules, each
  asked what could go wrong, and the answers fixed as
  24 tests in one SQL file, before any code. Run it
  now, and every test fails; the implementation is
  whatever makes them pass.
date: 2026-10-07
keywords:
- tutorial
- authz
- tests
- db
kind: reference
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 2, how we measure it
title: "2.2 What Each May Do: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §4, asked the
questions of [the tests'
conduct](../../conduct/the-cycle/tests.md) §2. Three
people: you, the first admin; alice; and bob, both in
as `deny-all`.

  -------------------------------------------------------------
  Rule              Test    Asks                 Expects
  ----------------- ------- -------------------- --------------
  R1 Nothing unless T2.1    bob, `deny-all`,     `false`
                            reads notes?

                    T2.2    someone never        `false`
                            admitted reads
                            notes?

  R2 Each role, its T2.3    bob, a `reader`,     `true`
  row                       reads notes?

                    T2.4    bob, a `reader`,     `false`
                            writes notes?

                    T2.5    you, an `admin`,     `false`
                            read notes?

                    T2.6    you list the people: `3`
                            how many?

  R3 Roles add up   T2.7    you, `admin` and     `true`
                            `member`, read notes
                            and grant?

  R4 Only           T2.8    bob makes himself    `42501`
  `users.grant`             `admin`

                    T2.9    a role given to      `P0002`
                            someone not in

                    T2.10   a role that does not `P0002`
                            exist given

                    T2.11   bob given `reader` a `1`
                            second time: how
                            many times does he
                            hold it?

  R5 No lock-out    T2.12   you, the only admin, `23001`
                            take away your own
                            `admin`

                    T2.13   alice made `admin`,  `false`
                            then unmade: may she
                            still grant?

  R2, R6 The        T2.14   bob lists the people `42501`
  database decides

                    T2.15   bob's own roles and  his two, and
                            permissions          `notes.read`

  R7 (u=rw, a=r)    T2.16   bob, a `reader`,     `42501`
                            writes a note

                    T2.17   alice, a `member`,   `true`
                            writes one: is it
                            hers?

                    T2.18   alice edits hers;    `edited`
                            bob reads it

                    T2.19   bob, a `member` now, `42501`
                            edits alice's

                    T2.20   bob deletes alice's  `42501`

                    T2.21   alice edits a note   `P0002`
                            that does not exist

  R8 Whether, never T2.22   bob lists the notes: `false`
  whose                     is alice's marked
                            his?

                    T2.23   the notes' list has  `true`
                            no owner in it

  R9                T2.24   a permission named   `23514`
  `<unit>.<verb>`           `Notes`
  -------------------------------------------------------------

An SQLSTATE is the refusal [the
contract](3-contract.md) §4 names. Note the pairs that
look alike and must not: T2.19 and T2.21, another's
note against no note at all; T2.12 and T2.13, the last
`users.grant` against any other.

## 2 The File

Save it as `test-2.sql` at your fork's root. One
helper, `expect`, runs each test in a savepoint of its
own, so a failure is recorded and the next test runs;
the file ends by counting, and exits with an error if
any failed.

``` sql
-- Tutorial 2's tests, T2.1 to T2.24: the concept's rules, each with its
-- answer fixed. Run in a transaction that is rolled back

-- expect(id, act, ask, want): run act, if any, then ask; pass if ask
-- answers want, or fails with the SQLSTATE want names. Either way act
-- is undone if ask fails, and the next test runs. One line a test
CREATE TEMP TABLE t2_results (id text PRIMARY KEY, ok boolean NOT NULL);
CREATE FUNCTION pg_temp.expect(p_id text, p_act text, p_ask text, p_want text) RETURNS text
  LANGUAGE plpgsql AS $$
DECLARE got text;
BEGIN
  BEGIN
    IF p_act IS NOT NULL THEN EXECUTE p_act; END IF;
    EXECUTE p_ask INTO got;
  EXCEPTION WHEN OTHERS THEN got := SQLSTATE;
  END;
  INSERT INTO t2_results VALUES (p_id, got IS NOT DISTINCT FROM p_want);
  RETURN format('%s %s: want %s, got %s',
    CASE WHEN got IS NOT DISTINCT FROM p_want THEN 'ok  ' ELSE 'FAIL' END, p_id, p_want, coalesce(got, 'nothing'));
END
$$;

-- Three people in, by tutorial 1's rules; you the first admin, by hand
SELECT users_admit('you', 'you@example.org', true), users_admit('alice', 'alice@example.org', true),
       users_admit('bob', 'bob@elsewhere.net', true);
INSERT INTO users_members (sub, role) VALUES ('you', 'admin');

-- R1: nothing unless a role says so
SELECT pg_temp.expect('T2.1', NULL, $$SELECT users_may('bob', 'notes.read')$$, 'false');
SELECT pg_temp.expect('T2.2', NULL, $$SELECT users_may('nobody', 'notes.read')$$, 'false');

-- R2: each role's row of the matrix
SELECT pg_temp.expect('T2.3', $$SELECT users_grant('you', 'bob', 'reader')$$,
  $$SELECT users_may('bob', 'notes.read')$$, 'true');
SELECT pg_temp.expect('T2.4', NULL, $$SELECT users_may('bob', 'notes.write')$$, 'false');
SELECT pg_temp.expect('T2.5', NULL, $$SELECT users_may('you', 'notes.read')$$, 'false');
SELECT pg_temp.expect('T2.6', NULL, $$SELECT count(*) FROM users_list('you')$$, '3');

-- R3: roles add up
SELECT pg_temp.expect('T2.7', $$SELECT users_grant('you', 'you', 'member')$$,
  $$SELECT users_may('you', 'notes.read') AND users_may('you', 'users.grant')$$, 'true');

-- R4: only users.grant gives a role, to a person and a role that exist
SELECT pg_temp.expect('T2.8', NULL, $$SELECT users_grant('bob', 'bob', 'admin')$$, '42501');
SELECT pg_temp.expect('T2.9', NULL, $$SELECT users_grant('you', 'nobody', 'reader')$$, 'P0002');
SELECT pg_temp.expect('T2.10', NULL, $$SELECT users_grant('you', 'bob', 'owner')$$, 'P0002');
SELECT pg_temp.expect('T2.11', $$SELECT users_grant('you', 'bob', 'reader')$$,
  $$SELECT count(*) FROM users_members WHERE sub = 'bob' AND role = 'reader'$$, '1');

-- R5: the project cannot lock itself out, and any other revoke goes through
SELECT pg_temp.expect('T2.12', NULL, $$SELECT users_revoke('you', 'you', 'admin')$$, '23001');
SELECT pg_temp.expect('T2.13', $$SELECT users_grant('you', 'alice', 'admin'), users_revoke('you', 'alice', 'admin')$$,
  $$SELECT users_may('alice', 'users.grant')$$, 'false');

-- R2, R6: the people, to users.read alone; the caller's own view
SELECT pg_temp.expect('T2.14', NULL, $$SELECT count(*) FROM users_list('bob')$$, '42501');
SELECT pg_temp.expect('T2.15', NULL,
  $$SELECT roles::text || ' ' || permissions::text FROM users_me('bob')$$, '{deny-all,reader} {notes.read}');

-- R7: notes, (u=rw, a=r)
SELECT pg_temp.expect('T2.16', NULL, $$SELECT py_api_note_new('bob', 'bob writes')$$, '42501');
SELECT pg_temp.expect('T2.17', $$SELECT users_grant('you', 'alice', 'member'), py_api_note_new('alice', 'a first note')$$,
  $$SELECT mine FROM py_api_notes_all('alice') ORDER BY id DESC LIMIT 1$$, 'true');
SELECT pg_temp.expect('T2.18', $$SELECT py_api_note_edit('alice', (SELECT max(id) FROM py_api_notes), 'edited')$$,
  $$SELECT body FROM py_api_notes_all('bob') ORDER BY id DESC LIMIT 1$$, 'edited');
SELECT pg_temp.expect('T2.19', $$SELECT users_grant('you', 'bob', 'member')$$,
  $$SELECT py_api_note_edit('bob', (SELECT max(id) FROM py_api_notes), 'bob was here')$$, '42501');
SELECT pg_temp.expect('T2.20', NULL,
  $$SELECT py_api_note_drop('bob', (SELECT max(id) FROM py_api_notes))$$, '42501');
SELECT pg_temp.expect('T2.21', NULL, $$SELECT py_api_note_edit('alice', -1, 'none')$$, 'P0002');

-- R8: a reader learns whether a note is theirs, never whose
SELECT pg_temp.expect('T2.22', NULL,
  $$SELECT mine FROM py_api_notes_all('bob') ORDER BY id DESC LIMIT 1$$, 'false');
SELECT pg_temp.expect('T2.23', NULL,
  $$SELECT array_to_string(proargnames, ',') NOT LIKE '%owner%' FROM pg_proc WHERE proname = 'py_api_notes_all'$$, 'true');

-- R9: a permission is <unit>.<verb>
SELECT pg_temp.expect('T2.24', NULL,
  $$INSERT INTO users_grants (role, permission) VALUES ('member', 'Notes') RETURNING role$$, '23514');

-- How many pass; exit 3 if any fails
SELECT format('%s of %s pass', count(*) FILTER (WHERE ok), count(*)) FROM t2_results;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM t2_results WHERE NOT ok) THEN
    RAISE EXCEPTION 'failed: %', (SELECT string_agg(id, ', ' ORDER BY split_part(id, '.', 2)::int) FROM t2_results WHERE NOT ok);
  END IF;
END $$;
```

## 3 Run It Now

Before any of tutorial 2's code exists, with tutorial
1's draft alone. Expect `t|t|t` for the three people
let in, then `FAIL` on every line: most with
`got 42883`, an undefined function; T2.23 with
`got nothing`, no such function to ask about; T2.24
with `got 42P01`, an undefined table. At the end,
`0 of 24 pass`, and `failed:` with every ID:

``` sh
psql "${MIGRATOR_URL}" -X -q -t -A -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f test-2.sql -c ROLLBACK
```

A test that passes now tests nothing: it would pass
whatever you wrote next.

## 4 See Also

- [The contract](3-contract.md): beside this step
- [The implementation](4-implementation.md): what makes
  these pass
- [The tests](../../conduct/the-cycle/tests.md): the questions,
  in general
