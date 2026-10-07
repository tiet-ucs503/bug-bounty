---
abstract: |
  Step 1 of tutorial 5: what a note is, and who may do
  what with it, before any code. The notes as a Unix
  mode, (u=rw, a=r); the two columns they add to the
  users unit's matrix; five rules, which the tests take
  up; and what they will not do.
date: 2026-10-07
keywords:
- tutorial
- notes
- authz
- concept
kind: explanation
sources:
- tools/native-dev.sh
status: draft
subtitle: Step 1, the concept
title: "5.1 Notes: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Short notes that the project's people write, and
everyone who may read them reads.** A unit of py-api's
own, under its prefix, `py_api_`. It decides nothing
about people: who someone is, tutorial 1's users unit
records; what their roles allow, tutorial 2's matrix
holds. The notes ask, and decide only whose a note is.

## 2 A Unix Mode

Read the notes as a file's mode, **(u=rw, a=r)**:
**u**, the owner, reads and writes; **a**, all, read.
Two questions, two places to answer them:

- **May this person use notes at all?** The matrix's,
  by the notes' two permissions. "All" is everyone the
  matrix gives `notes.read`; to write needs
  `notes.write`
- **Is this note theirs?** The notes', by the owner
  each note keeps. Changing a note needs the owner
  **and** `notes.write`

## 3 Two Columns in the Matrix

The notes bring their permissions, as [tutorial
2](../2-authorisation/1-concept.md) §3 foresaw, and say
which of the project's roles start with them:

  ------------------------------------------------------------------------
  Role       `users.read`   `users.grant`   `notes.read`   `notes.write`
  ---------- -------------- --------------- -------------- ---------------
  `reader`                                  yes            

  `member`                                  yes            yes

  `admin`    yes            yes                            
  ------------------------------------------------------------------------

**`admin` does not read notes:** running the people and
reading their notes are different trusts. An admin who
should read holds `member` too.

## 4 The Rules

Numbered, so [the tests](3-tests.md) can say which each
one checks:

- **N1 The notes bring their permissions.** Their
  migration adds `notes.read`, for `reader` and
  `member`, and `notes.write`, for `member`; their
  migration's down takes both away
- **N2 A member writes a note, and it is hers.** A
  reader may not write one
- **N3 Everyone with `notes.read` reads every note,**
  and learns whether a note is their own, never whose
  it is
- **N4 Only the owner changes or deletes her note,**
  and only while she holds `notes.write`. Another's
  note is refused for that reason; a note that is not
  there, for that one, so a client can tell them apart
- **N5 A note is 1 to 10,000 characters,** refused at
  the service, `422`, before the database is asked; the
  table's `CHECK` holds the same line behind it

Every accessor takes the caller first and asks
`users_may` before it acts, as tutorial 2's R6 asks of
every unit; and the notes call nothing else of the
users unit (R8).

## 5 What It Will Not Do

- **Show whose a note is.** N3
- **Share a note with one person.** Relations between
  people and things are the policy engine's, [tutorial
  2](../2-authorisation/1-concept.md) §2's third row
- **Hold files.** Tutorial 7 adds them
- **Draw a page.** Tutorial 6's dashboard does

## 6 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The concept](../../conduct/the-cycle/concept.md):
  what a concept holds, in general
