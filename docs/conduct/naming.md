---
abstract: |
  How things are named in this project, and why: the
  owner first, then the thing, then what is done to it;
  one word for one idea; the case each place expects. A
  table of every kind of name, from hosts to test IDs,
  with what not to do. Each project keeps its own copy
  of this page, and changes it there.
date: 2026-10-07
keywords:
- conduct
- naming
- glossary
- db
kind: reference
sources:
- box/project.json
- migrations/sql/
- Makefile
status: draft
subtitle: The owner, the thing, the verb
title: Naming
version: v0.1.0
---

## 1 This Page Is the Project's

The rules below are the template's, and every fork
starts with them. They are your project's once you fork
it: change them here, in your copy, and keep to what
you write. A rule nobody wrote down is a habit, and a
newcomer cannot learn a habit by reading.

## 2 The Principles

1.  **The owner first.** A name starts with whoever
    owns it: `py_api_notes` is py-api's, `users_may`
    the users unit's. You know whom to ask before you
    know what it does, and an owner's names sort
    together
2.  **Then the thing, then what is done to it.**
    `py_api_note_add`, `py_api_note_edit`,
    `py_api_note_drop`: the note, then the verb. Every
    accessor of a note is found by one search
3.  **One word, one idea.** A person is a *person*, in
    `users_people`; a *member* is a person holding a
    role, in `users_members`. Neither is a *user*,
    which here names the unit. A word in use is reused
    before a new one is coined; [the
    glossary](../glossary.md) lists them
4.  **Say what it is, not how it is made.** `objects`,
    not `s3_blobs`; `users_may`, not `check_acl_join`.
    The how changes; the name should not have to
5.  **A question reads as one.** A function that
    answers yes or no is a question: `users_may`, and a
    column, `mine`. Not `users_permission_flag`
6.  **Whole words.** `permission`, not `perm`. The
    exceptions are words the field already abbreviates:
    `sub`, `id`, `url`, `db`
7.  **No versions, dates or people in a name,** except
    a migration's version, which is its order:
    `notes_v2`, `new_users`, `asha_fix` all go stale

## 3 Each Kind of Name

- **A service, its host:** kebab-case; `py-api`,
  `py-api.<zone>`
- **A database prefix:** snake_case, the service's name
  or a unit's; `py_api`, `users`
- **A table:** the prefix, then a plural noun;
  `users_people`, `py_api_notes`
- **A function:** the prefix, the thing, the verb;
  `py_api_note_add`
- **A published function:** the prefix, a question;
  `users_may`
- **An index:** the table, its columns, `idx`;
  `py_api_notes_owner_idx`
- **A migration:** `<version>_<prefix>_<what>.sql`;
  `20261006130000_users_create_tables.sql`
- **A permission:** `<unit>.<verb>`; `notes.read`,
  `users.grant`
- **A role:** kebab-case, a noun or a short phrase;
  `reader`, `member`, `site-admin`
- **A route:** plural nouns, an ID between;
  `/users/people/{sub}/roles/{role}`
- **An environment variable:** UPPER_SNAKE, the owner
  first; `COGNITO_USERINFO_URL`, `DEV_BASE_PORT`
- **A make target:** kebab-case, a verb or a noun;
  `dev-token`, `check-deps`
- **A file, a page:** kebab-case; `native-dev.sh`,
  `shared-box.md`
- **A step's page:** its step's number first;
  `2-tests.md`
- **A Python name:** a function or a variable
  snake_case, `email_of`, `note_edit`; a class
  PascalCase, `Note`; a module's constant UPPER_SNAKE,
  `COLLECT_GRACE`
- **A JavaScript name:** a function or a variable
  camelCase, `signIn`, `redirectUri`; a module's
  constant UPPER_SNAKE, `USERS`
- **A Svelte component:** PascalCase, a noun;
  `People.svelte`
- **A branch:** `feature/<issue>-<slug>`;
  `feature/12-uploads`
- **A release:** `vMAJOR.MINOR.PATCH`; `v0.2.0`
- **A test's ID:** `T<feature>.<n>`; `T2.12`

## 4 What Not to Do

- **`notes`** as a table. Whose? With no prefix, the
  check refuses it; with one, `py_api_notes`, the
  answer is in the name
- **`add_note`, `edit_note`, `remove_note`.** The verb
  first scatters a thing's names across the list, and
  `remove` beside `drop` is two words for one idea
- **`user`** for a person. It is the unit's name;
  `users_user` says nothing twice
- **`isAllowed`, `can`, `check`.** Allowed what? A
  question names what it asks:
  `users_may(sub, 'notes.write')`
- **`data`, `info`, `item`, `tmp`.** Every value is
  data; name what it holds

## 5 See Also

- [The database's conduct](database.md): why every name
  carries its prefix
- [The glossary](../glossary.md): the words in use
- [How these pages are written](README.md) §4: the
  pages' titles and keywords
