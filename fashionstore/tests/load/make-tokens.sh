#!/usr/bin/env bash
# Prints a JSON array of access tokens for N load-test shoppers
# (loadtest+1@<domain> ... loadtest+N@<domain>), creating the users if needed.
#   BASE_URL=https://dxxxx.cloudfront.net TEST_USER_PASSWORD=... \
#   LOADTEST_EMAIL_DOMAIN=example.com tests/load/make-tokens.sh 15 > tests/load/tokens.json
# Tokens last 60 minutes. In the SES sandbox these addresses are not verified, so
# their confirmation emails fail and land in notifier-failures: expected in load runs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
N="${1:?usage: $0 <count>}"
: "${BASE_URL:?}" "${TEST_USER_PASSWORD:?}" "${LOADTEST_EMAIL_DOMAIN:?}"
emails=()
for i in $(seq 1 "$N"); do emails+=("loadtest+$i@$LOADTEST_EMAIL_DOMAIN"); done
"$ROOT/scripts/create-test-users.sh" "${emails[@]}" >&2
echo -n "["
for i in "${!emails[@]}"; do
  [ "$i" -gt 0 ] && echo -n ","
  node "$ROOT/tests/e2e/tools/get-token.mjs" "$BASE_URL" "${emails[$i]}" "$TEST_USER_PASSWORD" \
    | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["access_token"]), end="")'
done
echo "]"
