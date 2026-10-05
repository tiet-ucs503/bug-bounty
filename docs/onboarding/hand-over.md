---
abstract: |
  What to hand the box's owner for each kind of change,
  and what they do with it. A change to code, to the
  manifest, or to the UI and these pages takes a
  different path.
date: 2026-10-06
keywords:
- hand-over
- render
- manifest
- build
kind: how-to
sources:
- box/render.py
- box/how-the-box-works.md
status: draft
title: Hand a Change to the Box's Owner
version: v0.1.0
---

## 1 Before You Start

- The change committed, and `make check` and
  `make test` passing
- Which kind of change it is: §2, §3 or §4

## 2 A Change to a Service's Code

No new route, no new service. Hand over the commit and
the service's name. The owner uploads the service's
folder, builds it, pins the new digest, uploads the
stack and reloads. Nothing else changes on the box.

## 3 A Change to the Manifest

A new route, a new method on one, a new service, a new
port or memory. Render, and expect `box/out/<name>/`
written:

``` sh
make render
```

Hand over the commit and `box/out/<name>/`. The owner
reads the rendered `nginx.conf.in` above all, copies
the folder into the box's repository, and rolls it out;
a new service also needs its repository and build, one
Terraform plan and apply.

## 4 A Change to the UI or These Pages

No hand-over: your UI maintainer syncs it. See [Release
the UI and these pages](release-ui-and-docs.md).

## 5 What Can Go Wrong

- **The owner's upload is refused, "not yet built and
  pinned".** A new service in the compose piece has no
  build yet; the owner builds and pins it first
- **The new route still answers `404` after the
  rollout.** The route in the manifest and the route in
  the code differ: a path is exact, and `/items` is not
  `/items/`

## 6 See Also

- [The manifest, key by key](manifest.md)
- [Probe your hosts](run-the-probes.md): to check the
  change live
