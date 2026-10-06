---
abstract: |
  What this project is, who its pages are for, and the
  map of every page with its status. Start here.
date: 2026-10-06
keywords:
- overview
- audience
- map
kind: explanation
sources:
- box/project.json
status: draft
subtitle: A project on the box, its services and its UI
title: Example Project
version: v0.1.0
---

## 1 What This Is

A project whose API and UI run on a shared host, the
box, which another repository keeps. The project holds
its code, its manifest and its pages; the box's owner
rolls them out. Its parts:

- **`js-api.<zone>`:** a service in JavaScript
- **`py-api.<zone>`:** a service in Python
- **`www.<zone>`:** the UI, a single-page app
- **`docs.<zone>`:** these pages
- **`static.<zone>`:** public files
- **One database,** each service's part under its
  prefix

Replace this section with what your project does, once
you have named it in `box/project.json`.

## 2 Who These Pages Are For

- **You maintain the project.** You need to know how it
  meets the box, how a change reaches the box, and how
  each service is built
- **You write a client of its API,** the UI or another.
  You need the routes, who may call them, and what the
  box answers before a service does
- **You keep the box.** You need to know what the
  project asks of it and how to check it is right

You are assumed to read JavaScript or Python and to use
a shell. You are not assumed to know the box's own
repository.

## 3 The Map

Status: **checked** --- every claim and command checked
at the version the page names; **draft** --- written,
not yet checked; **planned** --- not yet written.

### Start Here

- `draft` This page
- `draft` [Glossary](glossary.md)

### Onboarding: the Project and the Box

- `draft` [How the project meets the
  box](onboarding/README.md)
- `draft` [From a fork to a live
  project](onboarding/first-rollout.md)
- `draft` [How a release reaches the
  box](onboarding/ci-cd.md)
- `draft` [A release by
  hand](onboarding/release-by-hand.md)
- `draft` [Hand a change to the box's
  owner](onboarding/hand-over.md)
- `draft` [Probe your
  hosts](onboarding/run-the-probes.md)
- `draft` [A local stack that mirrors the
  box](onboarding/local-dev.md)
- `draft` [Develop on a shared box without
  root](onboarding/shared-box.md)
- `draft` [Run the stack with rootless
  Podman](onboarding/podman.md)
- `draft` [The manifest, key by
  key](onboarding/manifest.md)

### Tutorials: From a Sign-in to Uploads

Each tutorial's badges, beside its status, say where it
ran ([the tutorials' page](tutorials/README.md) §5).

- `draft` [The path, and its
  conventions](tutorials/README.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [1
  Who comes in:
  authentication](tutorials/1-authentication.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [2
  What each may do:
  authorisation](tutorials/2-authorisation/README.md):
  [the
  concept](tutorials/2-authorisation/1-concept.md),
  [the tests](tutorials/2-authorisation/2-tests.md),
  [the
  contract](tutorials/2-authorisation/3-contract.md),
  [the
  implementation](tutorials/2-authorisation/4-implementation.md),
  [the
  refinement](tutorials/2-authorisation/5-refinement.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [3
  Make it a migration](tutorials/3-the-migration.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [4
  /users in Python, in
  py-api](tutorials/4-users-in-python.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [5
  /users in JavaScript, in
  js-api](tutorials/5-users-in-javascript.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [6
  A Svelte UI](tutorials/6-a-svelte-ui.md)
- `draft` `[OK:NATIVE]` `[NO:PODMAN]` `[NO:DOCKER]` [7
  Uploads](tutorials/7-uploads/README.md): [the
  store](tutorials/7-uploads/1-the-store.md), [the
  database](tutorials/7-uploads/2-the-database.md),
  [the service](tutorials/7-uploads/3-the-service.md),
  [the UI](tutorials/7-uploads/4-the-ui.md)

### js-api

- `draft` [What js-api is, and who may call
  it](js-api/README.md)
- `draft` [js-api's routes](js-api/api.md)
- `draft` [Develop and change
  js-api](js-api/develop.md)

### py-api

- `draft` [What py-api is, and who may call
  it](py-api/README.md)
- `draft` [py-api's routes](py-api/api.md)
- `draft` [Develop and change
  py-api](py-api/develop.md)

### Migrations: the Database

- `draft` [The database](migrations/README.md)
- `draft` [Write a
  migration](migrations/write-a-migration.md)

### UI

- `draft` [The UI](ui/README.md)
- `draft` [Develop the UI](ui/develop.md)
- `draft` [Release the UI](ui/release.md)

### Conduct

- `draft` [The project's conduct: how we work, and how
  we write it down](conduct/README.md)
- `draft` [The philosophy: one thing, done
  well](conduct/philosophy.md)
- `draft` [The page template](conduct/template.md)
- `draft` [The database's conduct](conduct/database.md)
- `draft` [The concept: before the first line of
  code](conduct/the-cycle/concept.md)
- `draft` [The tests: the questions a concept
  raises](conduct/the-cycle/tests.md)
- `draft` [The cycle: five steps, in
  turns](conduct/the-cycle/README.md)
- `draft` [From an issue to a
  merge](conduct/workflow.md)
- `draft` [Git and git-flow](conduct/git.md)
- `draft` [Naming](conduct/naming.md)
- `draft` [Writing: voice, person and
  tense](conduct/writing.md)

## 4 Reading the Pages

The pages are Markdown, rendered by
[md-preview](https://github.com/bvraghav/md-preview).
To read them locally, from the repository's root,
expecting a browser to open with a file tree on the
left:

``` sh
md-preview docs
```

To build them once into `docs/_site/`, the folder a
release syncs to `docs.<zone>`:

``` sh
md-preview build docs
```

## 5 See Also

- [How the project meets the
  box](onboarding/README.md): read next
- [The project's conduct](conduct/README.md): how
  we work, and before you add or change a page
