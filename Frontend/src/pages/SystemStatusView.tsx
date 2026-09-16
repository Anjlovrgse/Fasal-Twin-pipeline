import React, { useState, useEffect } from 'react';
import { getDetailedHealth, getCoverage, type DetailedHealthResponse, type CoverageResponse } from '@/api/client';
import { Loader2, AlertTriangle, CheckCircle2, XCircle, Database, Globe } from 'lucide-react';
import clsx from 'clsx';

// A genuine system-status page rather than a fake settings screen with toggles
// that do nothing: it reports real, live backend health and capability coverage.
export const SystemStatusView = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null);

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
