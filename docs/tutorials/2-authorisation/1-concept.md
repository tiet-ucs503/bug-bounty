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
> contract](2-contract.md) exists, and wherever it is
> silent, this page is the source of truth.

## 1 The Goal

**Each person may do what their roles allow, and
nothing else; the database decides.** Tutorial 1
records who signed in. This decides what each may do.

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
  high**         people and         §6
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

  ------------------------------------------------------------------------
  Role       `notes.read`   `notes.write`   `users.read`   `users.grant`
  ---------- -------------- --------------- -------------- ---------------
  `reader`   yes                                           

  `member`   yes            yes                            

  `admin`                                   yes            yes
  ------------------------------------------------------------------------

And the notes, read as a Unix mode, **(u=rw, a=r)**:
**u**, the owner, reads and writes; **a**, all, read.
"All" is everyone the matrix gives `notes.read`;
"writes" needs the owner **and** `notes.write`. The
matrix says who may use notes at all; the owner's
column says whose note it is.

## 4 The Rules

Read from the matrix, and numbered, so [the
tests](3-tests.md) can say which each one checks:

- **R1 Nothing unless a role says so.** No cell says
  no. Someone who signed in holds no role until one is
  given, and may do nothing; someone who never signed
  in holds none at all
- **R2 Each role, its row.** `reader` reads notes;
  `member` reads and writes them; `admin` reads the
  people and the matrix, and grants. **`admin` does not
  read notes:** running the people and reading their
  notes are different trusts. An admin who should read
  notes holds `member` too
- **R3 Roles add up.** A person may hold several, and
  may do what any of them may
- **R4 Only `users.grant` gives or takes a role,** and
  only a role that exists, to a person who signed in.
  The one exception is R10
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
- **R10 A starting role, by e-mail, once.** At a
  person's first sign-in, the first rule whose pattern
  their e-mail matches gives its role. No match, no
  role. The rules are read only then: a rule changed
  later changes nothing for people already signed in

## 5 Starting Roles

R10 saves an admin from granting every newcomer by
hand. A rule says: an e-mail like this starts with this
role. For example, `(10, '%@example.org', 'member')`
gives everyone at example.org `member`. Each rule has
three parts:

- **A position,** 10 here. The rules are tried in
  order, lowest first, and the first that matches wins
- **A pattern,** matched with SQL's `LIKE`: `%` stands
  for any run of characters, including none, and `_`
  for any single character
- **A role,** given at the first sign-in

Four sets of rules cover most projects:

- **No rules, the default.** Everyone signs in with no
  role, and an admin gives roles one at a time
- **One organisation as members:**
  `(10, '%@example.org', 'member')`. Anyone else signs
  in with no role
- **One organisation as members, everyone else as
  readers:** `(10, '%@example.org', 'member')`,
  `(20, '%', 'reader')`
- **A named list,** one rule a person:
  `(10, 'anu@example.org', 'member')`,
  `(11, 'raj@example.net', 'reader')`

**A starting role is still a role.** It adds up with
any other (R3), and `users_revoke` takes it away like
any other (R4). To change what newcomers start with,
change the rules; the people already in keep theirs.

Try a set of rules on four addresses, with no tables at
all. Expect `member` for the two at example.org,
whatever their case, `reader` for bhanu, and nothing
for manthara:

``` sh
psql "${MIGRATOR_URL}" -c "WITH rules (position, pattern, role) AS (VALUES (10, '%@example.org', 'member'), (20, '%@elsewhere.net', 'reader'))
SELECT e AS email, (SELECT r.role FROM rules r WHERE lower(e) LIKE r.pattern ORDER BY r.position LIMIT 1) AS role
FROM unnest(ARRAY['asha@example.org', 'Chitra@Example.org', 'bhanu@elsewhere.net', 'manthara@evil-example.org']) AS e"
```

> [!WARNING]
> Mind the `@`. `'%example.org'`, without it, would
> also let in `manthara@evil-example.org`. And since
> `_` matches any character, write it `\_` in a pattern
> that means a real underscore.

## 6 What It Will Not Do

- **Say no to one person.** A matrix cannot say
  "everyone but bhanu": take bhanu's role, or give the
  others a role he lacks. Refusals that override grants
  belong to §2's third row
- **Relations, sharing, delegation.** Also the third
  row: [OpenFGA's concepts of
  authorisation](https://openfga.dev/docs/authorization-concepts),
  relation-based, after Google's
  [Zanzibar](https://research.google/pubs/zanzibar-googles-consistent-global-authorization-system/);
  or [Cedar](https://www.cedarpolicy.com/), policies
  over attributes. Read 2026-10-06
- **Decide who signs in, or keep their record.** That
  is tutorial 1's

## 7 See Also

- [The contract](2-contract.md): next, then [the
  tests](3-tests.md)
- [The concept](../../conduct/the-cycle/concept.md):
  what a concept holds, in general
- [OWASP's Authorization Cheat
  Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html):
  deny by default, check every request, and the rest,
  for any size
