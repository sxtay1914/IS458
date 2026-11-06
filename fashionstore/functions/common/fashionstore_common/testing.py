"""Test helpers: a throwaway MySQL database built from database/migrations + seeds.

Set TEST_DB_HOST / TEST_DB_PORT / TEST_DB_USER / TEST_DB_PASSWORD to point at
MySQL 8 (defaults: 127.0.0.1:3306 root/root). Tests are skipped if MySQL is
unreachable, unless TEST_DB_REQUIRED=1 (CI), in which case they fail.
"""
from __future__ import annotations

import os
import pathlib
import re

import pymysql
import pymysql.cursors
from pymysql.constants import CLIENT

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
MIGRATIONS = REPO_ROOT / "database" / "migrations"
SEEDS = REPO_ROOT / "database" / "seeds"
CONTRACTS = REPO_ROOT / "contracts"

TABLES_IN_DELETE_ORDER = [
    "reconciliation_log", "notification_log", "order_items", "orders",
    "checkouts", "cart_items", "carts", "inventory", "products",
]


def settings() -> dict:
    return {
        "host": os.environ.get("TEST_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("TEST_DB_PORT", "3306")),
        "user": os.environ.get("TEST_DB_USER", "root"),
        "password": os.environ.get("TEST_DB_PASSWORD", "root"),
    }


def admin_connection() -> pymysql.connections.Connection:
    return pymysql.connect(**settings(), autocommit=True, client_flag=CLIENT.MULTI_STATEMENTS, connect_timeout=3)


def _run_sql_file(conn, path: pathlib.Path) -> None:
    sql = path.read_text()
    sql = re.sub(r"^\s*--.*$", "", sql, flags=re.MULTILINE)
    with conn.cursor() as cur:
        for statement in (s.strip() for s in sql.split(";")):
            if statement:
                cur.execute(statement)


def migration_files() -> list[pathlib.Path]:
    return sorted(MIGRATIONS.glob("V*__*.sql"), key=lambda p: int(p.name[1:].split("__")[0]))


def create_database(name: str) -> None:
    conn = admin_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
            cur.execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        conn.select_db(name)
        for path in migration_files():
            _run_sql_file(conn, path)
    finally:
        conn.close()


def reset_data(name: str) -> None:
    conn = admin_connection()
    try:
        conn.select_db(name)
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in TABLES_IN_DELETE_ORDER:
                cur.execute(f"DELETE FROM `{table}`")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        _run_sql_file(conn, SEEDS / "products.sql")
        _run_sql_file(conn, SEEDS / "inventory.sql")
    finally:
        conn.close()


def drop_database(name: str) -> None:
    conn = admin_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")
    finally:
        conn.close()


def connect(name: str) -> pymysql.connections.Connection:
    return pymysql.connect(**settings(), database=name, autocommit=False,
                           cursorclass=pymysql.cursors.DictCursor, charset="utf8mb4")


def query(name: str, sql: str, args=None) -> list[dict]:
    conn = connect(name)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return list(cur.fetchall())
    finally:
        conn.close()


def mysql_available() -> bool:
    try:
        admin_connection().close()
        return True
    except pymysql.err.Error:
        return False


def use_test_database_env(monkeypatch, name: str) -> None:
    """Point fashionstore_common.db at the test database."""
    s = settings()
    monkeypatch.setenv("DB_HOST", s["host"])
    monkeypatch.setenv("DB_PORT", str(s["port"]))
    monkeypatch.setenv("DB_USER", s["user"])
    monkeypatch.setenv("DB_PASSWORD", s["password"])
    monkeypatch.setenv("DB_NAME", name)
