"""
Fasal Twin - Production REST API Layer
Hardened FastAPI application with:
- Strongly typed Pydantic response models across all endpoints
- Standardized error envelopes ({error_type, message, affected_resource, timestamp})
- Request ID tracing middleware (X-Request-ID)
- Persisted model caching at application startup
- Detailed multi-source health monitoring (/health/detailed)
- Multi-district priority ranking (/priority-view)
- Structured model card performance metrics (/model-performance/{district}/{crop})
- Chronological backtest replay (/backtest/{district}/{crop}/{year}/replay)
"""

import os
import sys
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Request, Query, Path as FPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.data_loader import DataLoader
from src.counterfactual_optimizer import CounterfactualOptimizer
from src.confidence_gate import ConfidenceGate
from src.bottleneck_detector import BottleneckDetector, get_multi_district_priority_ranking
from src.backtest import HistoricalBacktester
from src.explain import DecisionExplainer
from src.see_layer import get_price_trend, get_weather_advisory, get_crop_maturity_proxy
from src.outcome_tracker import OutcomeTracker
from src.scheme_advisor import SchemeAdvisor
from src.price_elasticity_model import PriceElasticityModel
from src.forecast_model import ForecastModel
from src.capability_tier import resolve_tier, CapabilityTier, TIER_1_FULL_TWIN, TIER_2_LIVE_SNAPSHOT, TIER_3_INSUFFICIENT
from src.live_district_data import get_live_snapshot_summary, LiveDistrictDataConnector
from src.price_forecast import forecast_price
from src.satellite_climate_provider import fetch_satellite_climate
from src.sowing_advisory import recommend_sowing_window
from src.farmer_query import answer_farmer_query
from src.location_resolver import get_location_summary, resolve_location
from src.schemas import (
    StandardErrorResponse,
    HealthResponse,
    DetailedHealthResponse,
    DataSourceHealth,
    PriceTrendResponse,
    WeatherAdvisoryResponse,
    CropMaturityResponse,
    DataQualityResponse,
    BottleneckDetectionResponse,
    PriorityViewResponse,
    RecommendationResponse,
    ExplanationResponse,
    SchemeAdvisorResponse,
    OutcomeHistoryResponse,
    BacktestResponse,
    BacktestReplayResponse,
    ModelPerformanceResponse,
    CoverageDistrictItem,
    CoverageResponse,
    Tier2SnapshotResponse,
    Tier3InsufficientResponse,
    UniversalAnalyzeResponse,
    PriceForecastResponse,
    SatelliteClimateResponse,
    SowingAdvisoryResponse,
    FarmerQueryRequest,
    FarmerQueryResponse,
    LocationSummaryResponse,
)

from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ReqID: %(name)s] %(message)s")
logger = logging.getLogger("fasal-twin")

# In-memory application caches
RECOMMENDATION_STORE: Dict[str, Dict[str, Any]] = {}
PERSISTED_MODELS_CACHE: Dict[str, Any] = {}
outcome_tracker = OutcomeTracker()
scheme_advisor = SchemeAdvisor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Loads serialized model artifacts from models/ at startup to eliminate per-request refitting."""
    models_dir = repo_root / "models"
    loaded_names = []
    
    districts = ["alappuzha", "kottayam"]
    for dist in districts:
        # Load Price Elasticity Model
        price_files = list(models_dir.glob(f"price_elasticity_{dist}_rice_*.joblib"))
        if price_files:
            latest_price_file = sorted(price_files)[-1]
            try:
                m = PriceElasticityModel.load(latest_price_file)
                PERSISTED_MODELS_CACHE[f"price_{dist}_rice"] = m
                loaded_names.append(latest_price_file.name)
            except Exception as e:
                logger.warning(f"Could not load {latest_price_file.name}: {e}")

        # Load Forecast Model
        fc_files = list(models_dir.glob(f"forecast_{dist}_rice_*.joblib"))
        if fc_files:
            latest_fc_file = sorted(fc_files)[-1]
            try:
                f = ForecastModel.load(latest_fc_file)
                PERSISTED_MODELS_CACHE[f"forecast_{dist}_rice"] = f
                loaded_names.append(latest_fc_file.name)
            except Exception as e:
                logger.warning(f"Could not load {latest_fc_file.name}: {e}")

    logger.info(f"Startup complete: Loaded {len(loaded_names)} persisted models: {loaded_names}")
    yield


app = FastAPI(
    title="Fasal Twin - Regional Crop-Flow Bottleneck Simulator API",
    description="Backend API powering crop-flow simulations, robust optimization, confidence gating, explainability, and scheme advisory.",
    version="1.2.0",
    lifespan=lifespan,
)

# Configurable CORS allowlist via environment variable
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173")
allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ==========================================
# MIDDLEWARE: REQUEST ID & TIMING
# ==========================================

@app.middleware("http")
async def request_id_and_timing_middleware(request: Request, call_next):
    """Assigns unique X-Request-ID to every incoming call and logs structured execution latency."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    duration_ms = (time.time() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
    
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Latency: {duration_ms:.2f}ms (ID: {request_id})"
    )
    return response


# ==========================================
# EXCEPTION HANDLERS: STANDARDIZED ENVELOPE
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats all HTTPExceptions into the uniform StandardErrorResponse envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardErrorResponse(
            error_type="HTTPException",
            message=str(exc.detail),
            affected_resource=str(request.url.path),
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors into the uniform StandardErrorResponse envelope."""
    return JSONResponse(
        status_code=422,
        content=StandardErrorResponse(
            error_type="RequestValidationError",
            message=str(exc.errors()),
            affected_resource=str(request.url.path),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Formats unexpected exceptions into the uniform StandardErrorResponse envelope."""
    logger.error(f"Unhandled Exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=StandardErrorResponse(
            error_type="InternalServerError",
            message=f"An unexpected error occurred: {str(exc)}",
            affected_resource=str(request.url.path),
        ).model_dump(),
    )


# ==========================================
# 1. SYSTEM HEALTH ENDPOINTS
# ==========================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Basic health check endpoint returning system status."""
    return HealthResponse(status="healthy", service="fasal-twin-backend", version="1.2.0")


@app.get("/health/detailed", response_model=DetailedHealthResponse, tags=["System"])
def detailed_health_check():
    """
    Comprehensive multi-source health report verifying every CSV, live API reachability,
    SQLite outcome database connectivity, and loaded model artifacts.
    """
    data_dir = repo_root / "data"
    sources_health: Dict[str, DataSourceHealth] = {}
    
    # 1. Check CSV files
    csv_files = [
        ("rice_area_production.csv", "Kerala DES Agricultural Statistics Table 5.1.1"),
        ("mandi_arrivals_prices.csv", "Agmarknet Daily Mandi Arrivals & Prices"),
        ("weather_daily.csv", "IMD Daily Historical Rainfall"),
        ("network_capacity.csv", "Regional Node Capacity Registry"),
        ("network_edges.csv", "Regional Logistics Directed Edges"),
        ("supplyco_procurement.csv", "Supplyco Paddy Procurement Center Logs"),
    ]
    
    for filename, prov in csv_files:
        filepath = data_dir / filename
        exists = filepath.exists()
        row_count = 0
        status_msg = "Healthy"
        if exists:
            try:
                import pandas as pd
                df = pd.read_csv(filepath)
                row_count = len(df)
            except Exception as e:
                status_msg = f"Read error: {str(e)}"
        else:
            status_msg = "File missing"
            
        sources_health[filename] = DataSourceHealth(
            source_name=filename,
            resource_type="csv_file",
            is_available=exists and (row_count > 0),
            record_count=row_count,
            status_details=status_msg,
            provenance=prov,
        )

    # 2. Check Database Connectivity
    db_path = data_dir / "outcomes.db"
    db_ok = db_path.exists()
    db_count = 0
    db_status = "Connected"
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        # outcome_tracker.py creates 'recommendation_logs', not 'recommendation_alerts' —
        # querying the wrong table name silently marked a healthy DB as broken.
        cur.execute("SELECT COUNT(*) FROM recommendation_logs;")
        db_count = cur.fetchone()[0]
        conn.close()
    except Exception as e:
        db_ok = False
        db_status = f"Query error: {str(e)}"

    sources_health["outcomes.db"] = DataSourceHealth(
        source_name="outcomes.db",
        resource_type="sqlite_db",
        is_available=db_ok,
        record_count=db_count,
        status_details=db_status,
        provenance="SQLite persistent learning loop and alert reconciliation storage",
    )

    # 3. Check Live Weather API Reachability (Open-Meteo)
    weather_live_ok = True
    weather_status = "Reachable"
    try:
        import requests
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast?latitude=9.49&longitude=76.33&daily=precipitation_sum&timezone=auto",
            timeout=2.0,
        )
        weather_live_ok = (resp.status_code == 200)
        weather_status = "Online (200 OK)" if weather_live_ok else f"HTTP {resp.status_code}"
    except Exception as e:
        weather_live_ok = False
        weather_status = f"Offline / Timeout ({str(e)[:40]}) - Historical CSV fallback active"

    sources_health["open_meteo_live_api"] = DataSourceHealth(
        source_name="Open-Meteo Live Weather API",
        resource_type="live_api",
        is_available=weather_live_ok,
        record_count=None,
        status_details=weather_status,
        provenance="Open-Meteo open weather API (with automated historical CSV fallback)",
    )

    total_checked = len(sources_health)
    total_online = sum(1 for s in sources_health.values() if s.is_available)
    sys_status = "healthy" if total_online >= total_checked - 1 else "degraded"

    return DetailedHealthResponse(
        system_status=sys_status,
        service="fasal-twin-backend",
        version="1.2.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        data_sources=sources_health,
        persisted_models_loaded=list(PERSISTED_MODELS_CACHE.keys()),
        total_sources_online=total_online,
        total_sources_checked=total_checked,
    )


# ==========================================
# 2. SEE-LAYER ENDPOINTS
# ==========================================

@app.get("/see/price-trend/{district}/{market}/{crop}", response_model=PriceTrendResponse, tags=["SEE Layer"])
def see_price_trend(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    market: str = FPath(..., description="Target mandi market (e.g., Alappuzha Mandi)"),
    crop: str = FPath(..., description="Target crop (e.g., rice)"),
    days: int = Query(14, ge=1, le=90, description="Trailing lookback window in days"),
):
    """Returns time series from mandi_arrivals_prices.csv for frontend trend charts."""
    try:
        return get_price_trend(district=district, market=market, crop=crop, days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Price trend retrieval failed: {str(exc)}")


@app.get("/see/weather-advisory/{district}/{crop}", response_model=WeatherAdvisoryResponse, tags=["SEE Layer"])
def see_weather_advisory(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop (e.g., rice)"),
    lookback_days: int = Query(30, ge=7, le=90, description="Rainfall lookback window in days"),
):
    """Returns plain-language weather advisory based on IMD daily rainfall variance and harvest shift factor."""
    try:
        return get_weather_advisory(district=district, crop=crop, lookback_days=lookback_days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Weather advisory generation failed: {str(exc)}")


@app.get("/see/crop-maturity/{district}/{crop}", response_model=CropMaturityResponse, tags=["SEE Layer"])
def see_crop_maturity(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop (e.g., rice)"),
    reference_date: Optional[str] = Query(None, description="Optional evaluation date YYYY-MM-DD"),
):
    """Returns crop maturity stage estimated from sowing calendar norms (Principle 3)."""
    try:
        return get_crop_maturity_proxy(district=district, crop=crop, reference_date=reference_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crop maturity estimation failed: {str(exc)}")


# ==========================================
# 2b. CAPABILITY TIER CLASSIFICATION
# ==========================================

@app.get("/capability-tier/{state}/{district}/{crop}", tags=["Generalization"])
def get_capability_tier(
    state: str = FPath(..., description="Target Indian state (e.g., Kerala, Punjab)"),
    district: str = FPath(..., description="Target district name (e.g., Alappuzha, Ernakulam)"),
    crop: str = FPath(..., description="Target crop (e.g., rice, tomato)"),
):
    """
    Lightweight tier classification endpoint.
    Calls resolve_tier() directly without triggering the full simulation pipeline.
    Returns: tier string (TIER_1_FULL_TWIN / TIER_2_LIVE_SNAPSHOT / TIER_3_INSUFFICIENT),
    human-readable explanation, and metadata dict.
    """
    try:
        loader = DataLoader()
        live_connector = LiveDistrictDataConnector()
        tier_val, explanation, meta = resolve_tier(
            state=state, district=district, crop=crop, loader=loader, live_connector=live_connector
        )
        return {
            "tier": tier_val,
            "explanation": explanation,
            "state": state,
            "district": district,
            "crop": crop,
            "meta": meta,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Capability tier resolution failed: {str(exc)}")


# ==========================================
# 3. DATA QUALITY AUDIT
# ==========================================


@app.get("/data-quality/{district}/{crop}", response_model=DataQualityResponse, tags=["Data Quality"])
def get_data_quality(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
):
    """Returns the comprehensive data quality and density audit report per file and per column."""
    loader = DataLoader()
    try:
        report = loader.data_quality_report(district=district, crop=crop)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Data quality audit failed: {str(exc)}")


# ==========================================
# 4. BOTTLENECK SIMULATION & PRIORITY VIEW
# ==========================================

@app.get("/bottleneck/{district}/{crop}", response_model=BottleneckDetectionResponse, tags=["Bottlenecks"])
def get_bottlenecks(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
):
    """Returns detected node capacity overshoots ranked by severity across all 4 scenarios with alert-fatigue filtering."""
    try:
        detector = BottleneckDetector(district=district, crop=crop)
        reports = detector.detect_all_bottlenecks()

        response = {
            "district": district,
            "crop": crop,
            "scenarios": {}
        }

        for sc_name, rep in reports.items():
            response["scenarios"][sc_name] = {
                "computable": rep.computable,
                "status": rep.status,
                "reason": rep.reason,
                "total_bottleneck_nodes": rep.total_bottleneck_nodes,
                "active_alerts_count": rep.active_alerts_count,
                "total_overshoot_tonnes": rep.total_overshoot_tonnes,
                "max_utilization_ratio": rep.max_utilization_ratio,
                "data_provenance": rep.data_provenance,
                "bottlenecks": [
                    {
                        "rank": b.rank,
                        "node_id": b.node_id,
                        "node_name": b.node_name,
                        "node_type": b.node_type,
                        "district": b.district,
                        "capacity_tonnes": b.capacity_tonnes,
                        "forecast_inflow_tonnes": b.forecast_inflow_tonnes,
                        "overshoot_tonnes": b.overshoot_tonnes,
                        "overshoot_pct": b.overshoot_pct,
                        "utilization_ratio": b.utilization_ratio,
                        "is_active_alert": b.is_active_alert,
                    }
                    for b in rep.bottlenecks
                ],
            }

        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Bottleneck detection failed: {str(exc)}")


@app.get("/priority-view", response_model=PriorityViewResponse, tags=["Priority View"])
def get_priority_view(
    crop: str = Query("rice", description="Target crop to rank across districts"),
):
    """
    Returns multi-district priority ranking sorted descending by composite bottleneck risk score.
    Used by regional officers to identify which district requires immediate logistical coordination.
    """
    try:
        rankings = get_multi_district_priority_ranking(crop=crop)
        return PriorityViewResponse(
            crop=crop,
            districts_ranked=rankings,
            total_districts=len(rankings),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Priority view generation failed: {str(exc)}")


# ==========================================
# 5. RECOMMENDATIONS & CONFIDENCE GATE
# ==========================================

@app.get("/recommendation/{district}/{crop}", response_model=RecommendationResponse, tags=["Recommendations"])
def get_recommendation(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
):
    """
    Computes the counterfactual-optimized policy recommendation using Maximin & Minimax Regret selection
    and passes it through the Confidence Truth Gate. Automatically logs to the outcome tracker.
    """
    try:
        optimizer = CounterfactualOptimizer(district=district, crop=crop)
        rec = optimizer.optimize()

        gate = ConfidenceGate()
        conf = gate.evaluate(rec, optimizer.elasticity_model.get_summary())

        explainer = DecisionExplainer(district=district, crop=crop)
        exp = explainer.explain(rec, conf, optimizer.elasticity_model.get_summary())

        action_type = "staggered_holding" if "INT-2" in rec.selected_intervention_id else (
            "redirect_mandi" if "INT-1" in rec.selected_intervention_id else (
                "direct_mill_offload" if "INT-3" in rec.selected_intervention_id else "do_nothing"
            )
        )

        # Cache in memory for explainability and scheme advisor lookups
        RECOMMENDATION_STORE[exp.recommendation_id] = {
            "recommendation": rec,
            "confidence": conf,
            "explanation": exp,
            "action_type": action_type,
            "elasticity_summary": optimizer.elasticity_model.get_summary(),
        }

        # Log alert to persistent learning database
        scenario_inflows = {}
        all_sc_results = optimizer.scenario_engine.run_all_scenarios()
        for sc in rec.computable_scenarios:
            if sc in all_sc_results:
                scenario_inflows[sc] = {"forecast_inflow": all_sc_results[sc].forecast_inflow}

        outcome_tracker.log_alert(
            recommendation_id=exp.recommendation_id,
            district=district,
            crop=crop,
            chosen_action=rec.selected_intervention_name,
            chosen_intervention_id=rec.selected_intervention_id,
            confidence_label=conf.confidence_label,
            confidence_score=conf.confidence_score,
            scenario_outputs=scenario_inflows,
        )

        response = {
            "recommendation_id": exp.recommendation_id,
            "district": district,
            "crop": crop,
            "confidence_label": conf.confidence_label,
            "confidence_score": conf.confidence_score,
            "data_density_tier": conf.data_density_tier,
            "scenario_consensus": conf.scenario_consensus,
            "selected_action": rec.selected_intervention_name,
            "selected_intervention_id": rec.selected_intervention_id,
            "action_type": action_type,
            "worst_case_guaranteed_payoff_rs": rec.worst_case_payoff_rs,
            "average_payoff_rs": rec.average_payoff_rs,
            "max_regret_rs": rec.max_regret_rs,
            "minimax_regret_intervention": rec.minimax_regret_intervention_name,
            "computable_scenarios": rec.computable_scenarios,
            "uncomputable_scenarios": rec.uncomputable_scenarios,
            "provenance_note": conf.provenance_note,
            "disagreement_matrix": (
                {
                    "action_verdict": conf.disagreement_matrix.action_verdict,
                    "disagreement_reason": conf.disagreement_matrix.disagreement_reason,
                    "primary_disagreement_driver": conf.disagreement_matrix.primary_disagreement_driver,
                    "primary_disagreement_explanation": conf.disagreement_matrix.primary_disagreement_explanation,
                    "competing_interventions": conf.disagreement_matrix.competing_interventions,
                    "scenario_picks": conf.disagreement_matrix.scenario_picks,
                }
                if conf.disagreement_matrix
                else None
            ),
            "evidence_chain": exp.evidence_chain,
            "explanation_summary": exp.summary_verdict,
        }

        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendation engine failed: {str(exc)}")


# ==========================================
# 6. EXPLAINABILITY & SCHEME ADVISOR
# ==========================================

@app.get("/explain/{recommendation_id}", response_model=ExplanationResponse, tags=["Explainability"])
def get_explanation(
    recommendation_id: str = FPath(..., description="ID of a previous recommendation"),
):
    """Returns the structured JSON evidence chain, regret bounds, and audit trail for a specific recommendation."""
    if recommendation_id not in RECOMMENDATION_STORE:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation ID '{recommendation_id}' not found in active session cache.",
        )

    stored = RECOMMENDATION_STORE[recommendation_id]
    exp: Any = stored["explanation"]

    return {
        "recommendation_id": exp.recommendation_id,
        "district": exp.district,
        "crop": exp.crop,
        "selected_action": exp.selected_action,
        "confidence_label": exp.confidence_label,
        "confidence_score": exp.confidence_score,
        "evidence_chain": exp.evidence_chain,
        "worst_case_guaranteed_payoff_rs": exp.worst_case_guaranteed_payoff_rs,
        "max_regret_rs": exp.max_regret_rs,
        "scenario_consensus": exp.scenario_consensus,
        "primary_disagreement_driver": exp.primary_disagreement_driver,
        "summary_verdict": exp.summary_verdict,
    }


@app.get("/scheme-advisor/{recommendation_id}", response_model=SchemeAdvisorResponse, tags=["Scheme Advisor"])
def get_scheme_advice(
    recommendation_id: str = FPath(..., description="ID of a previous recommendation"),
):
    """Returns grounded government scheme recommendations and clauses attached to the recommendation's action type."""
    if recommendation_id in RECOMMENDATION_STORE:
        action_type = RECOMMENDATION_STORE[recommendation_id].get("action_type", "staggered_holding")
    else:
        action_type = "staggered_holding"

    try:
        advice = scheme_advisor.advise_for_recommendation(action_type=action_type)
        return {
            "recommendation_id": recommendation_id,
            **advice
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scheme advisory retrieval failed: {str(exc)}")


# ==========================================
# 7. OUTCOME HISTORY & LEARNING LOOP
# ==========================================

@app.get("/outcome-history/{district}/{crop}", response_model=OutcomeHistoryResponse, tags=["Learning Loop"])
def get_outcome_history(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
):
    """Returns the historical scenario accuracy summary and sample size N."""
    try:
        return outcome_tracker.scenario_accuracy_summary(district=district, crop=crop)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Outcome history retrieval failed: {str(exc)}")


# ==========================================
# 8. HISTORICAL BACKTESTING & REPLAY
# ==========================================

@app.get("/backtest/{district}/{crop}/{year}", response_model=BacktestResponse, tags=["Validation"])
def get_backtest(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
    year: str = FPath(..., description="Historical season/year to validate against (e.g., 2022-23)"),
):
    """Runs historical backtest comparing pre-harvest predictions against actual observed outcomes."""
    try:
        backtester = HistoricalBacktester(district=district, crop=crop)
        res = backtester.run_backtest(target_year=year)

        return {
            "district": res.district,
            "crop": res.crop,
            "backtest_year": res.backtest_year,
            "status": res.status,
            "reason": res.reason,
            "pre_harvest_records_count": res.pre_harvest_records_count,
            "post_harvest_actual_records_count": res.post_harvest_actual_records_count,
            "bottleneck_detection_precision": res.bottleneck_detection_precision,
            "bottleneck_detection_recall": res.bottleneck_detection_recall,
            "actual_mean_modal_price_rs": res.actual_mean_modal_price_rs,
            "predicted_price_impact_rs": res.predicted_price_impact_rs,
            "data_provenance": res.data_provenance,
            "comparison_table": [
                {
                    "node_id": r.node_id,
                    "node_name": r.node_name,
                    "node_type": r.node_type,
                    "capacity_tonnes": r.capacity_tonnes,
                    "predicted_inflow_tonnes": r.predicted_inflow_tonnes,
                    "predicted_overshoot_tonnes": r.predicted_overshoot_tonnes,
                    "predicted_is_bottleneck": r.predicted_is_bottleneck,
                    "actual_peak_arrival_tonnes": r.actual_peak_arrival_tonnes,
                    "actual_is_bottleneck": r.actual_is_bottleneck,
                    "prediction_correct": r.prediction_correct,
                }
                for r in res.comparison_table
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {str(exc)}")


@app.get("/backtest/{district}/{crop}/{year}/replay", response_model=BacktestReplayResponse, tags=["Validation"])
def get_backtest_replay(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
    year: str = FPath(..., description="Historical season/year to replay (e.g., 2022-23)"),
):
    """
    Returns ordered week-by-week chronological replay sequence of the harvest window,
    comparing forecasted flow states with actual recorded mandi arrivals.
    """
    try:
        backtester = HistoricalBacktester(district=district, crop=crop)
        replay_res = backtester.run_backtest_replay(target_year=year)

        return {
            "district": replay_res.district,
            "crop": replay_res.crop,
            "backtest_year": replay_res.backtest_year,
            "status": replay_res.status,
            "reason": replay_res.reason,
            "total_weeks": replay_res.total_weeks,
            "overall_accuracy_pct": replay_res.overall_accuracy_pct,
            "data_provenance": replay_res.data_provenance,
            "replay_timeline": [
                {
                    "week": pt.week,
                    "calendar_week": pt.calendar_week,
                    "week_start_date": pt.week_start_date,
                    "week_end_date": pt.week_end_date,
                    "predicted_state": pt.predicted_state,
                    "actual_state": pt.actual_state,
                    "flow_predicted_tonnes": pt.flow_predicted_tonnes,
                    "flow_actual_tonnes": pt.flow_actual_tonnes,
                    "bottleneck_predicted": pt.bottleneck_predicted,
                    "bottleneck_actual": pt.bottleneck_actual,
                    "is_accurate": pt.is_accurate,
                    "cumulative_spoilage_prevented_rs": pt.cumulative_spoilage_prevented_rs,
                }
                for pt in replay_res.replay_timeline
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest replay failed: {str(exc)}")


# ==========================================
# 9. MODEL PERFORMANCE & MODEL CARD METRICS
# ==========================================

@app.get("/model-performance/{district}/{crop}", response_model=ModelPerformanceResponse, tags=["Model Card"])
def get_model_performance(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha)"),
    crop: str = FPath(..., description="Target crop name (e.g., rice)"),
):
    """
    Returns the full model card metrics for both the price elasticity and inflow forecast models,
    including walk-forward cross-validation folds and honest technical limitations.
    """
    cache_key_price = f"price_{district.lower()}_{crop.lower()}"
    cache_key_forecast = f"forecast_{district.lower()}_{crop.lower()}"

    # Use cached startup models if available, otherwise fit on demand
    price_model = PERSISTED_MODELS_CACHE.get(cache_key_price)
    if price_model is None:
        price_model = PriceElasticityModel(district=district, crop=crop).fit()

    forecast_model = PERSISTED_MODELS_CACHE.get(cache_key_forecast)
    if forecast_model is None:
        forecast_model = ForecastModel(district=district, crop=crop).fit()

    p_sum = price_model.get_summary()
    f_sum = forecast_model.get_summary()

    limitations = [
        "Price elasticity slope is linear/log-log; does not model macroeconomic MSP baseline inflation over multi-year periods.",
        "Kottayam mandi flow has higher variance (MAPE ~37.5%) due to private mill direct offloading compared to Alappuzha (MAPE ~6.4%).",
        "Crop maturity stages are derived from agro-climatic sowing calendar norms (Principle 3), not live satellite NDVI/SAR imagery.",
        "Weather surge scaling is based on IMD precipitation variance and does not simulate catastrophic dyke breaches or road washouts.",
    ]

    return {
        "district": district,
        "crop": crop,
        "price_elasticity_model": {
            "district": p_sum["district"],
            "crop": p_sum["crop"],
            "is_fitted": p_sum["is_fitted"],
            "status": p_sum["status"],
            "cutoff_date": p_sum["cutoff_date"],
            "n_observations": p_sum["n_observations"],
            "n_train": p_sum.get("n_train", p_sum["n_observations"]),
            "n_test": p_sum.get("n_test", 0),
            "train_r2": p_sum.get("r_squared"),
            "test_r2": p_sum.get("test_r2_rs") or p_sum.get("test_r2"),
            "test_mae_rs": p_sum.get("test_mae_rs"),
            "test_rmse_rs": p_sum.get("test_rmse_rs"),
            "slope": p_sum.get("slope"),
            "elasticity": p_sum.get("elasticity"),
            "mean_price": p_sum.get("mean_price"),
            "walk_forward_folds": p_sum.get("walk_forward_summary", {}).get("folds", []),
            "data_provenance": p_sum.get("data_provenance", ""),
        },
        "flow_forecast_model": {
            "district": f_sum["district"],
            "crop": f_sum["crop"],
            "is_fitted": f_sum["is_fitted"],
            "status": f_sum["status"],
            "cutoff_year": f_sum["cutoff_year"],
            "season": f_sum.get("season", "punja"),
            "latest_production_tonnes": f_sum.get("latest_production_tonnes", 0.0),
            "baseline_weekly_tonnes": f_sum.get("baseline_weekly_tonnes", 0.0),
            "test_mae_tonnes": f_sum.get("test_mae_tonnes", 0.0),
            "test_mape_pct": f_sum.get("test_mape_pct", 0.0),
            "test_rmse_tonnes": f_sum.get("test_rmse_tonnes", 0.0),
            "walk_forward_folds": f_sum.get("walk_forward_summary", {}).get("folds", []),
            "data_provenance": f_sum.get("data_provenance", ""),
        },
        "limitations": limitations,
    }


# ==========================================
# 10. GENERALIZED DISTRICT ANALYZE & COVERAGE
# ==========================================

@app.get("/analyze/{state}/{district}/{crop}", response_model=UniversalAnalyzeResponse, tags=["Generalization"])
def analyze_any_district(
    state: str = FPath(..., description="Target Indian state (e.g., Kerala, Punjab, Haryana)"),
    district: str = FPath(..., description="Target district name (e.g., Alappuzha, Palakkad, Ludhiana)"),
    crop: str = FPath(..., description="Target crop (e.g., rice, wheat, maize)"),
):
    """
    Universal entry point to query any Indian district.
    Determines capability tier dynamically (Tier 1 Full Digital Twin, Tier 2 Live Observational Snapshot,
    or Tier 3 Insufficient Data) and returns an honest, calibrated response carrying capability_tier at the top level.
    """
    loader = DataLoader()
    live_connector = LiveDistrictDataConnector()
    tier_val, explanation, meta = resolve_tier(
        state=state, district=district, crop=crop, loader=loader, live_connector=live_connector
    )

    if tier_val == TIER_1_FULL_TWIN:
        # Full Digital Twin Pipeline
        optimizer = CounterfactualOptimizer(district=district, crop=crop, loader=loader)
        rec = optimizer.optimize()

        gate = ConfidenceGate()
        conf = gate.evaluate(rec, optimizer.elasticity_model.get_summary())

        explainer = DecisionExplainer(district=district, crop=crop)
        exp = explainer.explain(rec, conf, optimizer.elasticity_model.get_summary())

        action_type = "staggered_holding" if "INT-2" in rec.selected_intervention_id else (
            "redirect_mandi" if "INT-1" in rec.selected_intervention_id else (
                "direct_mill_offload" if "INT-3" in rec.selected_intervention_id else "do_nothing"
            )
        )

        RECOMMENDATION_STORE[exp.recommendation_id] = {
            "recommendation": rec,
            "confidence": conf,
            "explanation": exp,
            "action_type": action_type,
            "elasticity_summary": optimizer.elasticity_model.get_summary(),
        }

        advice_dict = scheme_advisor.advise_for_recommendation(action_type=action_type)

        rec_response = {
            "recommendation_id": exp.recommendation_id,
            "district": district,
            "crop": crop,
            "confidence_label": conf.confidence_label,
            "confidence_score": conf.confidence_score,
            "data_density_tier": conf.data_density_tier,
            "scenario_consensus": conf.scenario_consensus,
            "selected_action": rec.selected_intervention_name,
            "selected_intervention_id": rec.selected_intervention_id,
            "action_type": action_type,
            "worst_case_guaranteed_payoff_rs": rec.worst_case_payoff_rs,
            "average_payoff_rs": rec.average_payoff_rs,
            "max_regret_rs": rec.max_regret_rs,
            "minimax_regret_intervention": rec.minimax_regret_intervention_name,
            "computable_scenarios": rec.computable_scenarios,
            "uncomputable_scenarios": rec.uncomputable_scenarios,
            "provenance_note": conf.provenance_note,
            "disagreement_matrix": (
                {
                    "action_verdict": conf.disagreement_matrix.action_verdict,
                    "disagreement_reason": conf.disagreement_matrix.disagreement_reason,
                    "primary_disagreement_driver": conf.disagreement_matrix.primary_disagreement_driver,
                    "primary_disagreement_explanation": conf.disagreement_matrix.primary_disagreement_explanation,
                    "competing_interventions": conf.disagreement_matrix.competing_interventions,
                    "scenario_picks": conf.disagreement_matrix.scenario_picks,
                }
                if conf.disagreement_matrix
                else None
            ),
            "evidence_chain": exp.evidence_chain,
            "explanation_summary": exp.summary_verdict,
        }

        exp_response = {
            "recommendation_id": exp.recommendation_id,
            "district": exp.district,
            "crop": exp.crop,
            "selected_action": exp.selected_action,
            "confidence_label": exp.confidence_label,
            "confidence_score": exp.confidence_score,
            "evidence_chain": exp.evidence_chain,
            "worst_case_guaranteed_payoff_rs": exp.worst_case_guaranteed_payoff_rs,
            "max_regret_rs": exp.max_regret_rs,
            "scenario_consensus": exp.scenario_consensus,
            "primary_disagreement_driver": exp.primary_disagreement_driver,
            "summary_verdict": exp.summary_verdict,
        }

        scheme_response = {
            "recommendation_id": exp.recommendation_id,
            **advice_dict
        }

        return UniversalAnalyzeResponse(
            capability_tier=TIER_1_FULL_TWIN,
            state=state,
            district=district,
            crop=crop,
            tier_explanation=explanation,
            confidence_label=conf.confidence_label,
            answer=exp.summary_verdict,
            matched_intent="full_digital_twin_recommendation",
            referenced_context_ids=[exp.recommendation_id],
            full_twin_recommendation=RecommendationResponse(**rec_response),
            explanation=ExplanationResponse(**exp_response),
            scheme_advice=SchemeAdvisorResponse(**scheme_response),
            live_snapshot=None,
            insufficient_details=None,
            provenance="Tier 1 Digital Twin: Full multi-scenario simulation & optimization pipeline",
        )

    elif tier_val == TIER_2_LIVE_SNAPSHOT:
        snapshot = get_live_snapshot_summary(state=state, district=district, crop=crop, connector=live_connector)
        price_info = snapshot.get("live_prices", {}) or {}
        has_price = price_info.get("status") == "success"
        if has_price:
            answer = (
                f"{snapshot.get('notice', '')} Live observational snapshot: mean modal price of "
                f"Rs {price_info.get('mean_modal_price_rs')}/quintal across {price_info.get('records_count', 0)} "
                f"Agmarknet record(s)."
            )
            snapshot_confidence = "MODERATE"
        else:
            answer = snapshot.get("notice", explanation)
            snapshot_confidence = "LOW"

        return UniversalAnalyzeResponse(
            capability_tier=TIER_2_LIVE_SNAPSHOT,
            state=state,
            district=district,
            crop=crop,
            tier_explanation=explanation,
            confidence_label=snapshot_confidence,
            answer=answer,
            matched_intent="live_observational_snapshot",
            referenced_context_ids=[],
            full_twin_recommendation=None,
            explanation=None,
            scheme_advice=None,
            live_snapshot=snapshot,
            insufficient_details=None,
            provenance="Tier 2 Live Snapshot: Observational Agmarknet & Open-Meteo feeds (unmapped topology)",
        )

    else:
        return UniversalAnalyzeResponse(
            capability_tier=TIER_3_INSUFFICIENT,
            state=state,
            district=district,
            crop=crop,
            tier_explanation=explanation,
            confidence_label="LOW",
            answer=explanation,
            matched_intent="insufficient_data",
            referenced_context_ids=[],
            full_twin_recommendation=None,
            explanation=None,
            scheme_advice=None,
            live_snapshot=None,
            insufficient_details=meta,
            provenance="Tier 3 Insufficiency Gate: Insufficient local records and unmapped coordinates",
        )


@app.get("/coverage", response_model=CoverageResponse, tags=["Generalization"])
def get_system_coverage():
    """
    Returns the complete capability coverage map across India.
    Lists all Tier 1 mapped digital twin districts and Tier 2 live snapshot supported districts.
    """
    loader = DataLoader()
    live_connector = LiveDistrictDataConnector()
    
    tier_1_items: List[CoverageDistrictItem] = []
    tier_2_items: List[CoverageDistrictItem] = []
    
    # 1. Inspect Tier 1 districts from network_capacity and rice_area_production
    try:
        df_net = loader.load_network_capacity()
        df_prod = loader.load_rice_area_production()
        
        if not df_net.empty and "district" in df_net.columns:
            unique_net_districts = df_net["district"].dropna().unique().tolist()
            for dist in unique_net_districts:
                clean_dist = dist.strip().lower()
                matched_nodes = len(df_net[df_net["district"].str.strip().str.lower() == clean_dist])
                matched_prod = len(df_prod[df_prod["district"].str.strip().str.lower() == clean_dist]) if not df_prod.empty else 0
                
                if matched_nodes > 0 and matched_prod >= 5:
                    coords = live_connector.get_district_coordinates("Kerala", dist)
                    lat = coords[0] if coords else None
                    lon = coords[1] if coords else None
                    
                    tier_1_items.append(
                        CoverageDistrictItem(
                            district=dist.title(),
                            state="Kerala",
                            capability_tier=TIER_1_FULL_TWIN,
                            network_nodes_count=matched_nodes,
                            historical_records_count=matched_prod,
                            latitude=lat,
                            longitude=lon,
                            provenance="Mapped Network Topology (network_capacity.csv) + Kerala DES Agricultural Statistics",
                        )
                    )
    except Exception as exc:
        logger.warning(f"Error compiling Tier 1 coverage: {exc}")

    # 2. Inspect Tier 2 registered coordinates from district_coordinates.csv
    try:
        coords_df = live_connector._load_coordinates()
        tier_1_names = {item.district.strip().lower() for item in tier_1_items}
        
        if not coords_df.empty:
            for _, row in coords_df.iterrows():
                d_name = str(row["district"]).strip()
                s_name = str(row["state"]).strip()
                if d_name.lower() not in tier_1_names:
                    tier_2_items.append(
                        CoverageDistrictItem(
                            district=d_name.title(),
                            state=s_name.title(),
                            capability_tier=TIER_2_LIVE_SNAPSHOT,
                            network_nodes_count=0,
                            historical_records_count=0,
                            latitude=float(row["lat"]),
                            longitude=float(row["lon"]),
                            provenance=f"Centroid registry ({row['source']}) + Real-time Open-Meteo & Agmarknet feeds",
                        )
                    )
    except Exception as exc:
        logger.warning(f"Error compiling Tier 2 coverage: {exc}")

    return CoverageResponse(
        total_districts_tracked=len(tier_1_items) + len(tier_2_items),
        tier_1_full_twins_count=len(tier_1_items),
        tier_2_live_snapshots_count=len(tier_2_items),
        tier_1_districts=tier_1_items,
        tier_2_districts=tier_2_items,
        data_provenance="Fasal Twin Multi-Tier Capability Coverage Registry",
    )


# ==========================================
# 11. PRICE FORECAST & SATELLITE CLIMATE
# ==========================================

@app.get("/price-forecast/{state}/{district}/{crop}", response_model=PriceForecastResponse, tags=["Price Forecasting"])
def get_price_forecast(
    state: str = FPath(..., description="Target Indian state (e.g., Kerala, Punjab)"),
    district: str = FPath(..., description="Target district name (e.g., Alappuzha, Palakkad)"),
    crop: str = FPath(..., description="Target crop (e.g., rice)"),
    days_ahead: int = Query(14, ge=1, le=60, description="Forward forecast horizon in days"),
):
    """
    Computes an explicit forward price prediction range [low_rs, high_rs] per quintal with based_on traceability.
    - Tier 1 districts: Grounded econometric elasticity synthesis with arrival simulation.
    - Tier 2 & Tier 3 districts: Refuses forward price prediction without mapped arrival network topology.
    """
    try:
        cache_key_price = f"price_{district.lower()}_{crop.lower()}"
        cached_model = PERSISTED_MODELS_CACHE.get(cache_key_price)

        res = forecast_price(
            state=state,
            district=district,
            crop=crop,
            days_ahead=days_ahead,
            elasticity_model=cached_model,
        )

        return PriceForecastResponse(
            state=res.state,
            district=res.district,
            crop=res.crop,
            days_ahead=res.days_ahead,
            capability_tier=res.capability_tier,
            status=res.status,
            predicted_price_range=res.predicted_price_range,
            point_estimate_rs=res.point_estimate_rs,
            confidence_label=res.confidence_label,
            confidence_score=res.confidence_score,
            interval_width_rs=res.interval_width_rs,
            based_on=res.based_on,
            refusal_reason=res.refusal_reason,
            data_provenance=res.data_provenance,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Price forecasting failed: {str(exc)}")


@app.get("/see/satellite-climate/{district}", response_model=SatelliteClimateResponse, tags=["SEE Layer"])
def get_satellite_climate(
    district: str = FPath(..., description="Target district name (e.g., Alappuzha, Palakkad)"),
    state: str = Query("Kerala", description="Target Indian state"),
    days_lookback: int = Query(14, ge=7, le=60, description="Lookback window in days"),
):
    """
    Fetches real-time satellite/reanalysis-derived agro-meteorological climate data from NASA POWER.
    Returns solar radiation, thermal flux, and moisture indices. (Note: Optical NDVI vegetation imagery is separate).
    """
    try:
        data = fetch_satellite_climate(district=district, state=state, days_lookback=days_lookback)
        return SatelliteClimateResponse(
            status=data.get("status", "unavailable"),
            district=district,
            state=state,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            days_observed=data.get("days_observed"),
            mean_daily_solar_radiation_mj_m2=data.get("mean_daily_solar_radiation_mj_m2"),
            mean_temperature_c=data.get("mean_temperature_c"),
            relative_humidity_pct=data.get("relative_humidity_pct"),
            total_precipitation_mm=data.get("total_precipitation_mm"),
            accumulated_gdd_base10=data.get("accumulated_gdd_base10"),
            solar_maturity_acceleration_ratio=data.get("solar_maturity_acceleration_ratio"),
            climate_data_type=data.get("climate_data_type", "satellite_derived_agro_meteorology"),
            optical_vegetation_imagery_note=(
                "NASA POWER provides satellite-derived solar/climate flux; "
                "optical NDVI crop canopy imagery is a future roadmap integration."
            ),
            provenance=data.get("provenance", "NASA POWER Satellite Agroclimatology"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Satellite climate retrieval failed: {str(exc)}")


@app.get("/sowing-advisory/{state}/{district}/{crop}", response_model=SowingAdvisoryResponse, tags=["Decision Support"])
def get_sowing_advisory(
    state: str = FPath(..., description="Indian State (e.g., Kerala, Punjab)"),
    district: str = FPath(..., description="District Name (e.g., Alappuzha, Palakkad)"),
    crop: str = FPath(..., description="Crop commodity (e.g., rice, wheat)"),
    target_season: Optional[str] = Query(None, description="Optional target season (e.g., Punja, Virippu, Mundakan, Kharif, Rabi)"),
    current_date: Optional[str] = Query(None, description="Reference ISO date YYYY-MM-DD for evaluation"),
):
    """
    Forward-looking pre-sowing window optimization for harvest bottleneck avoidance.
    - Tier 1: Evaluates candidate sowing windows against predicted network loads to minimize bottleneck overlap.
    - Tier 2/3: Returns state agro-climatic calendar norms with transparent notice regarding unmapped topology.
    """
    try:
        loader = app.state.loader if hasattr(app.state, "loader") else DataLoader()
        res = recommend_sowing_window(
            state=state,
            district=district,
            crop=crop,
            target_season=target_season,
            current_date=current_date,
            loader=loader,
        )
        return SowingAdvisoryResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sowing advisory generation failed: {str(exc)}")


@app.post("/farmer-query", response_model=FarmerQueryResponse, tags=["Decision Support"])
def post_farmer_query(payload: FarmerQueryRequest):
    """
    Grounded query layer strictly bounded to Fasal Twin evidence chains, recommendations,
    price forecasts, and matched schemes. Questions outside system boundaries return out_of_scope=True.
    """
    try:
        loader = app.state.loader if hasattr(app.state, "loader") else DataLoader()
        res = answer_farmer_query(
            state=payload.state,
            district=payload.district,
            crop=payload.crop,
            question=payload.question,
            context_ids=payload.context_ids,
            loader=loader,
        )
        return FarmerQueryResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Farmer query evaluation failed: {str(exc)}")


@app.get("/location-summary", response_model=LocationSummaryResponse, tags=["Map Support"])
def get_map_location_summary(
    lat: float = Query(..., description="Tapped Latitude coordinate"),
    lon: float = Query(..., description="Tapped Longitude coordinate"),
    crop: str = Query("Rice", description="Crop commodity"),
    max_distance_km: float = Query(75.0, ge=10.0, le=300.0, description="Max snapping radius in kilometers"),
):
    """
    Single-call composite endpoint for interactive map pins and taps.
    Reverse-geocodes coordinate to nearest district centroid (with distance thresholding),
    bundling tier classification, sowing advisory, satellite climate, and decision intelligence.
    """
    try:
        loader = app.state.loader if hasattr(app.state, "loader") else DataLoader()
        res = get_location_summary(
            lat=lat,
            lon=lon,
            crop=crop,
            max_distance_km=max_distance_km,
            loader=loader,
        )
        return LocationSummaryResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Location summary resolution failed: {str(exc)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)

