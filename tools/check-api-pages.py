#!/usr/bin/env python3
"""Warn where a service's API page and its manifest name different routes.

    tools/check-api-pages.py

For each service in box/project.json, docs/<service>/api.md should hold
an entry, `METHOD /path` on a line of its own, for each route the
manifest names, and none for a route it does not (docs/conduct/api.md,
A5). A warning a line, on stderr; never a failure: the page is written
by hand, and a pull request's reader decides. It compares which routes
are named, not their words: those are yours to keep in step with each
route's description in the code. Python's standard library alone.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY = re.compile(r"^(GET|POST|PUT|PATCH|DELETE) (/\S*)$")


def main() -> int:
    manifest = json.loads((ROOT / "box" / "project.json").read_text())
    warned = 0
    for service in manifest["services"]:
        name = service["name"]
        page = ROOT / "docs" / name / "api.md"
        named = {(r["method"], r["path"]) for r in service["routes"]}
        if not page.exists():
            print(f"warning: docs/{name}/api.md is missing: {len(named)} routes with no page", file=sys.stderr)
            warned += 1
            continue
        written = {m.groups() for m in map(ENTRY.match, page.read_text().splitlines()) if m}
        for method, path in sorted(named - written):
            print(f"warning: docs/{name}/api.md has no entry for {method} {path}, which the manifest names",
                  file=sys.stderr)
        for method, path in sorted(written - named):
            print(f"warning: docs/{name}/api.md has an entry for {method} {path}, which the manifest does not name",
                  file=sys.stderr)
        warned += len(named ^ written)
    if warned:
        print(f"warning: {warned} to mend before a merge request; each entry's words are yours to keep in step "
              "with its route's description (docs/conduct/api.md, A5)", file=sys.stderr)
    else:
        print("docs/<service>/api.md name the manifest's routes; their words are yours to keep in step")
    return 0


if __name__ == "__main__":
    sys.exit(main())
