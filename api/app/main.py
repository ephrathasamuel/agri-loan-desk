"""Agri-Loan Climate Risk Desk API (FastAPI).

Interactive docs: /docs (Swagger UI) and /redoc.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import schemas
from .climate_store import field_daily
from .config import get_settings
from .db import Assessment, Base, SessionLocal, User, engine, get_db
from .risk import assumptions as A
from .risk.climate import ClimateError
from .risk.crops import CROPS, SOILS, season_length
from .risk.engine import AssessmentError, assess
from .risk.geo import GeoError, field_from_geojson
from .security import (hash_password, limiter, make_token, read_token,
                       verify_password)
from .summary import SummaryError, summarise

log = logging.getLogger("agri_loan_desk")

# Public on purpose: shown on the login page when DEMO_ACCOUNT is on.
DEMO_EMAIL = "demo@agri-loan-desk.app"
DEMO_PASSWORD = "try-the-desk"


def seed_admin(db: Session):
    """Create the first admin from ADMIN_EMAIL / ADMIN_PASSWORD if none exists."""
    s = get_settings()
    if not s.admin_email or not s.admin_password:
        return
    if db.scalar(select(func.count()).select_from(User).where(User.role == "admin")):
        return
    db.add(User(email=s.admin_email.strip().lower(), name=s.admin_name,
                password_hash=hash_password(s.admin_password), role="admin"))
    db.commit()
    log.info("Created the first admin account from ADMIN_EMAIL.")


def seed_demo(db: Session):
    """Create the shared demo account, or restore it, when DEMO_ACCOUNT is on. It is an
    admin so visitors see every feature; it cannot change its own password."""
    if not get_settings().demo_account:
        return
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        db.add(User(email=DEMO_EMAIL, name="Demo Account", role="admin",
                    password_hash=hash_password(DEMO_PASSWORD)))
    else:
        user.role = "admin"
        if not verify_password(DEMO_PASSWORD, user.password_hash):
            user.password_hash = hash_password(DEMO_PASSWORD)
    db.commit()


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_admin(db)
        seed_demo(db)
    yield


app = FastAPI(
    title="Agri-Loan Climate Risk Desk API",
    version="1.0.0",
    description="Climate risk, loan structure and weather-index insurance for smallholder crop loans.",
    lifespan=lifespan,
)


# ---- auth helpers ---------------------------------------------------------

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    unauthorised = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.",
                                 headers={"WWW-Authenticate": "Bearer"})
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorised
    payload = read_token(authorization[7:].strip(), get_settings().secret_key)
    if not payload:
        raise unauthorised
    user = db.get(User, payload["uid"])
    if user is None or user.session_version != payload.get("ver"):
        raise unauthorised
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can do this.")
    return user


# ---- health and reference -------------------------------------------------

@app.get("/health", response_model=schemas.HealthOut, tags=["system"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        ok = True
    except Exception:  # noqa: BLE001 - any database failure means "not healthy"
        ok = False
    return {"status": "ok" if ok else "degraded", "database": ok,
            "ai_available": bool(get_settings().anthropic_api_key)}


@app.get("/reference", response_model=schemas.ReferenceOut, tags=["reference"])
def reference(_: User = Depends(current_user)):
    crops = [
        {"key": k, "name": c["name"], "season_days": season_length(c), "ky": c["ky"], "notes": c["notes"],
         "typical_yield_t_per_ha": A.TYPICAL_YIELD_T_PER_HA[k], "price_etb_per_quintal": A.PRICE_ETB_PER_QUINTAL[k]}
        for k, c in CROPS.items()
    ]
    soils = [{"key": k, **s} for k, s in SOILS.items()]
    return {"crops": crops, "soils": soils, "assumptions": A.as_dict(),
            "ai_available": bool(get_settings().anthropic_api_key)}


# ---- auth -------------------------------------------------------------------

@app.post("/auth/login", response_model=schemas.LoginOut, tags=["auth"])
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    wait = limiter.locked_for(email)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed sign-ins. Try again in {wait // 60 + 1} minutes.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        limiter.failed(email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password.")
    limiter.succeeded(email)
    s = get_settings()
    return {"token": make_token(user.id, user.session_version, s.secret_key, s.session_hours),
            "expires_in_seconds": s.session_hours * 3600, "user": user}


@app.get("/auth/demo", response_model=schemas.DemoOut, tags=["auth"])
def demo_account():
    if not get_settings().demo_account:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "There is no demo account.")
    return {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}


@app.get("/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(user: User = Depends(current_user)):
    return user


@app.post("/auth/password", status_code=204, tags=["auth"])
def change_password(body: schemas.PasswordChange, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if user.email == DEMO_EMAIL:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The demo account's password cannot be changed.")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The current password is wrong.")
    user.password_hash = hash_password(body.new_password)
    user.session_version += 1  # signs out every other session
    db.commit()


# ---- users (admin) ----------------------------------------------------------

@app.get("/users", response_model=list[schemas.UserOut], tags=["users"])
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@app.post("/users", response_model=schemas.UserOut, status_code=201, tags=["users"])
def create_user(body: schemas.UserCreate, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    email = str(body.email).strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    return user


# ---- assessments ------------------------------------------------------------

def _utc(dt):
    # SQLite gives back naive datetimes; they were stored as UTC.
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _summary_row(a: Assessment):
    return {
        "id": a.id, "created_at": _utc(a.created_at), "created_by": a.created_by.name,
        "farmer_name": a.farmer_name, "farmer_ref": a.farmer_ref, "crop": a.crop,
        "area_ha": a.area_ha, "loan_amount_etb": a.loan_amount_etb,
        "risk_rating": a.risk_rating, "verdict": a.verdict,
    }


def _full_row(a: Assessment):
    return {
        **_summary_row(a), "lat": a.lat, "lon": a.lon, "boundary": a.boundary, "inputs": a.inputs,
        "result": a.result, "summary_text": a.summary_text, "summary_language": a.summary_language,
        "summary_model": a.summary_model, "summary_at": _utc(a.summary_at),
    }


def _visible(db: Session, user: User, assessment_id: int) -> Assessment:
    a = db.get(Assessment, assessment_id)
    # Officers see their own assessments; admins see all. A hidden one looks missing.
    if a is None or (user.role != "admin" and a.created_by_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assessment not found.")
    return a


@app.post("/assessments", response_model=schemas.AssessmentOut, status_code=201, tags=["assessments"])
def create_assessment(body: schemas.AssessmentIn, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    if body.boundary is not None:
        try:
            field = field_from_geojson(body.boundary)
        except GeoError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        lat, lon, area, area_source = field["lat"], field["lon"], field["area_ha"], "boundary"
        points = [(p[1], p[0]) for p in field["ring"][:-1]] + [(lat, lon)]
    else:
        lat, lon, area, area_source = body.lat, body.lon, body.area_ha, "entered"
        points = [(lat, lon)]

    try:
        daily, cells = field_daily(db, points)
        inputs = {**body.model_dump(exclude={"boundary", "lat", "lon", "area_ha"}), "area_ha": area}
        result = assess(inputs, daily)
    except ClimateError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except AssessmentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    result["field"] = {"lat": round(lat, 6), "lon": round(lon, 6), "area_ha": round(area, 3),
                       "area_source": area_source}
    result["climate"]["source"] = (
        "NASA POWER daily (MERRA-2 rainfall; ET0 by FAO-56 Penman-Monteith from POWER "
        "temperature, humidity, wind and solar radiation)"
    )
    result["climate"]["cells"] = [list(c) for c in cells]
    result = schemas.AssessmentResult.model_validate(result).model_dump()

    a = Assessment(
        created_by_id=user.id, farmer_name=body.farmer_name.strip(),
        farmer_ref=(body.farmer_ref or "").strip() or None, crop=body.crop, soil=body.soil,
        lat=lat, lon=lon, area_ha=area, boundary=body.boundary, loan_amount_etb=body.loan_amount_etb,
        risk_rating=result["climate"]["risk_rating"], verdict=result["loan"]["verdict"],
        inputs={**inputs, "lat": lat, "lon": lon}, result=result,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _full_row(a)


@app.get("/assessments", response_model=list[schemas.AssessmentSummary], tags=["assessments"])
def list_assessments(user: User = Depends(current_user), db: Session = Depends(get_db),
                     limit: int = 100):
    q = select(Assessment).order_by(Assessment.created_at.desc(), Assessment.id.desc()).limit(min(max(limit, 1), 500))
    if user.role != "admin":
        q = q.where(Assessment.created_by_id == user.id)
    return [_summary_row(a) for a in db.scalars(q).all()]


@app.get("/assessments/{assessment_id}", response_model=schemas.AssessmentOut, tags=["assessments"])
def get_assessment(assessment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _full_row(_visible(db, user, assessment_id))


@app.post("/assessments/{assessment_id}/summary", response_model=schemas.AssessmentOut, tags=["assessments"])
def create_summary(assessment_id: int, body: schemas.SummaryIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    a = _visible(db, user, assessment_id)
    key = get_settings().anthropic_api_key
    if not key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "AI summaries are off: set ANTHROPIC_API_KEY for the API. The assessment itself does not need it.")
    try:
        note = summarise(_full_row(a), body.language, api_key=key)
    except SummaryError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    a.summary_text, a.summary_language, a.summary_model = note["text"], note["language"], note["model"]
    a.summary_at = datetime.now(timezone.utc)
    db.commit()
    return _full_row(a)
