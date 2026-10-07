---
abstract: |
  Step 3 of tutorial 5: the concept's five rules, each
  asked what could go wrong, and the answers fixed as
  eighteen tests before any code: twelve in the
  database, in `test-5.sql`, and six through nginx, in
  `test-5.sh`, which runs both. Run it now, and every
  test fails.
date: 2026-10-07
keywords:
- tutorial
- notes
- tests
kind: reference
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 3, how we measure it
title: "5.3 Notes: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §4, held to
[the contract](2-contract.md). In the database, three
people: you, the first admin; asha, a member; and
bhanu, a reader:

- **T5.1, N1:** bhanu may read notes, and not write
  them? Expect `true`
- **T5.2, N1:** which roles hold `notes.write`? Expect
  `member`
- **T5.3, N2:** bhanu writes a note? Expect `42501`
- **T5.4, N2:** asha writes one: is it hers? Expect
  `true`
- **T5.5, N3:** asha edits hers; bhanu reads it? Expect
  `edited`
- **T5.6, N3:** is asha's note marked bhanu's? Expect
  `false`
- **T5.7, N3:** the notes' list has no owner in it?
  Expect `true`
- **T5.8, N4:** bhanu, a member now, edits asha's?
  Expect `42501`
- **T5.9, N4:** bhanu deletes asha's? Expect `42501`
- **T5.10, N4:** asha edits a note that is not there?
  Expect `P0002`
- **T5.11, N5:** an empty note, past the service?
  Expect `23514`, the table's `CHECK`
- **T5.12, N4:** asha, a member no more, edits her own?
  Expect `42501`

Through nginx, as a UI calls them, with `t5-asha`, a
member, and `t5-bhanu`, a reader and then a member too:

- **T5.13, N2:** `t5-asha` writes a note? Expect `201`
- **T5.14, N2:** is it hers? Expect `200 true`
- **T5.15, N3:** `t5-bhanu` reads it: does he see it,
  as not his? Expect `200 true`
- **T5.16, N2:** `t5-bhanu`, a reader, writes one?
  Expect `403`
- **T5.17, N4:** `t5-bhanu`, a member now, edits hers?
  Expect `403 not your note`
- **T5.18, N5:** an empty note? Expect `422`, from
  py-api, before the database is asked

Note the pairs that look alike and must not: T5.8 and
T5.10, another's note against no note at all; T5.11 and
T5.18, the same empty note refused by the table and by
the service.

## 2 The Database's

Save it as `test-5.sql` at your fork's root. Its
`expect` is tutorial 2's, each test in a savepoint of
its own:

``` sql
-- Tutorial 5's database tests, T5.1 to T5.12: the notes' rules, each with
-- its answer fixed, on the migrations. Run in a transaction that is
-- rolled back

-- expect(id, act, ask, want): as tutorial 2's, one line a test
CREATE TEMP TABLE t5_results (id text PRIMARY KEY, ok boolean NOT NULL);
CREATE FUNCTION pg_temp.expect(p_id text, p_act text, p_ask text, p_want text) RETURNS text
  LANGUAGE plpgsql AS $$
DECLARE got text;
BEGIN
  BEGIN
    IF p_act IS NOT NULL THEN EXECUTE p_act; END IF;
    EXECUTE p_ask INTO got;
  EXCEPTION WHEN OTHERS THEN got := SQLSTATE;
  END;
  INSERT INTO t5_results VALUES (p_id, got IS NOT DISTINCT FROM p_want);
  RETURN format('%s %s: want %s, got %s',
    CASE WHEN got IS NOT DISTINCT FROM p_want THEN 'ok  ' ELSE 'FAIL' END, p_id, p_want, coalesce(got, 'nothing'));
END
$$;

-- Three people signed in: you, the first admin; asha, a member; bhanu,
-- a reader
SELECT users_person_see('you', 'you@example.org', true, 'Google'), users_person_see('asha', 'asha@example.org', true, 'Google'),
       users_person_see('bhanu', 'bhanu@elsewhere.net', true, 'Google');
INSERT INTO users_members (sub, role) VALUES ('you', 'admin') ON CONFLICT DO NOTHING;
SELECT users_grant('you', 'asha', 'member'), users_grant('you', 'bhanu', 'reader');

-- N1: the notes bring their permissions, and the roles that start with them
SELECT pg_temp.expect('T5.1', NULL,
  $$SELECT users_may('bhanu', 'notes.read') AND NOT users_may('bhanu', 'notes.write')$$, 'true');
SELECT pg_temp.expect('T5.2', NULL,
  $$SELECT string_agg(role, ',' ORDER BY role) FROM users_matrix('you') WHERE 'notes.write' = ANY (permissions)$$, 'member');

-- N2: a member writes a note, and it is hers; a reader does not
SELECT pg_temp.expect('T5.3', NULL, $$SELECT py_api_note_new('bhanu', 'bhanu writes')$$, '42501');
SELECT pg_temp.expect('T5.4', $$SELECT py_api_note_new('asha', 'a first note')$$,
  $$SELECT mine FROM py_api_notes_all('asha') ORDER BY id DESC LIMIT 1$$, 'true');

-- N3: everyone with notes.read reads every note, and learns whether, never whose
SELECT pg_temp.expect('T5.5', $$SELECT py_api_note_edit('asha', (SELECT max(id) FROM py_api_notes), 'edited')$$,
  $$SELECT body FROM py_api_notes_all('bhanu') ORDER BY id DESC LIMIT 1$$, 'edited');
SELECT pg_temp.expect('T5.6', NULL,
  $$SELECT mine FROM py_api_notes_all('bhanu') ORDER BY id DESC LIMIT 1$$, 'false');
SELECT pg_temp.expect('T5.7', NULL,
  $$SELECT array_to_string(proargnames, ',') NOT LIKE '%owner%' FROM pg_proc WHERE proname = 'py_api_notes_all'$$, 'true');

-- N4: only the owner changes her note, and only while she holds notes.write
SELECT pg_temp.expect('T5.8', $$SELECT users_grant('you', 'bhanu', 'member')$$,
  $$SELECT py_api_note_edit('bhanu', (SELECT max(id) FROM py_api_notes), 'bhanu was here')$$, '42501');
SELECT pg_temp.expect('T5.9', NULL,
  $$SELECT py_api_note_drop('bhanu', (SELECT max(id) FROM py_api_notes))$$, '42501');
SELECT pg_temp.expect('T5.10', NULL, $$SELECT py_api_note_edit('asha', -1, 'none')$$, 'P0002');

-- N5: 1 to 10,000 characters, held by the table too
SELECT pg_temp.expect('T5.11', NULL, $$SELECT py_api_note_new('asha', '')$$, '23514');

-- N4 again: her own note, once she is a member no more
SELECT pg_temp.expect('T5.12', $$SELECT users_revoke('you', 'asha', 'member')$$,
  $$SELECT py_api_note_edit('asha', (SELECT max(id) FROM py_api_notes), 'mine still?')$$, '42501');

-- How many pass; exit 3 if any fails
SELECT format('%s of %s pass', count(*) FILTER (WHERE ok), count(*)) FROM t5_results;
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM t5_results WHERE NOT ok) THEN
    RAISE EXCEPTION 'failed: %', (SELECT string_agg(id, ', ' ORDER BY split_part(id, '.', 2)::int) FROM t5_results WHERE NOT ok);
  END IF;
END $$;
```

## 3 The Script

Save it as `test-5.sh` at your fork's root, and make it
runnable, `chmod +x test-5.sh`. It runs `test-5.sql`
first, in a transaction rolled back, then calls py-api
through nginx:

``` sh
#!/usr/bin/env bash
# Tutorial 5's tests, T5.1 to T5.18: the database's, by test-5.sql; then
# py-api's notes routes through nginx, as a UI calls them. Run from your
# fork's root, with MIGRATOR_URL, H and MOCK_URL set, and USERS the
# service that serves /users. Its rows are rolled back; it gives t5-asha
# and t5-bhanu roles, and takes them back with the note it adds
set -uo pipefail
USERS=${USERS:-py-api}
FIRST_ADMIN=${FIRST_ADMIN:-you@example.org}

tok() { make -s dev-token MOCK_URL="${MOCK_URL}" "$@"; }
Y=$(tok SUB=you EMAIL="${FIRST_ADMIN}")
A=$(tok SUB=t5-asha)
B=$(tok SUB=t5-bhanu)

# call SERVICE METHOD PATH TOKEN [BODY] [JQ]: the status, and what JQ picks
call() {
  local out code
  out=$(curl -s -w '\n%{http_code}' -X "$2" -H "Authorization: Bearer $4" \
    ${5:+-H 'Content-Type: application/json' -d "$5"} "http://$1.${H}$3")
  code=${out##*$'\n'}
  if [ -n "${6:-}" ]; then echo "${code} $(echo "${out%$'\n'*}" | jq -rc "$6" 2> /dev/null)"; else echo "${code}"; fi
}

pass=0; all=0; failed=""
expect() {
  all=$((all + 1))
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); echo "ok   $1: want $2, got $3"
  else failed="${failed} $1"; echo "FAIL $1: want $2, got ${3:-nothing}"; fi
}

# T5.1 to T5.12: the database, as test-5.sql prints them
while read -r line; do
  all=$((all + 1)); echo "${line}"
  case ${line} in ok*) pass=$((pass + 1)) ;; *) failed="${failed} $(echo "${line}" | cut -d' ' -f2 | tr -d :)" ;; esac
done < <(psql "${MIGRATOR_URL}" -X -q -t -A -c BEGIN -f test-5.sql -c ROLLBACK 2>&1 | grep -E '^(ok|FAIL) ')
[ "${all}" -ge 12 ] || { failed="${failed} sql"; echo "FAIL sql: test-5.sql did not run"; }

# All three seen, you first, so your starting role is given; asha a
# member and bhanu a reader
call "${USERS}" GET /users/me "${Y}" > /dev/null
call "${USERS}" GET /users/me "${A}" > /dev/null
call "${USERS}" GET /users/me "${B}" > /dev/null
call "${USERS}" PUT /users/people/t5-asha/roles/member "${Y}" > /dev/null
call "${USERS}" PUT /users/people/t5-bhanu/roles/reader "${Y}" > /dev/null

# N2: a member writes a note, and it is hers
note=$(call py-api POST /notes "${A}" '{"body": "t5: a first note"}' '.id')
expect T5.13 201 "${note%% *}"
id=${note#* }
expect T5.14 "200 true" "$(call py-api GET /notes "${A}" '' "any(.[]; .id == ${id:-0} and .mine)")"
# N3: a reader reads it, and learns it is not hers
expect T5.15 "200 true" "$(call py-api GET /notes "${B}" '' "any(.[]; .id == ${id:-0} and (.mine | not))")"
expect T5.16 403 "$(call py-api POST /notes "${B}" '{"body": "t5: not mine to write"}')"
# N4: another member may not change it
call "${USERS}" PUT /users/people/t5-bhanu/roles/member "${Y}" > /dev/null
expect T5.17 "403 not your note" "$(call py-api PUT "/notes/${id:-0}" "${B}" '{"body": "t5: bhanu was here"}' '.error')"
# N5: a body of 1 to 10,000 characters, refused at the service
expect T5.18 422 "$(call py-api POST /notes "${A}" '{"body": ""}')"

call py-api DELETE "/notes/${id:-0}" "${A}" > /dev/null
call "${USERS}" DELETE /users/people/t5-asha/roles/member "${Y}" > /dev/null
for r in reader member; do call "${USERS}" DELETE "/users/people/t5-bhanu/roles/${r}" "${Y}" > /dev/null; done

echo "${pass} of ${all} pass"
[ -z "${failed}" ] || { echo "failed:${failed}"; exit 3; }
```

## 4 Run It Now

Before any of tutorial 5's code, with tutorial 3's
migrations applied and nginx knowing no `/notes` route.
Expect `FAIL` on every line: T5.1 `got false`, as no
role holds `notes.read`; T5.2 and T5.7 `got nothing`;
`42883`, an undefined function, or `42P01`, an
undefined table, for the rest of the database's; `404`
for all six through nginx. At the end, `0 of 18 pass`:

``` sh
./test-5.sh
```

A test that passes now tests nothing: it would pass
whatever you wrote next.

## 5 See Also

- [The contract](2-contract.md): the step before, whose
  signatures and refusals these tests call
- [The implementation](4-implementation.md): what makes
  these pass
- [The tests](../../conduct/the-cycle/tests.md): the
  questions, in general
