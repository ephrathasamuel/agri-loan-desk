"""Database models and session handling (SQLAlchemy 2).

The same models run on SQLite (local) and PostgreSQL (docker-compose):
only DATABASE_URL changes.
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text,
                        create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column, relationship,
                            sessionmaker)

from .config import get_settings


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20), default="officer")  # "admin" or "officer"
    # Raised on password change so older session tokens stop working.
    session_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    farmer_name: Mapped[str] = mapped_column(String(120))
    farmer_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    crop: Mapped[str] = mapped_column(String(20))
    soil: Mapped[str] = mapped_column(String(20))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    area_ha: Mapped[float] = mapped_column(Float)
    boundary: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GeoJSON Polygon
    loan_amount_etb: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[str] = mapped_column(String(10))
    verdict: Mapped[str] = mapped_column(String(60))
    inputs: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary_model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[User] = relationship()


class ClimateCell(Base):
    """Cached NASA POWER history for one grid cell (zlib-compressed JSON)."""

    __tablename__ = "climate_cells"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    elevation: Mapped[float] = mapped_column(Float)
    start: Mapped[str] = mapped_column(String(10))
    end: Mapped[str] = mapped_column(String(10))
    payload: Mapped[bytes] = mapped_column(LargeBinary)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def make_engine(url):
    if url.startswith("sqlite:///"):
        path = url.removeprefix("sqlite:///")
        if path and path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
