# How the Box Works

What a project needs to know about the box it runs on, without any
control of the box. The box is one EC2 instance and the AWS and
Cloudflare around it, kept by its owner in the box's repository,
`aws-iac`. Your project is code, a manifest and a UI; the owner puts
them on the box.

## 1 The Path of a Request

```
browser ──https──▶ Cloudflare ──https, its client certificate──▶ nginx ──▶ your service
   │                 (your zone)                                 (the box)   (a container)
   │
   └──https──▶ Cloudflare ──http, a secret Referer──▶ S3: your www, docs and static buckets
```

- **Cloudflare is the only way in.** The box's ports 80 and 443 admit
  Cloudflare's addresses alone, and nginx requires Cloudflare's client
  certificate on 443 (Authenticated Origin Pulls). There is no SSH and
  no direct address to call.
- **nginx is a server per API host**, `<service>.<zone>`, rendered
  from your `box/project.json`. It decides three things before your
  code sees a request:
  - **the allow-list:** only the manifest's routes pass, each method as
    named. Anything else is `404`; a wrong method is `403`;
  - **CORS:** your `https://www.<zone>` and your developers' localhost
    alone. A preflight is answered by nginx, `204`, cached two hours;
    any `Access-Control-*` header your service sets is dropped;
  - **the rate of writes:** every method but `GET`, `HEAD` and
    `OPTIONS`, 10 a second per client, 100 a second across the whole
    box. A burst of 20 is queued; the rest get `429` with
    `Retry-After: 1`. Reads are not counted.

  Bodies are at most 1 MiB.
- **Your service** is a container on the box's network, reached by
  name, on the port the manifest names. It decides who the caller is
  and what they may do.
- **`www.<zone>`, `docs.<zone>` and `static.<zone>`** are S3 buckets
  named for those hosts, served by Cloudflare. They are readable only
  through Cloudflare, which adds a secret header the buckets require.
  `www` holds your UI, `docs` your documentation, both released from
  this repository (§5). `static` is for public objects; how your users
  write to it is not yet wired (§8).

## 2 Who Controls What

| You, in this repository | The box's owner |
|---|---|
| Your services' code, Dockerfiles and pinned packages | The instance, nginx, Docker, the compose file |
| `box/project.json`: services, ports, memory, routes | Whether and when a manifest is rolled out |
| The UI's files, and the documentation's pages | Terraform: repositories, builds, buckets, Cognito |
| Your probes, from outside | Cloudflare: records, rules, certificates |
| | Builds, pins, uploads and reloads |
| | Logs, alarms, backups |

You never write nginx, compose or IAM. `box/render.py` writes the
box's pieces from your manifest, and the owner reviews them and copies
them into the box's repository. A change to your routes is a change to
the manifest, rendered and handed over.

## 3 The Manifest

`box/project.json`:

- **`name`:** 2 to 16 characters, lower case and digits. Every name on
  the box is `tu-rgb-sites-<name>-<service>`: repository, build and
  container.
- **`ui.dev_callback_urls`:** `http://localhost:<port>/` addresses
  where a developer runs the UI. Each is a sign-in callback and an
  allowed CORS origin.
- **`services[]`**, each:
  - **`name`:** the API host's label, `<name>.<zone>`;
  - **`language`:** `node` or `python`, for the health check;
  - **`port`:** the port it listens on;
  - **`memory_mib`:** 64 to 512, a hard limit. The box has 1 GiB for
    every project and its database;
  - **`routes[]`:** `method`, `path` and `signed_in`. A path is exact,
    or has `{param}` segments, each 1 to 64 letters, digits, `_` or
    `-`. `GET /health`, not signed in, is required.

`make check` refuses what the box would refuse.

## 4 Rules for a Service

- **`GET /health`** answers `200` when the service can serve. The box
  checks it every 30 s; three failures mark the container unhealthy.
- **Listen on `0.0.0.0`** and the manifest's port; run as a non-root
  user; stop cleanly on `SIGTERM`.
- **Log to stdout,** one JSON object a line. The box sends container
  output to CloudWatch, which its owner reads. Never log a token or a
  header.
- **No secret in the image.** Configuration comes from the
  environment: today the pool's issuer and your UI's client ID, from an
  env file the box writes for your project at upload.
- **Stateless.** No database yet, and the container's disk goes at
  every recreate. State waits for the box's PostgreSQL (§8).
- **Built for arm64**, by the box's CodeBuild from your service's
  folder. The base image by digest from `public.ecr.aws`; every package
  pinned, by a lockfile or by version. `build.sh` and `buildspec.yml`
  are the box's: keep them as they are.
- **Who the caller is:** a Bearer access token from the box's Cognito
  pool. Verify:
  - the signature against the pool's keys, `<issuer>/.well-known/jwks.json`;
  - `iss`, the pool's issuer;
  - `token_use`, `access`;
  - `client_id`, your project's UI client (or the box's probe client).

  Another project's tokens carry another `client_id`; refuse them. The
  starters do all of this, and throttle the refetch of unknown keys.
- **What the caller may do** is yours: `sub` is the user,
  `cognito:groups` their groups in the pool.

## 5 The UI and the Documentation

- **Static files in `www`,** released by a sync of `ui/` to the bucket,
  by the box's owner or the project's UI maintainer, if the owner has
  made one.
- **Single-page routes:** a path with no file answers `index.html`
  with `404`, so a deep link loads the app and its router takes over.
  Whether `www` answers `200` instead is the box owner's choice, at
  Cloudflare.
- **Cloudflare caches by file extension.** Name assets by their
  content's hash, or expect an old copy for a while after a release.
- **Sign-in:** the authorisation code with PKCE, through Cognito's
  hosted pages, called back to the page's root. `ui/app.js` does it,
  with no package and no build.
- **Calls:** `https://<service>.<zone>`, the access token as
  `Authorization: Bearer`. Retry a `429` after its `Retry-After`; sign
  in again on `401`.
- **The documentation in `docs`,** public, no sign-in. The box gives
  it a bucket, and gives your UI maintainer leave to write it as it
  writes `www`. Everything else is yours: raw HTML, or Markdown built
  by pandoc, MkDocs, Hugo, md-preview or anything else, by hand or in
  your CI. `docs/` starts as md-preview pages, built by `md-preview
  build docs` into `docs/_site/`. A release is a sync of the built
  folder; its index is `index.html`, and a missing page is S3's `404`.
  Nothing secret goes here: it is as public as `www`.

## 6 A Change, From Commit to Live

1. **You:** commit; `make check test`; `make render` if the manifest
   changed; hand over the commit, and `box/out/<name>/` if it changed.
   A change to `ui/` or `docs/` alone needs neither build nor reload:
   only its sync to `www` or `docs`.
2. **The owner:** reviews and copies `box/out/<name>/`; uploads your
   service's folder; builds it; pins the new digest; uploads the stack
   and reloads. The box pulls images by digest only, so what runs is
   exactly what was built.
3. **You:** `make -C probes ZONE=<zone>`.

A new base image is a new digest in the Dockerfile. Read it from
`public.ecr.aws`, the index's digest, not one architecture's.

## 7 The First Rollout

`box/out/<name>/ONBOARDING.md`, rendered for your project, is the
owner's list. In short:

- **Cloudflare:** the four kinds of record, the bucket hosts' rules,
  and for a zone of its own, its Origin Pulls and certificate.
- **Terraform:** one plan and apply.
- **The probes:** the box's before and after, then yours.

## 8 Not Yet

- **State:** a database per app, after the box's move to PostgreSQL.
- **CI:** builds run by the owner until your code host and its OIDC
  role exist.
- **Writes to `static`:** the box's reference app writes public
  objects through nginx after a check; for a project, not yet wired.
- **A pool of your own:** the box's pool is shared by its circle.
