import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { getSowingAdvisory, type SowingAdvisoryResponse } from '@/api/client';
import { Loader2, AlertTriangle, CalendarClock, TrendingDown } from 'lucide-react';
import clsx from 'clsx';

const riskColor = (risk: string) => {
  const r = risk.toUpperCase();
  if (r.includes('CRITICAL') || r.includes('HIGH')) return 'text-[#c0392b]';
  if (r.includes('MODERATE')) return 'text-[#f5b041]';
  return 'text-[#1e847f]';
};

export const SowingAdvisoryView = () => {
  const { activeState, activeDistrict, activeCrop } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SowingAdvisoryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    getSowingAdvisory(activeState, activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setError('Backend not connected');
      } else {
        setData(result as SowingAdvisoryResponse);
      }
    });

    return () => { cancelled = true; };
  }, [activeState, activeDistrict, activeCrop]);

  return (
    <div className="p-6 h-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold font-fraunces text-gray-900">Sowing Advisory</h2>
        <p className="text-gray-500 text-sm mt-1">
          Pre-sowing window optimization to avoid harvest-time bottlenecks — {activeCrop} in {activeDistrict}
        </p>
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
            <span className="text-sm">Evaluating candidate sowing windows against predicted network loads…</span>
          </div>
        </div>
      )}

      {!loading && data && (
        <>
          <p className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mb-6">{data.notice}</p>

          {/* The one human-facing decision moment on this page: soft-rounded, distinct
              from the sharp data panels below it, matching the Evidence Drawer's shape language. */}
          <div className="bg-[#1e847f]/5 border border-[#1e847f]/30 rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <CalendarClock className="w-5 h-5 text-[#1e847f]" />
              <h3 className="font-bold text-[#1e847f] font-fraunces text-lg">Recommended Sowing Window</h3>
            </div>
            <div className="flex items-baseline gap-3 mb-2">
              <span className="text-2xl font-bold font-fraunces text-gray-900">
                {data.recommended_sowing_window.start_date} – {data.recommended_sowing_window.end_date}
              </span>
              <span className={clsx('text-xs font-bold uppercase px-2 py-0.5 rounded-full border', riskColor(data.recommended_sowing_window.peak_harvest_overlap_risk), 'border-current')}>
                {data.recommended_sowing_window.peak_harvest_overlap_risk} overlap risk
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-3">Expected harvest: {data.recommended_sowing_window.expected_harvest_window}</p>
            {data.recommended_sowing_window.rationale && (
              <p className="text-sm text-gray-700 mb-3">{data.recommended_sowing_window.rationale}</p>
            )}
            <div className="flex items-center gap-2 text-sm font-semibold text-[#1e847f]">
              <TrendingDown className="w-4 h-4" />
              {data.bottleneck_risk_reduction_pct.toFixed(0)}% lower peak overshoot vs. the nominal calendar window
            </div>
          </div>

          {/* Candidate windows — sharp, hairline-bordered data table */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-6">
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800 text-sm">Candidate Windows Evaluated</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3 font-medium">Window</th>
                    <th className="px-5 py-3 font-medium">Sowing</th>
                    <th className="px-5 py-3 font-medium">Harvest</th>
                    <th className="px-5 py-3 font-medium text-right">Peak Overshoot</th>
                    <th className="px-5 py-3 font-medium">Overlap Risk</th>
                    <th className="px-5 py-3 font-medium text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.candidate_windows_evaluated.map((w, idx) => (
                    <tr key={idx} className={w.optimization_score === data.recommended_sowing_window.score ? 'bg-[#1e847f]/5' : ''}>
                      <td className="px-5 py-3 font-medium text-gray-900">{w.window_name}</td>
                      <td className="px-5 py-3 text-gray-600">{w.sowing_start} – {w.sowing_end}</td>
                      <td className="px-5 py-3 text-gray-600">{w.expected_harvest_window}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs text-gray-700">{w.simulated_peak_overshoot_tonnes.toLocaleString()} t</td>
                      <td className={clsx('px-5 py-3 text-xs font-bold uppercase', riskColor(w.harvest_cluster_overlap_risk))}>{w.harvest_cluster_overlap_risk}</td>
                      <td className="px-5 py-3 text-right font-mono text-xs text-gray-700">{w.optimization_score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Evidence chain */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-800 text-sm mb-3">Evidence</h3>
            <div className="space-y-3">
              {data.evidence_chain.map((item, idx) => (
                <div key={idx} className="text-sm">
                  <p className="text-gray-700">{item.fact}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{item.source}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
