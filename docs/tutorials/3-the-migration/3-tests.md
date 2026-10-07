---
abstract: |
  Step 3 of tutorial 3: the concept's eight rules as
  eight tests in one script, before any migration. Run
  it now, and every test fails.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- tests
kind: reference
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 3, how we measure it
title: "3.3 Make It a Migration: the Tests"
version: v0.1.0
---

## 1 From the Rules to the Tests

Each rule of [the concept](1-concept.md) §3, held to
[the contract](2-contract.md):

- **T3.1, R1:** does a service own the `users` prefix?
  Expect `yes`
- **T3.2, R3:** applied, how many tables, indexes,
  functions and triggers named `users_`? Expect
  `6 1 10 1`
- **T3.3, R4:** what does `users_may`'s comment begin
  with? Expect `published`
- **T3.4, R5:** a grant for a role that does not exist?
  Expect `23503`, a foreign key's refusal
- **T3.5, R2, R6:** tutorial 2's tests, on the
  migrations? Expect `27 of 27 pass`
- **T3.6, R7:** the first admin signs in for the first
  time: may they grant? Expect `t`
- **T3.7, R8:** the four rolled back: how many `users_`
  names are left, and is the notes' `updated_at`?
  Expect `0 0`
- **T3.8, R8:** applied again: is the schema as it was?
  Expect `same`

## 2 The File

Save it as `test-3.sh` at your fork's root, and make it
runnable, `chmod +x test-3.sh`. It runs dbmate itself
if dbmate is on your `PATH`, as on the native stack,
and `make db` otherwise. Your first admin's address is
`FIRST_ADMIN`, `you@example.org` unless you set it.

> [!CAUTION]
> T3.7 rolls back tutorial 3's four migrations, and
> T3.8 applies them again. The rows go with them: every
> person, role and note on your local stack. It rolls
> back nothing unless the newest four are tutorial 3's.

``` sh
#!/usr/bin/env bash
# Tutorial 3's tests, T3.1 to T3.8: the drafts as migrations, applied,
# rolled back and applied again. Run from your fork's root, against your
# local stack's database, with MIGRATOR_URL set. It rolls back
# tutorial 3's migrations: their rows go with them
set -uo pipefail
FIRST_ADMIN=${FIRST_ADMIN:-you@example.org}
MINE="users_create_people users_create_roles users_first_admin py_api_notes_permissions"

# dbmate on your PATH, as on the native stack; else the dev stack's
db() {
  if command -v dbmate > /dev/null; then
    dbmate --url "${MIGRATOR_URL}" -d migrations/sql --no-dump-schema "$@"
  else
    make -s db CMD="$*"
  fi
}
# Each statement in a transaction rolled back; the last answer, or the
# SQLSTATE of the first refusal
ask() {
  local args=() s
  for s in "$@"; do args+=(-c "$s"); done
  psql "${MIGRATOR_URL}" -X -q -t -A -v ON_ERROR_STOP=1 -v VERBOSITY=sqlstate -c BEGIN "${args[@]}" -c ROLLBACK 2>&1 \
    | sed -n 's/^.*ERROR: *\([0-9A-Z]\{5\}\)$/\1/p; t; $p' | tail -1
}
q() { ask "$1"; }
schema() { pg_dump -s --no-owner --no-privileges "${MIGRATOR_URL}" | grep -v '^\\\|^--\|^$'; }

pass=0; all=0; failed=""
expect() {  # expect ID WANT GOT: one line a test
  all=$((all + 1))
  if [ "$2" = "$3" ]; then pass=$((pass + 1)); echo "ok   $1: want $2, got $3"
  else failed="${failed} $1"; echo "FAIL $1: want $2, got ${3:-nothing}"; fi
}

# The users unit's prefix, given to a service
expect T3.1 yes "$(jq -r '[.services[] | (.prefixes // [.prefix])[]] | if index("users") then "yes" else "no" end' box/project.json)"

# Applied, and everything the unit makes is there: six tables, an index,
# ten functions, a trigger
db up > /dev/null 2>&1
expect T3.2 "6 1 10 1" "$(q "SELECT (SELECT count(*) FROM pg_tables WHERE tablename LIKE 'users\_%') || ' ' ||
  (SELECT count(*) FROM pg_indexes WHERE indexname LIKE 'users\_%\_idx') || ' ' ||
  (SELECT count(*) FROM pg_proc WHERE proname LIKE 'users\_%') || ' ' ||
  (SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'users\_%')")"

# users_may is published, and says so
expect T3.3 published "$(q "SELECT split_part(obj_description('users_may(text, text)'::regprocedure), ':', 1)")"

# The data keeps its rules: no grant for a role that does not exist
expect T3.4 23503 "$(ask "INSERT INTO users_grants VALUES ('nobody', 'notes.read')")"

# Tutorial 2's tests, on the migrations instead of the drafts
expect T3.5 "27 of 27 pass" "$(psql "${MIGRATOR_URL}" -X -q -t -A -c BEGIN -f test-2.sql -c ROLLBACK 2>&1 | grep -o '[0-9]* of [0-9]* pass')"

# The first admin, at their first sign-in, may grant
expect T3.6 t "$(ask "SELECT users_person_see('t3-first', '${FIRST_ADMIN}', true, 'Google')" \
  "SELECT users_may('t3-first', 'users.grant')")"

# Rolled back, newest first, only if the newest four are tutorial 3's:
# nothing of theirs is left, and the notes are as the template made them
newest=$(q "SELECT string_agg(version, ' ' ORDER BY version DESC) FROM (SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 4) v")
names=$(for v in ${newest}; do ls migrations/sql/${v}_*.sql 2> /dev/null | sed 's|.*/[0-9]*_||; s|\.sql$||'; done | tac | paste -sd' ')
before=$(schema)
if [ "${names}" = "${MINE}" ]; then
  for _ in 1 2 3 4; do db rollback > /dev/null 2>&1; done
  expect T3.7 "0 0" "$(q "SELECT (SELECT count(*) FROM pg_class WHERE relname LIKE 'users\_%') + (SELECT count(*) FROM pg_proc WHERE proname LIKE 'users\_%') || ' ' ||
    (SELECT count(*) FROM information_schema.columns WHERE table_name = 'py_api_notes' AND column_name = 'updated_at')")"
  # Applied again: the schema exactly as it was
  db up > /dev/null 2>&1
  expect T3.8 same "$(diff -q <(schema) <(echo "${before}") > /dev/null && echo same || echo different)"
else
  expect T3.7 "${MINE}" "${names}"
  expect T3.8 same "not tried"
fi

echo "${pass} of ${all} pass"
[ -z "${failed}" ] || { echo "failed:${failed}"; exit 3; }
```

## 3 Run It Now

Before any migration exists, with the template's own
applied. Expect `FAIL` on every line: T3.1 `got no`;
T3.2 `got 0 0 0 0`; `42883`, an undefined function, for
T3.3 and T3.6; `42P01`, an undefined table, for T3.4;
T3.5 `got nothing`; T3.7 naming the one migration there
is; and T3.8 `got not tried`. At the end,
`0 of 8 pass`:

``` sh
./test-3.sh
```

## 4 See Also

- [The contract](2-contract.md): the step before
- [The implementation](4-implementation.md): what makes
  these pass
- [The tests](../../conduct/the-cycle/tests.md): the
  questions, in general
