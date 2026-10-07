---
abstract: |
  Step 5 of tutorial 4: run the tests against your
  service, read what they say, and change whichever
  step is wrong. How to read a result, how to try the
  tests by breaking the service on purpose, and what
  can go wrong.
date: 2026-10-07
keywords:
- tutorial
- api
- tests
- cycle
kind: how-to
sources:
- services/py-api/main.py
- services/js-api/server.js
status: draft
subtitle: Step 5, run, read, refine
title: "4.5 /users: the Refinement"
version: v0.1.0
---

## 1 Run

Expect fourteen lines starting `ok`, then
`14 of 14 pass`; for js-api, `SERVICE=js-api` first:

``` sh
./test-4.sh
```

Its exit status is 0 when all pass, and 3 when any
fails. It may run again at once: it takes back the role
it gives.

## 2 Read the Result

The status a test got says where to look:

- **`404` where the contract says otherwise:** nginx
  does not know the route. The manifest does not name
  it for the service in `SERVICE`, or nginx was not
  rendered again: `make dev`, or the native stack's
  `start`
- **`401` where you expected an answer:** the token.
  The service's `COGNITO_ISSUER` or client IDs are not
  the mock's
- **`403` for everyone at T4.4:**
  `COGNITO_USERINFO_URL` is unset, so the service
  learns no e-mail, and records no one
- **`500`:** the service failed. Its log, in
  `dev/out/native/<service>.log` or `make dev`'s
  output, names the line
- **`503`:** the database or `userInfo` did not answer
  within five seconds
- **A `200` with the wrong value:** the answer's shape
  is not the contract's; compare the two

**Read the first failure first.** T4.4 records
`t4-asha`; if it failed, the tests after it that ask
about her fail for its sake.

## 3 Try the Tests Themselves

Break the service on purpose and check that a test
fails. Here, in py-api, take `42501` out of `STATUS`,
so a refusal for want of a permission is no longer
`403`. Restart, and expect `FAIL` for T4.6 and T4.10,
and `12 of 14 pass`:

``` sh
cp services/py-api/main.py /tmp/main.py
sed -i 's/STATUS = {"42501": 403, /STATUS = {/' services/py-api/main.py
```

Then put it back, and restart again:

``` sh
cp /tmp/main.py services/py-api/main.py
```

Restart as the implementation page's §5 says:
`make dev`, or the native stack's `stop` and `start`.

## 4 What to Refine

- **A test fails, and the contract is right:** the code
- **A broken service passes every test:** the tests
- **Both languages fail the same test the same way:**
  more likely the contract or the test than the code
- **The UI needs an answer the contract lacks:** the
  contract, then the tests, then the code, in both
  languages if both are in use

## 5 What Can Go Wrong

- **`503`, `the database is not answering`.** The pool
  could not connect within five seconds:
  `DATABASE_URL`, or the database is down
- **`500`, and
  `function users_person_see(...) does not exist` in
  the log.** The migrations have not run:
  `make db CMD=status`
- **`make check` refuses a `users_` migration.**
  `users` is not among the service's `prefixes`:
  tutorial 3
- **`403` from nginx, an HTML page, not JSON.** A
  method the manifest does not name for that path
- **js-api:
  `package-lock.json differs from package.json for pg`.**
  `pg` was added by hand; run the JavaScript page's §2
- **js-api: the starter's routes answer `no-store`, or
  its errors as the database's.** A hook or the error
  handler was set on `app`, not inside the plugin

## 6 See Also

- [5 A Svelte UI](../5-a-svelte-ui/README.md): next
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
