---
abstract: |
  The cycle in git: an issue that states the concept, a
  feature branch that carries the turns, a merge
  request where the contract is read, and a merge that
  waits on the tests. Then a release. What each holds,
  and in what order.
date: 2026-10-07
keywords:
- conduct
- workflow
- git
- cycle
- release
kind: explanation
sources:
- .github/workflows/ci.yml
- .github/workflows/release.yml
status: draft
subtitle: The cycle, in git
title: From an Issue to a Merge
version: v0.1.0
---

## 1 The Shape

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  I["An issue<br/>the concept, its questions"]
  B["feature/12-uploads<br/>from develop"]
  M["A merge request<br/>the contract, read"]
  D["develop"]
  R["release/v0.2.0<br/>then master, tagged"]
  I -->|"git flow feature start"| B
  B -->|"tests pass"| M
  M -->|"git flow feature finish"| D
  D -->|"git flow release"| R
  classDef step fill:#fff6eb,stroke:#804900,color:#804900
  class I,B,M,D,R step
```

Each piece holds one step of [the
cycle](the-cycle/README.md) or carries it.

## 2 The Issue: the Concept

An issue opens a feature, and holds [its
concept](the-cycle/concept.md) as it stands: the goal
in a sentence, the people, the rules, what it will not
do, and the artefact. Then the questions still open.

Write it before the branch. A feature without an issue
is a feature whose concept nobody else has read.
Discussion on the issue refines the concept; when it
settles, the concept moves into the repository with the
first commit, and the issue links to it.

## 3 The Branch: the Turns

One branch a feature, from `develop`, named for its
issue:

``` sh
git flow feature start 12-uploads
```

Its commits, in the cycle's order:

1.  **The concept,** as a page, or the issue's text
    moved into one
2.  **The tests and the contract,** together or one
    after the other: the tests fail, and say so
3.  **The implementation,** a commit a step, each
    passing more tests than the last
4.  **The refinements,** each saying which step it
    refines: the concept, a test, the contract, or the
    code

A turn may end mid-branch; push it, so the work is
seen. CI runs `make check` and `make test` on every
push to every branch.

## 4 The Merge Request: the Contract, Read

Opened once the tests pass, and read by someone who
will rely on the contract: the UI's author for a
service's routes, another unit's author for an
accessor. They check:

- **The contract** says what they need, and nothing
  that ties the implementation's hands
- **The tests** follow from the concept, and every rule
  has one
- **The implementation** keeps the [database's
  conduct](database.md) and [the
  philosophy](philosophy.md)

A request that changes a released contract in place is
refused: add beside it ([the
cycle](the-cycle/README.md) §2).

## 5 The Merge, and the Release

When the request is approved and CI passes:

``` sh
git flow feature finish 12-uploads
```

The feature joins `develop`, its commits kept, and the
issue closes with a link to the merge. Features gather
on `develop` until a release:

``` sh
git flow release start v0.2.0
git flow release finish v0.2.0
```

The finish merges into `master` and tags `v0.2.0`. The
tag starts the release's CI, which builds every unit
and hands the release to the box.

## 6 What Can Go Wrong

- **A branch that lives for weeks.** Its turns were too
  big, or it holds several features. Merge what is
  finished; start the rest afresh from `develop`
- **A merge request nobody can review in one sitting.**
  The same cause. Split it by turns
- **The issue and the concept page disagree.** The page
  wins once it exists; say so on the issue, and stop
  editing the issue's concept

## 7 See Also

- [Git and git-flow](git.md): the branches, commits and
  identity
- [The cycle](the-cycle/README.md)
