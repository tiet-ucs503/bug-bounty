---
abstract: |
  How the project's pages speak: to you, in the active
  voice, in the present tense, a step as a command and
  a result before the command. Who "we" is, when the
  passive is right, and the words to leave out. Each
  rule with a sentence from the tutorials that keeps
  it, and, where the temptation is strong, one that
  does not.
date: 2026-10-07
keywords:
- conduct
- writing
- docs
kind: reference
sources:
- docs/conduct/README.md
status: draft
subtitle: Voice, person and tense, with examples
title: Writing
version: v0.1.0
---

## 1 The Person

- **The reader is "you".** Every page speaks to one
  person, who is doing what the page describes:

  > Save the notes' part as `notes-draft.sql`.

- **"We" is the project's team,** and only for what the
  team decided or holds to; never for the reader and
  the writer together:

  > We take it one step further: each member of the
  > team does one thing, and does it well.

- **Never "I".** A page is the project's, not its
  author's; who wrote it is in git.

Not:

> ~~Now we will add the matrix to our draft.~~

The reader adds it; nobody goes with them. Write: *Add
this to the end of `users-draft.sql`.*

> ~~I tested this on the native stack.~~

Write: *Run on the native stack, 2026-10-06.* A badge
says it shorter still: `[OK:NATIVE]`.

## 2 The Voice

**Active, so the reader knows who acts.** In a system
of several parts, who does a thing is most of what
there is to know:

> The database decides.

> A service that forgets to check cannot skip it,
> because the accessor checks.

Not:

> ~~The request is checked, and refused if needed.~~

By whom? nginx checks the token's shape; the accessor
checks the permission; they refuse different things,
with different answers. The passive hid the one fact
the reader needed.

**The passive, when the actor does not matter or is not
known:** *A Cognito `sub` is a UUID.* *The database's
data folder is kept between runs.* If you can name the
actor and the reader would care, name them.

## 3 The Tense and the Mood

- **The present, for what is.** *`users_may` answers
  whether a person may do a thing*; not *will answer*.
  The page describes the system as it stands

- **The imperative, for a step.** *Save*, *Run*,
  *Expect*. One step, one verb, first

- **The result before the command,** so the reader
  knows what to look for before it scrolls past:

  > Expect, in order: three `t`: everyone is in, by
  > tutorial 1's `%` rule; ...

Not:

> ~~Run the following command and you should hopefully
> see some output indicating success.~~

*Should* and *hopefully* say the writer did not look.
Say what it prints: *Expect `native-dev: up`.*

## 4 Sentences

- **Short, one idea each.** A sentence with three
  commas usually holds two

- **The point first.** Lead a list item with its claim
  in bold, then the reason:

  > **`admin` does not read notes.** Running the people
  > and reading their notes are different trusts.

- **A warning names the trap and its cost:**

  > Mind the `@`: `'%example.org'` would let in
  > `mallory@evil-example.org`.

- **Plain words.** *Use*, not *utilise*; *need*, not
  *require*; *about*, not *in relation to*

## 5 Words to Leave Out

  ----------------------------------------------------
  Word                   Why
  ---------------------- -----------------------------
  *simply*, *just*,      What is simple to the writer
  *easily*, *obviously*  is a wall to the reader who
                         is stuck

  *should* (of a         Either it does, and say what
  result), *hopefully*   it prints, or it does not,
                         and say why

  *please*               A step is not a favour

  *etc.*, *and so on*    Name them, or say "such as"
                         and name one

  *currently*, *now*,    Every page describes now; the
  *new*                  word goes stale, the page
                         does not

  *user*, for a person   It is the unit's name
                         ([naming](naming.md) §2)
  ----------------------------------------------------

## 6 Two Patterns Worth Keeping

**A counterfactual, where the wrong way is tempting.**
Show it struck through, then the right one, then why,
as this page does. Only where a reader would otherwise
do it; a page of counterfactuals teaches the wrong way
by repetition.

**Building up, never trimming down.** Tutorial 1 says
it of rights, and it holds for pages: start from what
the reader needs, and add; never start from everything
and cut.

## 7 See Also

- [How these pages are written](README.md): the
  template and the rules this page expands
- [Naming](naming.md): the words, as names
- [The Diátaxis framework](https://diataxis.fr/): the
  four kinds of page
