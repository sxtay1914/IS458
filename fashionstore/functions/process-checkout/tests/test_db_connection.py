from pathlib import Path

from fashionstore_common import db


def test_rds_connections_verify_tls_but_local_tests_need_no_certificate(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-password")
    calls = []
    monkeypatch.setattr(db.pymysql, "connect", lambda **kwargs: calls.append(kwargs))
    monkeypatch.delenv("DB_SECRET_ARN", raising=False)
    db.connect()
    assert "ssl_ca" not in calls[-1]

    monkeypatch.setenv("DB_SECRET_ARN", "test-secret")
    db.connect()
    assert calls[-1]["ssl_verify_cert"] and calls[-1]["ssl_verify_identity"]
    assert Path(calls[-1]["ssl_ca"]).read_text().startswith("-----BEGIN CERTIFICATE-----")
