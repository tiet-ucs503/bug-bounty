---
abstract: |
  Step 1 of tutorial 3: what makes a migration fit to
  run on the box. The goal, eight rules, why `users` is
  a prefix and not a service, and what this tutorial
  will not do.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- concept
kind: explanation
sources:
- migrations/sql/20261006120000_py_api_begin.sql
- box/render.py
status: draft
subtitle: Step 1, what and why
title: "3.1 Make It a Migration: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Tutorials 1 and 2's drafts, carried as they are into
migrations the box can run, undo and run again.** A
draft is SQL you run by hand. A migration is a file the
box runs once, in order, and records; it can be rolled
back, and the box's owner can read it before it runs.

## 2 Why `users` Is a Prefix, Not a Service

`/users` will be routes of a service you already have:
py-api, for tutorial 4's Python, or js-api, for its
JavaScript. A service of its own would be a host, an
image and a build more, and memory from the box's 1
GiB, for a handful of routes.

So the service that serves `/users` owns two prefixes,
its own and `users`. Its migrations may name both; any
other prefix `make check` refuses.

## 3 The Rules

Numbered, so [the tests](3-tests.md) can say which each
one checks:

- **R1 A unit's names, under a prefix a service owns.**
  Every name the users unit makes starts `users_`, and
  the manifest gives `users` to the service that serves
  it
- **R2 One migration a step of the path, in its
  order.** The people first, as tutorial 1 made them;
  then the roles, which refer to the people; then the
  first admin, a starting role. Authentication and
  authorisation stay in files of their own, as in their
  tutorials
- **R3 Complete.** Everything the drafts made, and
  nothing else: every table, index, function and
  trigger. Nothing it makes is left without a way to
  use it
- **R4 Three functions are published,** and say so:
  `users_may`, `users_permission_add` and
  `users_permission_drop`, the only ones another unit
  may call
- **R5 The data keeps its own rules.** Keys and checks
  hold whoever writes, so no caller has to be careful
- **R6 The migrations are the drafts.** Tutorial 2's
  tests, run on the migrations, pass as they passed on
  the drafts
- **R7 The first admin is a migration of its own:** a
  starting role, `admin`, for one address. It is the
  one place an address is written
- **R8 Every down undoes its up, exactly.** Rolled
  back, the schema is the template's again; applied
  again, it is what it was. A migration that fails part
  way can run again

## 4 What It Will Not Do

- **Change data that is already there.** These
  migrations make new things. A change to a live table
  has its own rules: [write a
  migration](../../migrations/write-a-migration.md)
- **Run on the box.** A release builds the migrations
  image; the box runs it once its PostgreSQL is there
  ([how a release reaches the
  box](../../onboarding/ci-cd.md))
- **Keep the drafts.** Once the migrations pass, the
  drafts are deleted

## 5 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The concept](../../conduct/the-cycle/concept.md):
  what a concept holds, in general
