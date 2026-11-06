#!/usr/bin/env bash
# Live smoke test of the checkout pipeline (needs AWS credentials for the demo account).
# Sends one checkout straight to SQS, then waits for process-checkout to log the outcome.
# Pass: outcome logged as CONFIRMED and the DLQ is empty.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TF="terraform -chdir=$ROOT/infra/terraform/environments/demo"
REGION="${AWS_REGION:-ap-southeast-1}"
QUEUE_URL=$($TF output -raw checkout_queue_url)
DLQ_URL=$($TF output -raw checkout_dlq_url)
FN=$($TF output -json function_names | python3 -c 'import json,sys; print(json.load(sys.stdin)["process-checkout"])')
EMAIL="${SMOKE_EMAIL:?set SMOKE_EMAIL to an SES-verified address}"
CID=$(python3 -c 'import uuid; print(uuid.uuid4())')
START_MS=$(($(date +%s) * 1000))

BODY=$(python3 - "$CID" "$EMAIL" <<'PY'
import json, sys, datetime
print(json.dumps({"schema_version": 1, "checkout_id": sys.argv[1], "user_sub": "smoke-test",
                  "email": sys.argv[2], "items": [{"sku": "DRS-001-M", "qty": 1}],
                  "requested_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}))
PY
)
aws sqs send-message --region "$REGION" --queue-url "$QUEUE_URL" --message-body "$BODY" >/dev/null
echo "sent checkout $CID; waiting for process-checkout..."

for i in $(seq 1 30); do
  sleep 4
  HIT=$(aws logs filter-log-events --region "$REGION" --log-group-name "/aws/lambda/$FN" \
        --start-time "$START_MS" --filter-pattern "\"$CID\"" --query 'events[].message' --output text || true)
  if echo "$HIT" | grep -q '"checkout_processed"'; then
    echo "$HIT" | grep checkout_processed | head -1
    echo "$HIT" | grep -q '"status": "CONFIRMED"' || { echo "FAIL: not CONFIRMED"; exit 1; }
    DLQ=$(aws sqs get-queue-attributes --region "$REGION" --queue-url "$DLQ_URL" \
          --attribute-names ApproximateNumberOfMessages --query 'Attributes.ApproximateNumberOfMessages' --output text)
    [ "$DLQ" = "0" ] || { echo "FAIL: DLQ has $DLQ messages"; exit 1; }
    echo "PASS: checkout confirmed, DLQ empty. Check $EMAIL for the confirmation email."
    exit 0
  fi
done
echo "FAIL: no outcome logged within 120s"; exit 1
