---
abstract: |
  Run the UI on your machine against the dev stack or
  the live services, and change it.
date: 2026-10-06
keywords:
- ui
- local-dev
kind: how-to
sources:
- ui/app.js
- ui/config.dev.example.js
- Makefile
status: draft
title: Develop the UI
version: v0.1.0
---

## 1 Before You Start

- Python 3, for `make ui`'s server
- The dev stack, for local services: [A local stack
  that mirrors the box](../onboarding/local-dev.md); or
  the live services, once the project is rolled out

## 2 Against the Dev Stack

Point the UI at the mock sign-in and the stack's nginx,
then serve it. Expect
`Serving HTTP on 127.0.0.1 port 5173`:

``` sh
cp ui/config.dev.example.js ui/config.js
make ui
```

Open `http://localhost:5173/`. **Sign in** shows the
mock's form: any user, email and groups.

## 3 Against the Live Services

With `ui/config.js` from `ui/config.example.js`, filled
in with what the box's owner gave you.
`http://localhost:5173/` is a callback of the UI's
client and an allowed CORS origin, from
`ui.dev_callback_urls`, so it signs in and calls the
live services.

``` sh
cp ui/config.example.js ui/config.js
make ui
```

## 4 Change It

Edit `ui/`, reload the page. A framework of your own is
welcome: give `ui/` a `package.json` whose `build`
writes `ui/dist/`, and the release builds it; `make ui`
then runs Vite's dev server, its config in
`ui/public/config.js` ([A Svelte
UI](../tutorials/5-a-svelte-ui/README.md)).

## 5 What Can Go Wrong

- **A CORS error on every call.** The page is not on a
  port in `ui.dev_callback_urls`; `make ui` serves 5173
- **The sign-in goes to Cognito, not the mock.**
  `ui/config.js` is the live one; copy the dev example
- **`No ui/config.js`.** Copy one of the examples

## 6 See Also

- [The UI](README.md)
- [Release the UI](release.md)
