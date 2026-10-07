---
abstract: |
  Step 2 of tutorial 6: what the dashboard relies on:
  tutorial 5's notes routes, `/users`, and the keys of
  its `config.js`; and what relies on the dashboard.
date: 2026-10-07
keywords:
- tutorial
- ui
- routes
- contract
kind: reference
sources:
- services/py-api/main.py
- ui/config.example.js
status: draft
subtitle: Step 2, what others may rely on
title: "6.2 A Svelte UI: the Contract"
version: v0.1.0
---

## 1 Who Relies on It

- **Tutorial 7,** uploads, which adds each note's files
  to the dashboard
- **The release,** which builds `ui/` and writes its
  `config.js`

## 2 What the Dashboard Relies On

- **The notes routes,** as [tutorial 5's
  contract](../5-notes/2-contract.md) §4 gives them, at
  py-api
- **`/users`,** as [tutorial 4's
  contract](../4-users/2-contract.md) §2 gives it, at
  the service that serves it
- **`config.js`** at the site's root, a module whose
  default export has:
  - `clientId`: your UI's client in the box's pool
  - `authDomain`: the pool's sign-in domain
  - `zone`: your zone, for `https://<service>.<zone>`
  - `apis`: your services, as the manifest names them
  - `apiUrl`, optional: a function from a service's
    name to its address, for a local stack
  - `staticUrl`, optional: the static bucket's address
- **The release** builds `ui/` when `ui/package.json`
  exists, and syncs `ui/dist/` to `www`

## 3 See Also

- [The tests](3-tests.md): next, held to this page
- [Release the UI](../../ui/release.md): how
  `config.js` is written
