---
abstract: |
  Run the dev stack in containers without root:
  rootless Podman and podman-compose, from your
  distribution or from conda-forge into your own
  directory. What the box's administrator must have
  given you, how to set Podman up, and how it differs
  from Docker.
date: 2026-10-06
keywords:
- local-dev
- podman
- mock
- db
kind: how-to
sources:
- box/render.py
- Makefile
status: draft
subtitle: The same containers, without root
title: Run the Stack with Rootless Podman
version: v0.1.0
---

## 1 Before You Start

- **Linux,** with user namespaces, which every current
  distribution allows

- **Subordinate IDs for your user,** given once by the
  machine's administrator. Expect a line in each file,
  your name and two numbers:

  ``` sh
  grep "^$(id -un):" /etc/subuid /etc/subgid
  ```

- **`newuidmap` and `newgidmap`,** installed by the
  administrator with the distribution's `shadow` or
  `uidmap` package. Expect both paths:

  ``` sh
  command -v newuidmap newgidmap
  ```

- **About 3 GB of disk,** for the images

If either is missing, ask the administrator for exactly
this: "the `uidmap` tools, and subordinate IDs for my
user, 65536 of each, so I can run rootless Podman".
Nothing else on this page needs root.

Tried 2026-10-06 with Podman 5.8.3 and podman-compose
1.5.0 from conda-forge, on Linux 7.2: every container
of the stack up, and the checks of [the dev stack's
page](local-dev.md) §4 passing through its nginx.

## 2 Install Podman

**From the distribution,** if the administrator
installed it; `make install-deps STACK=podman` does,
where you may use `sudo` ([the
tutorials](../tutorials/README.md) §2). Expect a
version, and `podman-compose` beside it:

``` sh
podman --version
command -v podman-compose
```

**Or from conda-forge,** into a folder of your own,
with [micromamba](shared-box.md) (§2 there). Expect
`Transaction finished`:

``` sh
"${HOME}/.local/bin/micromamba" create -y -p "${HOME}/.local/envs/podman" -c conda-forge podman netavark aardvark-dns crun fuse-overlayfs slirp4netns podman-compose
export PATH="${HOME}/.local/envs/podman/bin:${PATH}"
```

## 3 Set Podman Up

A distribution's Podman needs nothing here; skip to §4.
One from conda-forge must be told where its helpers
are, and given a policy for pulling images. All of it
in your own `~/.config/containers/`:

``` sh
P="${HOME}/.local/envs/podman"
mkdir -p "${HOME}/.config/containers"
cp "${P}/etc/containers/policy.json" "${P}/etc/containers/registries.conf" "${HOME}/.config/containers/"
cat > "${HOME}/.config/containers/containers.conf" <<EOF
[engine]
helper_binaries_dir = ["${P}/lib/podman", "${P}/libexec/podman", "${P}/bin"]
conmon_path = ["${P}/bin/conmon"]
[engine.runtimes]
crun = ["${P}/bin/crun"]
[network]
network_backend = "netavark"
default_rootless_network_cmd = "slirp4netns"
EOF
```

`slirp4netns`, because conda-forge has no `pasta`,
Podman's newer default.

Then expect `true netavark crun`:

``` sh
podman info --format '{{.Host.Security.Rootless}} {{.Host.NetworkBackend}} {{.Host.OCIRuntime.Name}}'
```

## 4 Start the Stack

As with Docker, through the Makefile, telling it the
compose command. The first run builds the images and
takes some minutes. Expect each container named, then
the prompt:

``` sh
make dev COMPOSE=podman-compose
```

Expect `db-users` and `migrate` `Exited (0)`, the rest
`Up`:

``` sh
podman ps -a --format '{{.Names}} {{.Status}}'
```

## 5 Use It

Every check of [the dev stack's page](local-dev.md), §4
to §7, answers the same:
`http://js-api.localhost:8080/health`, a token from
`make dev-token`, the UI on `http://localhost:5173/`,
the database on `localhost:5432`. The Makefile's other
compose targets take the same setting:

``` sh
make db COMPOSE=podman-compose CMD=status
```

## 6 Stop

Expect each container stopped and removed, about ten
seconds each; the database's volume is kept:

``` sh
make dev-down COMPOSE=podman-compose
```

## 7 How It Differs From Docker

- **Health checks never run without systemd.** Rootless
  Podman runs them through systemd's timers; where
  there are none, `podman ps` shows each service
  `(starting)` for good. Harmless here: the stack never
  waits on a health check, `db-users` waits for the
  database itself
- **The DNS resolver is the network's gateway,** not
  Docker's `127.0.0.11`. The stack's nginx is a
  template the nginx image fills with the container's
  own resolver at start, so it works in both
- **Ports below 1024** cannot be published without
  root; the stack uses 5432, 8080 and 9000
- **Images are named in full,** `public.ecr.aws/...`
  and `ghcr.io/...`, so Podman never asks which
  registry is meant

## 8 What Can Go Wrong

- **`no policy.json file found`.** §3's copy into
  `~/.config/containers/` is missing
- **`could not find pasta`.** §3's
  `default_rootless_network_cmd` is missing
- **`cannot set up namespace using "/usr/bin/newuidmap"`,
  or `insufficient UIDs or GIDs`.** §1's subordinate
  IDs or `uidmap` tools; only the administrator can
  give them
- **A container named `db-users` waits a minute, then
  fails.** The database did not start;
  `podman logs example-dev_db_1`
- **`address already in use`.** Something else holds
  5432, 8080 or 9000; stop it, or [run the stack
  without containers](shared-box.md) on ports of your
  own

## 9 See Also

- [A local stack that mirrors the box](local-dev.md):
  what each piece is
- [Develop on a shared box without
  root](shared-box.md): the same stack with no
  containers at all
