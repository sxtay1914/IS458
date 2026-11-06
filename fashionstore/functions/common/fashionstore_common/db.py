"""MySQL connection handling for Lambda.

Credentials come from the RDS-managed Secrets Manager secret (DB_SECRET_ARN).
For local runs and tests, DB_USER / DB_PASSWORD override the secret.
The connection is cached across warm invocations and re-validated with ping().
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pymysql
import pymysql.cursors

_connection: pymysql.connections.Connection | None = None
_credentials: dict | None = None

# MySQL error codes callers care about.
ER_DUP_ENTRY = 1062
ER_LOCK_DEADLOCK = 1213
ER_LOCK_WAIT_TIMEOUT = 1205
ER_ACCESS_DENIED = 1045
RETRYABLE_ERRORS = (ER_LOCK_DEADLOCK, ER_LOCK_WAIT_TIMEOUT)


def _load_credentials(refresh: bool = False) -> dict:
    global _credentials
    if os.environ.get("DB_PASSWORD"):
        return {"username": os.environ.get("DB_USER", "root"), "password": os.environ["DB_PASSWORD"]}
    if _credentials is None or refresh:
        import boto3  # available in the Lambda runtime

        secret = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])
        _credentials = json.loads(secret["SecretString"])
    return _credentials


def connect(database: str | None = None, refresh_credentials: bool = False) -> pymysql.connections.Connection:
    creds = _load_credentials(refresh_credentials)
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=creds["username"],
        password=creds["password"],
        database=database or os.environ.get("DB_NAME", "fashionstore"),
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=30,
        write_timeout=30,
        charset="utf8mb4",
        **({"ssl_ca": str(Path(__file__).with_name("rds-ca.pem")),
            "ssl_verify_cert": True, "ssl_verify_identity": True}
           if os.environ.get("DB_SECRET_ARN") else {}),
    )


def get_connection() -> pymysql.connections.Connection:
    """Return the cached connection, reconnecting (and refreshing rotated credentials) if needed."""
    global _connection
    if _connection is not None:
        try:
            _connection.ping(reconnect=True)
            return _connection
        except pymysql.err.Error:
            _connection = None
    try:
        _connection = connect()
    except pymysql.err.OperationalError as exc:
        if exc.args and exc.args[0] == ER_ACCESS_DENIED:
            _connection = connect(refresh_credentials=True)  # secret was rotated
        else:
            raise
    return _connection


def error_code(exc: BaseException) -> int | None:
    args = getattr(exc, "args", ())
    return args[0] if args and isinstance(args[0], int) else None
