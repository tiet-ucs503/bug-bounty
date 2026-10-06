---
abstract: |
  How a request reaches the project, what the box
  decides before your code does, and who controls what.
  Read it before you change a route, a service or the
  UI.
date: 2026-10-06
keywords:
- the-box
- nginx
- cloudflare
- auth
kind: explanation
sources:
- box/render.py
- .github/workflows/release.yml
status: draft
subtitle: Cloudflare, nginx, your containers and three
  buckets
title: How the Project Meets the Box
version: v0.1.0
---

## 1 The Path of a Request

``` mermaid
---
config:
  themeVariables:
    edgeLabelBackground: "#d9eaf2"
  themeCSS: ".edgeLabel, .edgeLabel p, .labelBkg { background-color: #d9eaf2 !important; color: #5c7a8a !important; }"
---
flowchart LR
  browser(["Browser"])
  cf["Cloudflare<br/>your zone"]
  nginx["The box's nginx<br/>allow-list, CORS, limits"]
  svc["Your service<br/>a container"]
  s3[("S3<br/>www, docs, static")]
  browser -->|"HTTPS"| cf
  cf -->|"HTTPS, its client certificate"| nginx
  nginx --> svc
  cf -->|"HTTP, a secret Referer"| s3
  classDef network fill:#dbeafe,stroke:#3b82f6,color:#111
  class cf network
  classDef compute fill:#fff6eb,stroke:#804900,color:#804900
  class nginx,svc compute
  classDef storage fill:#dcfce7,stroke:#22c55e,color:#111
  class s3 storage
```

- **Cloudflare is the only way in.** The box admits
  Cloudflare's addresses alone, and nginx requires
  Cloudflare's client certificate. There is no other
  address to call and no SSH
- **nginx is a server per service,**
  `<service>.<zone>`, written from your manifest by
  `make render`
- **`www`, `docs` and `static`** are buckets named for
  their hosts, readable only through Cloudflare

## 2 What nginx Decides First

Before a request reaches your service, nginx has
already decided:

- **The allow-list.** Only the manifest's routes pass,
  each with its methods. Any other path is `404`; a
  method the route does not name is `403`. A route your
  code adds is unreachable until the manifest names it
  and the box's owner rolls it out
- **CORS.** `https://www.<zone>` and the developers'
  localhost from `ui.dev_callback_urls` alone. nginx
  answers a preflight itself, `204`, cached for two
  hours, and drops any `Access-Control-*` header your
  service sets
- **The rate of writes.** Every method but `GET`,
  `HEAD` and `OPTIONS`: 10 a second per client, 100 a
  second across the whole box. A burst of 20 waits its
  turn; the rest are `429` with `Retry-After: 1`. Reads
  are not counted
- **The size of a body,** 1 MiB at most

## 3 What Your Service Decides

- **Who the caller is:** a Bearer access token from the
  box's Cognito pool, verified by the service: its
  signature against the pool's keys, its issuer,
  `token_use` of `access`, and `client_id` your
  project's UI client or the box's probe client.
  Another project's token carries another `client_id`,
  and is refused
- **What the caller may do:** yours. `sub` names the
  user, `cognito:groups` their groups

## 4 Who Controls What

  -----------------------------------------------------
  You, in this repository    The box's owner
  -------------------------- --------------------------
  The services' code,        The instance, nginx,
  Dockerfiles and pinned     Docker, the compose file
  packages; the migrations   

  The manifest: services,    Whether and when a
  ports, memory, routes,     manifest is rolled out
  prefixes                   

  The UI, these pages and    The buckets, the Cognito
  static files               clients, the records at
                             Cloudflare

  Releases: a tag, and the   The CI role a release
  workflow it runs           works as; the reading of
                             its record

  The probes, from outside   Logs and alarms
  -----------------------------------------------------

You never write nginx, compose or IAM. `make render`
writes the box's pieces from the manifest; the owner
reads them and copies them into the box's repository. A
release tag builds images and syncs buckets through one
role, and the box takes nothing from it but digests:
[How a release reaches the box](ci-cd.md).

## 5 The Limits

- **Memory:** the box has 1 GiB for every project and
  its database. Each service is held to its
  `memory_mib`, so a leak takes its own container and
  no other
- **State:** one database per project, each service's
  part under its prefix ([The
  database](../migrations/README.md)), on the box once
  its `feature/postgres` is done. A container's disk
  goes at every recreate
- **Builds:** arm64, by the box's CodeBuild from your
  service's folder, started by a release tag

## 6 What Can Go Wrong

- **A new route answers `404`.** The manifest does not
  name it yet, or the owner has not rolled the manifest
  out. See [Hand a change to the box's
  owner](hand-over.md)
- **The UI's calls fail with a CORS error.** The page's
  origin is neither `https://www.<zone>` nor a
  localhost in `ui.dev_callback_urls`
- **Writes come back `429`.** The rate limit, as
  designed: wait for `Retry-After` and try again, as
  `ui/app.js` does

## 7 See Also

- [From a fork to a live project](first-rollout.md):
  the whole path once
- [The manifest, key by key](manifest.md): what each
  key does
