---
abstract: |
  What py-api is, how it decides who the caller is, and
  what the box does in front of it. Read it before you
  add a route or a client.
date: 2026-10-06
keywords:
- py-api
- auth
- cognito
kind: explanation
sources:
- services/py-api/main.py
- box/project.json
status: draft
subtitle: The project's service in Python, at
  py-api.`<zone>`{=html}
title: What py-api Is, and Who May Call It
version: v0.1.0
---

## 1 What It Is

A starter service in Python: Python 3.12, FastAPI, and
PyJWT for tokens. Stateless, one process, listening on
port 8000. Its routes show the shape every service of
the project keeps, and are replaced by yours: see [its
routes](api.md).

## 2 In Front of It

The box's nginx, from the manifest's entry for py-api:
the allow-list, CORS for the UI, the rate of writes and
the 1 MiB body. The service does none of these, and a
CORS header it set would be dropped. See [How the
project meets the box](../onboarding/README.md).

## 3 Who the Caller Is

A signed-in route reads `Authorization: Bearer <token>`
and accepts it only if:

- the box's Cognito pool signed it, by a key set
  fetched with urllib, an unknown key refetched at most
  every five minutes, so a forged token cannot make the
  service fetch on every request
- its issuer is the pool's, `COGNITO_ISSUER`
- `token_use` is `access`, not an ID token
- `client_id` is the project's UI client,
  `COGNITO_UI_CLIENT_ID`, or the box's probe client,
  `COGNITO_PROBE_CLIENT_ID`

Otherwise `401`, with `WWW-Authenticate: Bearer`.
Without `COGNITO_ISSUER` or a client, no token is
accepted. The three come from an env file the box
writes for the project; none is a secret.

## 4 What the Caller May Do

The service's own business. The starter lets any
signed-in caller echo; `sub` names the user and
`cognito:groups` their groups, for a rule of your own.

## 5 Its Log

uvicorn's access lines on stdout, which carry no
header. The box sends it to CloudWatch, which its owner
reads. Never log a token.

## 6 What Can Go Wrong

- **Every signed-in call is `401`.** The env file is
  missing or its client is not the UI's; the UI sends
  an ID token, not the access token; or the token has
  lapsed, after an hour
- **The service answers locally but `404` live.** The
  manifest does not name the route

## 7 See Also

- [py-api's routes](api.md)
- [Develop and change py-api](develop.md)
