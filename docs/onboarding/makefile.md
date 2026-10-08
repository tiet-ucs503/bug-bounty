---
abstract: |
  Every target of the project's Makefile: what it does,
  what it needs, the variables it reads, and what it
  prints. And every variable, with its default.
date: 2026-10-07
keywords:
- make
- makefile
- targets
- reference
kind: reference
sources:
- Makefile
- tools/check-deps.sh
- tools/release-plan.sh
- box/render.py
status: draft
title: The Makefile, Target by Target
version: v0.1.0
---

Run from the repository's root, with GNU make. Nothing
here talks to AWS, Cloudflare or the box: every target
is local work. `make` alone is `make check`.

## 1 The Tools

install-deps
: Installs what the tutorials need, by your system's
  own packages, then runs `check-deps`. Arch, Alpine,
  Debian, Ubuntu and their relatives, and macOS by
  Homebrew. It uses `sudo` unless you are root.
  `STACK=docker` or `STACK=podman` adds the engine. It
  never adds you to the `docker` group

check-deps
: One line a tool: `ok`, `old` or `none`. Exits 1 if
  any is old or missing. `STACK` adds the engine's own
  lines

## 2 Check and Test

check
: The manifest against its rules, and what the box
  would refuse: each folder in `services/` named in the
  manifest and each named there a folder; `build.sh`
  and `buildspec.yml` the box's own in every image's
  folder; each Node lockfile agreeing with its
  `package.json`. It also warns, without failing, where
  a service's `api.md` and the manifest name different
  routes ([the API's conduct](../conduct/api.md), A5).
  Writes nothing. CI runs it on every push

render
: `check`, then the box's pieces into
  `box/out/<name>/`: the manifest normalised, the nginx
  servers, the compose file, and the box owner's steps

test
: Every service's tests, offline, by its language in
  the manifest. Node: `npm ci`, then `npm test`.
  Python: a `.venv` in the service's folder, its
  `requirements.txt` and `httpx`, then `unittest`. CI
  runs it on every push

## 3 The Local Stack

dev
: `check`, then the dev stack rendered into `dev/out/`
  and started: nginx, the services, a mock sign-in,
  PostgreSQL, the buckets as folders. Builds the pages
  too, if `md-preview` is installed. Needs Docker, or
  Podman with `COMPOSE=podman-compose`

dev-down
: Stops the dev stack

dev-token
: Prints an access token from the mock sign-in, for
  `curl`. `SUB`, `EMAIL`, `VERIFIED` and `GROUPS` say
  who; `MOCK_URL` says where the mock listens

ui
: Serves the UI on `http://localhost:5173/`. The
  starter's `ui/` as it is; once `ui/package.json`
  exists, Vite's dev server. Refuses to start without
  the UI's `config.js`. `UI_PORT` chooses another port

## 4 The Database

db-new
: Makes an empty migration,
  `migrations/sql/<time>_<PREFIX>_<NAME>.sql`, with its
  `up` and `down` and their timeouts, and prints the
  path. `PREFIX` must be one the manifest names; `NAME`
  is 3 to 61 lower-case letters, digits and `_`, a
  letter first

db-lint
: Squawk, at a fixed version, on every migration.
  Expect `Found 0 issues`. Needs `npx`, and the network
  the first time. CI runs it on every push

db
: dbmate in the dev stack, as the migrator: `CMD` is
  `status`, `up`, `rollback`, or `dump`, which writes
  `migrations/schema.sql`. Needs the dev stack up. On
  the native stack, call `dbmate` itself ([shared
  box](shared-box.md))

## 5 The Pages and the Release

docs-build
: These pages, by `md-preview`, into `docs/_site/`

plan
: What a release of `TAG` would build and sync, against
  the tag before it: a line each, `build <unit>`,
  `sync <bucket>`, or `hand-over`. `TAG` must be a tag
  that exists

## 6 The Variables

Each is given on the command line, as `make db CMD=up`.

  ---------------------------------------------------------------------------
  Variable     Read by           Default                   Says
  ------------ ----------------- ------------------------- ------------------
  `STACK`      `install-deps`,   none                      `docker` or
               `check-deps`                                `podman`: the
                                                           engine too

  `COMPOSE`    `dev`,            `docker compose`          the compose
               `dev-down`, `db`                            command;
                                                           `podman-compose`

  `UI_PORT`    `ui`              `5173`                    the UI's port

  `SUB`        `dev-token`       `dev-user`                whose token

  `EMAIL`      `dev-token`       `<SUB>@example.org`       their e-mail

  `VERIFIED`   `dev-token`       `true`                    whether the e-mail
                                                           is verified

  `GROUPS`     `dev-token`       none                      the pool's groups,
                                                           comma-separated

  `MOCK_URL`   `dev-token`       `http://localhost:9000`   the mock sign-in's
                                                           address

  `PREFIX`     `db-new`          none, required            the unit's prefix,
                                                           as the manifest
                                                           has it

  `NAME`       `db-new`          none, required            what the migration
                                                           does, `lower_case`

  `CMD`        `db`              `status`                  dbmate's command

  `TAG`        `plan`            none, required            the release's tag,
                                                           `vX.Y.Z`
  ---------------------------------------------------------------------------

## 7 The Other Makefile

`probes/Makefile` checks your live hosts from outside,
through Cloudflare. It is not included here, and is run
as `make -C probes ZONE=<your zone>`: [Probe your
hosts](run-the-probes.md).

## 8 What Can Go Wrong

- **`PREFIX=<a service's prefix>: js_api, py_api`.**
  `db-new` was given no prefix, or one the manifest
  does not name. The list is the ones it does
- **`NAME=<lower_case_words>`.** `db-new`'s name has a
  capital, a hyphen or a space, or is under three
  characters
- **`install-deps: no recipe for this system`.** Not
  one of the five systems. [The tutorials'
  page](../tutorials/README.md) §2 lists what to
  install by hand
- **`release-plan: no tag v0.2.0`.** `plan` reads tags,
  not branches. Tag first, or name a tag that exists
- **`no ui/config.js`.** Copy `ui/config.example.js`;
  for a Svelte UI, `ui/config.dev.example.js` to
  `ui/public/config.js`
- **`db` or `dev-down` cannot find
  `dev/out/compose.yml`.** The dev stack was never
  rendered: `make dev` first
- **`old  make, not GNU's`.** macOS's own make. Use
  `gmake`, or put Homebrew's first on `PATH`, as
  `install-deps` prints

## 9 See Also

- [The manifest, key by key](manifest.md): what `check`
  holds the manifest to
- [A local stack that mirrors the box](local-dev.md):
  `dev`, `dev-token` and `db`, in use
- [Write a
  migration](../migrations/write-a-migration.md):
  `db-new`, `db-lint` and `db`, in use
- [How a release reaches the box](ci-cd.md): what
  `plan` foretells
