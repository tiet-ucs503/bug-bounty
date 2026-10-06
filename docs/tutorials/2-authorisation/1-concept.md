---
abstract: |
  Step 1 of tutorial 2: what each person may do, before
  any code. Three sizes of rule and the one this
  builds; the access control matrix, the artefact that
  holds the concept; nine rules read from it, which the
  tests take up; and what it will not do.
date: 2026-10-07
keywords:
- tutorial
- authz
- acm
- concept
kind: explanation
sources:
- migrations/sql/20261006120000_py_api_create_notes.sql
status: draft
subtitle: Step 1, the concept
title: "2.1 What Each May Do: the Concept"
version: v0.1.0
---

> [!NOTE]
> This concept is subject to refinement during the
> development process. Until [the
> contract](3-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Each person may do what their roles allow, and
nothing else; the database decides.** Tutorial 1 let
people in. This decides what they may do once in.

## 2 Three Sizes of Rule

  ----------------------------------------------------
  Size           What decides       Where
  -------------- ------------------ ------------------
  **Trivial**    Signed in or not;  The manifest's
                 the owner or not   `signed_in`;
                                    `owner = caller`
                                    in an accessor

  **Low          A role's           An access control
  complexity,    permissions: the   matrix in the
  the general    access control     database: this
  case**         matrix, plus the   tutorial
                 trivial rules      
                 where an object    
                 has an owner       

  **Medium to    Relations between  A policy engine:
  high**         people and         §5
                 objects, groups of 
                 groups, sharing,   
                 delegation,        
                 attributes, time   
  ----------------------------------------------------

Most small projects never need the third. Start with
the second; move when you find yourself writing a role
per object, or a role per pair of people.

## 3 The Matrix

The concept's artefact. Rows are roles; columns are
permissions; a cell says yes or nothing. A permission
is `<unit>.<verb>`, named for the unit that asks for
it:

  --------------------------------------------------------------------------
  Role         `notes.read`   `notes.write`   `users.read`   `users.grant`
  ------------ -------------- --------------- -------------- ---------------
  `deny-all`                                                 

  `reader`     yes                                           

  `member`     yes            yes                            

  `admin`                                     yes            yes
  --------------------------------------------------------------------------

And the notes, read as a Unix mode, **(u=rw, a=r)**:
**u**, the owner, reads and writes; **a**, all, read.
"All" is everyone the matrix gives `notes.read`;
"writes" needs the owner **and** `notes.write`. The
matrix says who may use notes at all; the owner's
column says whose note it is.

## 4 The Rules

Read from the matrix, and numbered, so [the
tests](2-tests.md) can say which each one checks:

- **R1 Nothing unless a role says so.** No cell says
  no; `deny-all` is the row with nothing in it, and
  someone never admitted holds no role at all
- **R2 Each role, its row.** `reader` reads notes;
  `member` reads and writes them; `admin` reads the
  people and the matrix, and grants. **`admin` does not
  read notes:** running the people and reading their
  notes are different trusts. An admin who should read
  notes holds `member` too
- **R3 Roles add up.** A person may hold several, and
  may do what any of them may
- **R4 Only `users.grant` gives or takes a role,** and
  only a role that exists, to a person who is in
- **R5 The project cannot lock itself out.** The last
  `users.grant` there is cannot be taken away; any
  other can
- **R6 The database decides.** The service says who the
  caller is, from the token; every accessor takes the
  caller first, asks the matrix, and refuses before it
  acts. A service that forgets to check cannot skip it,
  and a second service, in another language, gets the
  same rules for nothing
- **R7 Notes are (u=rw, a=r),** as §3
- **R8 Whether, never whose.** A reader learns whether
  a note is their own, never whose it is
- **R9 A permission is `<unit>.<verb>`,** lower case,
  one dot, so its unit is in its name

## 5 What It Will Not Do

- **Say no to one person.** A matrix cannot say
  "everyone but bob": take bob's role, or give the
  others a role he lacks. Refusals that override grants
  belong to §2's third row
- **Relations, sharing, delegation.** Also the third
  row: [OpenFGA's concepts of
  authorisation](https://openfga.dev/docs/authorization-concepts),
  relation-based, after Google's
  [Zanzibar](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/);
  or [Cedar](https://www.cedarpolicy.com/), policies
  over attributes. Read 2026-10-06
- **Decide who comes in.** That is tutorial 1's

## 6 See Also

- [The tests](2-tests.md): next, beside [the
  contract](3-contract.md)
- [The concept](../../conduct/the-cycle/concept.md):
  what a concept holds, in general
- [OWASP's Authorization Cheat
  Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  deny by default, check every request, and the rest,
  for any size
