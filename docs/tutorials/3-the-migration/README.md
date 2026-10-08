---
abstract: |
  Tutorials 1 and 2's drafts become migrations, the
  form the box runs. Three files: the people, the
  roles, the first admin. Built in the project's five
  steps, a page each. This page is the way in: what you
  build, and how the steps get you there.
date: 2026-10-07
keywords:
- tutorial
- db
- migration
- dbmate
- cycle
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_begin.sql
- box/render.py
- Makefile
status: draft
subtitle: The drafts, as migrations the box will run
title: 3 Make It a Migration
version: v0.1.0
---

`[OK:NATIVE]` `[OK:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

- **Three migrations** in `migrations/sql/`: the users
  unit's people, from tutorial 1; its roles, from
  tutorial 2; and your project's first admin
- **`box/project.json`,** giving the `users` prefix to
  the service that will serve `/users`
- **`migrations/schema.sql`,** the schema they make,
  written down
- **`test-3.sh`:** eight tests, written before the
  migrations, that they must pass. One of them runs
  tutorial 2's tests on the migrations

At the end the drafts are deleted. From then on the
migrations are the truth, and a change is a new
migration.

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step. Read them in order.

1.  **[The concept](1-concept.md).** What makes a
    migration fit to run on the box, as eight rules
2.  **[The contract](2-contract.md).** What tutorials 4
    to 7 may rely on: the files, their order, every
    function the users unit offers, and the three it
    publishes
3.  **[The tests](3-tests.md).** The rules as eight
    tests in one script. You run it first, and every
    test fails
4.  **[The implementation](4-implementation.md).** The
    prefix, the three migrations, the lint, and the
    schema written down
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong. One refinement made while this tutorial was
    written, shown whole: to tutorial 2's tests

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- `users-draft.sql`, from tutorials
  [1](../1-authentication.md) and
  [2](../2-authorisation/README.md), and `test-2.sql`
- A local stack, up, with the template's own migration
  applied, as `make dev` and
  `tools/native-dev.sh start` do
- The settings of [the tutorials'
  conventions](../README.md) §3 in your shell
- [Write a
  migration](../../migrations/write-a-migration.md) is
  the how-to; these pages follow it

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md): the
  five steps in general
- [The database's conduct](../../conduct/database.md):
  prefixes, accessors, and what a unit may call
- [4 /users](../4-users/README.md): next
