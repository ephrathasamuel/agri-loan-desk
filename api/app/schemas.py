"""Typed request and response models (they also drive the OpenAPI docs)."""

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

CropKey = Literal["wheat", "teff", "maize", "sorghum", "barley"]
SoilKey = Literal["sand", "sandy_loam", "loam", "clay_loam", "clay"]
Language = Literal["en", "am"]


# ---- auth and users -------------------------------------------------------

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: Literal["admin", "officer"]
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def as_utc(cls, v):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


class LoginOut(BaseModel):
    token: str
    expires_in_seconds: int
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=200)
    role: Literal["admin", "officer"] = "officer"


class DemoOut(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


# ---- reference data ---------------------------------------------------------

class CropOut(BaseModel):
    key: CropKey
    name: str
    season_days: int
    ky: float
    notes: list[str]
    typical_yield_t_per_ha: float
    price_etb_per_quintal: float


class SoilOut(BaseModel):
    key: SoilKey
    name: str
    taw_mm_per_m: float


class ReferenceOut(BaseModel):
    crops: list[CropOut]
    soils: list[SoilOut]
    assumptions: dict[str, Any]
    ai_available: bool


# ---- assessments ----------------------------------------------------------

class AssessmentIn(BaseModel):
    farmer_name: str = Field(min_length=1, max_length=120)
    farmer_ref: str | None = Field(default=None, max_length=60)
    crop: CropKey
    soil: SoilKey
    planting_month: int = Field(ge=1, le=12)
    planting_day: int = Field(ge=1, le=31)
    loan_amount_etb: float = Field(gt=0, le=10_000_000)
    # Either a drawn field boundary (GeoJSON Polygon), or a point plus area.
    boundary: dict[str, Any] | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    area_ha: float | None = Field(default=None, gt=0, le=5000)
    # Optional overrides of the default assumptions.
    typical_yield_t_per_ha: float | None = Field(default=None, gt=0, le=20)
    price_etb_per_quintal: float | None = Field(default=None, gt=0, le=200_000)
    trigger_percentile: int | None = Field(default=None, ge=5, le=50)
    exit_percentile: int | None = Field(default=None, ge=1, le=45)

    @model_validator(mode="after")
    def check(self):
        try:
            date(2024, self.planting_month, self.planting_day)  # 2024: allow 29 Feb
        except ValueError as exc:
            raise ValueError("The planting day does not exist in that month.") from exc
        if self.boundary is None and (self.lat is None or self.lon is None or self.area_ha is None):
            raise ValueError("Draw the field boundary, or give a location and the farm size in hectares.")
        trig = self.trigger_percentile or 20
        if self.exit_percentile is not None and self.exit_percentile >= trig:
            raise ValueError("The insurance exit percentile must be below the trigger percentile.")
        return self


class Season(BaseModel):
    year: int
    planting: str
    season_rain_mm: float
    index_rain_mm: float
    etm_mm: float
    eta_mm: float
    stress_days: int
    relative_yield: float
    yield_loss: float
    dry: bool
    rain_share_of_median: float | None


class ClimateRisk(BaseModel):
    source: str
    cells: list[list[float]]
    years: int
    first_year: int
    last_year: int
    median_season_rain_mm: float
    dry_limit_mm: float
    dry_seasons: int
    dry_season_share: float
    mean_yield_loss: float
    mean_yield_loss_dry_seasons: float | None
    worst_year: int
    worst_yield_loss: float
    bad_season_share: float
    bad_loss_threshold: float
    risk_rating: Literal["Low", "Medium", "High"]
    seasons: list[Season]


class LoanTerms(BaseModel):
    requested_etb: float
    disbursement_date: str
    planting_date: str
    harvest_date: str
    repayment_due_date: str
    term_days: int
    annual_interest_rate: float
    interest_etb: float
    total_due_etb: float
    bad_year_percentile: int
    bad_year_relative_yield: float
    normal_year_relative_yield: float
    bad_year_harvest_value_etb: float
    normal_year_harvest_value_etb: float
    repayment_share: float
    max_loan_bad_year_etb: float
    max_loan_normal_year_etb: float
    verdict: str


class InsuranceYear(BaseModel):
    year: int
    index_rain_mm: float
    payout_fraction: float
    payout_etb: float
    yield_loss: float
    flag: str


class InsurancePolicy(BaseModel):
    index_name: str
    trigger_mm: float
    exit_mm: float
    trigger_percentile: int
    exit_percentile: int
    sum_insured_etb: float
    max_payout_per_ha_etb: float | None
    expected_payout_rate: float
    loading: float
    premium_rate: float
    premium_etb: float
    years_paid: int
    years_total: int
    bad_years: int
    bad_years_paid: int
    losses_not_covered: list[int]
    paid_with_small_loss: list[int]
    years: list[InsuranceYear]


class CropInfo(BaseModel):
    key: str
    name: str
    season_days: int
    ky: float
    notes: list[str]


class FieldInfo(BaseModel):
    lat: float
    lon: float
    area_ha: float
    area_source: Literal["boundary", "entered"]


class AssessmentResult(BaseModel):
    crop: CropInfo
    soil: dict[str, str]
    field: FieldInfo
    climate: ClimateRisk
    loan: LoanTerms
    insurance: InsurancePolicy
    assumptions: dict[str, Any]


class AssessmentSummary(BaseModel):
    id: int
    created_at: datetime
    created_by: str
    farmer_name: str
    farmer_ref: str | None
    crop: str
    area_ha: float
    loan_amount_etb: float
    risk_rating: str
    verdict: str


class AssessmentOut(AssessmentSummary):
    lat: float
    lon: float
    boundary: dict[str, Any] | None
    inputs: dict[str, Any]
    result: AssessmentResult
    summary_text: str | None
    summary_language: str | None
    summary_model: str | None
    summary_at: datetime | None


class SummaryIn(BaseModel):
    language: Language = "en"


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    ai_available: bool
