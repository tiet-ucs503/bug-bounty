#!/usr/bin/env bash
# What a release changes, from the tag before it to this one: each
# image to build, and each bucket to sync. On stdout, one line each, for
# the release workflow and for a release by hand:
#
#   tools/release-plan.sh v0.2.0          against the tag before v0.2.0
#   tools/release-plan.sh v0.2.0 v0.1.0   against v0.1.0
#
#   prev v0.1.0             or prev none, for the first release
#   build js-api            a service whose services/<name>/ changed
#   build migrations        migrations/ changed
#   sync www                ui/ changed
#   sync docs               docs/ changed
#   sync static             static/ changed
#   hand-over               box/project.json changed: the box's owner
#                           rolls the manifest out (docs/onboarding/hand-over.md)
#
# The first release builds and syncs everything. Needs git, and
# python3 for the manifest's units.
set -euo pipefail

tag=${1:?the tag of the release, vX.Y.Z}
cd "$(git rev-parse --show-toplevel)"
[[ $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "release-plan: $tag is not vX.Y.Z" >&2; exit 1; }
git rev-parse -q --verify "refs/tags/$tag" > /dev/null || { echo "release-plan: no tag $tag" >&2; exit 1; }
# The manifest read is the working tree's: check the tag out first
[ "$(git rev-parse HEAD)" = "$(git rev-parse "$tag^{commit}")" ] \
  || { echo "release-plan: HEAD is not $tag; git checkout $tag first" >&2; exit 1; }

# The newest vX.Y.Z tag before this one, by version, not by date
prev=${2:-$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
  | sort -V | awk -v t="$tag" '$0 == t {print p; exit} {p = $0}')}

changed() {
  [ -z "$prev" ] && return 0
  [ -n "$(git diff --name-only "$prev" "$tag" -- "$@")" ]
}

echo "prev ${prev:-none}"
for u in $(python3 box/render.py --units); do
  case $u in
    migrations) changed migrations/ && echo "build migrations" ;;
    *) changed "services/$u/" && echo "build $u" ;;
  esac
done
changed ui/ && echo "sync www"
changed docs/ && echo "sync docs"
changed static/ && echo "sync static"
[ -n "$prev" ] && changed box/project.json && echo "hand-over"
exit 0
