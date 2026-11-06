"""Only CloudFront is reachable from the internet (same checks as verify-private-resources.sh)."""
import ipaddress
import socket

import requests

from conftest import REGION, tf_output


def test_alb_is_internal_and_resolves_to_private_ips(aws):
    dns = tf_output("alb_dns_name")
    lbs = aws.client("elbv2").describe_load_balancers()["LoadBalancers"]
    assert [lb["Scheme"] for lb in lbs if lb["DNSName"] == dns] == ["internal"]
    ips = {a[4][0] for a in socket.getaddrinfo(dns, 80)}
    assert ips and all(ipaddress.ip_address(ip).is_private for ip in ips)


def test_storefront_bucket_refuses_direct_access():
    bucket = tf_output("storefront_bucket")
    r = requests.get(f"https://{bucket}.s3.{REGION}.amazonaws.com/index.html", timeout=10)
    assert r.status_code == 403


def test_database_is_not_public(aws):
    address = tf_output("db_address")
    dbs = aws.client("rds").describe_db_instances()["DBInstances"]
    assert [d["PubliclyAccessible"] for d in dbs if d["Endpoint"]["Address"] == address] == [False]


def test_cloudfront_serves_site_and_api_over_https(base_url):
    assert requests.get(base_url + "/", timeout=10).status_code == 200
    assert requests.get(base_url + "/api/products", timeout=10).status_code == 200
    r = requests.get(base_url.replace("https://", "http://") + "/", timeout=10, allow_redirects=False)
    assert r.status_code == 301 and r.headers["Location"].startswith("https://")


def test_spa_deep_links_are_rewritten_but_api_404s_are_not(base_url):
    assert requests.get(base_url + "/orders/123", timeout=10).status_code == 200
    r = requests.get(base_url + "/api/products/NO-SUCH-SKU", timeout=10)
    assert r.status_code == 404 and r.headers["Content-Type"].startswith("application/json")
