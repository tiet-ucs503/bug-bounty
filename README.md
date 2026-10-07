# A Project on the Box

A template for a project whose API, UI and documentation run on the
box kept by `aws-iac`. Fork it on GitHub, name your project, write
your services, migrations, UI and pages; a release is a tag. The box's
owner rolls the project out once, in a few Cloudflare, Terraform and
probe steps; after that, every release reaches the box by itself.
You need no AWS access and no control of the box.

Start with `docs/`, at `docs/README.md`, or run `md-preview docs`.

## What Is Here

    services/js-api/          a service in Node 24: Fastify, jose
    services/py-api/          a service in Python 3.12: FastAPI, PyJWT
    migrations/               the project's one database: dbmate, the SQL, its image
    ui/                       the UI, a single-page app with no build step, at www
    static/                   public files, added to static by a release
    docs/                     these pages, for md-preview, published at docs
    box/                      the manifest, its render, the box's build script
    tools/                    the release's steps: plan, build, record
    .github/workflows/        CI on every push; a release on every tag vX.Y.Z
    dev/                      the local stack's mock sign-in; dev/out/ rendered
    probes/Makefile           checks of your live hosts from outside, no AWS

Each image's folder, a service or `migrations/`, holds its own
`Dockerfile`, and the box's `build.sh` and `buildspec.yml`.

## Start

1. **Fork this repository** on GitHub.
2. **Name the project** in `box/project.json`: `name`, `github`,
   `database`, and each service's `prefix`.
3. **Check and test:**

       make check
       make test

4. **Render, and hand over** `box/out/<name>/` to the box's owner:

       make render

5. **Set the repository's variables** the owner gives you, and tag the
   first release, `v0.1.0`.

`docs/onboarding/first-rollout.md` has the whole path.

## Developing

- **The services' tests** run offline: `make test`
- **The whole stack, locally:** `make dev`: the box's nginx in front of
  your services, a mock sign-in, PostgreSQL with your migrations, the
  buckets as folders. Needs Docker; `docs/onboarding/local-dev.md` has
  the ways without Docker or root
- **The UI:** `make ui`, on `http://localhost:5173/`
- **A schema change:** `make db-new`, `make db-lint`, `make db`
- **What a release would do:** `make plan TAG=v0.2.0`

## Releasing

A tag `vX.Y.Z`. The workflow builds the image of each service or
`migrations/` that changed since the tag before, writes their digests
to the record the box reads, and syncs `www`, `docs` or `static` if
`ui/`, `docs/` or `static/` changed. A change to `box/project.json` is
handed to the box's owner. `docs/onboarding/ci-cd.md` explains it, and
`docs/onboarding/release-by-hand.md` is the same by hand.
