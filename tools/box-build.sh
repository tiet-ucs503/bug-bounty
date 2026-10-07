#!/usr/bin/env bash
# Build one of the project's images on the box's CodeBuild, for a
# release, and print its digest:
#
#   tools/box-build.sh js-api v0.2.0       prints "js-api sha256:..."
#
# As the project's CI role, or by hand with an identity that may do the
# same (docs/onboarding/release-by-hand.md). Puts the unit's folder,
# services/<name>/ or migrations/, under releases/<project>/src/<unit>/
# in the box's config bucket, which the box builds from and never runs;
# starts the build with IMAGE_TAG set to the release's tag; waits; reads
# the digest the tag names. A tag already built is not built again, so
# a release can be rerun. Prints no account and no ID.
set -euo pipefail

unit=${1:?the unit: a service, or migrations}
tag=${2:?the tag of the release, vX.Y.Z}
region=${AWS_REGION:-ap-south-1}
cd "$(git rev-parse --show-toplevel)"

name=$(python3 -c 'import json; print(json.load(open("box/project.json"))["name"])')
python3 box/render.py --units | grep -qx "$unit" || { echo "box-build: $unit is not one of the manifest's units" >&2; exit 1; }
case $unit in migrations) dir=migrations ;; *) dir=services/$unit ;; esac
repo=tu-rgb-sites-$name-$unit
acct=$(aws sts get-caller-identity --query Account --output text)
cfg=tu-rgb-sites-config-$acct

digest() {
  aws ecr describe-images --region "$region" --repository-name "$repo" --image-ids "imageTag=$tag" \
    --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true
}

d=$(digest)
if [[ $d == sha256:* ]]; then
  echo "box-build: $unit $tag built already" >&2
  echo "$unit $d"
  exit 0
fi

aws s3 sync --region "$region" --only-show-errors --delete --exact-timestamps \
  --exclude 'node_modules/*' --exclude 'test/*' --exclude '__pycache__/*' --exclude '.venv/*' \
  "$dir/" "s3://$cfg/releases/$name/src/$unit/"

id=$(aws codebuild start-build --region "$region" --project-name "$repo" \
  --environment-variables-override "name=IMAGE_TAG,value=$tag,type=PLAINTEXT" \
  --query build.id --output text)

t0=$(date +%s)
while :; do
  s=$(aws codebuild batch-get-builds --region "$region" --ids "$id" --query 'builds[0].buildStatus' --output text)
  [ "$s" = IN_PROGRESS ] || break
  [ $(( $(date +%s) - t0 )) -lt 1200 ] || { echo "box-build: $unit still building after 20 minutes" >&2; exit 1; }
  sleep 15
done
[ "$s" = SUCCEEDED ] || { echo "box-build: $unit $s; the box's owner has the build's log" >&2; exit 1; }

d=$(digest)
[[ $d == sha256:* ]] || { echo "box-build: $unit built, but no image tagged $tag" >&2; exit 1; }
echo "box-build: $unit in $(( ($(date +%s) - t0) / 60 )) min" >&2
echo "$unit $d"
