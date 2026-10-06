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
- `draft` [The manifest, key by
  key](onboarding/manifest.md)

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

- `draft` [How these pages are
  written](conduct/README.md)
- `draft` [The page template](conduct/template.md)
- `draft` [The database's conduct](conduct/database.md)

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
- [How these pages are written](conduct/README.md):
  before you add or change a page
