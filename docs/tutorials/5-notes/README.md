---
abstract: |
  Notes, a unit of py-api's own, built on the users
  unit: a migration that makes them and brings their
  two permissions, py-api's routes over them, and a
  page that documents them. The first unit after
  `/users`, and the pattern every later one follows.
  Built in the project's five steps.
date: 2026-10-07
keywords:
- tutorial
- notes
- py-api
- db
- cycle
kind: tutorial
sources:
- services/py-api/main.py
- migrations/sql/20261006120000_py_api_begin.sql
- tools/native-dev.sh
status: draft
subtitle: A unit of its own, on the users unit
title: 5 Notes
version: v0.1.0
---

`[OK:NATIVE]` `[OK:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

- **A migration, `py_api_create_notes`:** the notes'
  table, four accessors that ask `users_may` before
  they act, and the notes' two permissions, brought to
  the matrix by `users_permission_add`
- **py-api's notes routes:** list, add, edit and
  delete, the database deciding
- **`docs/py-api/notes.md`:** the notes as the project
  keeps them, for whoever maintains them next
- **`test-5.sql` and `test-5.sh`:** eighteen tests,
  written before the code: twelve in the database, six
  through nginx

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step. Read them in order.

1.  **[The concept](1-concept.md).** What a note is,
    who may do what with it, as five rules, and the
    matrix's two new columns
2.  **[The contract](2-contract.md).** The migration,
    the accessors, the routes and the manifest's
    entries: what tutorials 6 and 7 rely on
3.  **[The tests](3-tests.md).** The rules as eighteen
    tests. You run them first, and every one fails
4.  **[The implementation](4-implementation.md).** The
    migration, py-api's routes, and the pages that
    document them
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong. Two refinements, shown whole: one to the
    tests, and one to the order of the tutorials

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [3 Make it a
  migration](../3-the-migration/README.md), its
  migrations applied, and [4
  /users](../4-users/README.md), in py-api or js-api,
  running, with `test-4.sh` passing
- The settings of [the tutorials'
  conventions](../README.md) §3 in your shell

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md): the
  five steps in general
- [Bring an existing unit under
  authorisation](../../migrations/bring-under-authorisation.md):
  the same, for a unit that was there before the users
  unit
- [6 A Svelte UI](../6-a-svelte-ui/README.md): next
