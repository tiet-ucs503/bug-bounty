---
abstract: |
  The questions a concept raises, and how each becomes
  a test before the code exists: who may and who may
  not, the default, the edges, twice, the absent, the
  last one, and what must not leak. Each test with an
  ID, at the lowest layer that can answer it. Written
  as what the solution must not fail. With examples
  from the tutorials.
date: 2026-10-07
keywords:
- conduct
- tests
- concept
- cycle
kind: explanation
sources:
- docs/tutorials/2-authorisation/2-tests.md
status: draft
subtitle: The questions a concept raises, as tests
title: The Tests
version: v0.1.0
---

## 1 Why Before the Code

A test written first measures what you meant; one
written after measures what you did. Written first, the
tests say at any moment how much of the concept stands,
and they fail until it does. Written after, they pass
by construction, and they keep the code's mistakes as
carefully as its intentions.

The tests are step 2 of [the cycle](the-cycle.md),
beside the contract, and both follow from [the
concept](concept.md).

## 2 The Questions That Follow

Read each rule of the concept and ask it these. Most
rules answer only some; a rule none of them touches is
probably not a rule.

Each question below comes with an example from the
tutorials: what someone does, and what the test
expects.

- **Who may?** A `member` writes a note. Expect the
  note saved
- **Who may not?** A `reader` tries to write a note.
  Expect a refusal, `403`
- **And by default?** Someone has just signed in and
  holds no role but `deny-all`. They ask for the notes.
  Expect a refusal: nobody gets anything until a role
  says so
- **Together?** You hold `admin` and `member` at once.
  `admin` alone cannot read notes, `member` can. Expect
  you can read them: roles add up, and one role never
  takes away what another gives
- **Whose?** Bob, a `member`, edits a note alice wrote.
  Expect a refusal, `not your note`: being allowed to
  write notes is not being allowed to write hers
- **Absent?** Alice edits a note that does not exist.
  Expect `404`, which is a different answer from
  editing someone else's note (`403`), so the caller
  can tell the two apart
- **Twice?** Does doing the same thing again change
  anything? An admin gives bob the `reader` role, then,
  by mistake, gives it again. Expect no error, and bob
  holding `reader` once, not twice
- **The last one?** Can taking away the last of
  something break everything? The project's only admin
  takes away their own `admin` role. Were it allowed,
  nobody would be left who may give roles, and nobody
  could put it right from the app. Expect a refusal,
  `409`. And expect any other admin's role, while
  another admin remains, to be taken away as asked
- **At the edge?** A body of exactly 1 MiB is sent.
  Expect it to pass; one byte more, `413`
- **What leaks?** Does an answer say more than it
  should? Bob, a `reader`, lists the notes. He should
  see every note and, on each, whether it is his own,
  but not who wrote the others. Expect the list to
  carry a `mine` flag, `true` or `false`, and no owner
  at all

The last question is the one most often missed: its
test checks that something is **not** there.

## 3 Questions Become Tests

A test is the question with its answer fixed:

- **An ID,** `T2.3`: the tutorial's or the feature's
  number, then the test's. The test's code carries the
  ID in its name, so a failure names the line of the
  tests page it breaks
- **Where it comes from:** the rule of the concept it
  checks. A test that comes from nowhere tests the
  implementation, not the concept
- **One action, and the answer expected:** a call and
  its status, a function and its value, an error and
  its SQLSTATE

Write them **backwards**: not "it does this", but "it
must not fail this". The solution is whatever passes;
until something does, every test fails, and that is the
first thing to check: **a test that passes before the
code exists is testing nothing.**

## 4 The Lowest Layer That Can Answer

  -----------------------------------------------------
  Layer         Answers               In the tutorials
  ------------- --------------------- -----------------
  The database  Who may, whose, the   1, 2, 7.2: in a
                last one              transaction
                                      rolled back

  The service   Status codes, the     4, 5, 7.3: a test
                token, the e-mail     file, its
                                      database and
                                      Cognito stood in

  Through nginx The route exists, the 4 §7: calls with
                body's limit          `curl`

  The browser   The page shows it     6, 7.4: the
                                      dashboard, signed
                                      in
  -----------------------------------------------------

Ask each question once, as low as it can be asked. Then
once at the top, to prove the layers are joined: the
database's refusal still reaches the browser as a
refusal.

## 5 What Tests Catch That Eyes Do Not

When the tutorials were written, an edit to the
JavaScript service turned SQLSTATE `23001` into
`23000`. Nobody reading the diff saw it; the test that
a revoke of the last `users.grant` answers `409` did. A
test is a reader that never tires and never skims.

## 6 What Can Go Wrong

- **A test you cannot write.** The concept is vague
  there. Go back to it; do not guess
- **Every test passes at once.** The tests check the
  code's own output against itself, or nothing at all
- **A test breaks whenever the code is tidied.** It
  tests how, not what. Test through the contract: the
  route, the accessor, not the private function
- **A test that sometimes fails,** with nothing
  changed. It depends on the clock, on the order the
  tests run in, or on data another test left behind.
  Fix it the day you see it. Once people learn that a
  failure may be noise, they rerun until it passes, and
  the day a failure is real, they rerun that one too

## 7 See Also

- [The concept](concept.md): where the questions come
  from
- [The cycle](the-cycle.md): what to do when a test
  fails
- [2 What each may do: its
  tests](../tutorials/2-authorisation/2-tests.md)
