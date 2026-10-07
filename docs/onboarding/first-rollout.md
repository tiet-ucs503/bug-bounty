---
abstract: |
  The whole path once, from forking the template to a
  project answering on its hosts: what you do, what the
  box's owner does, and the first release tag that puts
  it live.
date: 2026-10-06
keywords:
- rollout
- manifest
- release
- github
kind: tutorial
sources:
- README.md
- box/render.py
- .github/workflows/release.yml
- probes/Makefile
status: draft
title: From a Fork to a Live Project
version: v0.1.0
---

## 1 Before You Start

- **A GitHub repository,** forked from the template
- **Tools:** git, Node 24, Python 3.12 or later, `jq`,
  `curl`, and md-preview for these pages
- **The box's owner,** willing to roll the project out,
  and a zone for it: a domain of its own, or one the
  box already serves
- **No AWS access** is needed for any step that is
  yours

## 2 Name the Project

In `box/project.json`:

- `name`: 2 to 16 characters, lower case and digits, a
  letter first. Every name on the box becomes
  `tu-rgb-sites-<name>-*`
- `github`: this repository, `owner/name`
- `database`: `true` if any service keeps state

Expect
`box/project.json: <name>, 2 services, 1 migrations, checked`:

``` sh
make check
```

## 3 Shape the Services

Keep, rename or remove `js-api` and `py-api`, and give
each its `prefix`. A folder in `services/` and an entry
in the manifest go together; `make check` refuses
either without the other. A new service starts as a
copy of the starter in its language. Expect each
suite's tests passing:

``` sh
make test
```

## 4 Render and Hand Over

Expect `box/out/<name>/:` and its six files:

``` sh
make render
```

Give the box's owner the folder `box/out/<name>/`. Its
`ONBOARDING.md` is their list: the records and rules at
Cloudflare, one Terraform plan and apply, the project's
CI role from `ci-trust.json.in` and
`ci-policy.json.in`, and their probes.

## 5 Set the Repository's Variables

The owner gives you four values, none a secret. Set
them as repository variables: [How a release reaches
the box](ci-cd.md), §4.

## 6 The First Release

Expect the tag pushed, and **Release** building every
image, writing the record, and syncing `www`, `docs`
and `static`:

``` sh
TAG=v0.1.0
git tag -a "${TAG}" -m "${TAG}"
git push origin "${TAG}"
```

The box pins the record's digests and reloads.

## 7 Probe the Hosts

Expect every target `PASS`: [Probe your
hosts](run-the-probes.md).

## 8 What Can Go Wrong

- **`make check` refuses the manifest.** It names the
  key and the rule; [the manifest](manifest.md) lists
  every rule
- **The release cannot assume its role.** A variable is
  wrong, or the owner has not yet made the role; [How a
  release reaches the box](ci-cd.md), §6
- **The sign-in returns to an error page.** The page's
  origin is not among the client's callbacks:
  `https://www.<zone>/` and `ui.dev_callback_urls`
- **A host times out or shows Cloudflare's error
  page.** Its record is not there yet, or the box has
  not reloaded; ask the owner

## 9 See Also

- [How the project meets the box](README.md): why each
  step is there
- [How a release reaches the box](ci-cd.md): every
  release after
