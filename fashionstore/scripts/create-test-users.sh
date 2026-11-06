#!/usr/bin/env bash
# Creates confirmed Cognito test shoppers for the live tests (idempotent).
#   scripts/create-test-users.sh <email> [<email> ...]
# Password comes from TEST_USER_PASSWORD (min 10 chars, upper+lower+digit).
# Use SES-verified addresses so confirmation emails can be delivered in the
# SES sandbox. An address containing "+decline" is always declined by payment-api.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="${AWS_REGION:-ap-southeast-1}"
PASSWORD="${TEST_USER_PASSWORD:?set TEST_USER_PASSWORD}"
[ $# -gt 0 ] || { echo "usage: $0 <email> [<email> ...]" >&2; exit 2; }
POOL=$(terraform -chdir="$ROOT/infra/terraform/environments/demo" output -json cognito \
       | python3 -c 'import json,sys; print(json.load(sys.stdin)["user_pool_id"])')

for email in "$@"; do
  if aws cognito-idp admin-get-user --region "$REGION" --user-pool-id "$POOL" --username "$email" >/dev/null 2>&1; then
    echo "exists   $email"
  else
    aws cognito-idp admin-create-user --region "$REGION" --user-pool-id "$POOL" --username "$email" \
      --user-attributes Name=email,Value="$email" Name=email_verified,Value=true \
      --message-action SUPPRESS >/dev/null
    echo "created  $email"
  fi
  aws cognito-idp admin-set-user-password --region "$REGION" --user-pool-id "$POOL" \
    --username "$email" --password "$PASSWORD" --permanent
done
