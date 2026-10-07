#!/usr/bin/env bash
# Write the release record the box reads, releases/<project>/release.json
# in its config bucket: the release's tag and commit, and the digest of
# every image, this release's builds over the record before it.
#
#   tools/release-record.sh v0.2.0 <commit> digests.txt
#
# digests.txt holds tools/box-build.sh's lines, "<unit> sha256:...". The
# box pins each image's digest into its own copy of the project's
# compose piece, and reloads; it never takes anything else from here
# (docs/onboarding/ci-cd.md). The record keeps the last 20 releases.
set -euo pipefail

tag=${1:?the tag of the release, vX.Y.Z}
commit=${2:?the release commit}
digests=${3:?the file of unit and digest lines}
region=${AWS_REGION:-ap-south-1}
cd "$(git rev-parse --show-toplevel)"

name=$(python3 -c 'import json; print(json.load(open("box/project.json"))["name"])')
acct=$(aws sts get-caller-identity --query Account --output text)
key="s3://tu-rgb-sites-config-$acct/releases/$name/release.json"

before=$(aws s3 cp --region "$region" --only-show-errors "$key" - 2>/dev/null || echo '{}')
built=$(jq -R -s 'split("\n") | map(select(test("^[a-z][a-z0-9-]* sha256:[0-9a-f]{64}$")) | split(" ") | {(.[0]): .[1]}) | add // {}' "$digests")
at=$(date -u +%Y-%m-%dT%H:%M:%SZ)

jq -n --argjson before "$before" --argjson built "$built" \
  --arg project "$name" --arg tag "$tag" --arg commit "$commit" --arg at "$at" '
  $before + {
    project: $project, tag: $tag, commit: $commit, at: $at,
    images: (($before.images // {}) + $built),
    history: ((($before.history // []) + [{tag: $tag, commit: $commit, at: $at, built: ($built | keys)}])[-20:])
  }' > release.json

aws s3 cp --region "$region" --only-show-errors --content-type application/json release.json "$key"
jq -r '"release-record: \(.tag), images \(.images | keys | join(" "))"' release.json >&2
