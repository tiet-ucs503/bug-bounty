---
abstract: |
  What each person may do, decided in the database: an
  access control matrix of roles and permissions, and
  notes as (u=rw, a=r). Built in the project's five
  steps, a page each: the concept, the tests, the
  contract, the implementation, and the refinement.
  This page is the way in: what you build, and how the
  steps get you there.
date: 2026-10-07
keywords:
- tutorial
- authz
- acm
- db
- cycle
kind: tutorial
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: An access control matrix, in the database
title: "2 What Each May Do: Authorisation"
version: v0.1.0
---

`[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` --- what
these mean, and what they do not: [the tutorials'
page](../README.md) §5.

## 1 What You Build

Three files at your fork's root, carried into tutorial
3's migrations as they are:

- **`users-draft.sql`,** grown from tutorial 1's: the
  roles and who holds them, the matrix, starting roles,
  and the accessors that read and change them
- **`notes-draft.sql`:** notes as (u=rw, a=r), each
  accessor asking the matrix first
- **`test-2.sql`:** 27 tests, written before either,
  that both must pass

At the end, every test passes, in a transaction rolled
back, so your database is as it was.

## 2 Five Steps

This tutorial follows [the project's
cycle](../../conduct/the-cycle/README.md), one page a
step. Read them in order: the contract before the
tests, because the tests call its signatures and expect
its refusals.

1.  **[The concept](1-concept.md).** Who may do what,
    drawn as one table, the matrix, and ten rules read
    from it. Until the contract exists, the concept is
    the source of truth
2.  **[The contract](2-contract.md).** What tutorials 4
    to 7 rely on: each accessor's signature, the
    permission it needs, and how it refuses
3.  **[The tests](3-tests.md).** Each rule asked what
    could go wrong, and the answers fixed as 27 tests,
    held to the contract. You run them first, and every
    one fails
4.  **[The implementation](4-implementation.md).** The
    SQL, a piece at a time, each piece justified by the
    rules and tests it answers
5.  **[The refinement](5-refinement.md).** Run the
    tests, read them, and change whichever step is
    wrong: the code, or the tests, the contract, or the
    concept. One refinement made while this tutorial
    was written, shown whole

The cycle then begins again. Tutorial 7 is such a turn:
it adds `objects.write` to the matrix, and the concept,
contract and tests grow with it.

## 3 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [1 Who is signed in](../1-authentication.md), with
  its `users-draft.sql`
- A local stack, up, with the template's own migration
  applied, as `make dev` and
  `tools/native-dev.sh start` do
- The settings of [the tutorials'
  conventions](../README.md) §3 in your shell

## 4 See Also

- [The cycle](../../conduct/the-cycle/README.md), [the
  concept](../../conduct/the-cycle/concept.md) and [the
  tests](../../conduct/the-cycle/tests.md): the five
  steps in general
- [3 Make it a migration](../3-the-migration.md): next
