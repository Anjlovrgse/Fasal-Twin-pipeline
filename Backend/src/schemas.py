"""
Fasal Twin - Strongly Typed Pydantic Request & Response Models
Defines explicit contracts and schemas for every API endpoint, ensuring
type safety and standardizing error response envelopes.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ==========================================
# 0. STANDARDIZED ERROR ENVELOPE
# ==========================================

class StandardErrorResponse(BaseModel):
    """Uniform error response structure returned across all API endpoints."""
    error_type: str = Field(..., description="Classification of the error (e.g., SchemaValidationError, NotFoundError)")
    message: str = Field(..., description="Human-readable explanation of why the request failed")
    affected_resource: str = Field(..., description="The specific file, district, or endpoint resource affected")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO timestamp of occurrence")


# ==========================================
# 1. SYSTEM HEALTH SCHEMAS
# ==========================================

class HealthResponse(BaseModel):
    """Basic service health check response."""
    status: str = Field("healthy", json_schema_extra={"example": "healthy"})
    service: str = Field("fasal-twin-backend", json_schema_extra={"example": "fasal-twin-backend"})
    version: str = Field("1.2.0", json_schema_extra={"example": "1.2.0"})


class DataSourceHealth(BaseModel):
    """Status and metadata for an individual data source."""
    source_name: str
    resource_type: str  # 'csv_file' | 'live_api' | 'sqlite_db' | 'persisted_model'
    is_available: bool
    record_count: Optional[int] = None
    status_details: str
    provenance: str


class DetailedHealthResponse(BaseModel):
    """Comprehensive multi-source health report for auditing data integrity."""
    system_status: str  # 'healthy' | 'degraded' | 'unhealthy'
    service: str
    version: str
    timestamp: str
    data_sources: Dict[str, DataSourceHealth]
    persisted_models_loaded: List[str]
    total_sources_online: int
    total_sources_checked: int


# ==========================================
# 2. SEE-LAYER SCHEMAS
# ==========================================

class PriceTrendPoint(BaseModel):
    """Daily price and arrival record in time series."""
    date: str
    arrival_qty_tonnes: Optional[float] = None
    arrival_data_available: bool = True
    modal_price_rs_per_quintal: float
    market: Optional[str] = None


class PriceTrendSummary(BaseModel):
    """Summary metrics of price trend window."""
    mean_modal_price_rs: float
    min_modal_price_rs: Optional[float] = 0.0
    max_modal_price_rs: Optional[float] = 0.0
    latest_modal_price_rs: Optional[float] = 0.0
    total_arrivals_tonnes: Optional[float] = 0.0
    mean_daily_arrival_tonnes: Optional[float] = 0.0
    trend_direction: Optional[str] = "stable"


class PriceTrendResponse(BaseModel):
    """Historical mandi arrival and price trends."""
    district: str
    market: str
    crop: str
    days_requested: int
    observations_count: Optional[int] = None
    status: Optional[str] = "available"
    time_series: List[PriceTrendPoint]
    summary: PriceTrendSummary
    data_provenance: str


class WeatherAdvisoryResponse(BaseModel):
    """Plain-language weather advisory and meteorological compression signals."""
    district: str
    crop: str
    lookback_days: int
    rainfall_variance_mm2: float
    rainfall_std_mm: float
    weather_surge_multiplier: float
    estimated_harvest_shift_days: int
    has_meaningful_shift: bool
    advisory_sentence: str
    data_source: str
    provenance: str
    data_provenance: str


class CropMaturityResponse(BaseModel):
    """Crop maturity stage derived from sowing calendar norms and optional NASA satellite climate refinement."""
    district: str
    crop: str
    reference_date: str
    current_season: str
    crop_stage: str
    estimated_maturity_pct: float
    days_to_peak_harvest: int
    sowing_window: str
    expected_harvest_window: str
    satellite_climate_data: Optional[Dict[str, Any]] = None
    source: str
    provenance: Optional[str] = "sowing_calendar_baseline"
    data_provenance: str


# ==========================================
# 3. DATA QUALITY AUDIT SCHEMAS
# ==========================================

class FileQualityReport(BaseModel):
    """Quality audit summary for a single data file."""
    status: str
    row_count: int
    year_min: Optional[Any] = None
    year_max: Optional[Any] = None
    verdict: str
    columns: Dict[str, Dict[str, Any]]


class DataQualityResponse(BaseModel):
    """Comprehensive data quality report across all repository tables."""
    district_filter: Optional[str] = None
    crop_filter: Optional[str] = None
    files: Dict[str, FileQualityReport]


# ==========================================
# 4. BOTTLENECK & PRIORITY VIEW SCHEMAS
# ==========================================

class BottleneckNodeResponse(BaseModel):
    """Node capacity overshoot representation."""
    rank: int
    node_id: str
    node_name: str
    node_type: str
    district: str
    capacity_tonnes: float
    forecast_inflow_tonnes: float
    overshoot_tonnes: float
    overshoot_pct: float
    utilization_ratio: float
    is_active_alert: bool


class ScenarioBottlenecksResponse(BaseModel):
    """Bottleneck summary for a single reliability scenario."""
    computable: bool
    status: str
    reason: Optional[str] = None
    total_bottleneck_nodes: int
    active_alerts_count: int
    total_overshoot_tonnes: float
    max_utilization_ratio: float
    data_provenance: str
    bottlenecks: List[BottleneckNodeResponse]


class BottleneckDetectionResponse(BaseModel):
    """All scenarios bottleneck simulation results."""
    district: str
    crop: str
    scenarios: Dict[str, ScenarioBottlenecksResponse]


class PriorityDistrictView(BaseModel):
    """District priority rank entry for the multi-district dashboard."""
    priority_rank: int
    district: str
    crop: str
    bottleneck_risk_score: float
    total_overshoot_tonnes: float
    active_alerts_count: int
    max_utilization_ratio: float
    top_bottleneck_node: str
    top_bottleneck_overshoot_tonnes: float
    confidence_tier: str
    computable: bool
    reason: Optional[str] = None


class PriorityViewResponse(BaseModel):
    """Multi-district priority ranking response."""
    crop: str
    districts_ranked: List[PriorityDistrictView]
    total_districts: int


# ==========================================
# 5. RECOMMENDATION & CONFIDENCE GATE SCHEMAS
# ==========================================

class DisagreementMatrixResponse(BaseModel):
    """Divergence diagnosis returned when scenarios disagree."""
    action_verdict: str
    disagreement_reason: str
    primary_disagreement_driver: str
    primary_disagreement_explanation: str
    competing_interventions: List[str]
    scenario_picks: Dict[str, Dict[str, Any]]


class EvidenceItemResponse(BaseModel):
    """Single itemized fact and source citation."""
    fact: str
    source: str
    category: str


class RecommendationResponse(BaseModel):
    """Full counterfactual optimization and confidence gate response."""
    recommendation_id: str
    district: str
    crop: str
    confidence_label: str
    confidence_score: float
    data_density_tier: str
    scenario_consensus: bool
    selected_action: str
    selected_intervention_id: str
    action_type: str
    worst_case_guaranteed_payoff_rs: float
    average_payoff_rs: float
    max_regret_rs: float
    minimax_regret_intervention: str
    computable_scenarios: List[str]
    uncomputable_scenarios: List[str]
    provenance_note: str
    disagreement_matrix: Optional[DisagreementMatrixResponse] = None
    evidence_chain: List[EvidenceItemResponse]
    explanation_summary: str


# ==========================================
# 6. EXPLAINABILITY & SCHEME ADVISOR SCHEMAS
# ==========================================

class ExplanationResponse(BaseModel):
    """Structured explanation report for the frontend Why? panel."""
    recommendation_id: str
    district: str
    crop: str
    selected_action: str
    confidence_label: str
    confidence_score: float
    evidence_chain: List[EvidenceItemResponse]
    worst_case_guaranteed_payoff_rs: float
    max_regret_rs: float
    scenario_consensus: bool
    primary_disagreement_driver: Optional[str] = None
    summary_verdict: str


class SchemeDetailResponse(BaseModel):
    """Government scheme document explanation details."""
    scheme_id: str
    scheme_name: str
    ministry: Optional[str] = None
    matched_action_type: Optional[str] = None
    source_document: str
    plain_language_summary: str
    grounded_clauses: List[str] = Field(default_factory=list)
    mandatory_notice: str


class SchemeAdvisorResponse(BaseModel):
    """Grounded government scheme recommendations."""
    recommendation_id: Optional[str] = None
    action_type: str
    matched_schemes_count: int
    matched_scheme_ids: List[str]
    schemes: List[SchemeDetailResponse]
    mandatory_notice: str


# ==========================================
# 7. OUTCOME HISTORY & LEARNING LOOP SCHEMAS
# ==========================================

class OutcomeHistoryResponse(BaseModel):
    """Learning database reconciliation summary."""
    district: str
    crop: str
    total_reconciled_alerts: int
    calibration_status: str
    scenario_win_counts: Dict[str, int]
    scenario_win_percentages: Dict[str, float]
    data_provenance: str
    caution_note: str


# ==========================================
# 8. BACKTESTING & REPLAY SCHEMAS
# ==========================================

class BacktestRowResponse(BaseModel):
    """Side-by-side node prediction vs actual comparison."""
    node_id: str
    node_name: str
    node_type: str
    capacity_tonnes: float
    predicted_inflow_tonnes: float
    predicted_overshoot_tonnes: float
    predicted_is_bottleneck: bool
    actual_peak_arrival_tonnes: float
    actual_is_bottleneck: bool
    prediction_correct: bool


class BacktestResponse(BaseModel):
    """Historical seasonal backtest validation."""
    district: str
    crop: str
    backtest_year: str
    status: str
    reason: Optional[str] = None
    pre_harvest_records_count: int
    post_harvest_actual_records_count: int
    bottleneck_detection_precision: float
    bottleneck_detection_recall: float
    actual_mean_modal_price_rs: float
    predicted_price_impact_rs: float
    data_provenance: str
    comparison_table: List[BacktestRowResponse]


class BacktestReplayPointResponse(BaseModel):
    """Single chronological step in the harvest replay."""
    week: int
    calendar_week: int
    week_start_date: str
    week_end_date: str
    predicted_state: str
    actual_state: str
    flow_predicted_tonnes: float
    flow_actual_tonnes: float
    bottleneck_predicted: bool
    bottleneck_actual: bool
    is_accurate: bool
    cumulative_spoilage_prevented_rs: float


class BacktestReplayResponse(BaseModel):
    """Complete chronological replay timeline."""
    district: str
    crop: str
    backtest_year: str
    status: str
    reason: Optional[str] = None
    total_weeks: int
    overall_accuracy_pct: float
    data_provenance: str
    replay_timeline: List[BacktestReplayPointResponse]


# ==========================================
# 9. MODEL PERFORMANCE & MODEL CARD SCHEMAS
# ==========================================

class PriceModelPerformance(BaseModel):
    """Price elasticity model card metrics."""
    district: str
    crop: str
    is_fitted: bool
    status: str
    cutoff_date: str
    n_observations: int
    n_train: int
    n_test: int
    train_r2: Optional[float] = None
    test_r2: Optional[float] = None
    test_mae_rs: Optional[float] = None
    test_rmse_rs: Optional[float] = None
    slope: Optional[float] = None
    elasticity: Optional[float] = None
    mean_price: Optional[float] = None
    walk_forward_folds: List[Dict[str, Any]] = Field(default_factory=list)
    data_provenance: str


class ForecastModelPerformance(BaseModel):
    """Flow forecast model card metrics."""
    district: str
    crop: str
    is_fitted: bool
    status: str
    cutoff_year: str
    season: str
    latest_production_tonnes: float
    baseline_weekly_tonnes: float
    test_mae_tonnes: float
    test_mape_pct: float
    test_rmse_tonnes: float
    walk_forward_folds: List[Dict[str, Any]] = Field(default_factory=list)
    data_provenance: str


class ModelPerformanceResponse(BaseModel):
    """Combined model card performance endpoint."""
    district: str
    crop: str
    price_elasticity_model: PriceModelPerformance
    flow_forecast_model: ForecastModelPerformance
    limitations: List[str]


# ==========================================
# 10. CAPABILITY TIER & GENERALIZATION SCHEMAS
# ==========================================

class CoverageDistrictItem(BaseModel):
    """Coverage registry item for Tier 1 mapped or Tier 2 coordinate districts."""
    district: str
    state: str
    capability_tier: str
    network_nodes_count: Optional[int] = 0
    historical_records_count: Optional[int] = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    provenance: str


class CoverageResponse(BaseModel):
    """District capability coverage map for demo and audit visibility."""
    total_districts_tracked: int
    tier_1_full_twins_count: int
    tier_2_live_snapshots_count: int
    tier_1_districts: List[CoverageDistrictItem]
    tier_2_districts: List[CoverageDistrictItem]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    data_provenance: str


class Tier2SnapshotResponse(BaseModel):
    """Live observational market and meteorological snapshot for unmapped districts."""
    capability_tier: str = "TIER_2_LIVE_SNAPSHOT"
    state: str
    district: str
    crop: str
    timestamp: str
    topology_status: str = "NOT_MAPPED"
    simulation_status: str = "UNAVAILABLE"
    notice: str
    live_prices: Dict[str, Any]
    live_weather: Dict[str, Any]
    production_trend: Dict[str, Any]
    provenance_summary: Dict[str, str]


class Tier3InsufficientResponse(BaseModel):
    """Honest insufficiency report when neither local data nor live feeds exist."""
    capability_tier: str = "TIER_3_INSUFFICIENT"
    state: str
    district: str
    crop: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: str = "insufficient_data"
    message: str
    provenance: str


class UniversalAnalyzeResponse(BaseModel):
    """
    Unified entry point response for any Indian district.
    Carries capability_tier at top level always, along with a flat
    confidence_label/answer/matched_intent/referenced_context_ids projection
    (derived from whichever tier branch actually ran) so callers do not need
    to know the tier-specific nested shape just to render a headline answer.
    """
    capability_tier: str = Field(..., description="TIER_1_FULL_TWIN | TIER_2_LIVE_SNAPSHOT | TIER_3_INSUFFICIENT")
    state: str
    district: str
    crop: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    tier_explanation: str
    confidence_label: str = Field(..., description="HIGH | MODERATE | LOW, mirrored from the active tier's own assessment")
    answer: str = Field(..., description="Plain-language headline answer for this tier, safe to render directly")
    matched_intent: str = Field(..., description="Which tier pathway produced this answer")
    referenced_context_ids: List[str] = Field(default_factory=list)
    full_twin_recommendation: Optional[RecommendationResponse] = None
    explanation: Optional[ExplanationResponse] = None
    scheme_advice: Optional[SchemeAdvisorResponse] = None
    live_snapshot: Optional[Dict[str, Any]] = None
    insufficient_details: Optional[Dict[str, Any]] = None
    provenance: str


class PriceForecastResponse(BaseModel):
    """Explicit forward price prediction with uncertainty bounds and based_on traceability."""
    state: str
    district: str
    crop: str
    days_ahead: int
    capability_tier: str
    status: str
    predicted_price_range: Optional[List[float]] = None
    point_estimate_rs: Optional[float] = None
    confidence_label: str
    confidence_score: float
    interval_width_rs: Optional[float] = None
    based_on: Dict[str, Any] = Field(default_factory=dict)
    refusal_reason: Optional[str] = None
    data_provenance: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SatelliteClimateResponse(BaseModel):
    """NASA POWER satellite-derived agro-meteorological climate parameters."""
    status: str
    district: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    days_observed: Optional[int] = None
    mean_daily_solar_radiation_mj_m2: Optional[float] = None
    mean_temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    total_precipitation_mm: Optional[float] = None
    accumulated_gdd_base10: Optional[float] = None
    solar_maturity_acceleration_ratio: Optional[float] = None
    climate_data_type: str = "satellite_derived_agro_meteorology"
    optical_vegetation_imagery_note: str
    provenance: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ==========================================
# 11. SOWING ADVISORY, FARMER QUERY & LOCATION SCHEMAS
# ==========================================

class SowingAdvisoryResponse(BaseModel):
    """Pre-sowing window optimization response for bottleneck avoidance."""
    state: str
    district: str
    crop: str
    target_season: str
    capability_tier: str
    confidence_label: str
    confidence_score: float
    optimization_status: str
    nominal_sowing_window: Dict[str, Any]
    recommended_sowing_window: Dict[str, Any]
    candidate_windows_evaluated: List[Dict[str, Any]] = Field(default_factory=list)
    bottleneck_risk_reduction_pct: float = 0.0
    evidence_chain: List[Dict[str, str]] = Field(default_factory=list)
    notice: str
    provenance: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class FarmerQueryRequest(BaseModel):
    """Grounded query request payload."""
    state: str = Field(default="Kerala", description="State name")
    district: str = Field(default="Alappuzha", description="District name")
    crop: str = Field(default="rice", description="Crop commodity")
    question: str = Field(..., description="Farmer or FPO question to evaluate")
    context_ids: Optional[List[str]] = Field(default=None, description="Optional referenced prior output IDs")


class FarmerQueryResponse(BaseModel):
    """Grounded query layer response strictly bounded to system evidence chains."""
    question: str
    answer: str
    out_of_scope: bool
    matched_intent: str
    confidence_label: str
    provenance: str
    referenced_context_ids: List[str] = Field(default_factory=list)
    mandatory_notice: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class LocationSummaryResponse(BaseModel):
    """Single-call map interaction summary payload."""
    status: str
    input_coordinates: Dict[str, float]
    resolved_location: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    district: Optional[str] = None
    crop: Optional[str] = None
    capability_tier: str
    confidence_label: str
    tier_explanation: str
    sowing_advisory: Optional[Dict[str, Any]] = None
    satellite_climate: Optional[Dict[str, Any]] = None
    full_twin: Optional[Dict[str, Any]] = None
    live_snapshot: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    provenance: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")



