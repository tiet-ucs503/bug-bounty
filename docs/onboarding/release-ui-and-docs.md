---
abstract: |
  Put a new UI on www and new pages on docs: a sync of
  a folder to each bucket, by the project's UI
  maintainer. No build on the box, no reload.
date: 2026-10-06
keywords:
- release
- ui
- docs
- md-preview
kind: how-to
sources:
- ui/app.js
- ui/config.example.js
status: draft
title: Release the UI and These Pages
version: v0.1.0
---

## 1 Before You Start

- **The UI maintainer's sign-in,** a profile the box's
  owner has set up for you. It may write `www.<zone>`
  and `docs.<zone>`, and nothing else
- **`ui/config.js`** filled in, from
  `ui/config.example.js`
- **md-preview,** for these pages, or the builder you
  chose instead

> [!CAUTION]
> `--delete` removes from the bucket every file the
> folder no longer holds. A wrong folder empties the
> site; the previous release is the previous commit,
> synced again.

## 2 The UI

Set the zone and the profile, then sync. Expect one
`upload:` line per changed file:

``` sh
ZONE=example.org
UI_PROFILE=ui-maintainer
aws s3 sync ui/ "s3://www.${ZONE}/" --delete --exclude config.example.js --profile "${UI_PROFILE}"
```

## 3 These Pages

Build them, expecting `docs/_site/` with an
`index.html`:

``` sh
md-preview build docs
```

Then sync the built folder:

``` sh
ZONE=example.org
UI_PROFILE=ui-maintainer
aws s3 sync docs/_site/ "s3://docs.${ZONE}/" --delete --profile "${UI_PROFILE}"
```

The builder is yours to choose: raw HTML, pandoc,
MkDocs, Hugo or another. The box expects static files,
`index.html` as the index, and public pages.

## 4 Check

Expect `PASS` from both:

``` sh
make -C probes www docs ZONE=example.org
```

## 5 What Can Go Wrong

- **The old page still shows.** Cloudflare caches by
  file extension. Name assets by their content's hash,
  or ask the owner to purge
- **`AccessDenied` on the sync.** The profile is not
  the UI maintainer's, or its session has lapsed; sign
  in again
- **A deep link answers `404` with the app.** S3 serves
  `index.html` for a path with no file, with `404`; the
  app loads all the same. A `200` there is the owner's
  choice at Cloudflare

## 6 See Also

- [Probe your hosts](run-the-probes.md)
- [How these pages are written](../conduct/README.md)
