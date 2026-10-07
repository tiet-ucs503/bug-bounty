---
abstract: |
  Step 5 of tutorial 6: run the tests, read what they
  say, and change whichever step is wrong. How to read
  a result, how to try the tests by breaking the
  dashboard on purpose, and what can go wrong.
date: 2026-10-07
keywords:
- tutorial
- ui
- tests
- cycle
kind: how-to
sources:
- ui/app.js
- services/py-api/main.py
status: draft
subtitle: Step 5, run, read, refine
title: "6.5 A Svelte UI: the Refinement"
version: v0.1.0
---

## 1 Run

Expect thirteen lines starting `ok`, then
`13 of 13 pass`:

``` sh
./test-6.sh
```

Its exit status is 0 when all pass, and 3 when any
fails. The dashboard's tests alone, with each one's
failure in full: `cd ui && npm test`.

## 2 Read the Result

- **T6.1 to T6.6 with `404`:** nginx knows no `/notes`:
  the manifest, or nginx not rendered again
- **T6.1 with `403`:** `t5-asha` is no member: the
  grant failed. Run `test-4.sh`; `USERS` may name the
  wrong service
- **T6.5 with `200`:** an edit went through that should
  not: the owner is missing from the accessor's
  `WHERE`, tutorial 2's T2.19
- **`FAIL ui`:** `ui/`'s tests did not run: no
  `ui/package.json`, or `npm install` not run
- **A dashboard test fails:** `cd ui && npm test` names
  what it found instead

## 3 Try the Tests Themselves

Break the dashboard on purpose, so it shows the notes
to everyone. Expect `FAIL` for T6.9, and
`12 of 13 pass`:

``` sh
cp ui/src/App.svelte /tmp/App.svelte
sed -i 's/{#if may("notes.read")}/{#if true}/' ui/src/App.svelte
./test-6.sh
cp /tmp/App.svelte ui/src/App.svelte
```

Only T6.9 catches it: the others give the notes'
permission anyway, or none of the other sections. That
is the reason for T6.9's question, "and nothing else".

## 4 What to Refine

- **A test fails, and the contract is right:** the code
- **A broken dashboard passes every test:** the tests
- **A page shows what the person may not do, and the
  service refuses it:** the dashboard; the database is
  right
- **The dashboard needs an answer the contract lacks:**
  the contract, then the tests, then the code

## 5 What Can Go Wrong

- **A blank page, and
  `Failed to fetch dynamically imported module` for
  `config.js`.** No `ui/public/config.js`: the
  implementation's §6
- **Every call fails with a CORS error.** The page's
  origin is not admitted: `localhost:5173` is the
  manifest's `ui.dev_callback_urls`; the native stack
  admits your `UI_PORT`. Open the page at `localhost`,
  not `127.0.0.1`
- **Signed in, then straight back to "Sign in".** The
  token was refused, `401`: the services restarted and
  the mock made a new key. Sign in again
- **"E-mail not verified".** The address is not
  verified; on the box, ask its owner whether
  `email_verified` is mapped
- **`make check` fails on `ui/`.** It does not look
  there; `npm run build` is CI's check

## 6 See Also

- [7 Uploads](../7-uploads/README.md): next
- [The cycle](../../conduct/the-cycle/README.md) §3:
  what to refine, in general
