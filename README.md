# A Project on the Box

A template for a project whose API and UI run on the box kept by
`aws-iac`. Fork it, name your project, write your services and UI; the
box's owner rolls it out in a few Cloudflare, Terraform and probe
steps. You need no AWS access and no control of the box.

Start with [docs/how-the-box-works.md](docs/how-the-box-works.md).

## What Is Here

    box/project.json      your project, as the box sees it: services, ports, memory, routes
    box/render.py         the box's pieces from it, into box/out/<name>/, for the owner
    box/build.sh          the box's build script; every service holds a copy
    services/js-api/      a starter in Node 24: Fastify, jose
    services/py-api/      a starter in Python 3.12: FastAPI, PyJWT
    ui/                   a UI with no build step: PKCE sign-in, calls to both services
    probes/Makefile       checks of your live hosts from outside, no AWS
    docs/                 how the box works

## Start

1. **Fork this repository.**
2. **Name the project:** `name` in `box/project.json`, 2 to 16
   characters, lower case and digits.
3. **Shape the services.** Keep, rename or remove `js-api` and
   `py-api`. Every folder in `services/` is named in the manifest, and
   every service in the manifest has a folder. A new service starts as
   a copy of a starter.
4. **Check and test:**

       make check
       make test

5. **Render, and hand over:**

       make render

   Give the owner your repository's commit and `box/out/<name>/`.
   `box/out/<name>/ONBOARDING.md` is their list.
6. **After the rollout,** the owner gives you the zone, Cognito's
   sign-in domain and your UI's client ID. Copy `ui/config.example.js`
   to `ui/config.js` and fill them in.
7. **Probe your hosts:**

       make -C probes ZONE=<your zone>

## Developing

- **The services' tests** run offline, against a key pair standing in
  for Cognito's (`make test`).
- **The UI:** `make ui` serves it on `http://localhost:5173/`, which
  the manifest lists as a callback and a CORS origin, so it signs in
  and calls your live services.
- **A new route** is code in the service and a line in the manifest.
  Until the owner rolls the manifest out, nginx answers it `404`.

## The Box's Side

The box's own work for projects is `aws-iac`'s `todo.md` §51:
- **include points** for each project's nginx and compose pieces;
- **Terraform** over `projects/*/project.json`;
- **its policies by pattern;**
- **a probe per project.**

Until those are done, the owner wires a project's pieces in by hand,
as for the box's second app.
