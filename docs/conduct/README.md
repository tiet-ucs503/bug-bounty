---
abstract: |
  How the project works, page by page, and how its
  pages are written.
date: 2026-10-07
keywords:
- conduct
- writing
- template
- frontmatter
- diataxis
- masking
kind: explanation
sources:
- docs/conduct/template.md
status: draft
subtitle: How we work, and how we write it down
title: The Project's Conduct
version: v0.1.0
---

## 1 The Conduct, Page by Page

In the order a newcomer reads them.

1.  [The philosophy](philosophy.md): one thing, done
    well, by each part
2.  [The cycle](the-cycle/README.md): concept,
    contract, tests, implementation, refinement
    - [The concept](the-cycle/concept.md): before the
      first line of code
    - [The tests](the-cycle/tests.md): the questions a
      concept raises
3.  [From an issue to a merge](workflow.md): the cycle,
    in git
4.  [Git and git-flow](git.md): branches, commits, and
    who wrote them
5.  [Naming](naming.md): the owner, the thing, the verb
6.  [The database's conduct](database.md): prefixes,
    accessors, and what a service may do
7.  [The API's conduct](api.md): a reference made from
    the routes, shown by Scalar
8.  [The UI's conduct](ui.md): mobile first, Tailwind,
    Svelte, and a visual language of your own
9.  [Writing](writing.md): voice, person and tense
10. **How these pages are written:** this page, §2 to
    §6, and [the template](template.md) to copy

## 2 Who We Write For

The pages are public, at `docs.<zone>`. Write for a
reader who reads JavaScript or Python and uses a shell,
but has never seen this repository's history or the
box's. That reader might be:

- someone maintaining the project, a year from now
- someone writing a client of its API
- the box's owner, checking what the project asks of
  the box

Address the reader as "you"; [Writing](writing.md) has
the voice, the person and the tense, with examples.
Name the project, its services and its files; do not
name people or institutions.

## 3 Four Kinds of Page

Each page is one kind, after
[Diátaxis](https://diataxis.fr/). A page that needs two
kinds is two pages, linked.

  -------------------------------------------------------
  Kind          Answers       Its reader   Its shape
  ------------- ------------- ------------ --------------
  Tutorial      "Show me how  is learning  Numbered steps
                to begin"                  to one working
                                           result

  How-to        "How do I do  has a task   Numbered
                this?"                     steps, nothing
                                           that is not a
                                           step

  Reference     "What exactly is looking   Tables and
                is this?"     something up lists that
                                           mirror the
                                           code

  Explanation   "Why is it    wants to     Prose, with
                so?"          understand   the
                                           alternatives
                                           weighed
  -------------------------------------------------------

## 4 The Template

Start from [the template](template.md). It has two
parts.

**The frontmatter.** md-preview shows every key in a
table above the title, so the keys are the page's
record of itself:

  ---------------------------------------------------
  Key        What it holds
  ---------- ----------------------------------------
  title      The task or the thing, in title case:
             "Restore the Database from a Dump", not
             "Restoring"

  subtitle   One line, only if the title needs it

  date       When the page was last checked against
             the code

  version    The release it was checked against, such
             as `v0.1.0`, from `VERSION`

  kind       `tutorial`, `how-to`, `reference` or
             `explanation`

  keywords   Three to six words a reader might search
             for, lower case, hyphenated: `backups`,
             `deployer-policy`. Reuse a word already
             in use before coining one; the glossary
             lists them

  status     `planned`, `draft` or `checked`, as in
             the map

  sources    The repository's files the page
             describes, by path from the root; a
             release that changes one of them puts
             the page back to `draft`

  abstract   Two or three sentences: what the page
             does for you, and for whom
  ---------------------------------------------------

**The body.** Numbered sections, so a page can be cited
as "§3"; a third level of heading only if a section
cannot be split. The first sections depend on the kind;
the last two are always the same:

- **Before You Start** --- in a tutorial or a how-to:
  what you need, and whether the change can be undone
- **The steps, or the subject** --- one section each
- **What Can Go Wrong** --- the symptoms you will see,
  what each means, and what to do
- **See Also** --- the pages to read next, each with a
  reason

## 5 The Rules

### 5.1 True

- **Check every claim against the code** at the version
  in the frontmatter, and name the file it rests on, by
  its path: `services/js-api/server.js`
- **Describe what is,** in the present tense. How it
  came to be lives in the repository's history. A page
  says "not yet" only to mark a limit
- **Never write from what is missing.** That a command
  printed no error is not the same as a result; say
  what output shows success

### 5.2 Safe to Publish

Nothing on a page may identify the box's account or
open a door into it. Never write:

- an AWS account ID, or an ARN that carries it
- the IDs of instances, volumes, security groups, keys
  or Cognito pools and clients
- IP addresses, public or private
- any e-mail address
- passwords, tokens, shared secrets, or anything from
  `ui/config.js` you were not told is public

Your own zone may appear where the project has chosen
to name it; until then, write `<zone>`.

In prose and in sample output, write a placeholder in
angle brackets: `<account-id>`, `<instance-id>`,
`<domain>`. In a command, use a shell variable, set at
the top of the block or read from AWS, so the command
runs as written.

Before every commit, scan what is staged; exit status 1
means nothing matched:

``` sh
git diff --cached -U0 | grep -nE '[0-9]{12}|@[a-z]+\.(com|in|edu)|[^m]i-0[0-9a-f]{8,}|10\.0\.[0-9]+\.[0-9]+|ip-[0-9]+-|[0-9a-f]{8}-[0-9a-f]{4}-'
```

Read every line it prints; do not explain one away.

### 5.3 Runnable

- **Complete commands,** run from the repository's
  root, as they will be typed: no `<...>` inside a
  command, no step left to the reader. A command that
  needs AWS is the release's, by its CI role, or the
  box owner's; say whose
- **Inputs as variables,** set at the top of the block,
  written with braces, `${PROJECT}`, so that a colon
  after one cannot be read as a shell modifier
- **The expected result before the command,** so the
  reader knows what to look for before it scrolls past
- **One command per block** where its output decides
  what comes next
- **A destructive step is flagged above itself,** in a
  `> [!CAUTION]` alert that says what is lost

### 5.4 Readable

- UK English; plain words; short sentences; the active
  voice: [Writing](writing.md)
- Names as [Naming](naming.md) gives them
- Define a term where it is first used, and add it to
  [the glossary](../glossary.md)
- Alerts only for their meaning: `[!NOTE]` for an
  aside, `[!WARNING]` for a trap, `[!CAUTION]` for a
  loss. A page with an alert in every section has none
- **Diagrams in Mermaid,** a fenced `mermaid` block,
  which md-preview draws; never ASCII art, which breaks
  at the wrap and reads badly aloud. Give the edges
  labels, and reuse the colour classes of [How the
  project meets the box](../onboarding/README.md)
- Wrap to 55 columns before committing (§6)

### 5.5 Linked

- **Between pages,** relative links to the `.md` file:
  `[the template](template.md)`. md-preview rewrites
  them to the rendered pages
- **To the repository's files,** the path in code, not
  a link: the published pages are built from `docs/`
  alone, so a link out of it breaks
- **To vendors' documentation,** a link, with the date
  read if the page is versioned

### 5.6 Kept Current

- A page moves `planned`, then `draft`, then `checked`.
  It is `checked` once every command on it has been run
  at its version, and every claim read against its
  sources
- A release that changes a page's sources puts the page
  back to `draft` until it is checked again
- The map in [the home page](../README.md) lists every
  page and its status; a new page is added to the map
  in the same commit. An entry is a quote of its own, a
  blank line before and after: its status and badges on
  the first line, ended by a backslash, and its link on
  the next
- **A new service** is a new top-level folder, named as
  the manifest names it, with the same three pages as
  `js-api/`: what it is, its routes, how to develop it

## 6 What Can Go Wrong

- **An alert turns into `\[!NOTE\]`.** Pandoc wraps
  alerts only when told they exist. Wrap with the
  extension, and `-s` to keep the frontmatter:

  ``` sh
  pandoc -s -f markdown+alerts -t markdown+alerts --columns=55 docs/conduct/README.md -o docs/conduct/README.md
  ```

  `-s` also sorts the frontmatter's keys; md-preview
  sorts them anyway

- **Square brackets render as display maths.** Pandoc
  escapes a bracket in the frontmatter to `\[`, and
  md-preview reads `\[ ... \]` as LaTeX. Keep brackets
  out of the frontmatter; say it in words

- **A table's rows break apart.** In a simple table,
  one line is one row, so a cell the wrap folds onto a
  second line becomes a row of its own. Write a
  multiline table, with a blank line between rows and a
  dashed line above and below, as in §3 and §4; or a
  list

- **A multiline table's cells come out mangled,
  backticks escaped.** A code name longer than its
  column cannot wrap, so pandoc splits it across cells.
  Long identifiers go in a definition list, one term to
  an entry, as the Terraform reference does

- **A link works locally and breaks when published.**
  It points out of `docs/`. Write the path in code
  instead

- **A page is right but out of date.** Its `version` is
  older than a release that changed one of its
  `sources`. Put it back to `draft` in the map

## 7 See Also

- [The template](template.md): the skeleton to copy for
  a new page
- [The glossary](../glossary.md): the terms these pages
  use, and the keywords in use
- [The home page](../README.md): the map of every page
  and its status
- [Diátaxis](https://diataxis.fr/): the four kinds of
  page, at length
- [md-preview's
  reference](https://github.com/bvraghav/md-preview/blob/main/REFERENCE.md):
  the Markdown it renders, and its folder mode
