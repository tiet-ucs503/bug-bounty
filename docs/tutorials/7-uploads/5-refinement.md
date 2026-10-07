---
abstract: |
  Step 5 of tutorial 7: run the tests, read what they
  say, and change whichever step is wrong. How to read
  a result, how to try the tests by breaking the
  collector on purpose, and a refinement of tutorial
  5's tests made while this tutorial was written.
date: 2026-10-07
keywords:
- tutorial
- uploads
- tests
- cycle
kind: how-to
sources:
- services/py-api/main.py
- ui/src/Notes.svelte
status: draft
subtitle: Step 5, run, read, refine
title: "7.5 Uploads: the Refinement"
version: v0.1.0
---

## 1 Run

With the quick collector of [the
service](4-the-service.md) §5 in `dev/dev.env`. Expect
the two checks of the stack, eighteen lines starting
`ok`, then `18 of 18 pass`:

``` sh
./test-7.sh
```

Its exit status is 0 when all pass, and 3 when any
fails or the stack is not as the box's. Run `test-4.sh`
and `test-6.sh` too: uploads change what `GET /notes`
answers, and a turn that breaks an earlier tutorial's
tests is not done.

## 2 Read the Result

- **The script stops at the store:** the stack's render
  is older than the mock store, or the store is down:
  [the store](4-the-store.md) §7
- **T7.1 to T7.8 with `42883` or `42P01`:** the
  migrations of [the database](4-the-database.md) have
  not run
- **T7.9 to T7.14 with `404`:** nginx knows no
  `/objects` route: the manifest, or nginx not rendered
  again
- **T7.9 with `502`:** the bucket refused the write:
  `STORE_URL`, as the service sees it
- **T7.15 with `200`:** nothing was collected:
  `dev/dev.env` was not read, so the grace is six
  hours. Restart after writing it
- **`FAIL ui`:** `ui/test/attach.test.js` or
  `Attach.svelte` is missing

## 3 Try the Tests Themselves

Break the collector on purpose: take the grace out of
`py_api_objects_to_collect`, in a transaction rolled
back, so an object no note needs is collected at once.
Expect `FAIL` for T7.6 alone, `0 1`, and `7 of 8 pass`:

``` sh
psql "${MIGRATOR_URL}" -X -q -t -A -c BEGIN -c "CREATE OR REPLACE FUNCTION py_api_objects_to_collect(p_grace interval, p_limit int) RETURNS SETOF text
  LANGUAGE sql AS \$\$
  SELECT o.key FROM py_api_objects o
  WHERE NOT EXISTS (SELECT 1 FROM py_api_note_objects l WHERE l.key = o.key)
  ORDER BY o.created_at LIMIT p_limit
  FOR UPDATE SKIP LOCKED
\$\$" -f test-7.sql -c ROLLBACK
```

The rollback takes the broken function with it.

## 4 What to Refine

- **A test fails, and the contract is right:** the
  code, in whichever part the test names
- **A broken part passes every test:** the tests
- **An earlier tutorial's tests fail:** this turn
  changed what they rely on. If the change keeps the
  contract, adding beside it, refine those tests; if it
  breaks the contract, refine the code
- **The box's owner cannot give what §5 of the contract
  asks:** the concept

## 5 A Refinement of Tutorial 6's Tests

Run after this tutorial, tutorial 6's tests failed:
T6.4 and T6.5, a reader's and a member's notes. The
dashboard's notes now show each note's objects, and the
notes in tutorial 6's tests had none to show, not even
an empty list, so the component failed to draw.

The code was right: [the contract](2-contract.md) §2
adds `objects` to every note `GET /notes` answers,
beside what it had. Tutorial 6's tests had faked notes
in the old shape. So the tests were refined, not the
code: each fake note gained `objects: []`, as
`GET /notes` answers it now. The contract grew by
adding beside, and the tests that copy its answers grew
with it.

## 6 What Can Go Wrong

- **`Connection refused` on `STORE_URL`.** The stack's
  render is older than the mock store: `make dev`
  again, or the native stack's `stop` and `start`
- **Rolling back the objects' migration on a stack with
  uploads.** The rows go; the objects stay in the
  store, and nothing will ever collect them. On your
  machine, clear the store: the dev stack's `store`
  volume, or the native stack's
  `dev/out/native/store/`. Never anywhere else
- **`an object that is not yours, or not stored`, for
  your own upload.** The bucket never confirmed it:
  `stored` is `f`. Upload it again
- **`413`, an HTML page.** Over 1 MiB: nginx refuses it
  before py-api sees it

## 7 See Also

- [The tutorials](../README.md): the whole path, and
  where these pages ran
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
