---
abstract: |
  How to lay down what you mean to build before you
  write a line of it: the goal, the people, the things,
  the rules, what it will not do, and one artefact that
  holds them. The concept is the first step of every
  turn of the cycle, and the source of truth until a
  contract replaces it. With examples from the
  tutorials.
date: 2026-10-07
keywords:
- conduct
- concept
- cycle
kind: explanation
sources:
- docs/tutorials/2-authorisation/1-concept.md
status: draft
subtitle: Before the first line of code
title: The Concept
version: v0.1.0
---

## 1 Why Before the Code

Code answers *how*. Before it can, someone has to say
*what*, and *for whom*, in words the whole team can
check. Written first, the concept is cheap to change: a
sentence crossed out, not a migration rolled back.
Written after, it describes the code, and nobody can
tell what the code was meant to do.

It is step 1 of [the cycle](README.md). The questions
its promises to other people become the contract; the
questions it raises become [the tests](tests.md).

## 2 What a Concept Holds

Six parts, each short. A part you cannot write is a
question to answer before you write code.

- **The goal, in one sentence.** What a person can do
  afterwards that they cannot do now. Tutorial 2's:
  *each person may do what their roles allow, and
  nothing else*
- **The people,** by what they may do, not by name:
  `reader`, `member`, `admin`; and the one nobody
  thinks of, someone signed in who holds no role, and
  may do nothing
- **The things** they act on: notes, objects, roles.
  Each with its owner, if it has one
- **The rules** that join the two: who may do what to
  which. The rules are most of the concept, and every
  rule is a test waiting to be written
- **What it will not do.** Tutorial 2 says it plainly:
  a matrix cannot say no to one person; "everyone but
  bhanu" belongs to a policy engine, and to another
  project
- **One artefact,** below

## 3 One Artefact, the Fallback Truth

Choose the one thing a newcomer could read in a minute
and know what is being built: a table, a diagram, a
list of routes, a header of signatures. It is the
**source of truth until the contract exists**, and
whenever the contract is silent.

- **1 Who is signed in:** the people's record, as the
  sign-in gives it, and the profile the project keeps
- **2 What each may do:** the access control matrix,
  roles by permissions, a cell yes or nothing; and
  notes as (u=rw, a=r)
- **4 /users:** the five routes, each with the
  permission it needs
- **6 A Svelte UI:** the dashboard's three panels: who
  you are, the notes, the people
- **7 Uploads:** the key,
  `objects/<owner's tag>/<the bytes' SHA-256>`, and an
  object's life, drawn

Every concept page carries this note, so nobody takes
the artefact for a promise:

``` markdown
> [!NOTE]
> This concept is subject to refinement during the
> development process. Until the contract exists, and
> wherever it is silent, this page is the source of
> truth.
```

## 4 What a Concept Is Not

Two ways to miss, from either side:

- **Too vague to test.** *"People can manage their
  notes."* Which people? Whose notes? May a reader see
  who wrote one? A sentence that raises no question you
  could answer with yes or no is not a rule yet
- **Already the implementation.** *"A FastAPI router
  with a `users` table and a JWT check."* That is how,
  and it closes doors before anyone has asked whether
  they should be open. Name the language, the table or
  the framework only when the goal depends on it

And the one that costs most:

- **Kept in someone's head.** A concept that is not
  written is a different concept for each person who
  holds it. The pull request is not the place to find
  that out

## 5 What Can Go Wrong

- **The concept grows a section a week.** It is doing
  the contract's work, or several features' at once.
  Split it: one goal a concept
- **Nobody reads it.** It is too long, or the artefact
  is missing. Lead with the artefact
- **The code and the concept disagree.** One is wrong.
  Decide which in [the refinement](README.md), and
  change it; never leave both standing

## 6 See Also

- [The tests](tests.md): the questions a concept raises
- [The cycle](README.md): where the concept sits, and
  when to revisit it
- [2 What each may
  do](../../tutorials/2-authorisation/1-concept.md): a
  concept, written out
