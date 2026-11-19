import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


@pytest.fixture(scope="session", autouse=True)
def migrate_identity_test_database():
    url = os.environ.get("IDENTITY_TEST_DATABASE_URL")
    if not url:
        pytest.fail("IDENTITY_TEST_DATABASE_URL is required for Identity tests")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or parsed.database != "identity_test":
        pytest.fail("Identity tests require a dedicated PostgreSQL database named identity_test")
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=True,
    )
