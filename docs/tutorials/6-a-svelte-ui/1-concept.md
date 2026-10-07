---
abstract: |
  Step 1 of tutorial 6: what the dashboard is for. The
  goal, six rules, the page drawn as a wireframe, and
  what the rules will not do.
date: 2026-10-07
keywords:
- tutorial
- ui
- concept
- wireframe
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

## 3 The Wireframe

The concept's artefact: the whole page on a phone, 360
px wide, as someone who is both `member` and `admin`
sees it. A phone first ([the UI's
conduct](../../conduct/ui.md), U1): a wider screen adds
to this, and the margin says where. In the margin, each
part is marked with its rule, and with the permission
that shows it. Take a permission away and its part
goes; nothing else moves.

![The dashboard's wireframe on a phone: who you are,
the profile, the notes and the people in one column,
each part marked with its rule and its
permission](wireframe-dashboard.svg)

And the three pages with less on them:

![Three smaller wireframes, on a phone: D1 signed out,
D2 an unverified e-mail, D3 no
role](wireframe-states.svg)

- **How to read them:** lines and words, no colour. A
  heavy outline is the button a part is for. Grey words
  are not content: a field's placeholder, or a line the
  page says quietly. The words are examples
- **One column, top to bottom:** who you are, your
  profile, the notes, the people. A part you may not
  see is absent, not greyed out. From 768 px wide, the
  profile's two fields and its button share a row;
  nothing else changes
- **Every button and tick is 44 px tall,** a finger's
  width
- **A note says `yours` or `another's`,** never a name
  (§5)
- **The roles are tick boxes,** one a role, for every
  person. Without `users.grant` they show and cannot be
  changed
- **The wireframe fixes what is on the page and in what
  order,** not its spacing, type or colour

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

- **Uploads.** Tutorial 7
- **Show whose a note is.** N3 of tutorial 5: whether,
  never whose
- **Work without JavaScript.** It signs in by PKCE,
  which needs it

## 6 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The UI](../../ui/README.md): what the box asks of
  any UI
