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
// Basic Health API (GET /health) — used for the sidebar's live connection indicator
// ─────────────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export const getHealth = async (): Promise<HealthResponse | { error: true; message: string }> => {
  const response = await api.get<HealthResponse>(`/health`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Recommendation / Analyze API
// ─────────────────────────────────────────────────────────────────────────────

export interface EvidenceChainItem {
  fact: string;
  source: string;
  category: string;
}

export interface SchemeDetail {
  scheme_id: string;
  scheme_name: string;
  ministry?: string;
  matched_action_type?: string;
  source_document: string;
  plain_language_summary: string;
  grounded_clauses: string[];
  mandatory_notice: string;
}

export interface SchemeAdvisorResponse {
  recommendation_id?: string;
  action_type: string;
  matched_schemes_count: number;
  matched_scheme_ids: string[];
  schemes: SchemeDetail[];
  mandatory_notice: string;
}

export interface FullTwinRecommendation {
  recommendation_id: string;
  district: string;
  crop: string;
  confidence_label: string;
  confidence_score: number;
  data_density_tier: string;
  scenario_consensus: boolean;
  selected_action: string;
  worst_case_guaranteed_payoff_rs: number;
  average_payoff_rs: number;
  max_regret_rs: number;
  evidence_chain: EvidenceChainItem[];
  explanation_summary: string;
}

// ── /analyze/{state}/{district}/{crop} — carries capability_tier at top level
// always, plus a flat confidence_label/answer/matched_intent projection derived
// from whichever tier branch actually ran (Tier 1 full twin, Tier 2 live
// snapshot, or Tier 3 insufficient-data), so the Evidence Drawer can render a
// headline immediately without branching on tier first.
export interface RecommendationResponse {
  capability_tier: string;
  state: string;
  district: string;
  crop: string;
  tier_explanation: string;
  confidence_label: 'HIGH' | 'MODERATE' | 'MEDIUM' | 'LOW';
  answer: string;
  matched_intent: string;
  provenance: string;
  referenced_context_ids: string[];
  full_twin_recommendation?: FullTwinRecommendation | null;
  scheme_advice?: SchemeAdvisorResponse | null;
  live_snapshot?: Record<string, any> | null;
  insufficient_details?: Record<string, any> | null;
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
  priority_rank: number;
  district: string;
  crop: string;
  bottleneck_risk_score: number;
  total_overshoot_tonnes: number;
  active_alerts_count: number;
  max_utilization_ratio: number;
  top_bottleneck_node: string;
  top_bottleneck_overshoot_tonnes: number;
  confidence_tier: string;
  computable: boolean;
  reason?: string | null;
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

// ─────────────────────────────────────────────────────────────────────────────
// Bottleneck Detection API (GET /bottleneck/{district}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface BottleneckNode {
  rank: number;
  node_id: string;
  node_name: string;
  node_type: string;
  district: string;
  capacity_tonnes: number;
  forecast_inflow_tonnes: number;
  overshoot_tonnes: number;
  overshoot_pct: number;
  utilization_ratio: number;
  is_active_alert: boolean;
}

export interface ScenarioBottlenecks {
  computable: boolean;
  status: string;
  reason?: string | null;
  total_bottleneck_nodes: number;
  active_alerts_count: number;
  total_overshoot_tonnes: number;
  max_utilization_ratio: number;
  data_provenance: string;
  bottlenecks: BottleneckNode[];
}

export interface BottleneckDetectionResponse {
  district: string;
  crop: string;
  scenarios: Record<string, ScenarioBottlenecks>;
}

export const getBottleneckDetection = async (
  district: string,
  crop: string
): Promise<BottleneckDetectionResponse | { error: true; message: string }> => {
  const response = await api.get<BottleneckDetectionResponse>(`/bottleneck/${district}/${crop}`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Full Recommendation API (GET /recommendation/{district}/{crop})
// ─────────────────────────────────────────────────────────────────────────────

export interface FullRecommendationResponse {
  recommendation_id: string;
  district: string;
  crop: string;
  confidence_label: string;
  confidence_score: number;
  selected_action: string;
  action_type: string;
  worst_case_guaranteed_payoff_rs: number;
  max_regret_rs: number;
  evidence_chain: EvidenceChainItem[];
  explanation_summary: string;
}

export const getFullRecommendation = async (
  district: string,
  crop: string
): Promise<FullRecommendationResponse | { error: true; message: string }> => {
  const response = await api.get<FullRecommendationResponse>(`/recommendation/${district}/${crop}`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// Scheme Advisor API (GET /scheme-advisor/{recommendation_id})
// Action-triggered by design (never a standalone chat endpoint) — callers should
// obtain a real recommendation_id from getFullRecommendation first.
// ─────────────────────────────────────────────────────────────────────────────

export const getSchemeAdvice = async (
  recommendationId: string
): Promise<SchemeAdvisorResponse | { error: true; message: string }> => {
  const response = await api.get<SchemeAdvisorResponse>(`/scheme-advisor/${recommendationId}`);
  return response.data;
};

// ─────────────────────────────────────────────────────────────────────────────
// System Health & Coverage API
// ─────────────────────────────────────────────────────────────────────────────

export interface DataSourceHealth {
  source_name: string;
  resource_type: string;
  is_available: boolean;
  record_count?: number | null;
  status_details: string;
  provenance: string;
}

export interface DetailedHealthResponse {
  system_status: string;
  service: string;
  version: string;
  timestamp: string;
  data_sources: Record<string, DataSourceHealth>;
  persisted_models_loaded: string[];
  total_sources_online: number;
  total_sources_checked: number;
}

export const getDetailedHealth = async (): Promise<DetailedHealthResponse | { error: true; message: string }> => {
  const response = await api.get<DetailedHealthResponse>(`/health/detailed`);
  return response.data;
};

export interface CoverageDistrictItem {
  district: string;
  state: string;
  capability_tier: string;
  network_nodes_count?: number;
  historical_records_count?: number;
  latitude?: number | null;
  longitude?: number | null;
  provenance: string;
}

export interface CoverageResponse {
  total_districts_tracked: number;
  tier_1_full_twins_count: number;
  tier_2_live_snapshots_count: number;
  tier_1_districts: CoverageDistrictItem[];
  tier_2_districts: CoverageDistrictItem[];
  data_provenance: string;
}

export const getCoverage = async (): Promise<CoverageResponse | { error: true; message: string }> => {
  const response = await api.get<CoverageResponse>(`/coverage`);
  return response.data;
};
