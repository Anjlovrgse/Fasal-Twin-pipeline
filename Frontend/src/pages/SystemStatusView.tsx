import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import {
  getDetailedHealth,
  getCoverage,
  getModelPerformance,
  getOutcomeHistory,
  getDataQuality,
  type DetailedHealthResponse,
  type CoverageResponse,
  type ModelPerformanceResponse,
  type OutcomeHistoryResponse,
  type DataQualityResponse,
} from '@/api/client';
import { Loader2, AlertTriangle, CheckCircle2, XCircle, Database, Globe, Gauge, History } from 'lucide-react';
import clsx from 'clsx';

// A genuine system-status page rather than a fake settings screen with toggles
// that do nothing: it reports real, live backend health and capability coverage.
export const SystemStatusView = () => {
  const { activeDistrict, activeCrop } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);

  const [modelPerf, setModelPerf] = useState<ModelPerformanceResponse | null>(null);
  const [outcomeHistory, setOutcomeHistory] = useState<OutcomeHistoryResponse | null>(null);
  const [dataQuality, setDataQuality] = useState<DataQualityResponse | null>(null);
  const [districtLoading, setDistrictLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([getDetailedHealth(), getCoverage()]).then(([h, c]) => {
      if (cancelled) return;
      setLoading(false);
      if (('error' in h && h.error) || ('error' in c && c.error)) {
        setError('Backend not connected');
        return;
      }
      setHealth(h as DetailedHealthResponse);
      setCoverage(c as CoverageResponse);
    });

    return () => { cancelled = true; };
  }, []);

  // District-scoped diagnostics: model card metrics, learning-loop calibration,
  // and data density — for whichever district/crop is currently active.
  useEffect(() => {
    let cancelled = false;
    setDistrictLoading(true);
    setModelPerf(null);
    setOutcomeHistory(null);
    setDataQuality(null);

    Promise.all([
      getModelPerformance(activeDistrict, activeCrop),
      getOutcomeHistory(activeDistrict, activeCrop),
      getDataQuality(activeDistrict, activeCrop),
    ]).then(([mp, oh, dq]) => {
      if (cancelled) return;
      setDistrictLoading(false);
      if (!('error' in mp && mp.error)) setModelPerf(mp as ModelPerformanceResponse);
      if (!('error' in oh && oh.error)) setOutcomeHistory(oh as OutcomeHistoryResponse);
      if (!('error' in dq && dq.error)) setDataQuality(dq as DataQualityResponse);
    });

    return () => { cancelled = true; };
  }, [activeDistrict, activeCrop]);

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold font-fraunces text-gray-900">System Status</h2>
        <p className="text-gray-500 text-sm mt-1">Live backend health, data source freshness, and district capability coverage</p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-24">
          <div className="flex items-center gap-3 text-gray-500">
            <Loader2 className="w-7 h-7 animate-spin text-[#1e847f]" />
            <span className="text-sm">Checking every data source…</span>
          </div>
        </div>
      )}

      {!loading && health && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">System Status</p>
              <p className={clsx(
                'text-xl font-bold font-fraunces capitalize',
                health.system_status === 'healthy' ? 'text-[#1e847f]' : 'text-[#c0392b]'
              )}>
                {health.system_status}
              </p>
            </div>
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Data Sources Online</p>
              <p className="text-xl font-bold font-fraunces text-gray-900">{health.total_sources_online} / {health.total_sources_checked}</p>
            </div>
            <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
              <p className="text-xs text-gray-500 mb-1">Persisted Models Loaded</p>
              <p className="text-xl font-bold font-fraunces text-gray-900">{health.persisted_models_loaded.length}</p>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-6 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
              <Database className="w-4 h-4 text-[#1e847f]" />
              <h3 className="font-semibold text-gray-800 text-sm">Data Sources</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {Object.values(health.data_sources).map((src) => (
                <div key={src.source_name} className="flex items-center justify-between px-5 py-3 text-sm">
                  <div className="flex items-center gap-3">
                    {src.is_available ? (
                      <CheckCircle2 className="w-4 h-4 text-[#1e847f] shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-[#c0392b] shrink-0" />
                    )}
                    <div>
                      <p className="font-medium text-gray-800">{src.source_name}</p>
                      <p className="text-xs text-gray-400">{src.provenance}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    {src.record_count != null && (
                      <p className="text-xs font-mono text-gray-500">{src.record_count.toLocaleString()} rows</p>
                    )}
                    <p className="text-xs text-gray-400">{src.status_details}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {coverage && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                <Globe className="w-4 h-4 text-[#1e847f]" />
                <h3 className="font-semibold text-gray-800 text-sm">District Coverage</h3>
              </div>
              <div className="px-5 py-3 flex gap-6 text-sm border-b border-gray-100">
                <span><strong className="text-[#1e847f]">{coverage.tier_1_full_twins_count}</strong> Tier 1 full digital twins</span>
                <span><strong className="text-[#f5b041]">{coverage.tier_2_live_snapshots_count}</strong> Tier 2 live snapshots</span>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-gray-100">
                {coverage.tier_1_districts.map((d) => (
                  <div key={`${d.state}-${d.district}`} className="flex items-center justify-between px-5 py-2 text-sm">
                    <span className="font-medium text-gray-800">{d.district}, {d.state}</span>
                    <span className="text-xs font-semibold text-white bg-[#1e847f] px-2 py-0.5 rounded">Tier 1</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model performance for the currently active district/crop — this is where
              the system's own honest calibration problem (a negative test R²) is
              surfaced directly, not hidden behind a green "healthy" badge above. */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
            <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
              <Gauge className="w-4 h-4 text-[#1e847f]" />
              <h3 className="font-semibold text-gray-800 text-sm">Model Performance — {activeCrop} in {activeDistrict}</h3>
            </div>
            {districtLoading && (
              <div className="flex items-center justify-center gap-2 text-gray-500 py-8 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading model card…
              </div>
            )}
            {!districtLoading && !modelPerf && (
              <p className="px-5 py-4 text-sm text-gray-500">No persisted model for this district/crop.</p>
            )}
            {!districtLoading && modelPerf && (
              <div className="p-5">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Train R²</p>
                    <p className="text-lg font-bold font-fraunces text-gray-900">
                      {modelPerf.price_elasticity_model.train_r2?.toFixed(3) ?? '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Test R² (out-of-sample)</p>
                    <p className={clsx(
                      'text-lg font-bold font-fraunces',
                      (modelPerf.price_elasticity_model.test_r2 ?? 0) < 0 ? 'text-[#c0392b]' : 'text-gray-900'
                    )}>
                      {modelPerf.price_elasticity_model.test_r2?.toFixed(3) ?? '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Test MAE</p>
                    <p className="text-lg font-bold font-fraunces text-gray-900">
                      {modelPerf.price_elasticity_model.test_mae_rs != null ? `Rs ${modelPerf.price_elasticity_model.test_mae_rs.toFixed(0)}` : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Flow forecast MAPE</p>
                    <p className="text-lg font-bold font-fraunces text-gray-900">
                      {modelPerf.flow_forecast_model.test_mape_pct?.toFixed(1)}%
                    </p>
                  </div>
                </div>
                {(modelPerf.price_elasticity_model.test_r2 ?? 0) < 0 && (
                  <div className="flex items-start gap-2 bg-red-50 border border-red-200 text-[#c0392b] text-xs px-3 py-2 rounded-md mb-4">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span>
                      Negative test R² — this model performs worse than predicting the mean price. The confidence
                      gate downgrades any recommendation built on it to LOW; it has not yet been recalibrated.
                    </span>
                  </div>
                )}
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Known limitations</p>
                <ul className="text-xs text-gray-500 space-y-1 list-disc list-inside">
                  {modelPerf.limitations.map((l, idx) => <li key={idx}>{l}</li>)}
                </ul>
              </div>
            )}
          </div>

          {/* Outcome history — the learning-loop calibration tracker */}
          {outcomeHistory && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                <History className="w-4 h-4 text-[#1e847f]" />
                <h3 className="font-semibold text-gray-800 text-sm">Outcome History (Learning Loop)</h3>
              </div>
              <div className="px-5 py-4 text-sm">
                <p className="text-gray-700">
                  <strong>{outcomeHistory.total_reconciled_alerts}</strong> reconciled alerts &middot; status:{' '}
                  <span className="font-semibold">{outcomeHistory.calibration_status}</span>
                </p>
                <p className="text-xs text-gray-400 mt-2">{outcomeHistory.caution_note}</p>
              </div>
            </div>
          )}

          {/* Data quality — per-file density/verdict for the active district/crop */}
          {dataQuality && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
              <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
                <Database className="w-4 h-4 text-[#1e847f]" />
                <h3 className="font-semibold text-gray-800 text-sm">Data Quality — {activeCrop} in {activeDistrict}</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {Object.entries(dataQuality.files).map(([filename, report]) => (
                  <div key={filename} className="flex items-center justify-between px-5 py-2.5 text-sm">
                    <span className="font-mono text-xs text-gray-700">{filename}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-400">{report.row_count.toLocaleString()} rows</span>
                      <span className={clsx(
                        'text-[10px] font-bold uppercase px-2 py-0.5 rounded-full',
                        report.verdict === 'sparse' ? 'bg-yellow-100 text-[#f5b041]' :
                        report.verdict === 'insufficient' ? 'bg-red-100 text-[#c0392b]' :
                        'bg-teal-100 text-[#1e847f]'
                      )}>
                        {report.verdict}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 text-sm mb-3">Connection</h3>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">API base URL</span>
              <span className="font-mono text-gray-800">{apiBaseUrl}</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-2">
              <span className="text-gray-500">Backend version</span>
              <span className="font-mono text-gray-800">{health.version}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
