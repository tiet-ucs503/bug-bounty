---
abstract: |
  Every route js-api answers, who may call it, and what
  it returns, as the manifest names them.
date: 2026-10-06
keywords:
- js-api
- api
- routes
kind: reference
sources:
- services/js-api/server.js
- box/project.json
status: draft
title: js-api's Routes
version: v0.1.0
---

## 1 The Host

`https://js-api.<zone>`, through Cloudflare alone.
Every response carries `Vary: Origin`; a response to
the UI's origin carries `Access-Control-Allow-Origin`.

## 2 The Routes

The same, made from the code and tried from a page:
`https://js-api.<zone>/scalar-ui` ([the API's
conduct](../conduct/api.md)).

> [!WARNING]
> Each entry below repeats a route's description in the
> code, and is written by hand. `make check` warns when
> the manifest names a route with no entry here, or an
> entry names a route the manifest does not. It does
> not compare the words: when you change a route,
> change its entry in the same commit.

GET /health
: Anyone. `200` and
  `{"status": "ok", "service": "js-api"}`. The box's
  check, every 30 s, and the probes'

GET /hello
: Anyone. `200` and a greeting

POST /echo
: Signed in. A JSON body, at most 1 MiB. `200` and
  `{"service": "js-api", "caller": "<sub>", "groups": [...], "body": ...}`,
  with `Cache-Control: no-store`. `401` without a valid
  token; `413` over 1 MiB

GET /openapi.json
: Anyone. `200` and the service's OpenAPI document,
  made from its routes

GET /scalar-ui
: Anyone. `200` and Scalar's page of that document, to
  read the routes and try them

Your fork adds routes as [the
tutorials](../tutorials/README.md) go: `/users` in
tutorial 4, if you take JavaScript there. Each tutorial
gives the entries for this page; add them here, in the
same commit as the routes.

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

- [What js-api is](README.md): how a token is checked
