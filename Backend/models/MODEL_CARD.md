# Model Card — Fasal Twin Econometric & Flow Forecasting Models

## 1. Model Details & Architecture Overview

Fasal Twin employs two interpretable, empirically grounded models to simulate regional crop-flow bottlenecks and economic impacts:

1. **Price Elasticity Econometric Model (`PriceElasticityModel`)**:
   - **Type**: Linear Regression ($P = \alpha + \beta Q$) and Log-Log Constant Elasticity Regression ($\ln P = a + \epsilon \ln Q$).
   - **Target**: Modal Mandi Price ($\text{Rs}/\text{quintal}$).
   - **Feature**: Daily / Weekly Arrival Volume ($Q$ in tonnes).
   - **Purpose**: Translates physical volume congestion and diversion interventions into local farmgate price impacts and spoilage avoidance payoffs.

2. **Crop Inflow Forecasting Model (`ForecastModel`)**:
   - **Type**: Agro-statistical seasonal allocation model combined with meteorological compression scaling.
   - **Target**: Peak Weekly Inflow ($Q_{\text{peak}}$ in tonnes) distributed across regional logistics network nodes.
   - **Features**: Historical season production statistics (Kerala Dept of Economics & Statistics / EARAS Compendium Table 5.1.1), harvest calendar window (8 weeks for Kuttanad Punja), and trailing 30-day IMD precipitation variance.

---

## 2. Training Data & Temporal Split

To prevent lookahead bias and data leakage, all models use **strict chronological (temporal) splitting**, never random shuffling.

| Model / District | Data Source | Total Observations ($N$) | Training Date Window | Training Records ($N_{\text{train}}$) | Test Window (Holdout) | Test Records ($N_{\text{test}}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Price Elasticity — Alappuzha Rice** | Agmarknet (via CEDA) | 1,563 daily records | 2021-01-01 to 2023-12-31 | 1,407 | 2024-01-01 to 2024-04-29 | 156 |
| **Price Elasticity — Kottayam Rice** | Agmarknet (via CEDA) | 1,042 daily records | 2021-01-01 to 2023-12-31 | 938 | 2024-01-01 to 2024-04-29 | 104 |
| **Inflow Forecast — Alappuzha Rice** | Kerala DES / EARAS | 21 Punja seasons (2002–2023) | 2002-03 to 2022-23 | 21 seasons | 2023-24 Season | 1 season |
| **Inflow Forecast — Kottayam Rice** | Kerala DES / EARAS | 7 Punja seasons (2016–2023) | 2016-17 to 2022-23 | 7 seasons | 2023-24 Season | 1 season |

---

## 3. Walk-Forward Validation Results

Walk-forward validation tests the model iteratively across historical time horizons: training only on data prior to each season and evaluating on the subsequent unseen season.

### 3.1 Price Elasticity Model Validation

#### Alappuzha Rice (3 Temporal Folds)
- **Train Slope ($\beta$)**: $-0.8492\text{ Rs/qtl per tonne}$
- **Price Elasticity ($\epsilon$)**: $-0.0144$
- **Holdout Test MAE**: $\text{Rs } 121.54/\text{quintal}$ (4.4% of mean modal price $\text{Rs } 2,740.38$)
- **Holdout Test RMSE**: $\text{Rs } 123.92/\text{quintal}$
- **Walk-Forward Aggregate Metrics Across All Folds**:
  - **Aggregate Test MAE**: $\text{Rs } 90.46/\text{quintal}$
  - **Aggregate Test RMSE**: $\text{Rs } 94.02/\text{quintal}$
  - **Fold 1 (Train $\le 2021$, Test 2022)**: Train $R^2 = 0.5902$, Test MAE = $\text{Rs } 59.47/\text{qtl}$, Slope = $-0.7943$
  - **Fold 2 (Train $\le 2022$, Test 2023)**: Train $R^2 = 0.4019$, Test MAE = $\text{Rs } 90.37/\text{qtl}$, Slope = $-0.8222$
  - **Fold 3 (Train $\le 2023$, Test 2024)**: Train $R^2 = 0.2640$, Test MAE = $\text{Rs } 121.54/\text{qtl}$, Slope = $-0.8492$

#### Kottayam Rice (3 Temporal Folds)
- **Train Slope ($\beta$)**: $-0.8443\text{ Rs/qtl per tonne}$
- **Price Elasticity ($\epsilon$)**: $-0.0158$
- **Holdout Test MAE**: $\text{Rs } 119.01/\text{quintal}$ (4.3% of mean modal price $\text{Rs } 2,735.25$)
- **Holdout Test RMSE**: $\text{Rs } 121.91/\text{quintal}$
- **Walk-Forward Aggregate Metrics Across All Folds**:
  - **Aggregate Test MAE**: $\text{Rs } 89.50/\text{quintal}$
  - **Aggregate Test RMSE**: $\text{Rs } 93.17/\text{quintal}$
  - **Fold 1 (Train $\le 2021$, Test 2022)**: Train $R^2 = 0.6195$, Test MAE = $\text{Rs } 60.03/\text{qtl}$, Slope = $-0.7846$
  - **Fold 2 (Train $\le 2022$, Test 2023)**: Train $R^2 = 0.4308$, Test MAE = $\text{Rs } 89.45/\text{qtl}$, Slope = $-0.8054$
  - **Fold 3 (Train $\le 2023$, Test 2024)**: Train $R^2 = 0.2971$, Test MAE = $\text{Rs } 119.01/\text{qtl}$, Slope = $-0.8443$

---

### 3.2 Crop Flow Forecast Model Validation

#### Alappuzha Rice (4 Multi-Year Folds)
- **Aggregate Walk-Forward MAPE**: **6.40%**
- **Aggregate Walk-Forward MAE**: **75.29 tonnes**
- **Aggregate Walk-Forward RMSE**: **90.88 tonnes**
- **Fold 1 (2021 Spring Harvest)**: Predicted Peak: 1,045.92 t vs Actual: 1,204.60 t (Error: 158.67 t, MAPE: 13.17%)
- **Fold 2 (2022 Spring Harvest)**: Predicted Peak: 1,181.25 t vs Actual: 1,203.00 t (Error: 21.75 t, MAPE: 1.81%)
- **Fold 3 (2023 Spring Harvest)**: Predicted Peak: 1,200.62 t vs Actual: 1,147.20 t (Error: 53.42 t, MAPE: 4.66%)
- **Fold 4 (2024 Spring Harvest)**: Predicted Peak: 1,200.62 t vs Actual: 1,133.30 t (Error: 67.33 t, MAPE: 5.94%)

#### Kottayam Rice (4 Multi-Year Folds)
- **Aggregate Walk-Forward MAPE**: **37.55%**
- **Aggregate Walk-Forward MAE**: **330.19 tonnes**
- **Aggregate Walk-Forward RMSE**: **332.09 tonnes**
- **Fold 1 (2021 Spring Harvest)**: Predicted Peak: 508.29 t vs Actual: 841.70 t (Error: 333.41 t, MAPE: 39.61%)
- **Fold 2 (2022 Spring Harvest)**: Predicted Peak: 543.75 t vs Actual: 930.60 t (Error: 386.85 t, MAPE: 41.57%)
- **Fold 3 (2023 Spring Harvest)**: Predicted Peak: 570.00 t vs Actual: 868.20 t (Error: 298.20 t, MAPE: 34.35%)
- **Fold 4 (2024 Spring Harvest)**: Predicted Peak: 570.00 t vs Actual: 872.30 t (Error: 302.30 t, MAPE: 34.66%)

---

## 4. Model Persistence Artifacts

Models are serialized via `joblib` in `models/` with timestamps and data cutoffs:
- `models/price_elasticity_alappuzha_rice_2023-12-31.joblib`
- `models/price_elasticity_kottayam_rice_2023-12-31.joblib`
- `models/forecast_alappuzha_rice_2022-23.joblib`
- `models/forecast_kottayam_rice_2022-23.joblib`

These files are loaded into memory once at application startup, eliminating refitting latency during inference.

---

## 5. Explicit Limitations & Failure Modes

This section explicitly documents what these models **cannot** do and where technical assumptions may degrade under real-world conditions:

1. **Macroeconomic Baseline Shifts vs. Test $R^2$**:
   - The price elasticity model fits an econometric slope ($\Delta P / \Delta Q \approx -0.85\text{ Rs/tonne}$). While within-year variance is explained with moderate $R^2$ ($0.26$ to $0.62$), multi-year test $R^2$ is negative because base mandi prices climbed across 2021–2024 due to state Minimum Support Price (MSP) revisions and general inflation. The model accurately captures the marginal price depression of volume surges ($\pm 4.4\%$ MAE), but does not predict macroeconomic monetary inflation.
2. **Kottayam Mandi Share Divergence**:
   - In Alappuzha (Kuttanad core), Supplyco procurement and regulated mandis absorb a predictable 10–12% mandi share, yielding low forecast error ($6.4\%$ MAPE). In Kottayam, private mill direct procurement fluctuates heavily between seasons, leading to higher baseline forecast variance ($37.5\%$ MAPE). The confidence gate correctly adjusts for this uncertainty.
3. **No IoT Hardware / Satellite Sensor Dependence**:
   - Crop maturity stages and arrival window shapes are mathematical proxies calibrated to Kerala Department of Agriculture sowing norms (Principle 3). They do not incorporate live satellite NDVI/SAR imagery or ground-level IoT moisture sensors.
4. **Extreme Flood Non-Linearities**:
   - The weather delay compression factor ($1.00\text{x}$ to $1.65\text{x}$) is derived empirically from IMD precipitation variance. It models rain-induced harvesting pauses, but does not simulate catastrophic dyke breaches or complete physical road washouts.
