---
abstract: |
  How a feature is made and rolled out here: in turns,
  each of five steps (concept, tests, contract,
  implementation, refinement), each turn returning to
  the concept and its questions. What the contract is
  for, what a refinement may change, and how a turn
  reaches the box.
date: 2026-10-07
keywords:
- conduct
- cycle
- concept
- tests
- contract
- release
kind: explanation
sources:
- docs/tutorials/2-authorisation/README.md
- .github/workflows/release.yml
status: draft
subtitle: Five steps, in turns
title: The Cycle
version: v0.1.0
---

## 1 Five Steps, in Turns

A feature is not written once. It is written in turns,
each turn small enough to finish, and each ending with
something that runs and is measured.

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  C["1 Concept<br/>what, for whom"]
  T["2 Tests<br/>how we measure it"]
  K["3 Contract<br/>what others may rely on"]
  I["4 Implementation<br/>the code"]
  R["5 Refinement<br/>run, read, change"]
  C --> T
  C --> K
  T --> I
  K --> I
  I --> R
  R -->|"the next turn"| C
  classDef step fill:#fff6eb,stroke:#804900,color:#804900
  class C,T,K,I,R step
```

1.  **[The concept](concept.md):** what you mean to
    build, for whom, and one artefact that holds it
2.  **[The tests](tests.md):** the concept's questions,
    each with its answer fixed, written to fail until
    the work is done
3.  **The contract,** beside the tests: what other
    people may rely on
4.  **The implementation:** the code, each step
    justified by a test or a clause of the contract
5.  **The refinement:** run the tests, read what they
    say, and change whichever step is wrong

Steps 2 and 3 run side by side: both follow from the
concept, and neither waits for the other.

## 2 The Contract

The concept is for the team; the contract is for
everyone else, and for whoever comes after. It says
what the feature promises, **exactly**: the routes and
their answers, the accessors' signatures and their
errors, the shape of a token. Nothing about how.

It is the interchange. With it, the UI's author writes
against `/users/me` before `/users/me` exists, and
another unit calls `users_may` without reading the
users unit's code. They trust the contract, not the
implementation, and the implementation may change
underneath them as long as the contract holds.

So a contract is changed with care:

- **Add beside, never change in place.** Tutorial 2's
  new accessors sit beside the template's
  `py_api_note_add`, whose signature is a promise
  already made
- **One source of truth.** Once the contract exists, it
  outranks the concept wherever both speak; the concept
  stays for what the contract does not say
- **For posterity.** A year from now the contract is
  what someone reads to know what the feature does

## 3 Every Turn Begins Again

The fifth step returns to the first. Each turn, before
any code, read the concept and ask its questions again:
what was learnt last turn may have changed either. The
signs, and which step they point to:

  ----------------------------------------------------
  You see                           Refine
  --------------------------------- ------------------
  A test you cannot write           The concept: a
                                    rule too vague to
                                    test

  A test that passes with no code   The test

  The contract cannot be met, or    The contract, or
  met only by a contortion          the concept behind
                                    it

  The code is awkward where the     The contract
  contract meets it                 

  A user asks for something the     The concept: a
  concept never imagined            missing person or
                                    rule

  Everything passes, and it is      The concept, first
  still wrong                       
  ----------------------------------------------------

**Refinement is not only of the code.** The concept,
the tests and the contract are drafts too, until a turn
ends with nothing to change in any of them.

## 4 A Turn's Size

Small enough to finish in a few days, and to review in
one sitting. A turn that touches the concept, the
contract and three layers of code is several turns.
Tutorial 7 is one feature in four turns: the store, the
database, the service, the UI, each finished and tried
before the next.

## 5 Rolling It Out

A turn ends where its tests pass; a feature reaches the
box only when every turn's tests pass and the contract
is settled:

1.  **On your machine,** the dev stack: every test, at
    every layer
2.  **In review,** [the workflow](../workflow.md): the
    contract read by someone who will rely on it
3.  **A release:** git-flow's release puts a tag such
    as `v0.2.0` on `master`, and the release's CI
    builds it and hands it to the box. Nothing reaches
    the box any other way

A contract already released is a promise to people you
may not know. The next turn adds beside it.

## 6 See Also

- [The concept](concept.md) and [the tests](tests.md):
  steps 1 and 2
- [From an issue to a merge](../workflow.md): the cycle
  in git
- [2 What each may
  do](../../tutorials/2-authorisation/README.md): the
  five steps, in a tutorial
