#!/usr/bin/env python3
"""Render, from box/project.json, the pieces the box's owner rolls out.

    python3 box/render.py            check the manifest, write box/out/<name>/
    python3 box/render.py --check    check it alone, write nothing
    python3 box/render.py --dev      write dev/out/, the local stack
    python3 box/render.py --units    list what a release builds: services, migrations
    python3 box/render.py --native   write dev/out/native/, the stack without Docker or root

Into box/out/<name>/, for the box's owner to copy into the box's
repository as projects/<name>/ and review there:

    project.json    the manifest, checked and normalised; the box's
                    Terraform reads it for repositories, builds,
                    buckets and your UI's Cognito client
    nginx.conf.in   a server per service, each its own allow-list;
                    ${ZONE} is filled at the box's upload from your
                    zone, which the box's owner holds, never committed
    compose.yml     a service per service, unpinned until its first
                    build: sha256:0...0, which the box refuses to upload
    ONBOARDING.md   the box owner's steps for this project, by name

With --dev, into dev/out/ instead, for docs/onboarding/local-dev.md:
the same nginx servers on plain HTTP at <service>.localhost:8080, and
a compose file that builds each service from services/ beside a mock
Cognito, PostgreSQL, the buckets as folders, and a mock of the static
bucket's objects/, which services write at run time.

Python's standard library alone, so it runs anywhere. Nothing here
talks to AWS or Cloudflare. docs/onboarding/README.md says what each
piece does on the box.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOX = "tu-rgb-sites"  # the box's project: every name of yours sits under it
UNPINNED = "sha256:" + "0" * 64
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
LANGUAGES = {
    "node": ["CMD", "node", "-e",
             "fetch('http://localhost:{port}/health').then(r => process.exit(r.ok ? 0 : 1), () => process.exit(1))"],
    "python": ["CMD", "python", "-c",
               "import urllib.request; urllib.request.urlopen('http://localhost:{port}/health', timeout=5)"],
}
RESERVED_LABELS = {"www", "static", "docs"}

NAME = re.compile(r"^[a-z][a-z0-9]{1,15}$")
GITHUB = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
PREFIX = re.compile(r"^[a-z][a-z0-9_]{1,20}$")
SERVICE = re.compile(r"^[a-z][a-z0-9-]{0,18}[a-z0-9]$")
SEGMENT = re.compile(r"^(?:[A-Za-z0-9._-]+|\{[a-z][a-z0-9_]{0,19}\})$")


class Bad(Exception):
    pass


def check(m: dict) -> dict:
    """The manifest, checked, with defaults filled; Bad otherwise"""
    if not isinstance(m, dict):
        raise Bad("the manifest is not an object")
    name = m.get("name", "")
    if not NAME.match(name):
        raise Bad(f"name {name!r}: 2 to 16 characters, lower case and digits, a letter first")
    ui = m.get("ui") or {}
    dev = ui.get("dev_callback_urls", [])
    for u in dev:
        if not re.match(r"^http://localhost(:[0-9]{2,5})?/[A-Za-z0-9._/-]*$", u):
            raise Bad(f"ui.dev_callback_urls: {u!r} is not http://localhost[:port]/...; Cognito allows http there alone")
    github = m.get("github", "")
    if not GITHUB.match(github):
        raise Bad(f"github {github!r}: the repository as owner/name, which the box's CI role trusts")
    database = m.get("database", False)
    if not isinstance(database, bool):
        raise Bad(f"database {database!r}, true or false")
    if (HERE.parent / "static" / "objects").exists():
        raise Bad("static/objects/: the static bucket's objects/ is written at run time, by the services; "
                  "a release's static/ must not hold it")
    services = m.get("services") or []
    if not services:
        raise Bad("no services")
    seen = set()
    prefixes = set()
    out = []
    for s in services:
        sn = s.get("name", "")
        if not SERVICE.match(sn):
            raise Bad(f"service {sn!r}: 2 to 20 characters, lower case, digits and hyphens")
        if sn in seen or sn in RESERVED_LABELS:
            raise Bad(f"service {sn!r}: taken, or one of {sorted(RESERVED_LABELS)}")
        seen.add(sn)
        if len(f"{BOX}-{name}-{sn}") > 48:
            raise Bad(f"{BOX}-{name}-{sn}: over 48 characters, too long for its names on the box")
        lang = s.get("language")
        if lang not in LANGUAGES:
            raise Bad(f"{sn}: language {lang!r}, one of {sorted(LANGUAGES)}")
        port = s.get("port")
        if not isinstance(port, int) or not 1024 <= port <= 65535:
            raise Bad(f"{sn}: port {port!r}, 1024 to 65535")
        mem = s.get("memory_mib", 192)
        if not isinstance(mem, int) or not 64 <= mem <= 512:
            raise Bad(f"{sn}: memory_mib {mem!r}, 64 to 512: the box has 1 GiB for everyone")
        routes = []
        keys = set()
        for r in s.get("routes") or []:
            meth, path = r.get("method"), r.get("path", "")
            if meth not in METHODS:
                raise Bad(f"{sn}: method {meth!r}, one of {METHODS}")
            segs = path.split("/")[1:]
            if (not path.startswith("/") or "//" in path or any(g in (".", "..") for g in segs)
                    or not all(SEGMENT.match(g) for g in segs if g)):
                raise Bad(f"{sn}: path {path!r}: /a/b, each segment letters, digits, ._- or a {{param}}")
            params = [g[1:-1] for g in segs if g.startswith("{")]
            if len(set(params)) != len(params):
                raise Bad(f"{sn}: path {path!r} repeats a parameter")
            if (meth, path) in keys:
                raise Bad(f"{sn}: {meth} {path} twice")
            keys.add((meth, path))
            routes.append({"method": meth, "path": path, "signed_in": bool(r.get("signed_in", True))})
        if ("GET", "/health") not in keys or any(r["path"] == "/health" and r["signed_in"] for r in routes):
            raise Bad(f"{sn}: needs GET /health, signed_in false: the box and the probes check it")
        # The API's reference (docs/conduct/api.md): made from the routes,
        # and Scalar's page of it, for anyone
        for path in ("/openapi.json", "/scalar-ui"):
            if ("GET", path) not in keys or any(r["path"] == path and r["signed_in"] for r in routes):
                raise Bad(f"{sn}: needs GET {path}, signed_in false: the API's reference, docs/conduct/api.md")
        # The database prefixes the service owns: its own, prefix, or
        # several, prefixes, its own first. A second is a part of the
        # service with tables of its own, as /users in
        # docs/tutorials/4-users/
        if "prefix" in s and "prefixes" in s:
            raise Bad(f"{sn}: prefix or prefixes, not both")
        own = s["prefixes"] if "prefixes" in s else [s.get("prefix", sn.replace("-", "_"))]
        if not isinstance(own, list) or not own:
            raise Bad(f"{sn}: prefixes {own!r}: a list of one or more")
        for prefix in own:
            if not isinstance(prefix, str) or not PREFIX.match(prefix) or prefix in prefixes:
                raise Bad(f"{sn}: prefix {prefix!r}: lower case, digits and _, a letter first, and no other's")
            prefixes.add(prefix)
        out.append({"name": sn, "language": lang, "port": port, "memory_mib": mem, "prefixes": own,
                    "routes": routes})
    return {"name": name, "description": m.get("description", ""), "github": github, "database": database,
            "ui": {"dev_callback_urls": dev}, "services": out}


# Every object a migration makes, by kind and name; comments out first
CREATE = re.compile(r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:UNIQUE\s+)?"
                    r"(TABLE|VIEW|MATERIALIZED\s+VIEW|FUNCTION|PROCEDURE|INDEX|SEQUENCE|TYPE|TRIGGER|DOMAIN)\s+"
                    r"(?:CONCURRENTLY\s+)?(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_.\"]+)", re.I)
MIGRATION = re.compile(r"^([0-9]{14})_([a-z][a-z0-9_]*)\.sql$")


def check_migrations(p: dict) -> int:
    """The one database's migrations, against the manifest: each file
    named <version>_<prefix>_<what>.sql for a service's prefix, and
    every table, view, function, procedure, index, sequence, type,
    trigger and domain it makes named with that prefix (conduct's
    database page). A service may own several prefixes; each file has
    one. The count checked; Bad otherwise"""
    d = HERE.parent / "migrations" / "sql"
    files = sorted(d.glob("*.sql")) if d.is_dir() else []
    if p["database"] != bool(files):
        raise Bad("database true needs migrations/sql/*.sql, and migrations need database true")
    prefixes = sorted((x for s in p["services"] for x in s["prefixes"]), key=len, reverse=True)
    for f in files:
        m = MIGRATION.match(f.name)
        own = m and next((x for x in prefixes if m.group(2).startswith(x + "_")), None)
        if not own:
            raise Bad(f"migrations/sql/{f.name}: not <14-digit version>_<prefix>_<what>.sql for a prefix of {prefixes}")
        sql = re.sub(r"--[^\n]*", "", f.read_text())
        for kind, obj in CREATE.findall(sql):
            bare = obj.replace('"', "").split(".")[-1]
            if not bare.startswith(own + "_"):
                raise Bad(f"migrations/sql/{f.name}: {kind.upper()} {bare} is not {own}_*, the file's prefix")
    return len(files)


def var(*parts: str) -> str:
    return "_".join(p.replace("-", "_") for p in parts)


def location(path: str, methods: list[str], upstream: str) -> str:
    """One location for one path: exact, or a regex for its {params},
    passing its own fixed URI, never the client's raw one"""
    segs = path.split("/")[1:]
    if any(g.startswith("{") for g in segs):
        rx, to = [], []
        for g in segs:
            if g.startswith("{"):
                p = "p_" + g[1:-1]
                rx.append(f"(?<{p}>[A-Za-z0-9_-]{{1,64}})")
                to.append(f"${p}")
            else:
                rx.append(re.escape(g))
                to.append(g)
        head = f'location ~ "^/{"/".join(rx)}$"'
        target = "/" + "/".join(to)
    else:
        head = f"location = {path}"
        target = path
    allow = " ".join(sorted(set(methods), key=METHODS.index))
    return f"""
    {head} {{
        limit_except {allow} {{
            deny all;
        }}
        proxy_pass http://${upstream}{target};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }}
"""


def nginx(p: dict) -> str:
    n = p["name"]
    v = lambda *a: var(n, *a)  # noqa: E731
    # The developers' machines, from ui.dev_callback_urls: a Bearer
    # token, not a cookie, so an origin allowed here reads only what
    # its own token may
    origins = sorted({re.match(r"^http://localhost(:[0-9]+)?", u).group(0) for u in p["ui"]["dev_callback_urls"]})
    dev = "".join(f'    {json.dumps(o):<24} $http_origin;\n' for o in origins)
    writes = sorted({r["method"] for s in p["services"] for r in s["routes"]} | {"GET"}, key=METHODS.index)
    out = [f"""# Project {n}, rendered by its box/render.py from box/project.json: do
# not edit here; edit the manifest and render again. Included in the
# box's http block. ${{ZONE}} is the project's zone, filled at the
# box's upload. The box defines the write limits used below,
# api_write_ip and api_write_all, and the certificate's paths.

# CORS for the project's UI alone, https://www.${{ZONE}}, and the
# developers' localhost from ui.dev_callback_urls: no credentials, the
# token goes as a Bearer header. A preflight is an OPTIONS from those
# origins, answered by nginx and cached two hours
map $http_origin ${v("cors_origin")} {{
    default                  "";
    "https://www.${{ZONE}}"    $http_origin;
{dev}}}

map "$request_method ${v("cors_origin")}" ${v("preflight")} {{
    default        0;
    "~^OPTIONS ."  1;
}}

map ${v("preflight")} ${v("cors_methods")} {{
    default  "";
    1        "{", ".join(writes)}";
}}

map ${v("preflight")} ${v("cors_headers")} {{
    default  "";
    1        "Authorization, Content-Type";
}}

map ${v("preflight")} ${v("cors_max_age")} {{
    default  "";
    1        7200;
}}
"""]
    for s in p["services"]:
        sn, up = s["name"], v(s["name"], "upstream")
        paths: dict[str, list[str]] = {}
        for r in s["routes"]:
            paths.setdefault(r["path"], []).append(r["method"])
        locs = "".join(location(path, ms, up) for path, ms in paths.items())
        out.append(f"""
# {n}-{sn}: {s["language"]}, port {s["port"]}
server {{
    listen 443 ssl;
    server_name {sn}.${{ZONE}};

    ssl_certificate         /etc/nginx/tls/origin-cert.pem;
    ssl_certificate_key     /etc/nginx/tls/origin-key.pem;
    ssl_client_certificate  /etc/nginx/site/origin-pull-ca.pem;
    ssl_verify_client       on;
    ssl_protocols           TLSv1.2 TLSv1.3;

    client_max_body_size 1m;

    # By name, per request, through Docker's resolver: nginx starts
    # whether or not the service is up, and answers 502 for it alone
    set ${up} {n}-{sn}:{s["port"]};

    proxy_hide_header Access-Control-Allow-Origin;
    proxy_hide_header Access-Control-Allow-Methods;
    proxy_hide_header Access-Control-Allow-Headers;
    proxy_hide_header Access-Control-Max-Age;
    add_header Access-Control-Allow-Origin ${v("cors_origin")} always;
    add_header Access-Control-Allow-Methods ${v("cors_methods")} always;
    add_header Access-Control-Allow-Headers ${v("cors_headers")} always;
    add_header Access-Control-Max-Age ${v("cors_max_age")} always;
    add_header Vary Origin always;

    if (${v("preflight")}) {{
        return 204;
    }}

    # Writes: 10 a second per client, 100 in all across the box, a
    # short burst queued, the rest 429 with Retry-After. Reads uncounted
    limit_req zone=api_write_ip burst=20;
    limit_req zone=api_write_all burst=50;
    limit_req_status 429;
    error_page 429 @too_many;

    location @too_many {{
        default_type application/json;
        add_header Retry-After 1 always;
        add_header Access-Control-Allow-Origin ${v("cors_origin")} always;
        add_header Vary Origin always;
        return 429 '{{"error": "too many requests"}}\\n';
    }}

    # The allow-list: the manifest's routes, and nothing else. 404, not
    # 403: it says nothing of what exists
    location / {{
        return 404;
    }}
{locs}}}
""")
    return "".join(out)


def units(p: dict) -> list[str]:
    """What the project builds into images, each a repository and a
    build on the box: its services, and its migrations if it has a
    database"""
    return [s["name"] for s in p["services"]] + (["migrations"] if p["database"] else [])


def compose(p: dict) -> str:
    n = p["name"]
    lines = [f"""# Project {n}, rendered by its box/render.py from box/project.json: do
# not edit here but for the digests, which the box pins from the
# project's release record, releases/{n}/release.json. Each image at
# {UNPINNED[:9]}...0 until its first release, which the box's upload
# refuses. Bounded in memory, on the box's network. From env files the
# box writes for it: the Cognito issuer, the project's clients and
# userInfo's URL (cognito.env); the static bucket's write and read
# addresses (store.env).
services:
"""]
    if p["database"]:
        lines.append(f"""  # The project's one database to the newest migration, as its migrator,
  # before any service starts; the database is the box's PostgreSQL
  {n}-migrate:
    image: ${{APP_REGISTRY:?no APP_REGISTRY in .env}}/{BOX}-{n}-migrations@{UNPINNED}
    container_name: {n}-migrate
    command: ["--wait", "up"]
    env_file:
      - path: ./projects/{n}/db-migrator.env
    networks:
      - app-network
    restart: "no"

""")
    for s in p["services"]:
        sn = s["name"]
        hc = json.dumps([a.replace("{port}", str(s["port"])) for a in LANGUAGES[s["language"]]])
        db = (f"""
      - path: ./projects/{n}/db-app.env""" if p["database"] else "")
        dep = (f"""
    depends_on:
      {n}-migrate:
        condition: service_completed_successfully""" if p["database"] else "")
        lines.append(f"""  {n}-{sn}:
    image: ${{APP_REGISTRY:?no APP_REGISTRY in .env}}/{BOX}-{n}-{sn}@{UNPINNED}
    container_name: {n}-{sn}
    environment:
      SERVICE: {sn}
    env_file:
      - path: ./projects/{n}/cognito.env
        required: false
      - path: ./projects/{n}/store.env
        required: false{db}
    networks:
      - app-network
    expose:
      - "{s["port"]}"
    mem_limit: {s["memory_mib"]}m
    restart: unless-stopped{dep}
    healthcheck:
      test: {hc}
      interval: 30s
      timeout: 10s
      retries: 3

""")
    return "".join(lines).rstrip("\n") + "\n"


def ci_trust(p: dict) -> str:
    """The project's CI role's trust: GitHub's OIDC provider, for this
    repository's release tags alone. ${ACCOUNT_ID} filled by the box's
    owner"""
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "ReleaseTagsOfOneRepository",
            "Effect": "Allow",
            "Principal": {"Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"},
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                "StringLike": {"token.actions.githubusercontent.com:sub": f"repo:{p['github']}:ref:refs/tags/v*"},
            },
        }],
    }, indent=2) + "\n"


def ci_policy(p: dict) -> str:
    """What a release may do, and nothing else: put its sources and its
    release record under releases/<name>/ in the config bucket, which
    the box never runs; start its own builds and read them; read its own
    images' digests; sync www and docs, and add to static without
    deleting, and never into its objects/, which the services write at
    run time. ${ACCOUNT_ID} and ${ZONE} filled by the box's owner"""
    n = p["name"]
    cfg = "arn:aws:s3:::tu-rgb-sites-config-${ACCOUNT_ID}"
    region = "ap-south-1"
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "PutTheRelease", "Effect": "Allow",
             "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
             "Resource": f"{cfg}/releases/{n}/*"},
            {"Sid": "ListTheRelease", "Effect": "Allow", "Action": "s3:ListBucket", "Resource": cfg,
             "Condition": {"StringLike": {"s3:prefix": f"releases/{n}/*"}}},
            {"Sid": "RunItsBuilds", "Effect": "Allow",
             "Action": ["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
             "Resource": f"arn:aws:codebuild:{region}:${{ACCOUNT_ID}}:project/{BOX}-{n}-*"},
            {"Sid": "ReadItsImages", "Effect": "Allow", "Action": "ecr:DescribeImages",
             "Resource": f"arn:aws:ecr:{region}:${{ACCOUNT_ID}}:repository/{BOX}-{n}-*"},
            {"Sid": "ListItsSites", "Effect": "Allow", "Action": "s3:ListBucket",
             "Resource": ["arn:aws:s3:::www.${ZONE}", "arn:aws:s3:::docs.${ZONE}", "arn:aws:s3:::static.${ZONE}"]},
            {"Sid": "ReleaseWwwAndDocs", "Effect": "Allow",
             "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
             "Resource": ["arn:aws:s3:::www.${ZONE}/*", "arn:aws:s3:::docs.${ZONE}/*"]},
            {"Sid": "AddToStatic", "Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"],
             "Resource": "arn:aws:s3:::static.${ZONE}/*"},
            {"Sid": "NeverTheRunTimesObjects", "Effect": "Deny",
             "Action": ["s3:PutObject", "s3:DeleteObject"],
             "Resource": "arn:aws:s3:::static.${ZONE}/objects/*"},
        ],
    }, indent=2) + "\n"


def onboarding(p: dict) -> str:
    n = p["name"]
    svcs = [s["name"] for s in p["services"]]
    hosts = ", ".join(f"`{h}.<zone>`" for h in ["www", "static", "docs", *svcs])
    images = ", ".join(f"`{BOX}-{n}-{u}`" for u in units(p))
    mem = sum(s["memory_mib"] for s in p["services"])
    db = (f"""
   - **the database:** `{n}`, its logins `{n}_migrator` and `{n}`, and
     the env files `projects/{n}/db-migrator.env` and `db-app.env`;
     dbmate's ledger made by the migrator and kept from `{n}`; after
     the box's `feature/postgres`""" if p["database"] else "")
    return f"""# Onboarding `{n}`

Rendered by `box/render.py`; the box owner's steps, on the box's
repository. Every name below is `{BOX}-{n}-*`. The hosts: {hosts}.
The images: {images}. Memory asked for: {mem} MiB in all, of the
box's 1 GiB. The repository: `{p["github"]}`.

1. **Review and copy.** This folder to the box's repository as
   `projects/{n}/`. Read the allow-list in `nginx.conf.in` and the CI
   role's `ci-policy.json.in` above all. Commit.
2. **The zone.** Your zone for `{n}` in the box's ignored
   `terraform/.envrc.local`, in `TF_VAR_project_zones`, a JSON object
   by project name.
3. **Cloudflare, by hand, in the zone:**
   - records for {hosts}, each proxied: the API hosts `A` to the
     box's Elastic IP; `www`, `static` and `docs` `CNAME` to their
     buckets' website endpoints, from Terraform's outputs after
     step 5;
   - `www`, `static` and `docs` in the Configuration Rule for
     Flexible, and in the Transform Rule that sets the Referer;
   - **a zone of its own:** the zone's Authenticated Origin Pulls with
     the box's client certificate, and the box's Origin CA
     certificate reissued to name the zone and its wildcard (one
     `ACT-store-cert` and a reload).
4. **Before:** `make -f probes/40-project.Makefile PROJECT={n}`.
5. **Terraform:** `plan-check`, then `ACT-apply CONFIRM=project`, both
   with `PROJECT={n}`:
   - a repository and a build for each image, sourced from
     `releases/{n}/src/<image>/` in the config bucket, with a push role
     of the project's own;
   - the `www`, `static` and `docs` buckets, and the UI's Cognito
     client; the `static` bucket admitting `PUT` and `DELETE` on
     `objects/*` from the box's Elastic IP, as the box's own does,
     for the services' uploads;
   - the env files: `projects/{n}/cognito.env`, the issuer, the
     clients and `COGNITO_USERINFO_URL`, Cognito's domain's
     `/oauth2/userInfo`; `projects/{n}/store.env`,
     `STORE_URL=https://s3.ap-south-1.amazonaws.com/static.<zone>` and
     `STATIC_URL=https://static.<zone>`;
   - the CI role `{BOX}-{n}-ci`, from `ci-trust.json.in` and
     `ci-policy.json.in`, trusted by GitHub's OIDC provider for
     `{p["github"]}`'s `v*` tags alone;{db}
6. **Tell the project** its role's ARN, its zone, Cognito's sign-in
   domain and its UI's client ID, for the repository's variables.
7. **The first release** is the project's: a tag `v0.1.0`. Its
   workflow builds every image, writes `releases/{n}/release.json`, and
   syncs `www`, `docs` and `static`. The box pins the record's digests
   into `projects/{n}/compose.yml` and reloads.
8. **After:** `make -f probes/40-project.Makefile after PROJECT={n}`,
   then the project's own, `make -C probes ZONE=<zone>`.

Steps 4, 5, 7 and 8 name the box's probe 40, its Terraform over
projects, and its reading of release records: the box's
`todo-project-template.md` subtasks 2 to 5, 12 and 13.
"""


# The box's nginx, as the box's compose file pins it, from AWS's mirror
NGINX = "public.ecr.aws/docker/library/nginx@sha256:abe47724e466aeab9a345d8e46a221c2fa8953c7848bb4a3bd9976a7199f8cf2"
# PostgreSQL 17.11, Alpine: what the box moves to, not what it has
POSTGRES = "public.ecr.aws/docker/library/postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
DEV_PORT = 8080


def dev_nginx(p: dict) -> str:
    """The box's servers for the project, on plain HTTP at
    <service>.localhost, inside a whole nginx.conf with what the box
    defines around them: the write limits, by the client's address
    here since no Cloudflare header comes, and Docker's resolver"""
    lines = [l if l.lstrip().startswith("#") else l.replace("${ZONE}", "localhost")
             for l in nginx(p).splitlines() if not l.startswith("    ssl_")]
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    body = body.replace("    listen 443 ssl;\n", f"    listen {DEV_PORT};\n")
    servers = "\n".join("    " + l if l else l for l in body.splitlines())
    return f"""# The dev stack's nginx, rendered by box/render.py --dev from
# box/project.json: the box's servers for the project, on plain HTTP,
# with the box's limits around them. Local development only.
worker_processes 1;
events {{
    worker_connections 256;
}}

http {{
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    # The container's own resolver, filled in by the nginx image at start
    # (NGINX_ENTRYPOINT_LOCAL_RESOLVERS): Docker's is 127.0.0.11,
    # Podman's its network's gateway
    resolver ${{NGINX_LOCAL_RESOLVERS}} valid=10s ipv6=off;

    # As the box's, but by the client's address: no CF-Connecting-IP here
    map $request_method $api_write_ip {{
        default  $binary_remote_addr;
        GET      "";
        HEAD     "";
        OPTIONS  "";
    }}

    map $request_method $api_write_all {{
        default  all;
        GET      "";
        HEAD     "";
        OPTIONS  "";
    }}

    limit_req_zone $api_write_ip  zone=api_write_ip:1m  rate=10r/s;
    limit_req_zone $api_write_all zone=api_write_all:1m rate=100r/s;

{servers}

    # The buckets, as folders: static.localhost from static/, and
    # docs.localhost from md-preview's build, docs/_site/. The static
    # bucket's objects/, which services write at run time, from the mock
    # store, read alone here
    server {{
        listen {DEV_PORT};
        server_name static.localhost;
        root /srv/static;

        location /objects/ {{
            limit_except GET {{
                deny all;
            }}
            set $store mock-store:9100;
            proxy_pass http://$store/static.localhost$uri;
        }}
    }}

    server {{
        listen {DEV_PORT};
        server_name docs.localhost;
        root /srv/docs;
        index index.html;
    }}

    server {{
        listen {DEV_PORT} default_server;
        return 404;
    }}
}}
"""


DBMATE = "ghcr.io/amacneil/dbmate@sha256:520c740c6e0ad73fde2cd1ea7e2b779aaf789d22aca8858f87a478e7094535fb"  # 2.36.0


def dev_db_users(p: dict) -> str:
    """The project's one database, owned by its migrator, and its app
    login: rows on every table, and every function and procedure, that
    the migrator makes from now on. Idempotent: run at every up"""
    n = p["name"]
    if not p["database"]:
        return "-- No database: database false in box/project.json\n"
    return f"""-- Rendered by box/render.py --dev: the project's database and its two
-- logins (docs/migrations/README.md). Local development only.
SELECT 'CREATE ROLE {n}_migrator LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{n}_migrator')\\gexec
SELECT 'CREATE ROLE {n} LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{n}')\\gexec
ALTER ROLE {n}_migrator PASSWORD 'dev-only';
ALTER ROLE {n} PASSWORD 'dev-only';
SELECT 'CREATE DATABASE {n} OWNER {n}_migrator' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{n}')\\gexec
REVOKE ALL ON DATABASE {n} FROM PUBLIC;
GRANT CONNECT ON DATABASE {n} TO {n};
\\connect {n}
GRANT USAGE ON SCHEMA public TO {n};
ALTER DEFAULT PRIVILEGES FOR ROLE {n}_migrator IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {n};
ALTER DEFAULT PRIVILEGES FOR ROLE {n}_migrator IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {n};
ALTER DEFAULT PRIVILEGES FOR ROLE {n}_migrator IN SCHEMA public GRANT EXECUTE ON ROUTINES TO {n};
-- dbmate's ledger, made here as the migrator, as dbmate would make it,
-- and kept from the app login, which the default privileges above
-- would otherwise let rewrite which migrations have run
SET client_min_messages = warning;
SET ROLE {n}_migrator;
CREATE TABLE IF NOT EXISTS schema_migrations (version varchar NOT NULL PRIMARY KEY);
REVOKE ALL ON TABLE schema_migrations FROM {n};
RESET ROLE;
"""


# What a container was made from, as a label of its service: Compose
# makes a container again when its service's definition changes, and
# podman-compose for nothing else, a rebuilt image included. So a
# changed file changes the label, and `make dev` restarts what changed
# and nothing more, under Docker and Podman alike. A service is made
# from its folder and from dev/dev.env
SKIPPED = {"node_modules", ".venv", "__pycache__", ".git"}


def made_from(*paths: Path) -> str:
    h = hashlib.sha256()
    for path in paths:
        if not path.exists():
            continue
        files = [path] if path.is_file() else sorted(
            f for f in path.rglob("*") if f.is_file() and not SKIPPED & set(f.relative_to(path).parts))
        for f in files:
            h.update(f.relative_to(path.parent).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()[:16]


def dev_compose(p: dict, nginx: str = "") -> str:
    n = p["name"]
    root = HERE.parent
    origins = sorted({re.match(r"^http://localhost(:[0-9]+)?", u).group(0) for u in p["ui"]["dev_callback_urls"]})
    db_env = (f"""
      # The project's one database, as its app login (docs/migrations/README.md)
      DATABASE_URL: postgres://{n}:dev-only@db:5432/{n}?sslmode=disable""" if p["database"] else "")
    db_dep = ("""
      migrate:
        condition: service_completed_successfully""" if p["database"] else "")
    svcs = []
    for s in p["services"]:
        hc = json.dumps([a.replace("{port}", str(s["port"])) for a in LANGUAGES[s["language"]]])
        svcs.append(f"""  {n}-{s["name"]}:
    build: ../../services/{s["name"]}
    labels:
      dev.made-from: "{made_from(root / "services" / s["name"], root / "dev" / "dev.env")}"
    # Settings of your own for the dev stack, in dev/dev.env, which git
    # ignores: KEY=value lines, read by every service
    env_file:
      - path: ../dev.env
        required: false
    environment:
      SERVICE: {s["name"]}
      COGNITO_ISSUER: http://mock-auth:9000
      COGNITO_UI_CLIENT_ID: dev-ui
      COGNITO_PROBE_CLIENT_ID: dev-probe
      COGNITO_USERINFO_URL: http://mock-auth:9000/oauth2/userInfo
      # The static bucket: written at S3's path-style address, read
      # through static.<zone> (docs/tutorials/7-uploads/)
      STORE_URL: http://mock-store:9100/static.localhost
      STATIC_URL: http://static.localhost:{DEV_PORT}{db_env}
    expose:
      - "{s["port"]}"
    mem_limit: {s["memory_mib"]}m
    depends_on:
      mock-auth:
        condition: service_started{db_dep}
    healthcheck:
      test: {hc}
      interval: 10s
      timeout: 5s
      retries: 3
""")
    deps = "".join(f"      - {n}-{s['name']}\n" for s in p["services"])
    database = f"""
  # PostgreSQL, as the box will have it after its feature/postgres: the
  # project's one database, its migrator and its app login
  db:
    image: {POSTGRES}
    environment:
      POSTGRES_PASSWORD: dev-only
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 2s
      timeout: 2s
      retries: 30

  db-users:
    image: {POSTGRES}
    environment:
      PGPASSWORD: dev-only
    # Waits for the database itself, not for its health check: rootless
    # Podman without systemd never runs health checks
    entrypoint: ["sh", "-c"]
    command:
      - |
        for i in $$(seq 60); do pg_isready -q -h db -U postgres && break; sleep 1; done
        exec psql -h db -U postgres -v ON_ERROR_STOP=1 -q -f /dev-out/db-users.sql
    volumes:
      - ./db-users.sql:/dev-out/db-users.sql:ro
    depends_on:
      - db
    restart: "no"

  # migrations/ to the newest, as the migrator, at every up: dbmate's
  # own image on the folder, so a new migration needs no build here.
  # The release builds migrations/ into the image the box runs
  migrate:
    image: {DBMATE}
    environment:
      DATABASE_URL: postgres://{n}_migrator:dev-only@db:5432/{n}?sslmode=disable
      DBMATE_MIGRATIONS_DIR: /work/sql
      DBMATE_SCHEMA_FILE: /work/schema.sql
    command: ["--wait", "--no-dump-schema", "up"]
    volumes:
      - ../../migrations:/work
    depends_on:
      db-users:
        condition: service_completed_successfully
    restart: "no"
""" if p["database"] else ""
    return f"""# The dev stack, rendered by box/render.py --dev from box/project.json.
# Local development only: every port on 127.0.0.1, the database's
# password a constant, the sign-in a mock that admits anyone.
#
#   docker compose -f dev/out/compose.yml up --build
name: {n}-dev
services:
  nginx:
    image: {NGINX}
    # The rendered nginx.conf: nginx reads it at its start alone
    labels:
      dev.made-from: "{hashlib.sha256(nginx.encode()).hexdigest()[:16]}"
    ports:
      - "127.0.0.1:{DEV_PORT}:{DEV_PORT}"
    # A template, so the image fills in the resolver and nothing else
    environment:
      NGINX_ENTRYPOINT_LOCAL_RESOLVERS: "1"
      NGINX_ENVSUBST_OUTPUT_DIR: /etc/nginx
      NGINX_ENVSUBST_FILTER: ^NGINX_LOCAL_RESOLVERS$$
    volumes:
      - ./nginx.conf:/etc/nginx/templates/nginx.conf.template:ro
      - ../../static:/srv/static:ro
      - ../../docs/_site:/srv/docs:ro
    depends_on:
{deps}
  # Cognito's part, mocked: its tokens name the issuer the services
  # reach it by, http://mock-auth:9000; the browser reaches it on
  # localhost:9000, and never reads the issuer
  mock-auth:
    build: ../mock-auth
    labels:
      dev.made-from: "{made_from(root / "dev" / "mock-auth")}"
    environment:
      ISSUER: http://mock-auth:9000
      BIND: 0.0.0.0
      CLIENTS: dev-ui,dev-probe
      ORIGINS: {",".join(origins)}
    ports:
      - "127.0.0.1:9000:9000"

  # S3's part, mocked: the static bucket's objects/, which a service
  # writes at run time; the rest of the bucket is static/, as above
  mock-store:
    build: ../mock-store
    labels:
      dev.made-from: "{made_from(root / "dev" / "mock-store")}"
    environment:
      BUCKET: static.localhost
      BIND: 0.0.0.0
      ROOT: /store
    ports:
      - "127.0.0.1:9100:9100"
    volumes:
      - store:/store
{database}
{"".join(svcs)}
volumes:
  db:
  store:
"""


def native_ports(p: dict, base: int) -> dict:
    """Every port the native stack uses, from one base: five in a row
    for the stack, then one per service from base + 10. On a shared box
    each user's base differs (tools/native-dev.sh), so no two users'
    ports meet"""
    ports = {"NGINX_PORT": base, "MOCK_PORT": base + 1, "PG_PORT": base + 2, "UI_PORT": base + 3,
             "STORE_PORT": base + 4}
    for i, s in enumerate(p["services"]):
        ports["PORT_" + s["name"].replace("-", "_").upper()] = base + 10 + i
    return ports


def native_nginx(p: dict, ports: dict, root: Path, out: Path) -> str:
    """The box's servers for the project, as the dev stack's, for an
    nginx run by you, without root: plain HTTP on 127.0.0.1 at your own
    port, each service on 127.0.0.1 at its own port, every file nginx
    writes in dev/out/native/, and the UI's origin on your own port
    admitted too"""
    lines = []
    for line in nginx(p).splitlines():
        if line.startswith("    ssl_"):
            continue
        if not line.lstrip().startswith("#"):
            line = line.replace("${ZONE}", "localhost")
        lines.append(line)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    body = body.replace("    listen 443 ssl;\n", f"    listen 127.0.0.1:{ports['NGINX_PORT']};\n")
    for s in p["services"]:
        port = ports["PORT_" + s["name"].replace("-", "_").upper()]
        body = body.replace(f" {p['name']}-{s['name']}:{s['port']};", f" 127.0.0.1:{port};")
    www = '    "https://www.localhost"    $http_origin;\n'
    ui = json.dumps(f"http://localhost:{ports['UI_PORT']}")
    body = body.replace(www, www + f"    {ui:<24} $http_origin;\n", 1)
    servers = "\n".join("    " + line if line else line for line in body.splitlines())
    o = out.as_posix()
    n = ports["NGINX_PORT"]
    return f"""# The native stack's nginx, rendered by box/render.py --native from
# box/project.json: the box's servers for the project, on plain HTTP on
# this machine alone, for an nginx you run without root. Local
# development only (docs/onboarding/shared-box.md).
pid {o}/nginx.pid;
error_log {o}/nginx-error.log warn;
worker_processes 1;
events {{
    worker_connections 256;
}}

http {{
    default_type application/octet-stream;
    types {{
        text/html html;
        text/css css;
        application/javascript js;
        application/json json;
        image/svg+xml svg;
        image/png png;
        text/plain txt;
    }}
    access_log {o}/nginx-access.log;
    client_body_temp_path {o}/tmp/body;
    proxy_temp_path {o}/tmp/proxy;
    fastcgi_temp_path {o}/tmp/fastcgi;
    uwsgi_temp_path {o}/tmp/uwsgi;
    scgi_temp_path {o}/tmp/scgi;

    # As the box's, but by the client's address: no CF-Connecting-IP here
    map $request_method $api_write_ip {{
        default  $binary_remote_addr;
        GET      "";
        HEAD     "";
        OPTIONS  "";
    }}

    map $request_method $api_write_all {{
        default  all;
        GET      "";
        HEAD     "";
        OPTIONS  "";
    }}

    limit_req_zone $api_write_ip  zone=api_write_ip:1m  rate=10r/s;
    limit_req_zone $api_write_all zone=api_write_all:1m rate=100r/s;

{servers}

    server {{
        listen 127.0.0.1:{n};
        server_name static.localhost;
        root {(root / 'static').as_posix()};

        location /objects/ {{
            limit_except GET {{
                deny all;
            }}
            proxy_pass http://127.0.0.1:{ports['STORE_PORT']}/static.localhost$uri;
        }}
    }}

    server {{
        listen 127.0.0.1:{n};
        server_name docs.localhost;
        root {(root / 'docs' / '_site').as_posix()};
        index index.html;
    }}

    server {{
        listen 127.0.0.1:{n} default_server;
        return 404;
    }}
}}
"""


def native_env(p: dict, ports: dict, password: str) -> str:
    n = p["name"]
    lines = ["# Rendered by box/render.py --native: the native stack's ports and",
             "# settings, for tools/native-dev.sh. Local development only.",
             *[f"export {k}={v}" for k, v in ports.items()],
             f"export PROJECT={n}",
             f"export COGNITO_ISSUER=http://localhost:{ports['MOCK_PORT']}",
             "export COGNITO_UI_CLIENT_ID=dev-ui",
             "export COGNITO_PROBE_CLIENT_ID=dev-probe",
             f"export COGNITO_USERINFO_URL=http://localhost:{ports['MOCK_PORT']}/oauth2/userInfo",
             f"export STORE_URL=http://127.0.0.1:{ports['STORE_PORT']}/static.localhost",
             f"export STATIC_URL=http://static.localhost:{ports['NGINX_PORT']}"]
    if p["database"]:
        lines += [f"export DATABASE_URL='postgres://{n}:{password}@127.0.0.1:{ports['PG_PORT']}/{n}?sslmode=disable'",
                  f"export MIGRATOR_URL='postgres://{n}_migrator:{password}@127.0.0.1:{ports['PG_PORT']}/{n}?sslmode=disable'"]
    return "\n".join(lines) + "\n"


def native_ui_config(p: dict, ports: dict) -> str:
    apis = json.dumps([s["name"] for s in p["services"]])
    return f"""// The native stack's UI config, rendered by box/render.py --native:
// copy to ui/config.js. The mock sign-in and nginx on your own ports.
export default {{
  authDomain: "http://localhost:{ports['MOCK_PORT']}",
  clientId: "dev-ui",
  zone: "localhost",
  apis: {apis},
  apiUrl: (service) => `http://${{service}}.localhost:{ports['NGINX_PORT']}`,
  staticUrl: "http://static.localhost:{ports['NGINX_PORT']}",
}};
"""


def main(argv: list[str]) -> int:
    only_check = "--check" in argv
    try:
        p = check(json.loads((HERE / "project.json").read_text()))
        k = check_migrations(p)
    except (Bad, json.JSONDecodeError) as e:
        print(f"box/project.json: {e}", file=sys.stderr)
        return 1
    if only_check:
        print(f"box/project.json: {p['name']}, {len(p['services'])} services, {k} migrations, checked")
        return 0
    if "--units" in argv:
        print("\n".join(units(p)))
        return 0
    if "--native" in argv:
        base = int(os.environ.get("DEV_BASE_PORT", "20000"))
        if not 1024 <= base <= 65000:
            print(f"DEV_BASE_PORT {base}: 1024 to 65000", file=sys.stderr)
            return 1
        password = os.environ.get("DEV_DB_PASSWORD", "dev-only")
        if not re.match(r"^[A-Za-z0-9_.-]{8,64}$", password):
            print("DEV_DB_PASSWORD: 8 to 64 letters, digits and _.-", file=sys.stderr)
            return 1
        root = HERE.parent
        out = root / "dev" / "out" / "native"
        (out / "tmp").mkdir(parents=True, exist_ok=True)
        ports = native_ports(p, base)
        (out / "nginx.conf").write_text(native_nginx(p, ports, root, out))
        (out / "env.sh").write_text(native_env(p, ports, password))
        (out / "config.js").write_text(native_ui_config(p, ports))
        (out / "db-users.sql").write_text(dev_db_users(p).replace("'dev-only'", f"'{password}'"))
        print("dev/out/native/: nginx.conf, env.sh, config.js, db-users.sql")
        for k, v in ports.items():
            print(f"  {k:<14} {v}")
        return 0
    if "--dev" in argv:
        out = HERE.parent / "dev" / "out"
        out.mkdir(parents=True, exist_ok=True)
        nginx = dev_nginx(p)
        (out / "nginx.conf").write_text(nginx)
        (out / "compose.yml").write_text(dev_compose(p, nginx))
        (out / "db-users.sql").write_text(dev_db_users(p))
        print("dev/out/: nginx.conf, compose.yml, db-users.sql")
        return 0
    out = HERE / "out" / p["name"]
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "project.json": json.dumps(p, indent=2) + "\n",
        "nginx.conf.in": nginx(p),
        "compose.yml": compose(p),
        "ci-trust.json.in": ci_trust(p),
        "ci-policy.json.in": ci_policy(p),
        "ONBOARDING.md": onboarding(p),
    }
    for f, text in files.items():
        (out / f).write_text(text)
    print(f"box/out/{p['name']}/: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
