#!/usr/bin/env bash
# Write platform/kubernetes/overlays/demo/generated/*.env from terraform outputs.
# Usage: scripts/render-k8s-config.sh [v1-image-tag] [v2-image-tag]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="terraform -chdir=$ROOT/infra/terraform/environments/demo"
OUT="$ROOT/platform/kubernetes/overlays/demo/generated"
V1_TAG="${1:-v1}"
V2_TAG="${2:-v2}"
mkdir -p "$OUT"

$TF output -json app_config | python3 -c '
import json, sys
for k, v in sorted(json.load(sys.stdin).items()):
    print(f"{k}={v}")' > "$OUT/app-config.env"

REPO=$($TF output -json ecr_repository_urls | python3 -c 'import json,sys; print(json.load(sys.stdin)["store-api"])')
$TF output -json | python3 -c '
import json, sys
o = json.load(sys.stdin)
print("STORE_API_ROLE_ARN=" + o["irsa_role_arns"]["value"]["store-api"])
print("TG_V1_ARN=" + o["target_group_arns"]["value"]["v1"])
print("TG_V2_ARN=" + o["target_group_arns"]["value"]["v2"])' > "$OUT/terraform-outputs.env"
echo "STORE_API_IMAGE_V1=$REPO:$V1_TAG" >> "$OUT/terraform-outputs.env"
echo "STORE_API_IMAGE_V2=$REPO:$V2_TAG" >> "$OUT/terraform-outputs.env"
echo "wrote $OUT/app-config.env and $OUT/terraform-outputs.env"
