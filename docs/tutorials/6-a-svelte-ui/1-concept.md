---
abstract: |
  Step 1 of tutorial 6: what the dashboard is for. The
  goal, six rules, and what they will not do.
date: 2026-10-07
keywords:
- tutorial
- ui
- concept
kind: explanation
sources:
- services/py-api/main.py
- ui/app.js
status: draft
subtitle: Step 1, what and why
title: "6.1 A Svelte UI: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**A page where each person sees what they may do, and
does it.** Tutorial 4 put `/users` on HTTP; tutorial 5
put the notes there too. This tutorial draws a page
over both.

## 2 The Dashboard

What `/users/me` answers decides what the page shows:

- **D1 Signed out:** a button to sign in, and nothing
  asked of any service
- **D2 An unverified e-mail:** told so, by address
- **D3 No role:** told so, and asked to find an admin;
  the profile, and nothing else
- **D4 The notes, to `notes.read`;** an add box to
  `notes.write`; the buttons on one's own notes alone
- **D5 The people, to `users.read`;** their roles
  changed only with `users.grant`
- **D6 The profile:** shown, the display name in the
  header, and saved as typed

**The buttons follow the permissions; the database
decides regardless.** A button hidden is a courtesy.
Whoever calls the API by hand meets the same refusals
as tutorials 4 and 5 tried.

## 3 Two Choices, and Why

- **Svelte, built by Vite.** Small, compiled, no
  framework in the browser to speak of. The starter's
  `ui/` had no build; this one has, and the release
  runs it
- **The configuration read at run time.** `config.js`
  sits beside the page, never bundled: the release
  writes it from the repository's variables, so one
  build serves any zone

## 4 What It Will Not Do

- **Uploads.** Tutorial 7
- **Show whose a note is.** N3 of tutorial 5: whether,
  never whose
- **Work without JavaScript.** It signs in by PKCE,
  which needs it

## 5 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The UI](../../ui/README.md): what the box asks of
  any UI
