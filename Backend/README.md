# Fasal Twin: Regional Crop-Flow Bottleneck Simulator

**Fasal Twin** is an explainable backend digital twin and regional crop-flow bottleneck simulator engineered for agricultural logistics and crisis intervention in India (defaulted to **Rice in Kuttanad, Alappuzha & Kottayam districts, Kerala**).

---

## 🏛️ Section 0 — Non-Negotiable Core Principles

Fasal Twin operates strictly under four core principles enforced across all codebase modules, models, and endpoints:

1. **Never fabricate a number.**
   If a required data file is missing, empty, or fails schema validation, the system halts with a named error (`SchemaValidationError`, `MissingDataFileError`). No silent interpolation or synthetic numbers dressed up as empirical truth.
2. **Every model output carries a confidence label and data-provenance citation.**
   Confidence tiers (`HIGH`, `MEDIUM`, `LOW`) are derived deterministically from actual empirical observation density ($N$, $R^2$, temporal span), never hardcoded.
3. **Zero IoT hardware or live satellite dependency.**
   All crop status and maturity signals originate from verified government statistical compendiums (DES/EARAS), Agmarknet market records, or IMD gridded daily weather files, with explicit proxy labeling.
4. **Transparent "I don't have enough data" path.**
   When historical observation depth is insufficient or when stress scenarios diverge in Low confidence, the system emits a structured **Disagreement Matrix** (`NO_ACTION_RECOMMENDED` or `SPLIT_ADVISORY`) with explicit driver diagnosis rather than forcing a fragile single choice.

---

## 📑 Model Card & Validation Packet

For technical reviewers, jury members, and econometricians:
- 📄 [**`models/MODEL_CARD.md`**](file:///c:/ai%20alans%20project/models/MODEL_CARD.md) — Complete documentation of training data spans, walk-forward cross-validation folds ($R^2$, MAE, RMSE, MAPE), and structural assumptions.
- 📄 [**`models/GENERALIZATION_TEST.md`**](file:///c:/ai%20alans%20project/models/GENERALIZATION_TEST.md) — Multi-district portability evaluation on Kottayam rice and thin-data guardrail verification on Idukki without code modification.
- 📄 [**`models/VALIDATION_SUMMARY.md`**](file:///c:/ai%20alans%20project/models/VALIDATION_SUMMARY.md) — Multi-year historical backtesting results (2020–2024), season-by-season precision/recall, and inter-annual variance analysis.

---

## 📁 Repository Structure

```
fasal-twin/
├── data/
│   ├── schemes/
│   │   ├── aif_scheme.txt             # Agriculture Infrastructure Fund guidelines & terms
│   │   ├── cgs_npf_scheme.txt         # Credit Guarantee Scheme for e-NWR Pledge Financing
│   │   ├── pmfby_scheme.txt           # Pradhan Mantri Fasal Bima Yojana paddy guidelines
│   │   └── supplyco_procurement_scheme.txt # Kerala Supplyco MSP & State Incentive Bonus manual
│   ├── rice_area_production.csv       # Area, production & yield (DES Compendium Table 5.1.1 & EARAS)
│   ├── mandi_arrivals_prices.csv      # Mandi daily arrivals & modal prices (Agmarknet via CEDA)
│   ├── weather_daily.csv              # IMD historical daily rainfall & forecast flags
│   ├── network_capacity.csv           # Logistics nodes: FPOs, Mandis, Storage, Processors
│   ├── network_edges.csv              # Road transit distances (km), hours, freight cost/tonne
│   ├── supplyco_procurement.csv       # Krishibhavan-level paddy procurement (Supplyco Paddy)
│   └── outcomes.db                    # Append-only SQLite database for alert logs & reconciliations
├── models/
│   ├── MODEL_CARD.md                  # Comprehensive model card & walk-forward metrics
│   ├── GENERALIZATION_TEST.md         # Kottayam & Idukki multi-district generalization report
│   ├── VALIDATION_SUMMARY.md          # Multi-year historical backtest evaluation & variance
│   ├── price_elasticity_alappuzha_rice_2023-12-31.joblib
│   ├── price_elasticity_kottayam_rice_2023-12-31.joblib
│   ├── forecast_alappuzha_rice_2022-23.joblib
│   └── forecast_kottayam_rice_2022-23.joblib
├── src/
│   ├── __init__.py
│   ├── config.py                      # Secure environment & fallback configuration
│   ├── capability_tier.py             # Multi-tier capability classifier (Tier 1 Twin, Tier 2 Snapshot, Tier 3 Insufficient)
│   ├── data_loader.py                 # Central schema enforcement & quality auditor
│   ├── network_model.py               # NetworkX logistics graph & capacity tracker
│   ├── price_elasticity_model.py      # Econometric price-volume elasticity regression & temporal CV
│   ├── price_forecast.py              # Explicit forward price prediction with uncertainty intervals & Tier 2/3 refusal
│   ├── sowing_advisory.py             # Forward-looking pre-sowing window optimization for bottleneck avoidance
│   ├── farmer_query.py                # Grounded query layer strictly bounded to evidence chains & out-of-scope guardrail
│   ├── location_resolver.py           # Reverse coordinate lookup & composite single-call map summary provider
│   ├── forecast_model.py              # Area-production and weather-driven flow forecasting & CV
│   ├── scenario_engine.py             # 4-scenario reliability engine (Baseline, Weather, Adjacent, Capacity)
│   ├── guardrails.py                  # Biological yield ceilings & temporal window integrity
│   ├── see_layer.py                   # SEE-layer feeds (price trend, weather advisory, maturity proxy with satellite refinement)
│   ├── satellite_climate_provider.py  # NASA POWER satellite agroclimatology telemetry (solar radiation & GDD)
│   ├── live_data_provider.py          # Real-time Open-Meteo weather & Data.gov.in mandi API with historical fallbacks
│   ├── bottleneck_detector.py         # Node capacity overshoot detection, alert-fatigue filter & priority ranking
│   ├── counterfactual_optimizer.py    # Maximin & Minimax Regret robust intervention optimizer
│   ├── confidence_gate.py             # Confidence labeling (HIGH/MED/LOW), Disagreement Matrix & Driver diagnosis
│   ├── outcome_tracker.py             # Append-only alert logger & scenario calibration feedback loop
│   ├── scheme_advisor.py              # Grounded government scheme decision support (AIF, CGS-NPF, PMFBY, Supplyco)
│   ├── backtest.py                    # Temporal pre-harvest backtest & week-by-week replay engine
│   ├── explain.py                     # Itemized JSON evidence chain generator ({fact, source})
│   ├── schemas.py                     # Strongly typed Pydantic request/response & error models
│   └── api.py                         # Production FastAPI REST application
├── tests/                             # 84 Unit & Integration tests (100% passing)
├── scripts/
│   ├── run_demo_sequence.py           # Automated rehearsal script executing all 9 live demo beats
│   └── system_readiness_check.py      # 11-point comprehensive end-to-end diagnostic & sign-off check
├── Dockerfile                         # Container deployment specification
├── render.yaml                        # Render cloud deployment blueprint
├── requirements.txt
└── README.md
```

---

## 🎯 Scope & Boundary: What Fasal Twin Does and Does Not Do

To maintain scientific integrity and prevent misrepresentation during demonstrations and audits, Fasal Twin maintains strictly defined operational boundaries:

### What Fasal Twin DOES:
- ✅ **Regional Crop-Flow Bottleneck Simulation**: Simulates regional post-harvest volume surges across 4 deterministic stress scenarios (Baseline, Weather Compression, Adjacent Spillover, and Capacity Shock).
- ✅ **Forward-Looking Sowing Window Optimization**: Recommends pre-sowing dates to prevent post-harvest logistics bottlenecks before they form, evaluating candidate windows against simulated network load.
- ✅ **Grounded Farmer & FPO Query Layer**: Answers questions strictly from verified system evidence chains, price forecasts, and scheme terms, enforcing an explicit `out_of_scope: true` guardrail to eliminate chatbot hallucinations.
- ✅ **Map-Ready Location Geocoding**: Reverse-geocodes coordinate taps to district centroids with strict distance thresholding ($\le 75\text{ km}$), bundling tiered intelligence in a single roundtrip.
- ✅ **Maximin & Minimax Regret Decision Optimization**: Solves for logistics interventions that maximize the guaranteed worst-case financial payoff for farmers and FPOs.
- ✅ **Explicit Forward Price Forecasting with Scaled Uncertainty**: Combines area-production arrival surges with econometric elasticity slopes to output a predicted price range $[P_{\text{low}}, P_{\text{high}}]$ whose uncertainty width scales inversely with sample density $N$ ($\pm 35\%$ for small $N=30$ vs $\pm 18\%$ for $N=1563$).
- ✅ **Satellite-Derived Agroclimatological Telemetry**: Ingests real-time solar irradiance ($MJ/m^2/\text{day}$), ambient temperature ($^\circ C$), and Growing Degree Days ($GDD$) from NASA POWER agroclimatology satellites via Census 2011 district centroids to refine phenological maturity timing.
- ✅ **Multi-Tier Nationwide Portability**: Classifies any Indian district into Tier 1 (Full Twin), Tier 2 (Live Snapshot), or Tier 3 (Transparent Insufficiency), refusing to hallucinate parameters for unmapped districts.
- ✅ **Deterministic Itemized Evidence Chains**: Provides auditable, line-by-line provenance citations (`[{fact, source}]`) for every recommendation.

### What Fasal Twin DOES NOT do:
- ❌ **Optical/SAR NDVI Crop Canopy Imagery**: NASA POWER telemetry provides surface solar radiation and thermal flux, **not** live 10-meter optical NDVI vegetation greenness imagery. *Direct Sentinel-2 / Landsat NDVI canopy health integration is a planned future capability on the product roadmap.*
- ❌ **Open-Ended Unconstrained Chatbotting**: The system architecturally refuses to act as a general agronomic chatbot (e.g. inventing chemical pesticide recipes or answering general questions), routing ungrounded queries to local Krishi Bhavan officers.
- ❌ **2D Hydrodynamic Flood Inundation Modeling**: The weather surge multiplier models rain-induced harvesting pauses empirically from IMD precipitation; it does not solve Saint-Venant hydraulic flood wave equations.
- ❌ **Live IoT Farm Hardware Telemetry**: The system intentionally does not depend on private in-situ IoT soil probes or connected weather stations, relying entirely on public statistical compendiums and open APIs.
- ❌ **Unconstrained Speculative Price Betting**: The system explicitly refuses forward price predictions on Tier 2 or Tier 3 districts where local supply elasticity has not been econometrically estimated.

---

## 🔬 Mathematical Formulation

### 1. Econometric Price Elasticity Model (`src/price_elasticity_model.py`)
Fits an explainable linear and constant-elasticity log-log regression using temporal splitting:
$$\text{Price} = \alpha + \beta \cdot \text{ArrivalTonnes}$$
$$\ln(\text{Price}) = \alpha' + \epsilon \cdot \ln(\text{ArrivalTonnes})$$
- Exposes sample size $N$, train/test $R^2$, slope $\beta$, constant elasticity $\epsilon$, MAE, and multi-fold walk-forward validation.
- If $N < 24$, status becomes `insufficient_data` and fitting is aborted.

### 2. Forward Price Range Predictor (`src/price_forecast.py`)
Predicts forward modal price by projecting volume-shift impacts through the fitted elasticity slope:
$$\Delta Q = Q_{\text{scenario}} - Q_{\text{baseline}}$$
$$P_{\text{pred}} = P_{\text{baseline}} + \beta \cdot \Delta Q$$
$$\text{CI} = \left[ P_{\text{pred}} - t_{\alpha/2} \cdot \text{RMSE} \cdot \sqrt{1 + \frac{1}{N}}, \quad P_{\text{pred}} + t_{\alpha/2} \cdot \text{RMSE} \cdot \sqrt{1 + \frac{1}{N}} \right]$$

### 3. 4-Scenario Reliability Engine (`src/scenario_engine.py`)
1. **Scenario 1 (Baseline)**: Production-weighted weekly harvest allocation across network topology.
2. **Scenario 2 (Weather-Shifted)**: Compresses harvest window using empirical IMD rainfall variance:
   $$\text{Surge Multiplier} = 1.0 + \min\left(0.65, \frac{\sigma_{\text{rain}}}{20} \cdot 0.35 + N_{>25\text{mm}} \cdot 0.08\right)$$
3. **Scenario 3 (Adjacent Spillover Shock)**: Inflow spillover derived from empirical Agmarknet cross-district correlation $r$. Returns `not_computable` if single district.
4. **Scenario 4 (Capacity Shock)**: Applies `CAPACITY_SHOCK_REDUCTION_RATIO = 0.30` (30% capacity reduction due to canal waterlogging/high moisture).

### 4. Maximin & Minimax Regret Decision Rules (`src/counterfactual_optimizer.py`)
Evaluates candidate interventions against worst-case scenario outcomes and bounded regret:
$$\text{Intervention}^*_{\text{Maximin}} = \arg\max_{i \in \text{Interventions}} \left[ \min_{s \in \text{Scenarios}} \text{Payoff}(i, s) \right]$$
$$\text{Regret}(i, s) = \max_{j} \text{Payoff}(j, s) - \text{Payoff}(i, s)$$
$$\text{Intervention}^*_{\text{Minimax Regret}} = \arg\min_{i} \left[ \max_{s \in \text{Scenarios}} \text{Regret}(i, s) \right]$$

---

## 🌐 Full REST API Reference

| Endpoint | Method | Description | Primary Response Fields |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | Basic system health probe | `status`, `service`, `version` |
| `/health/detailed` | `GET` | Comprehensive data integrity audit across all CSVs, DB & API | `system_status`, `data_sources`, `persisted_models_loaded` |
| `/see/price-trend/{district}/{market}/{crop}` | `GET` | Trailing mandi arrival & modal price series | `time_series`, `summary`, `data_provenance` |
| `/see/weather-advisory/{district}/{crop}` | `GET` | Plain-language weather disruption advisory & surge factor | `advisory_sentence`, `rainfall_std_mm`, `provenance` |
| `/see/crop-maturity/{district}/{crop}` | `GET` | Sowing-calendar maturity stage calibrated with satellite thermal GDD | `crop_stage`, `estimated_maturity_pct`, `satellite_gdd_calibrated`, `source` |
| `/see/satellite-climate/{district}` | `GET` | NASA POWER satellite agroclimatology telemetry (solar irradiance & GDD) | `solar_radiation_mj_m2_day`, `temperature_2m_c`, `growing_degree_days_base10` |
| `/price-forecast/{state}/{district}/{crop}` | `GET` | Explicit forward price range forecast with uncertainty width & traceability | `predicted_modal_price_rs_per_qtl`, `price_range_low_rs`, `price_range_high_rs`, `based_on` |
| `/sowing-advisory/{state}/{district}/{crop}` | `GET` | Pre-sowing window optimization for harvest bottleneck avoidance | `recommended_sowing_window`, `nominal_sowing_window`, `bottleneck_risk_reduction_pct` |
| `/farmer-query` | `POST` | Grounded farmer & FPO query layer bounded strictly to evidence chains | `question`, `answer`, `out_of_scope`, `matched_intent`, `provenance` |
| `/location-summary` | `GET` | Reverse coordinate lookup & single-call composite map summary | `resolved_location`, `capability_tier`, `sowing_advisory`, `full_twin`, `live_snapshot` |
| `/data-quality/{district}/{crop}` | `GET` | Per-file and per-column quality metrics & density verdicts | `district_filter`, `files` (row counts, null %, verdicts) |
| `/bottleneck/{district}/{crop}` | `GET` | Ranked node capacity overshoots across all 4 scenarios | `scenarios`, `bottlenecks`, `active_alerts_count` |
| `/priority-view` | `GET` | Multi-district bottleneck priority ranking for dashboard | `districts_ranked`, `priority_rank`, `bottleneck_risk_score` |
| `/recommendation/{district}/{crop}` | `GET` | Maximin robust recommendation + confidence gate + regret | `selected_action`, `worst_case_payoff_rs`, `max_regret_rs` |
| `/explain/{recommendation_id}` | `GET` | Itemized JSON evidence chain (`[{fact, source}]`) | `evidence_chain`, `summary_verdict`, `max_regret_rs` |
| `/scheme-advisor/{recommendation_id}` | `GET` | Attached government scheme recommendations & clauses | `matched_schemes`, `mandatory_krishi_bhavan_notice` |
| `/analyze/{state}/{district}/{crop}` | `GET` | Universal entry point for any Indian district (Tier 1 / 2 / 3) | `capability_tier`, `tier_explanation`, `full_twin_recommendation`, `live_snapshot` |
| `/coverage` | `GET` | Capability coverage map listing all Tier 1 and Tier 2 districts | `total_districts_tracked`, `tier_1_districts`, `tier_2_districts` |
| `/backtest/{district}/{crop}/{year}` | `GET` | Historical pre-harvest validation vs observed actuals | `bottleneck_detection_precision`, `recall`, `comparison_table` |
| `/backtest/{district}/{crop}/{year}/replay` | `GET` | Chronological week-by-week replay timeline | `total_weeks`, `overall_accuracy_pct`, `replay_timeline` |
| `/model-performance/{district}/{crop}` | `GET` | Structured Model Card performance metrics & limitations | `price_elasticity_model`, `flow_forecast_model`, `limitations` |

---

## ⚠️ Known Technical Limitations

1. **Macroeconomic Monetary Inflation vs. Price Elasticity**:
   - The price elasticity model estimates the marginal price responsiveness to volume surges ($\Delta P / \Delta Q \approx -0.85\text{ Rs/tonne}$). However, multi-year base prices climbed significantly across 2021–2024 due to government MSP revisions and general monetary inflation. While short-term volume impact MAE is low ($\approx \text{Rs } 120/\text{qtl}$, $4.4\%$), multi-year holdout $R^2$ is negative across years because the regression does not model macroeconomic monetary inflation.
2. **Private Offload Share Variance in Kottayam**:
   - In Alappuzha (Kuttanad core), Supplyco procurement and regulated mandis absorb a predictable 10–12% mandi share, yielding low forecast error ($6.4\%$ MAPE). In Kottayam, private mill direct procurement fluctuates heavily between seasons, leading to higher baseline forecast variance ($37.5\%$ MAPE). The confidence gate correctly adjusts for this uncertainty.
3. **Approximated Crop Maturity Sowing Proxy**:
   - Crop phenology stages are baseline mathematical proxies derived from Kerala Department of Agriculture sowing calendars, enriched with NASA POWER surface thermal accumulation ($GDD$). They do not incorporate live multispectral satellite imagery or soil sensor data.
4. **Meteorological Surge Multiplier vs. Hydrodynamics**:
   - The weather delay compression factor ($1.00\text{x}$ to $1.65\text{x}$) is derived empirically from IMD precipitation variance. It models rain-induced harvesting pauses, but does not simulate catastrophic dyke breaches or complete physical road washouts.
5. **Reporting Tail Truncation in Late April 2024**:
   - The Agmarknet historical dataset concludes on April 29, 2024. In the 2023-24 season for Kottayam, post-harvest evaluation had only 78 records, leading to truncation in late harvest reporting.

---

## 🚀 Quickstart & Verification

```powershell
# 1. Install Dependencies
pip install -r requirements.txt

# 2. Run Comprehensive 11-Point System Readiness Check
python scripts/system_readiness_check.py

# 3. Run All Unit & Integration Tests (84 tests)
python -m pytest -v tests/

# 4. Execute 9-Beat Live Demo Rehearsal
python scripts/run_demo_sequence.py

# 5. Launch FastAPI Server
uvicorn src.api:app --reload --port 8000
```
API Documentation: `http://127.0.0.1:8000/docs`


