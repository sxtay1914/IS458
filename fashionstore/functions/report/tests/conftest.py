import os
import pathlib
import sys
import uuid

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1] / "common")]

from fashionstore_common import testing  # noqa: E402


@pytest.fixture(scope="session")
def database():
    if not testing.mysql_available():
        if os.environ.get("TEST_DB_REQUIRED") == "1":
            pytest.fail("MySQL is required (TEST_DB_REQUIRED=1) but unreachable")
        pytest.skip("MySQL not reachable; set TEST_DB_HOST or start the local container")
    name = f"fs_test_report_{uuid.uuid4().hex[:8]}"
    testing.create_database(name)
    yield name
    testing.drop_database(name)


@pytest.fixture
def db(database, monkeypatch):
    testing.reset_data(database)
    testing.use_test_database_env(monkeypatch, database)
    return database


@pytest.fixture
def new_conn(db):
    conns = []

    def factory():
        c = testing.connect(db)
        conns.append(c)
        return c

    yield factory
    for c in conns:
        c.close()
