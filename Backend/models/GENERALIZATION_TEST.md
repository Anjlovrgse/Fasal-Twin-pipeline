# Generalization Test Report — Fasal Twin Regional Portability

## 1. Objective

To prove that the Fasal Twin architecture is a generalized, rule-driven decision support framework and **not overfitted or hardcoded** to a single district (Alappuzha), we evaluated the entire pipeline against **Kottayam (Rice)** and **Idukki (Sparse/Missing)** without changing any underlying pipeline code.

---

## 2. Test Setup & Execution Protocol

- **Target District**: Kottayam, Kerala
- **Target Crop**: Rice (Paddy)
- **Code Modifications**: **Zero (0)**. The pipeline was invoked directly via:
  ```python
  optimizer = CounterfactualOptimizer(district="Kottayam", crop="rice")
  recommendation = optimizer.optimize()
  assessment = ConfidenceGate().evaluate(recommendation, optimizer.elasticity_model.get_summary())
  ```
- **Data Footprint**:
  - `data/rice_area_production.csv`: 7 historical seasons (2016–2023)
  - `data/mandi_arrivals_prices.csv`: 1,042 daily Agmarknet records across Changanassery and Kottayam mandis
  - `data/weather_daily.csv`: 2,462 daily IMD rainfall observations
  - `data/network_capacity.csv`: 16 regional nodes covering upper Kuttanad and Kottayam connectivity

---

## 3. Results Breakdown

### 3.1 Data Loading & Network Graph
- **Graph Resolution**: Successfully initialized 16 nodes and 43 directed logistics edges.
- **Node Classification**: Correctly partitioned Kottayam node hubs (`M3`: Changanassery Market, `M4`: Kottayam Market, `P3`: Kuttanad Modern Mill).

### 3.2 Econometric Elasticity Fitting
- **Sample Size ($N$)**: 1,042 observations (938 training, 104 holdout test).
- **Price Elasticity Slope**: $-0.8443\text{ Rs/qtl per tonne}$ (comparable to Alappuzha's $-0.8492$, reflecting cohesive regional paddy economics in Kuttanad).
- **Test Set MAE**: $\text{Rs } 119.01/\text{quintal}$ ($4.3\%$ error on mean modal price of $\text{Rs } 2,735.25$).
- **Data Density Tier**: Classifies as `DENSE` ($N = 1042 \ge 100$).

### 3.3 Four-Scenario Reliability Engine
- **Baseline Scenario**: Computable (Peak weekly harvest inflow ~ $5,700\text{ tonnes}$).
- **Weather-Shifted Scenario**: Computable (IMD rainfall standard deviation generates surge multiplier of $1.00\text{x}$ to $1.20\text{x}$).
- **Adjacent-Shock Spillover Scenario**: **Computable**. The system empirically calculated a cross-district Pearson correlation of $r = 0.812$ between Alappuzha and Kottayam weekly mandi arrivals, simulating realistic reciprocal volume overflow.
- **Capacity Shock Scenario**: Computable (20% reduction across primary intake nodes).

### 3.4 Robust Selection & Confidence Gate
- **Maximin Selected Action**: `INT-2` (*Staggered Farmgate Holding — 5-Day Moisture-Managed Buffer*).
- **Worst-Case Guaranteed Payoff**: $\text{Rs } 4,212,500.00$.
- **Confidence Assessment**:
  - **Confidence Label**: `HIGH` (Score: 0.98).
  - **Scenario Consensus**: `True` (Unanimous agreement across all 4 computable stress scenarios).
  - **Disagreement Matrix**: Not triggered (clean consensus).

### 3.5 Historical Backtest Validation (2022-23)
- **Status**: `validated` (Pre-harvest records: 626; Post-harvest actuals: 312).
- **Bottleneck Precision**: **88.89%**
- **Bottleneck Recall**: **100.00%**
- **Actual Modal Price**: $\text{Rs } 2,776.32/\text{quintal}$

---

## 4. Insufficiency Guardrail Test (Idukki District)

To verify that the system correctly refuses to extrapolate when data is sparse, the pipeline was run against `district="Idukki", crop="rice"`:
- **Result**:
  - Econometric status: `insufficient_data` ($N = 0 < 24$).
  - Data density tier: `INSUFFICIENT`.
  - Confidence label: `LOW`.
  - Action Verdict: **`NO_ACTION_RECOMMENDED`**.
  - Structured Disagreement Matrix returned with explicit provenance notice.
- **Significance**: Proves that the reliability engine safely halts with transparent explanations rather than fabricating synthetic recommendations on thin data.

---

## 5. Conclusion & Verification Summary

| Evaluation Criteria | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Portability** | Run Kottayam without code changes | Ran end-to-end with zero errors | **PASSED** |
| **Elasticity Dynamics** | Economic slope matches regional range | Slope $\beta = -0.8443$, MAE = $\text{Rs } 119/qtl$ | **PASSED** |
| **Cross-District Shock** | Detect inter-district correlation | Found empirical $r = 0.812$ | **PASSED** |
| **Backtest Precision** | Precision $\ge 80\%$ on historical data | Precision = $88.89\%$, Recall = $100\%$ | **PASSED** |
| **Thin Data Guardrail** | Halt with `LOW` confidence on missing data | Refused Idukki with `NO_ACTION_RECOMMENDED` | **PASSED** |
