---
abstract: |
  Step 1 of tutorial 5: what the notes routes and the
  dashboard are for. The goal, ten rules, and what they
  will not do.
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
title: "5.1 A Svelte UI: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**A page where each person sees what they may do, and
does it.** Tutorial 2 decided who may do what with the
notes; tutorial 4 put `/users` on HTTP. This tutorial
puts the notes on HTTP too, and draws a page over both.

## 2 The Notes, Over HTTP

Tutorial 2's notes accessors, one route each, in
py-api, the notes' owner:

- **N1 A member writes a note, and it is hers**
- **N2 A reader reads every note, and learns only
  whether it is her own,** never whose
- **N3 Only the owner changes or deletes her note,**
  and only while she holds `notes.write`
- **N4 A note is 1 to 10,000 characters,** refused at
  the service, `422`, before the database is asked; the
  table's `CHECK` holds the same line behind it

## 3 The Dashboard

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
as tutorials 2 and 4 tried.

## 4 Two Choices, and Why

- **Svelte, built by Vite.** Small, compiled, no
  framework in the browser to speak of. The starter's
  `ui/` had no build; this one has, and the release
  runs it
- **The configuration read at run time.** `config.js`
  sits beside the page, never bundled: the release
  writes it from the repository's variables, so one
  build serves any zone

## 5 What It Will Not Do

- **Uploads.** Tutorial 6
- **Show whose a note is.** R8 of tutorial 2: whether,
  never whose
- **Work without JavaScript.** It signs in by PKCE,
  which needs it

## 6 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The UI](../../ui/README.md): what the box asks of
  any UI
