import os
import random
import tempfile
from datetime import date, timedelta

import pytest

# Settings are read when the app is imported, so set them first.
_tmp = tempfile.mkdtemp(prefix="agri-loan-test-")
# TEST_DATABASE_URL runs the suite against PostgreSQL (as CI does); default is a fresh SQLite file.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or (
    "sqlite:///" + os.path.join(_tmp, "test.db").replace("\\", "/")
)
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "admin-password-123"
os.environ["ADMIN_NAME"] = "Administrator"
os.environ["ANTHROPIC_API_KEY"] = ""


def synthetic_daily(first_year=1984, last_year=2025, seed=7, dry_years=(1990, 2002, 2015)):
    """Plausible daily weather: a wet season from June to September and a
    few clearly dry years. Deterministic for a given seed."""
    rng = random.Random(seed)
    out = {}
    d = date(first_year, 1, 1)
    end = date(last_year, 12, 31)
    while d <= end:
        wet = 6 <= d.month <= 9
        rain = rng.choice([0, 0, 4, 8, 12]) if wet else rng.choice([0, 0, 0, 0, 3])
        if d.year in dry_years:
            rain *= 0.15
        out[d] = {"rain": float(rain), "et0": 4.0}
        d += timedelta(days=1)
    return out


@pytest.fixture
def daily():
    return synthetic_daily()
