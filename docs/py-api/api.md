---
abstract: |
  Every route py-api answers, who may call it, and what
  it returns, as the manifest names them.
date: 2026-10-06
keywords:
- py-api
- api
- routes
kind: reference
sources:
- services/py-api/main.py
- box/project.json
status: draft
title: py-api's Routes
version: v0.1.0
---

## 1 The Host

`https://py-api.<zone>`, through Cloudflare alone.
Every response carries `Vary: Origin`; a response to
the UI's origin carries `Access-Control-Allow-Origin`.

## 2 The Routes

GET /health
: Anyone. `200` and
  `{"status": "ok", "service": "py-api"}`. The box's
  check, every 30 s, and the probes'

GET /hello
: Anyone. `200` and a greeting

POST /echo
: Signed in. A JSON body, at most 1 MiB. `200` and
  `{"service": "py-api", "caller": "<sub>", "groups": [...], "body": ...}`,
  with `Cache-Control: no-store`. `401` without a valid
  token; `413` over 1 MiB

## 3 What the Box Answers Instead

  ----------------------------------------------------
  Status   When
  -------- -------------------------------------------
  204      A preflight from the UI's origin

  403      A method the route does not name; a
           preflight from another origin

  404      A path the manifest does not name

  429      Over the rate of writes; `Retry-After: 1`

  502      The service is down or starting
  ----------------------------------------------------

## 4 What Can Go Wrong

- **`413` from nginx, not the service.** The body is
  over 1 MiB; the box refuses it first

## 5 See Also

- [What py-api is](README.md): how a token is checked
