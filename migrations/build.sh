#!/usr/bin/env bash
# Build the image of this folder, push it to REPOSITORY_URI, and print
# its digest, which the box's compose file then names. The same script
# in every folder the box builds, its own and every project's, since
# CodeBuild sees one folder alone: aws-iac's probes/39-second-app.Makefile
# and a project's `make check` compare the copies. Change it in aws-iac
# first, then in the project template.
#
# Run by the box's CodeBuild on arm64, the box's architecture, from its
# config bucket's copy of this folder. Needs docker, and an AWS identity
# that may push: a build's push role, the only one its repositories'
# policies admit.
#
# The tag is IMAGE_TAG if the build was started with one, as a release
# starts it with its own tag, else the build's UTC time. Tags are
# immutable, so neither is ever reused. The digest, not the tag, is what
# the box pulls.
set -euo pipefail

: "${REPOSITORY_URI:?REPOSITORY_URI unset: the build project sets it}"
cd "$(dirname "$0")"

registry=${REPOSITORY_URI%%/*}
region=$(cut -d. -f4 <<< "$registry")
tag=${IMAGE_TAG:-$(date -u +%Y%m%dT%H%M%SZ)}

aws ecr get-login-password --region "$region" \
  | docker login --username AWS --password-stdin "$registry"

docker build --pull --tag "$REPOSITORY_URI:$tag" .
docker push "$REPOSITORY_URI:$tag"

echo "IMAGE $(docker inspect --format '{{index .RepoDigests 0}}' "$REPOSITORY_URI:$tag") TAG $tag"
