#!/usr/bin/env bash
# Build the store-api image and push it to ECR (tags are immutable).
#   scripts/build-push-api.sh [tag]      default tag: git short sha, else a timestamp
# Then: make k8s-config V1_TAG=<stable tag> V2_TAG=<this tag> && make k8s-apply
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-ap-southeast-1}"
TAG="${1:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)}"
REPO=$(terraform -chdir="$ROOT/infra/terraform/environments/demo" output -json ecr_repository_urls \
       | python3 -c 'import json,sys; print(json.load(sys.stdin)["store-api"])')
REGISTRY="${REPO%%/*}"

if aws ecr describe-images --region "$REGION" --repository-name "${REPO#*/}" --image-ids imageTag="$TAG" >/dev/null 2>&1; then
  echo "$REPO:$TAG already exists (immutable tags); nothing to do"; exit 0
fi

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
# EKS nodes are t3.medium (x86_64), so build amd64 even on an Apple-silicon laptop.
docker build --platform linux/amd64 -t "$REPO:$TAG" "$ROOT/apps/store-api"
docker push "$REPO:$TAG"
echo "pushed $REPO:$TAG"
