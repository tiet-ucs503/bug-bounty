---
abstract: |
  Publish the pages in `docs/` to GitHub Pages, built
  by md-preview in a workflow of the repository's own.
  One setting, once; then every push to `master` that
  changes a page publishes them.
date: 2026-10-07
keywords:
- docs
- github-pages
- ci
- md-preview
kind: how-to
sources:
- .github/workflows/pages.yml
status: draft
subtitle: Built by md-preview, in a workflow
title: Publish the Pages to GitHub Pages
version: v0.1.0
---

## 1 Before You Start

- **Your fork on GitHub,** and its admin's rights, for
  one setting
- **What this adds:** a second copy of the pages, at
  GitHub's address for your repository. The release
  still syncs its own to `docs.<zone>` ([How a release
  reaches the box](ci-cd.md)); neither needs the other
- **What it does not need:** AWS, the box, or any
  secret. The workflow holds no credential but GitHub's
  own for Pages

> [!WARNING]
> The pages become public, whoever may read the
> repository. Hold every page to [Safe to
> publish](../conduct/README.md) §5.2 before the first
> push.

## 2 Turn Pages On

Once, in the repository's **Settings**, under
**Pages**: set **Source** to **GitHub Actions**. Not
"Deploy from a branch": the pages are built, not
committed.

## 3 Publish

`.github/workflows/pages.yml` runs at every push to
`master` that changes `docs/`, so at every release. To
publish without one, by hand: **Actions**, **Pages**,
**Run workflow**, on `master`.

It has two jobs:

1.  **build:** pandoc and md-preview, each fetched at a
    fixed version and checked; `md-preview build docs`;
    the folder `docs/_site/` handed on
2.  **deploy:** publishes that folder. The only job
    that may write to Pages, and it runs nothing else

Expect both green, and the address under the **deploy**
job, `https://<owner>.github.io/<repository>/`.

## 4 Try the Build First

The same build, on your machine. Expect
`rendered 80 of 80 pages`, or your own count, and
`docs/_site/index.html`:

``` sh
md-preview build --force docs
```

Open `docs/_site/index.html` in a browser. The pages
link to each other and to their styles by relative
paths, so they read the same from a folder, from
`docs.<zone>` and from GitHub's address.

## 5 What Can Go Wrong

- **The deploy job fails, `Get Pages site failed` or
  `Not Found`.** Pages is not turned on, or its source
  is a branch: §2
- **The deploy job waits for approval.** The
  `github-pages` environment has a protection rule.
  Approve it, or lift the rule in **Settings**,
  **Environments**
- **`Branch "master" is not allowed to deploy`.**
  GitHub makes the `github-pages` environment admit the
  repository's default branch alone. If yours is
  `develop`, add `master` in **Settings**,
  **Environments**, **github-pages**, under its
  deployment branches
- **A page is missing its drawing.** An image added
  after a first build is not copied by a later one on
  your machine; `--force` copies it. The workflow
  builds afresh, and is not affected
- **The pages are a release behind.** They follow
  `master`, not `develop`: they show what is released

## 6 See Also

- [How a release reaches the box](ci-cd.md): the other
  copy, at `docs.<zone>`
- [How these pages are written](../conduct/README.md):
  the template, and what is safe to publish
