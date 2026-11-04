import pytest

from app.db import normalise_url


@pytest.mark.parametrize("given,expected", [
    # Supabase and Render show these forms; the app installs the psycopg 3 driver.
    ("postgresql://u:p@aws-0-eu-central-1.pooler.supabase.com:5432/postgres",
     "postgresql+psycopg://u:p@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"),
    ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
    # Already explicit, or not PostgreSQL: unchanged.
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("sqlite:///./data/agri_loan_desk.db", "sqlite:///./data/agri_loan_desk.db"),
])
def test_database_url_from_hosts_is_accepted(given, expected):
    assert normalise_url(given) == expected
