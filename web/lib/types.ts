// Shapes returned by the FastAPI service (see /docs for the OpenAPI schema).

import type { PolygonGeometry } from "./geo";

export type Role = "admin" | "officer";
export type RiskRating = "Low" | "Medium" | "High";

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  created_at: string;
}

export interface CropRef {
  key: string;
  name: string;
  season_days: number;
  ky: number;
  notes: string[];
  typical_yield_t_per_ha: number;
  price_etb_per_quintal: number;
}

export interface Reference {
  crops: CropRef[];
  soils: { key: string; name: string; taw_mm_per_m: number }[];
  assumptions: {
    lending: Record<string, number>;
    risk: Record<string, number>;
    insurance: Record<string, number>;
  };
  ai_available: boolean;
}

export interface Season {
  year: number;
  planting: string;
  season_rain_mm: number;
  index_rain_mm: number;
  etm_mm: number;
  eta_mm: number;
  stress_days: number;
  heat_days?: number;
  water_yield_loss?: number | null;
  heat_yield_loss?: number;
  relative_yield: number;
  yield_loss: number;
  dry: boolean;
  rain_share_of_median: number | null;
}

export interface Trend {
  per_decade: number;
  p_value: number;
  significant: boolean;
}

export interface ClimateTrend {
  rain_mm: Trend;
  yield_loss: Trend;
  recent_from_year: number;
  recent_bad_season_share: number | null;
  earlier_bad_season_share: number | null;
  recent_mean_rain_mm: number | null;
  earlier_mean_rain_mm: number | null;
  significance_level: number;
}

export interface InsuranceYear {
  year: number;
  index_rain_mm: number;
  payout_fraction: number;
  payout_etb: number;
  yield_loss: number;
  flag: string;
}

export interface AssessmentResult {
  crop: { key: string; name: string; season_days: number; ky: number; heat_tmax_c?: number | null; notes: string[] };
  soil: { key: string; name: string };
  field: { lat: number; lon: number; area_ha: number; area_source: "boundary" | "entered" };
  climate: {
    source: string;
    cells: number[][];
    years: number;
    first_year: number;
    last_year: number;
    median_season_rain_mm: number;
    dry_limit_mm: number;
    dry_seasons: number;
    dry_season_share: number;
    mean_yield_loss: number;
    mean_yield_loss_dry_seasons: number | null;
    worst_year: number;
    worst_yield_loss: number;
    bad_season_share: number;
    bad_loss_threshold: number;
    risk_rating: RiskRating;
    // Missing on assessments saved before heat stress and trends were added.
    heat_seasons?: number | null;
    mean_heat_yield_loss?: number | null;
    trend?: ClimateTrend | null;
    seasons: Season[];
  };
  loan: {
    requested_etb: number;
    disbursement_date: string;
    planting_date: string;
    harvest_date: string;
    repayment_due_date: string;
    term_days: number;
    annual_interest_rate: number;
    interest_etb: number;
    total_due_etb: number;
    bad_year_percentile: number;
    bad_year_relative_yield: number;
    normal_year_relative_yield: number;
    bad_year_harvest_value_etb: number;
    normal_year_harvest_value_etb: number;
    repayment_share: number;
    max_loan_bad_year_etb: number;
    max_loan_normal_year_etb: number;
    verdict: string;
  };
  insurance: {
    index_name: string;
    trigger_mm: number;
    exit_mm: number;
    trigger_percentile: number;
    exit_percentile: number;
    sum_insured_etb: number;
    max_payout_per_ha_etb: number | null;
    expected_payout_rate: number;
    loading: number;
    premium_rate: number;
    premium_etb: number;
    years_paid: number;
    years_total: number;
    bad_years: number;
    bad_years_paid: number;
    losses_not_covered: number[];
    paid_with_small_loss: number[];
    years: InsuranceYear[];
  };
  assumptions: Record<string, number | string>;
}

export interface AssessmentSummary {
  id: number;
  created_at: string;
  created_by: string;
  farmer_name: string;
  farmer_ref: string | null;
  crop: string;
  area_ha: number;
  loan_amount_etb: number;
  risk_rating: RiskRating;
  verdict: string;
}

export interface Assessment extends AssessmentSummary {
  lat: number;
  lon: number;
  boundary: PolygonGeometry | null;
  inputs: Record<string, unknown>;
  result: AssessmentResult;
  summary_text: string | null;
  summary_language: string | null;
  summary_model: string | null;
  summary_at: string | null;
}
