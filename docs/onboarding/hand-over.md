---
abstract: |
  The one change a release cannot make: a change to the
  manifest. What the release hands over, and what the
  box's owner does with it.
date: 2026-10-06
keywords:
- hand-over
- render
- manifest
kind: how-to
sources:
- box/render.py
- .github/workflows/release.yml
status: draft
title: Hand a Change to the Box's Owner
version: v0.1.0
---

## 1 What Needs a Hand-over

A release builds images and syncs buckets alone ([How a
release reaches the box](ci-cd.md)). A change to
`box/project.json` changes what the box runs around
them:

- a new route, or a new method on one: nginx's
  allow-list
- a new service: its repository, its build, its host,
  its compose piece
- a new port, memory or prefix, or the database turned
  on

The box's owner reviews and rolls those out; a release
never can.

## 2 What the Release Does

A tag whose changes include `box/project.json` renders
the box's pieces and attaches them to the release on
GitHub, `box-<name>-<tag>.tgz`, with a warning. Its
images and buckets go out as usual. To see the pieces
before the tag, expect `box/out/<name>/` written:

``` sh
make render
```

## 3 What the Owner Does

Reads the rendered `nginx.conf.in`, `compose.yml` and
`ci-policy.json.in`, copies the folder into the box's
repository, and rolls it out: a reload for a route; one
Terraform plan and apply for a new service.

## 4 Until Then

The new image may run before its route is out: the
route answers `404`, from nginx, until the owner's
rollout. A new service has no image until its
repository and build exist: release it again after.

## 5 What Can Go Wrong

- **The new route still answers `404` after the
  rollout.** The route in the manifest and the route in
  the code differ: a path is exact, and `/items` is not
  `/items/`
- **A new service's build fails, `project not found`.**
  The owner's Terraform has not run yet; release again
  after it

## 6 See Also

- [The manifest, key by key](manifest.md)
- [Probe your hosts](run-the-probes.md): to check the
  change live
