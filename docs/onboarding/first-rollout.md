---
abstract: |
  The whole path once, from forking the template to a
  project answering on its hosts: what you do, what the
  box's owner does, and what you should see at each
  step.
date: 2026-10-06
keywords:
- rollout
- manifest
- render
- probes
kind: tutorial
sources:
- README.md
- box/render.py
- probes/Makefile
status: draft
title: From a Fork to a Live Project
version: v0.1.0
---

## 1 Before You Start

- **Tools:** git, Node 24, Python 3.12 or later, `jq`,
  `curl`, and md-preview for these pages
- **The box's owner,** willing to roll the project out,
  and a zone for it: a domain of its own, or one the
  box already serves
- **No AWS access** is needed for any step that is
  yours

## 2 Fork and Name

Fork the template, then set `name` in
`box/project.json`: 2 to 16 characters, lower case and
digits, a letter first. Every name on the box becomes
`tu-rgb-sites-<name>-<service>`.

Expect `box/project.json: <name>, 2 services, checked`:

``` sh
make check
```

## 3 Shape the Services

Keep, rename or remove `js-api` and `py-api`. A folder
in `services/` and an entry in the manifest go
together; `make check` refuses either without the
other. A new service starts as a copy of the starter in
its language.

Expect each suite's tests passing, 4 of 4 for the
starters:

``` sh
make test
```

## 4 Render and Hand Over

Expect
`box/out/<name>/: project.json, nginx.conf.in, compose.yml, ONBOARDING.md`:

``` sh
make render
```

Give the box's owner your commit and the folder
`box/out/<name>/`. Its `ONBOARDING.md` is their list:
the records and rules at Cloudflare, one Terraform plan
and apply, the builds, the pins, an upload and a
reload, and their probes.

## 5 Configure the UI

When the owner is done, they give you three things that
are not secret: Cognito's sign-in domain, your UI's
client ID, and the zone confirmed. Copy the example and
fill them in:

``` sh
cp ui/config.example.js ui/config.js
```

Expect a page at `http://localhost:5173/` that signs
you in and calls both services:

``` sh
make ui
```

## 6 Release the UI and These Pages

Your UI maintainer syncs `ui/` to `www` and the built
pages to `docs`: [Release the UI and these
pages](release-ui-and-docs.md).

## 7 Probe the Hosts

Expect every target `PASS`: [Probe your
hosts](run-the-probes.md).

## 8 What Can Go Wrong

- **`make check` refuses the manifest.** It names the
  key and the rule; [the manifest](manifest.md) lists
  every rule
- **The sign-in returns to an error page.** The page's
  origin is not among the client's callbacks:
  `https://www.<zone>/` and `ui.dev_callback_urls`
- **A host times out or shows Cloudflare's error
  page.** Its record is not there yet, or the owner's
  reload has not run; ask the owner

## 9 See Also

- [How the project meets the box](README.md): why each
  step is there
- [Hand a change to the box's owner](hand-over.md):
  every change after this one
