// src/api/client.ts
import axios from 'axios';

// Base URL from environment, default to localhost backend
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
});

// Global error interceptor: Return a standardized error object instead of throwing.
// We wrap it as { data: { error, message } } so callers that access response.data
// receive the error object in the same position as a real API response.
api.interceptors.response.use(
  response => response,
  error => {
    const message = error?.response?.data?.message || error.message || 'Network error';
    return Promise.resolve({ data: { error: true as const, message } });
  }
);

// ─────────────────────────────────────────────────────────────────────────────
// Recommendation / Analyze API
// ─────────────────────────────────────────────────────────────────────────────

export interface RecommendationResponse {
  capability_tier: string;
  confidence_label: 'HIGH' | 'MODERATE' | 'LOW';
  answer: string;
  matched_intent: string;
  provenance: string;
  referenced_context_ids: string[];
  // UI‑specific optional fields
  recommendedAction?: string;
  factors?: Array<{ id: string; description: string; source?: string; date?: string }>;
  scheme?: {
    title: string;
    description: string;
    source: string;
    verificationNote: string;
  };
}

export const getRecommendation = async (
  state: string,
  district: string,
  crop: string
): Promise<RecommendationResponse | { error: true; message: string }> => {
  const response = await api.get<RecommendationResponse>(`/analyze/${state}/${district}/${crop}`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Price Forecast API
// ─────────────────────────────────────────────────────────────────────────────

export interface PriceForecastResponse {
  state: string;
  district: string;
  crop: string;
  days_ahead: number;
  capability_tier: string;
  status: string;
  predicted_price_range: [number, number];
  point_estimate_rs: number;
  confidence_label: string;
  confidence_score: number;
  based_on: {
    implausible_magnitude?: boolean;
    elasticity_model_r2: number;
    elasticity_model_n: number;
  };
  refusal_reason?: string;
  data_provenance: string;
}

export const getPriceForecast = async (
  state: string,
  district: string,
  crop: string,
  daysAhead: number = 14
): Promise<PriceForecastResponse | { error: true; message: string }> => {
  const response = await api.get<PriceForecastResponse>(
    `/price-forecast/${state}/${district}/${crop}`,
    { params: { days_ahead: daysAhead } }
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Capability Tier API  (GET /capability-tier/{state}/{district}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface CapabilityTierResponse {
  tier: string;          // e.g. "TIER_1_FULL_TWIN"
  explanation: string;   // human-readable description
  state: string;
  district: string;
  crop: string;
  meta: Record<string, unknown>;
}

export const getCapabilityTier = async (
  state: string,
  district: string,
  crop: string
): Promise<CapabilityTierResponse | { error: true; message: string }> => {
  const response = await api.get<CapabilityTierResponse>(
    `/capability-tier/${state}/${district}/${crop}`
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// SEE Layer — Crop Maturity (GET /see/crop-maturity/{district}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface SEECropMaturityResponse {
  district: string;
  crop: string;
  reference_date: string;
  current_season: string;
  crop_stage: string;
  estimated_maturity_pct: number;
  days_to_peak_harvest: number;
  sowing_window: string;
  expected_harvest_window: string;
  source: string;          // provenance label — must be shown verbatim
  provenance: string;
  data_provenance: string;
  satellite_climate_data?: Record<string, unknown> | null;
}

export const getSEECropMaturity = async (
  district: string,
  crop: string
): Promise<SEECropMaturityResponse | { error: true; message: string }> => {
  const response = await api.get<SEECropMaturityResponse>(
    `/see/crop-maturity/${district}/${crop}`
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// SEE Layer — Price Trend (GET /see/price-trend/{district}/{market}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface SEEPriceTrendResponse {
  district: string;
  market: string;
  crop: string;
  days_requested: number;
  observations_count?: number;
  status: string;
  time_series: Array<{
    date: string;
    modal_price_rs_per_quintal: number;
    arrival_qty_tonnes: number | null;
    arrival_data_available: boolean;
    market: string;
  }>;
  summary: {
    mean_modal_price_rs: number;
    min_modal_price_rs: number;
    max_modal_price_rs: number;
    latest_modal_price_rs: number;
    total_arrivals_tonnes: number;
    mean_daily_arrival_tonnes: number;
    trend_direction: string;
  };
  data_provenance: string;
}

export const getSEEPriceTrend = async (
  district: string,
  market: string,
  crop: string,
  days: number = 14
): Promise<SEEPriceTrendResponse | { error: true; message: string }> => {
  const response = await api.get<SEEPriceTrendResponse>(
    `/see/price-trend/${district}/${market}/${crop}`,
    { params: { days } }
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// SEE Layer — Weather Advisory (GET /see/weather-advisory/{district}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface SEEWeatherAdvisoryResponse {
  district: string;
  crop: string;
  lookback_days: number;
  rainfall_variance_mm2: number;
  rainfall_std_mm: number;
  weather_surge_multiplier: number;
  estimated_harvest_shift_days: number;
  has_meaningful_shift: boolean;
  advisory_sentence: string;    // shown verbatim
  data_source: string;          // e.g. "live_open_meteo" or "historical_imd_csv"
  provenance: string;
  data_provenance: string;
}

export const getSEEWeatherAdvisory = async (
  district: string,
  crop: string
): Promise<SEEWeatherAdvisoryResponse | { error: true; message: string }> => {
  const response = await api.get<SEEWeatherAdvisoryResponse>(
    `/see/weather-advisory/${district}/${crop}`
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Priority View API (GET /priority-view?crop=rice)
// ─────────────────────────────────────────────────────────────────────────────

export interface PriorityDistrictItem {
  district: string;
  crop: string;
  composite_risk_score: number;
  confidence_label: string;
  total_bottleneck_nodes: number;
  max_utilization_ratio: number;
  top_alert_reason: string;
  computable_scenarios: number;
}

export interface PriorityViewResponse {
  crop: string;
  districts_ranked: PriorityDistrictItem[];
  total_districts: number;
}

export const getPriorityView = async (
  crop: string = 'rice'
): Promise<PriorityViewResponse | { error: true; message: string }> => {
  const response = await api.get<PriorityViewResponse>(`/priority-view`, {
    params: { crop },
  });
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Backtest Replay API (GET /backtest/{district}/{crop}/{year}/replay)
// ─────────────────────────────────────────────────────────────────────────────

export interface BacktestReplayPoint {
  week: number;
  calendar_week: number;
  week_start_date: string;
  week_end_date: string;
  predicted_state: string;
  actual_state: string;
  flow_predicted_tonnes: number;
  flow_actual_tonnes: number;
  bottleneck_predicted: boolean;
  bottleneck_actual: boolean;
  is_accurate: boolean;
  cumulative_spoilage_prevented_rs: number;
}

export interface BacktestReplayResponse {
  district: string;
  crop: string;
  backtest_year: string;
  status: string;
  reason?: string;
  total_weeks: number;
  overall_accuracy_pct: number;
  data_provenance: string;
  replay_timeline: BacktestReplayPoint[];
}

export const getBacktestReplay = async (
  district: string,
  crop: string,
  year: string
): Promise<BacktestReplayResponse | { error: true; message: string }> => {
  const response = await api.get<BacktestReplayResponse>(
    `/backtest/${district}/${crop}/${year}/replay`
  );
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Farmer Query API
// ─────────────────────────────────────────────────────────────────────────────

export interface FarmerQueryResponse {
  question: string;
  answer: string;
  out_of_scope: boolean;
  matched_intent: string;
  confidence_label: string;
  provenance: string;
  referenced_context_ids: string[];
}

export const farmerQuery = async (
  state: string,
  district: string,
  crop: string,
  question: string
): Promise<FarmerQueryResponse | { error: true; message: string }> => {
  const response = await api.post<FarmerQueryResponse>(`/farmer-query`, {
    state,
    district,
    crop,
    question,
  });
  return response.data;
};
