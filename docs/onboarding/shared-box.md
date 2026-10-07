---
abstract: |
  Run the whole project on a machine you share and
  cannot install on: no Docker and no root. The tools
  in your own directory, PostgreSQL on a port of your
  own, the box's nginx in front of your services, the
  mock sign-in, and the UI in your own browser through
  SSH.
date: 2026-10-06
keywords:
- local-dev
- shared-box
- mock
- db
- nginx
kind: how-to
sources:
- tools/native-dev.sh
- box/render.py
- dev/mock-auth/server.py
- Makefile
status: draft
subtitle: No Docker, no root, the same stack
title: Develop on a Shared Box Without Root
version: v0.1.0
---

## 1 Before You Start

- **A shell on the box,** Linux on x86-64 or arm64,
  with `git`, `curl` and `bash`. Nothing else, and no
  root
- **About 2 GB of disk** in your home directory, for
  the tools
- **Your own machine,** with a browser and `ssh`, for
  the UI (§10)
- **What you get:** the same pieces as [the dev
  stack](local-dev.md), each run as a program of yours.
  nginx with the box's servers, each service on its own
  port, the mock sign-in, the mock static bucket, and
  PostgreSQL with the project's database. All of it
  listens on `127.0.0.1` alone, and writes only in
  `dev/out/native/`. A Python service runs as
  `main:app` from its folder, a Node service as
  `server.js`, the starters' shape

> [!WARNING]
> Everyone on the box can reach `127.0.0.1`, and the
> mock sign-in admits anyone as anyone. Choose your own
> database password (§5), and keep nothing real in the
> stack.

## 2 Install micromamba

micromamba installs packages into a folder of yours,
from conda-forge, with no root. Fetch its single binary
into `~/.local/bin`. Expect its version:

``` sh
mkdir -p "${HOME}/.local/bin"
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C "${HOME}/.local" bin/micromamba
"${HOME}/.local/bin/micromamba" --version
```

On arm64, `linux-aarch64` for `linux-64`.

## 3 Install the Tools

Node, Python, PostgreSQL, nginx, `jq`, GNU `make` and
`openssl`, in one environment of your own. Expect a
list of packages, then `Transaction finished`:

``` sh
"${HOME}/.local/bin/micromamba" create -y -p "${HOME}/.local/envs/project-dev" -c conda-forge nodejs=24 python=3.12 postgresql=17 nginx jq make openssl
```

Then dbmate, a single binary, checked against the
SHA-256 its release publishes. Expect the two lines to
show the same hash:

``` sh
curl -sSLo "${HOME}/.local/bin/dbmate" https://github.com/amacneil/dbmate/releases/download/v2.36.0/dbmate-linux-amd64
chmod +x "${HOME}/.local/bin/dbmate"
sha256sum "${HOME}/.local/bin/dbmate"
curl -s https://api.github.com/repos/amacneil/dbmate/releases/tags/v2.36.0 | "${HOME}/.local/envs/project-dev/bin/jq" -r '.assets[] | select(.name == "dbmate-linux-amd64") | .digest'
```

On arm64, `dbmate-linux-arm64` in both.

Put both folders on your `PATH`, in this shell and in
your shell's startup file. Expect each tool's path:

``` sh
export PATH="${HOME}/.local/bin:${HOME}/.local/envs/project-dev/bin:${PATH}"
command -v node python3 initdb pg_ctl psql pg_dump nginx jq make openssl dbmate
```

Then the tutorials' check, [their
page](../tutorials/README.md) §2.3. Expect every line
to start `ok`:

``` sh
make check-deps
```

## 4 Your Ports

Each user's ports come from their user ID, so two users
on one box do not meet: ten in a row for the stack,
then one per service. From the project's root, expect
your base and each port:

``` sh
tools/native-dev.sh ports
```

To check that nobody holds them, expect no output:

``` sh
ss -ltn | grep -E ":($(tools/native-dev.sh ports | awk '/^  [A-Z_]*PORT/ {print $2}' | paste -sd'|' -)) "
```

If something does, choose another base, say
`DEV_BASE_PORT=41000`, and export it in every shell you
use for the project.

## 5 Your Database Password

Your own, kept in a file only you can read. Expect no
output:

``` sh
mkdir -p "${HOME}/.config/project-dev"
( umask 077; openssl rand -hex 16 > "${HOME}/.config/project-dev/db-password" )
export DEV_DB_PASSWORD="$(cat "${HOME}/.config/project-dev/db-password")"
```

Export it in every shell you use for the project, as
the last line does.

## 6 Set It Up, Once

The database's data folder, the project's database and
its two logins, and every service's packages. Expect,
at the end,
`native-dev: ready: tools/native-dev.sh start`:

``` sh
tools/native-dev.sh init
```

## 7 Start It

PostgreSQL, the migrations, the mock sign-in, each
service, then nginx. Expect `Applied:` for any
migration not yet run, then `native-dev: up` with the
addresses:

``` sh
tools/native-dev.sh start
```

Then expect each piece `running` and each service's
health `200`:

``` sh
tools/native-dev.sh status
```

## 8 Call a Service

Through nginx, as the box would answer. Read your ports
into this shell first:

``` sh
. dev/out/native/env.sh
curl -s "http://js-api.localhost:${NGINX_PORT}/health"
```

Expect `{"status":"ok","service":"js-api"}`. A
signed-in route, with a token from the mock; expect
`200` and `bhanu` as the caller:

``` sh
. dev/out/native/env.sh
TOKEN=$(curl -s -H 'Content-Type: application/json' -d '{"sub": "bhanu", "client_id": "dev-probe"}' "http://localhost:${MOCK_PORT}/dev/token" | jq -r .access_token)
curl -s -X POST -H "Authorization: Bearer ${TOKEN}" -H 'Content-Type: application/json' -d '{"n": 1}' "http://js-api.localhost:${NGINX_PORT}/echo"
```

## 9 Use the Database

As the services' login, expect a `psql` prompt:

``` sh
. dev/out/native/env.sh
psql "${DATABASE_URL}"
```

## 10 The UI, in Your Own Browser

The browser runs on your machine, not on the box. Serve
the UI on the box, then carry its three ports to your
machine over SSH.

On the box, with your ports in its config:

``` sh
. dev/out/native/env.sh
cp dev/out/native/config.js ui/config.js
make ui UI_PORT="${UI_PORT}"
```

A Svelte UI ([6 A Svelte
UI](../tutorials/6-a-svelte-ui/README.md)) reads its
config from `ui/public/` instead:

``` sh
. dev/out/native/env.sh
cp dev/out/native/config.js ui/public/config.js
make ui UI_PORT="${UI_PORT}"
```

On your machine, in another terminal, with the box's
name and your three ports from §4; expect it to wait,
saying nothing:

``` sh
BOX=dev.example.org
NGINX_PORT=40000
MOCK_PORT=40001
UI_PORT=40003
ssh -N -L "${NGINX_PORT}:localhost:${NGINX_PORT}" -L "${MOCK_PORT}:localhost:${MOCK_PORT}" -L "${UI_PORT}:localhost:${UI_PORT}" "${BOX}"
```

Open `http://localhost:40003/`, your `UI_PORT`. **Sign
in** shows the mock's form. Your machine resolves
`js-api.localhost` to itself, and the tunnel carries it
to the box's nginx.

## 11 After a Change

- **A service's code, or a migration:** stop and start;
  a start runs any new migration first

  ``` sh
  tools/native-dev.sh stop
  tools/native-dev.sh start
  ```

- **The manifest:** start again. It renders nginx
  afresh and reloads it

- **The UI:** reload the page

- **A setting of your own** for every service:
  `KEY=value` lines in `dev/dev.env`, read at `start`

## 12 Stop

Expect `native-dev: stopped`; the database's data stays
in `dev/out/native/pg`:

``` sh
tools/native-dev.sh stop
```

> [!CAUTION]
> Removing `dev/out/` removes the database with it.
> Stop first, and keep nothing there you need.

## 13 What Can Go Wrong

- **`no ... on PATH`.** §3's `export` is missing from
  this shell
- **`DEV_DB_PASSWORD unset`.** §5's `export` is missing
  from this shell
- **`a service is not answering`.** Its log says why:
  `dev/out/native/<service>.log`; nginx's is
  `nginx-error.log`
- **PostgreSQL will not start:
  `Unix-domain socket path ... is too long`.** A
  socket's path has at most 107 bytes. The script turns
  the socket off and listens on `127.0.0.1`; a hand-run
  `pg_ctl` should pass `-c unix_socket_directories=`
  too
- **`bind() ... failed (98: Address already in use)`.**
  Another user holds a port: choose another
  `DEV_BASE_PORT`, §4
- **Every signed-in call is `401` after a restart.**
  The mock makes a new key at each start; sign in again
- **The browser cannot reach the UI.** The tunnel is
  not running, or forwards other ports than
  `tools/native-dev.sh ports` shows

## 14 See Also

- [A local stack that mirrors the box](local-dev.md):
  the same, with Docker
- [Run the stack with rootless Podman](podman.md):
  containers, without root, where the box allows them
- [Write a
  migration](../migrations/write-a-migration.md)
