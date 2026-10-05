#!/usr/bin/env python3
"""Render, from box/project.json, the pieces the box's owner rolls out.

    python3 box/render.py            check the manifest, write box/out/<name>/
    python3 box/render.py --check    check it alone, write nothing

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

Python's standard library alone, so it runs anywhere. Nothing here
talks to AWS or Cloudflare. box/how-the-box-works.md says what each
piece does on the box.
"""

import json
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
    services = m.get("services") or []
    if not services:
        raise Bad("no services")
    seen = set()
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
        out.append({"name": sn, "language": lang, "port": port, "memory_mib": mem, "routes": routes})
    return {"name": name, "description": m.get("description", ""), "ui": {"dev_callback_urls": dev},
            "services": out}


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


def compose(p: dict) -> str:
    n = p["name"]
    lines = [f"""# Project {n}, rendered by its box/render.py from box/project.json: do
# not edit here but for the digests, which the box's pin writes after
# each build. Each service at {UNPINNED[:9]}...0 until then, which the
# box's upload refuses. Stateless, bounded in memory, on the box's
# network; the Cognito issuer and the project's client from the env
# file the box writes for the project at upload.
services:
"""]
    for s in p["services"]:
        sn = s["name"]
        hc = json.dumps([a.replace("{port}", str(s["port"])) for a in LANGUAGES[s["language"]]])
        lines.append(f"""  {n}-{sn}:
    image: ${{APP_REGISTRY:?no APP_REGISTRY in .env}}/{BOX}-{n}-{sn}@{UNPINNED}
    container_name: {n}-{sn}
    environment:
      SERVICE: {sn}
    env_file:
      - path: ./projects/{n}/cognito.env
        required: false
    networks:
      - app-network
    expose:
      - "{s["port"]}"
    mem_limit: {s["memory_mib"]}m
    restart: unless-stopped
    healthcheck:
      test: {hc}
      interval: 30s
      timeout: 10s
      retries: 3

""")
    return "".join(lines).rstrip("\n") + "\n"


def onboarding(p: dict) -> str:
    n = p["name"]
    svcs = [s["name"] for s in p["services"]]
    hosts = ", ".join(f"`{h}.<zone>`" for h in ["www", "static", "docs", *svcs])
    builds = "\n".join(
        f"       make -f probes/40-project.Makefile ACT-build PROJECT={n} SVC={s} CONFIRM=project" for s in svcs
    )
    mem = sum(s["memory_mib"] for s in p["services"])
    return f"""# Onboarding `{n}`

Rendered by `box/render.py`; the box owner's steps, on the box's
repository. Every name below is `{BOX}-{n}-*`. The hosts: {hosts}.
Memory asked for: {mem} MiB in all, of the box's 1 GiB.

1. **Review and copy.** This folder to the box's repository as
   `projects/{n}/`: `project.json`, `nginx.conf.in`, `compose.yml`.
   Read the allow-list in `nginx.conf.in` above all. Commit.
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
   with `PROJECT={n}`: the repositories and builds, the `www`,
   `static` and `docs` buckets, the UI's Cognito client.
6. **Builds,** after `ACT-upload-sources PROJECT={n} CONFIRM=project`:

{builds}

   then `ACT-pin PROJECT={n} CONFIRM=project`.
7. **The stack:** the box's upload and reload, then
   `make -f probes/40-project.Makefile after PROJECT={n}`.
8. **The first releases** of the UI and the documentation, from the
   project's commit: `ui/` synced to `www`, `make docs` and
   `build/docs/` synced to `docs`, each by its bucket's writers.
9. **The project's own probes,** from its repository:
   `make -C probes ZONE=<zone>`.

Steps 4 to 7 name the box's probe 40, which the box's `todo.md` §51
subtasks 2 to 5 make.
"""


def main(argv: list[str]) -> int:
    only_check = "--check" in argv
    try:
        p = check(json.loads((HERE / "project.json").read_text()))
    except (Bad, json.JSONDecodeError) as e:
        print(f"box/project.json: {e}", file=sys.stderr)
        return 1
    if only_check:
        print(f"box/project.json: {p['name']}, {len(p['services'])} services, checked")
        return 0
    out = HERE / "out" / p["name"]
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "project.json": json.dumps(p, indent=2) + "\n",
        "nginx.conf.in": nginx(p),
        "compose.yml": compose(p),
        "ONBOARDING.md": onboarding(p),
    }
    for f, text in files.items():
        (out / f).write_text(text)
    print(f"box/out/{p['name']}/: {', '.join(files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
