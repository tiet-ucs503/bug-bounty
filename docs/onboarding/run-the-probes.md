---
abstract: |
  Check the live hosts from outside, as a user sees
  them: each host through Cloudflare, each service's
  health, the allow-list, the signed-in routes, CORS,
  the rate of writes, www and docs. No AWS.
date: 2026-10-06
keywords:
- probes
- cloudflare
- nginx
kind: how-to
sources:
- probes/Makefile
status: draft
title: Probe Your Hosts
version: v0.1.0
---

## 1 Before You Start

- `curl` and `jq`
- The project rolled out, its records at Cloudflare

## 2 Every Probe but the Token's

Expect a `PASS` line per check, and exit status 0:

``` sh
make -C probes ZONE=example.org
```

  ----------------------------------------------------
  Target       What it checks
  ------------ ---------------------------------------
  hosts        Every host answers through Cloudflare

  health       Each `/health` names its own service

  allow-list   A path not named is `404`;
               `DELETE /health` is `403`

  signed-in    Each signed-in route is `401` without a
               token and with a bad one

  cors         `www`'s preflight `204` with an origin
               and a max age; another origin's `403`

  rate         Sixty writes at once: some `429`, each
               with `Retry-After`, the rest `401`

  www          The UI's page, `200`

  docs         `index.html`, `200`

  static       A missing key, `404`
  ----------------------------------------------------

## 3 Signed In

An access token for your UI's client, from the UI's
sign-in, in a file of its own, mode 0600. It lasts an
hour. Expect `echo signed in 200` for each service:

``` sh
make -C probes token ZONE=example.org TOKEN_FILE="${HOME}/.config/example/token"
```

> [!WARNING]
> Never commit or paste the token. The probe hands it
> to `curl` as a config on a descriptor, never as an
> argument.

## 4 What Can Go Wrong

- **`hosts` fails, `server none`.** The record is
  missing or not proxied
- **`health` names another service.** Two hosts point
  at one service; the owner's rollout has a mistake
- **`rate` sees no `429`.** Your writes went out one at
  a time; or the limit is gone, which the owner should
  hear about

## 5 See Also

- [How the project meets the box](README.md): why each
  answer is the right one
