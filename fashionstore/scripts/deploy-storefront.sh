#!/usr/bin/env bash
# Build the React storefront, write its runtime config from terraform outputs,
# upload to the private S3 bucket and invalidate the CloudFront entry points.
#   scripts/deploy-storefront.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/apps/storefront"
TF="terraform -chdir=$ROOT/infra/terraform/environments/demo"
BUCKET=$($TF output -raw storefront_bucket)
DIST_ID=$($TF output -raw cloudfront_distribution_id)
SITE=$($TF output -raw storefront_url)

(cd "$APP" && npm ci --no-audit --no-fund && npm run build)

# One build works in any environment: settings come from /config.json at runtime.
$TF output -json cognito | python3 -c '
import json, sys
c = json.load(sys.stdin)
json.dump({"apiBase": "/api", "cognitoDomain": c["domain"], "clientId": c["client_id"],
           "scopes": "openid email fashionstore-api/checkout.write fashionstore-api/orders.read"},
          sys.stdout, indent=2)' > "$APP/dist/config.json"

# Vite's hashed bundles can be cached forever; everything else is revalidated.
aws s3 sync "$APP/dist/assets" "s3://$BUCKET/assets" --delete --exclude '*.map' \
  --cache-control 'public,max-age=31536000,immutable'
aws s3 sync "$APP/dist" "s3://$BUCKET" --delete --exclude 'assets/*' --exclude index.html \
  --exclude config.json --cache-control 'public,max-age=300'
aws s3 cp "$APP/dist/index.html" "s3://$BUCKET/index.html" --cache-control 'no-cache' --content-type 'text/html'
aws s3 cp "$APP/dist/config.json" "s3://$BUCKET/config.json" --cache-control 'no-cache' --content-type 'application/json'
aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths /index.html /config.json / "/images/*" >/dev/null
echo "storefront deployed: $SITE"
