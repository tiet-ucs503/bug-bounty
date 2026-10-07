---
abstract: |
  Step 3 of tutorial 2: the concept's ten rules, each
  asked what could go wrong, and the answers fixed as
  29 tests in one SQL file, before any code. Run it
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
- tools/native-dev.sh
status: draft
subtitle: Step 3, how we measure it
title: "2.3 What Each May Do: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §4, asked the
questions of [the tests'
conduct](../../conduct/the-cycle/tests.md) §2. Three
people: you, the first admin; asha; and bhanu, both
signed in with no role. And one unit, `example`,
standing in for the units to come: the setup adds its
`example.read`, for `reader` and `member`, and its
`example.write`, for `member`, as their migrations
will. Each test calls an accessor as [the
contract](2-contract.md) signs it, and expects its
refusals by the SQLSTATEs the contract names.

  -------------------------------------------------------------
  Rule              Test    Asks                 Expects
  ----------------- ------- -------------------- --------------
  R1 Nothing unless T2.1    bhanu, no role,      `false`
                            reads examples?

                    T2.2    someone never signed `false`
                            in reads examples?

  R2 Each role, its T2.3    bhanu, a `reader`,   `true`
  row                       reads examples?

                    T2.4    bhanu, a `reader`,   `false`
                            writes examples?

                    T2.5    you, an `admin`,     `false`
                            read examples?

                    T2.6    you list the people: `3`
                            how many?

  R3 Roles add up   T2.7    you, `admin` and     `true`
                            `member`, read
                            examples and grant?

  R4 Only           T2.8    bhanu makes himself  `42501`
  `users.grant`             `admin`

                    T2.9    a role given to      `P0002`
                            someone not in

                    T2.10   a role that does not `P0002`
                            exist given

                    T2.11   bhanu given `reader` `1`
                            a second time: how
                            many times does he
                            hold it?

  R5 No lock-out    T2.12   you, the only admin, `23001`
                            take away your own
                            `admin`

                    T2.13   asha made `admin`,   `false`
                            then unmade: may she
                            still grant?

  R2, R6 The        T2.14   bhanu lists the      `42501`
  database decides          people

                    T2.15   bhanu's own roles    `reader` and
                            and permissions      `example.read`

  R7 A unit brings  T2.16   `example.share`      `true`
  its permissions           added for `member`:
                            may asha, a
                            `member`, share?

                    T2.17   added again: how     `1`
                            many cells?

                    T2.18   added for a role     `P0002`
                            that does not exist

                    T2.19   `example.share`      `false`
                            taken away: may asha
                            still share?

                    T2.20   may she still write  `true`
                            examples?

                    T2.21   taken away again     no refusal

                    T2.22   `users.grant` taken  `42501`
                            away

  R8 Three doors    T2.23   which functions say  the three
                            they are published?

  R9                T2.24   a permission named   `23514`
  `<unit>.<verb>`           `Example`

  R10 A starting    T2.25   chitra, at           `true`
  role, by e-mail,          example.org, signs
  once                      in under a rule for
                            it: may she read
                            examples?

                    T2.26   anu, at              `0`
                            elsewhere.net,
                            matching no rule:
                            how many roles?

                    T2.27   a rule for everyone  `0`
                            added, anu signs in
                            again: how many?

  R2, R6 The        T2.28   you read the matrix: `example.read`
  matrix, read              what does `reader`   alone
                            hold?

                    T2.29   bhanu reads the      `42501`
                            matrix

  -------------------------------------------------------------

An SQLSTATE is the refusal [the
contract](2-contract.md) §3 names. Note the pairs that
look alike and must not: T2.19 and T2.20, the
permission taken away against the one kept; T2.12 and
T2.13, the last `users.grant` against any other.

## 2 The File, as a Story

The tests run in order, and each leaves the database as
the next expects it. Read in order, they tell one
story: a project's first days. Each step names the
accessors it calls and the tests that check it.

1.  **Three people sign in,** by tutorial 1's
    `users_person_see`: you, asha and bhanu. You are
    made the first admin by hand. The `example` unit
    arrives with its two permissions, by
    `users_permission_add`. The setup; no test
2.  **Nobody may do anything yet.** `users_may` says
    bhanu may not read examples, nor may someone who
    never signed in. T2.1, T2.2
3.  **You give bhanu a role.** `users_grant` makes him
    a `reader`: he may read examples, but not write
    them. You, an admin, may not read them: your role
    is about people, not examples. `users_list` shows
    you all three people. T2.3 to T2.6
4.  **You make yourself a `member` as well,** by
    `users_grant`, and may now both read examples and
    grant roles. T2.7
5.  **Grants that go wrong.** Bhanu tries
    `users_grant` to make himself `admin`, and is
    refused. You name someone who never signed in, then
    a role that does not exist, and are refused each
    time. You make bhanu a `reader` again, and he holds
    it once. T2.8 to T2.11
6.  **You try to step down.** `users_revoke` refuses to
    take away your own `admin`: nobody else could grant
    roles. You make asha an admin and unmake her, and
    that goes through. T2.12, T2.13
7.  **Bhanu looks around.** `users_list` refuses him;
    `users_me` shows him his own roles and permissions.
    T2.14, T2.15
8.  **The unit grows, then shrinks.** You make asha a
    `member`. The unit adds `example.share` by
    `users_permission_add`, and asha may share; added
    twice, it is there once; added for a role that does
    not exist, it is refused. The unit takes it away by
    `users_permission_drop`: asha may no longer share,
    but may still write. Taken away twice, no refusal;
    `users.grant` cannot be taken away at all. T2.16 to
    T2.22
9.  **Three functions are published** for other units
    to call: `users_may`, `users_permission_add` and
    `users_permission_drop`. T2.23
10. **A badly named permission is refused:** `Example`
    has no unit and no verb. T2.24
11. **Newcomers.** A starting rule gives everyone at
    example.org `reader`. Chitra signs in, by
    `users_person_see`, and may read examples at once.
    Anu, at elsewhere.net, matches no rule and gets no
    role. A rule for everyone is added; anu signs in
    again, and still gets none: a starting role comes
    at the first sign-in alone. T2.25 to T2.27
12. **You read the matrix.** `users_matrix` shows you
    each role and the permissions it holds: `reader`
    holds `example.read` and nothing else. Bhanu asks
    for it too, and is refused, as he was the people.
    T2.28, T2.29

## 3 The File

Save it as `test-2.sql` at your fork's root. One
helper, `expect`, runs each test in a savepoint of its
own, so a failure is recorded and the next test runs;
the file ends by counting, and exits with an error if
any failed.

``` sql
-- Tutorial 2's tests, T2.1 to T2.29: the concept's rules, each with its
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

-- Three people signed in, by tutorial 1; you the first admin, by hand,
-- once there is a table to hold it. An example unit, standing in for
-- the units to come, adds its permissions as their migrations will
SELECT users_person_see('you', 'you@example.org', true, 'Google'), users_person_see('asha', 'asha@example.org', true, 'Google'),
       users_person_see('bhanu', 'bhanu@elsewhere.net', true, 'Google');
DO $$ BEGIN
  INSERT INTO users_members (sub, role) VALUES ('you', 'admin') ON CONFLICT DO NOTHING;
  PERFORM users_permission_add('example.read', 'reads examples', '{reader,member}'),
          users_permission_add('example.write', 'writes examples', '{member}');
EXCEPTION WHEN undefined_table OR undefined_function THEN NULL;
END $$;

-- R1: nothing unless a role says so
SELECT pg_temp.expect('T2.1', NULL, $$SELECT users_may('bhanu', 'example.read')$$, 'false');
SELECT pg_temp.expect('T2.2', NULL, $$SELECT users_may('nobody', 'example.read')$$, 'false');

-- R2: each role's row of the matrix
SELECT pg_temp.expect('T2.3', $$SELECT users_grant('you', 'bhanu', 'reader')$$,
  $$SELECT users_may('bhanu', 'example.read')$$, 'true');
SELECT pg_temp.expect('T2.4', NULL, $$SELECT users_may('bhanu', 'example.write')$$, 'false');
SELECT pg_temp.expect('T2.5', NULL, $$SELECT users_may('you', 'example.read')$$, 'false');
SELECT pg_temp.expect('T2.6', NULL, $$SELECT count(*) FROM users_list('you')$$, '3');

-- R3: roles add up
SELECT pg_temp.expect('T2.7', $$SELECT users_grant('you', 'you', 'member')$$,
  $$SELECT users_may('you', 'example.read') AND users_may('you', 'users.grant')$$, 'true');

-- R4: only users.grant gives a role, to a person and a role that exist
SELECT pg_temp.expect('T2.8', NULL, $$SELECT users_grant('bhanu', 'bhanu', 'admin')$$, '42501');
SELECT pg_temp.expect('T2.9', NULL, $$SELECT users_grant('you', 'nobody', 'reader')$$, 'P0002');
SELECT pg_temp.expect('T2.10', NULL, $$SELECT users_grant('you', 'bhanu', 'owner')$$, 'P0002');
SELECT pg_temp.expect('T2.11', $$SELECT users_grant('you', 'bhanu', 'reader')$$,
  $$SELECT count(*) FROM users_members WHERE sub = 'bhanu' AND role = 'reader'$$, '1');

-- R5: the project cannot lock itself out, and any other revoke goes through
SELECT pg_temp.expect('T2.12', NULL, $$SELECT users_revoke('you', 'you', 'admin')$$, '23001');
SELECT pg_temp.expect('T2.13', $$SELECT users_grant('you', 'asha', 'admin'), users_revoke('you', 'asha', 'admin')$$,
  $$SELECT users_may('asha', 'users.grant')$$, 'false');

-- R2, R6: the people, to users.read alone; the caller's own view
SELECT pg_temp.expect('T2.14', NULL, $$SELECT count(*) FROM users_list('bhanu')$$, '42501');
SELECT pg_temp.expect('T2.15', NULL,
  $$SELECT roles::text || ' ' || permissions::text FROM users_me('bhanu')$$, '{reader} {example.read}');

-- R7: a unit brings its permissions, and takes them away
SELECT pg_temp.expect('T2.16', $$SELECT users_grant('you', 'asha', 'member'),
                                        users_permission_add('example.share', 'shares examples', '{member}')$$,
  $$SELECT users_may('asha', 'example.share')$$, 'true');
SELECT pg_temp.expect('T2.17', $$SELECT users_permission_add('example.share', 'shares examples', '{member}')$$,
  $$SELECT count(*) FROM users_grants WHERE permission = 'example.share'$$, '1');
SELECT pg_temp.expect('T2.18', NULL, $$SELECT users_permission_add('example.lend', 'lends examples', '{owner}')$$, 'P0002');
SELECT pg_temp.expect('T2.19', $$SELECT users_permission_drop('example.share')$$,
  $$SELECT users_may('asha', 'example.share')$$, 'false');
SELECT pg_temp.expect('T2.20', NULL, $$SELECT users_may('asha', 'example.write')$$, 'true');
SELECT pg_temp.expect('T2.21', $$SELECT users_permission_drop('example.share')$$, $$SELECT 'once'$$, 'once');
SELECT pg_temp.expect('T2.22', NULL, $$SELECT users_permission_drop('users.grant')$$, '42501');

-- R8: three published functions, and only three
SELECT pg_temp.expect('T2.23', NULL,
  $$SELECT string_agg(p.proname, ',' ORDER BY p.proname) FROM pg_proc p JOIN pg_description d ON d.objoid = p.oid
    WHERE p.proname LIKE 'users\_%' AND d.description LIKE 'published:%'$$,
  'users_may,users_permission_add,users_permission_drop');

-- R9: a permission is <unit>.<verb>
SELECT pg_temp.expect('T2.24', NULL, $$SELECT users_permission_add('Example', 'no unit', '{member}')$$, '23514');

-- R10: a starting role, by e-mail, at the first sign-in alone
SELECT pg_temp.expect('T2.25', $$INSERT INTO users_starting_roles VALUES (10, '%@example.org', 'reader');
                                 SELECT users_person_see('chitra', 'Chitra@Example.org', true, 'Google')$$,
  $$SELECT users_may('chitra', 'example.read')$$, 'true');
SELECT pg_temp.expect('T2.26', $$SELECT users_person_see('anu', 'anu@elsewhere.net', true, 'Google')$$,
  $$SELECT count(*) FROM users_members WHERE sub = 'anu'$$, '0');
SELECT pg_temp.expect('T2.27', $$INSERT INTO users_starting_roles VALUES (20, '%', 'reader');
                                 SELECT users_person_see('anu', 'anu@elsewhere.net', true, 'Google')$$,
  $$SELECT count(*) FROM users_members WHERE sub = 'anu'$$, '0');

-- R2, R6: the matrix, each role its row, to users.read alone
SELECT pg_temp.expect('T2.28', NULL,
  $$SELECT permissions::text FROM users_matrix('you') WHERE role = 'reader'$$, '{example.read}');
SELECT pg_temp.expect('T2.29', NULL, $$SELECT count(*) FROM users_matrix('bhanu')$$, '42501');

-- How many pass; exit 3 if any fails
SELECT format('%s of %s pass', count(*) FILTER (WHERE ok), count(*)) FROM t2_results;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM t2_results WHERE NOT ok) THEN
    RAISE EXCEPTION 'failed: %', (SELECT string_agg(id, ', ' ORDER BY split_part(id, '.', 2)::int) FROM t2_results WHERE NOT ok);
  END IF;
END $$;
```

## 4 Run It Now

Before any of tutorial 2's code exists, with tutorial
1's draft alone. Expect `t|t|t` for the three people
recorded, then `FAIL` on every line: most with
`got 42883`, an undefined function; T2.23 with
`got nothing`, no published function to find; T2.25 to
T2.27 with `got 42P01`, an undefined table. At the
end, `0 of 29 pass`, and `failed:` with every ID:

``` sh
psql "${MIGRATOR_URL}" -X -q -t -A -v ON_ERROR_STOP=1 -c BEGIN -f users-draft.sql -f test-2.sql -c ROLLBACK
```

A test that passes now tests nothing: it would pass
whatever you wrote next.

## 5 See Also

- [The contract](2-contract.md): the step before,
  whose signatures and refusals these tests call
- [The implementation](4-implementation.md): what makes
  these pass
- [The tests](../../conduct/the-cycle/tests.md): the
  questions, in general
