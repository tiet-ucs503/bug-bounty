---
abstract: |
  What the UI is, how it signs a user in and calls the
  services, what its config holds, and what the box
  asks of it.
date: 2026-10-06
keywords:
- ui
- auth
- cognito
kind: explanation
sources:
- ui/app.js
- ui/index.html
- ui/config.example.js
status: draft
subtitle: A single-page app at www, with no build step
title: The UI
version: v0.1.0
---

## 1 What It Is

`ui/`: an `index.html`, an `app.js` and a `config.js`,
served as they are from the `www` bucket at
`https://www.<zone>`. No package and no build: a module
the browser loads. It is a starter, to be replaced by
yours, in any framework that writes a folder of static
files. Once `ui/` has a `package.json`, the release
builds it and syncs `ui/dist/`; [A Svelte
UI](../tutorials/6-a-svelte-ui/README.md) does so.

## 2 Sign-in

The authorisation code with PKCE, through Cognito's
hosted pages, the box's pool:

1.  **Sign in** sends the browser to Cognito with a
    hash of a secret the page keeps in the session's
    storage
2.  Cognito sends it back to the page's root with a
    code
3.  The page trades the code and its secret for tokens,
    and clears the code from the address

The UI's client has no secret of its own; PKCE is what
makes a public client safe. Its callbacks are
`https://www.<zone>/` and the developers'
`ui.dev_callback_urls`.

## 3 Calls

To `https://<service>.<zone>`, the access token as
`Authorization: Bearer`. The box answers CORS for
`www`'s origin alone. The page retries:

- a `429` after its `Retry-After`
- a `502` or `503`, or a lost connection, backing off

A `401` drops the token: the user signs in again.

## 4 Its Config

`ui/config.js`, from `ui/config.example.js`: Cognito's
sign-in domain, the UI's client ID, the zone, and the
services to call. None is a secret. A release writes it
from the repository's variables; git ignores it.
`ui/config.dev.example.js` points the UI at the dev
stack.

## 5 What the Box Asks of It

- **Static files,** with `index.html` at the root
- **Call the APIs,** never the box itself
- **The access token,** not the ID token, as the Bearer
- **Wait on `429`,** and sign in again on `401`
- **A deep link** answers `index.html` with `404` from
  S3; the app loads all the same, and its router takes
  over

## 6 See Also

- [Develop the UI](develop.md)
- [Release the UI](release.md)
