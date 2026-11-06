#!/usr/bin/env bash
# Evidence that nothing but CloudFront is exposed (needs AWS credentials + curl).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TF="terraform -chdir=$ROOT/infra/terraform/environments/demo"
REGION="${AWS_REGION:-ap-southeast-1}"
fail=0
check() { if eval "$2"; then echo "PASS  $1"; else echo "FAIL  $1"; fail=1; fi; }

ALB_DNS=$($TF output -raw alb_dns_name)
BUCKET=$($TF output -raw storefront_bucket)
SITE=$($TF output -raw storefront_url)
DB=$($TF output -raw db_address)

check "ALB scheme is internal" \
  "[ \"\$(aws elbv2 describe-load-balancers --region $REGION --query \"LoadBalancers[?DNSName=='$ALB_DNS'].Scheme\" --output text)\" = internal ]"
check "ALB DNS resolves only to private IPs" \
  "python3 -c \"import socket,ipaddress,sys; ips={a[4][0] for a in socket.getaddrinfo('$ALB_DNS',80)}; sys.exit(0 if ips and all(ipaddress.ip_address(i).is_private for i in ips) else 1)\""
check "RDS is not publicly accessible" \
  "[ \"\$(aws rds describe-db-instances --region $REGION --query \"DBInstances[?Endpoint.Address=='$DB'].PubliclyAccessible\" --output text)\" = False ]"
check "S3 storefront denies direct access (403)" \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' https://$BUCKET.s3.$REGION.amazonaws.com/index.html)\" = 403 ]"
check "CloudFront serves the storefront (200)" \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' $SITE/)\" = 200 ]"
check "CloudFront redirects HTTP to HTTPS" \
  "[ \"\$(curl -s -o /dev/null -w '%{http_code}' \${SITE/https:/http:}/)\" = 301 ]"
check "API is reachable through CloudFront VPC origin (not 502/504)" \
  "code=\$(curl -s -o /dev/null -w '%{http_code}' $SITE/api/products); [ \"\$code\" != 502 ] && [ \"\$code\" != 504 ]"
exit $fail
