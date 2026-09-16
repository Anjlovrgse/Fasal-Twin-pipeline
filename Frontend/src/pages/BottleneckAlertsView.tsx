import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { getBottleneckDetection, type BottleneckDetectionResponse } from '@/api/client';
import { Loader2, AlertTriangle, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';

const SCENARIO_LABELS: Record<string, string> = {
  baseline: 'Baseline',
  weather_shifted: 'Weather-shift',
  adjacent_shock: 'Regional shock',
  capacity_shock: 'Capacity shock',
};

const SCENARIO_ORDER = ['baseline', 'weather_shifted', 'adjacent_shock', 'capacity_shock'];

export const BottleneckAlertsView = () => {
  const { activeDistrict, activeCrop, setEvidenceDrawerOpen } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BottleneckDetectionResponse | null>(null);
  const [activeScenario, setActiveScenario] = useState('baseline');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    getBottleneckDetection(activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setError('Backend not connected');
      } else {
        setData(result as BottleneckDetectionResponse);
      }
    });

    return () => { cancelled = true; };
  }, [activeDistrict, activeCrop]);

  const scenario = data?.scenarios?.[activeScenario];

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold font-fraunces text-gray-900">Bottleneck Alerts</h2>
        <p className="text-gray-500 text-sm mt-1">
          Node-level capacity overshoot across all four reliability scenarios — {activeCrop} in {activeDistrict}
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-gray-500">
            <Loader2 className="w-7 h-7 animate-spin text-[#1e847f]" />
            <span className="text-sm">Running 4-scenario bottleneck detection…</span>
          </div>
        </div>
      )}

      {!loading && data && (
        <>
          {/* Scenario tabs — sharp, hairline-bordered, matching the "machine-generated data" panel language */}
          <div className="flex items-center gap-2 mb-4 border-b border-gray-200">
            {SCENARIO_ORDER.filter((s) => data.scenarios[s]).map((s) => (
              <button
                key={s}
                onClick={() => setActiveScenario(s)}
                className={clsx(
                  'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                  activeScenario === s
                    ? 'border-[#1e847f] text-[#1e847f]'
                    : 'border-transparent text-gray-500 hover:text-gray-800'
                )}
              >
                {SCENARIO_LABELS[s] ?? s}
                {!data.scenarios[s].computable && (
                  <span className="ml-1.5 text-[10px] text-gray-400">(n/a)</span>
                )}
              </button>
            ))}
          </div>

          {scenario && !scenario.computable && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg text-sm font-medium mb-4">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {scenario.reason ?? 'Not computable for this scenario.'}
            </div>
          )}

          {scenario && scenario.computable && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">Active Alerts</p>
                  <p className="text-2xl font-bold font-fraunces text-[#c0392b]">{scenario.active_alerts_count}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">Bottleneck Nodes</p>
                  <p className="text-2xl font-bold font-fraunces text-gray-900">{scenario.total_bottleneck_nodes}</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">Total Overshoot</p>
                  <p className="text-2xl font-bold font-fraunces text-gray-900">{scenario.total_overshoot_tonnes.toLocaleString()} t</p>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                  <p className="text-xs text-gray-500 mb-1">Peak Utilization</p>
                  <p className="text-2xl font-bold font-fraunces text-[#f5b041]">{(scenario.max_utilization_ratio * 100).toFixed(0)}%</p>
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                <div className="overflow-x-auto flex-1">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider sticky top-0 z-10">
                      <tr>
                        <th className="px-6 py-3 font-medium">Rank</th>
                        <th className="px-6 py-3 font-medium">Node</th>
                        <th className="px-6 py-3 font-medium">Type</th>
                        <th className="px-6 py-3 font-medium">Capacity</th>
                        <th className="px-6 py-3 font-medium">Forecast Inflow</th>
                        <th className="px-6 py-3 font-medium">Overshoot</th>
                        <th className="px-6 py-3 font-medium">Utilization</th>
                        <th className="px-6 py-3 font-medium">Alert</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {scenario.bottlenecks.map((b) => (
                        <tr key={b.node_id} className="hover:bg-gray-50">
                          <td className="px-6 py-3 text-gray-400 font-mono text-xs">#{b.rank}</td>
                          <td className="px-6 py-3 font-medium text-gray-900">{b.node_name}</td>
                          <td className="px-6 py-3 text-gray-600 capitalize">{b.node_type}</td>
                          <td className="px-6 py-3 font-mono text-xs text-gray-700">{b.capacity_tonnes.toLocaleString()} t</td>
                          <td className="px-6 py-3 font-mono text-xs text-gray-700">{b.forecast_inflow_tonnes.toLocaleString()} t</td>
                          <td className="px-6 py-3 font-mono text-xs text-[#c0392b] font-semibold">+{b.overshoot_tonnes.toLocaleString()} t</td>
                          <td className="px-6 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                <div
                                  className={clsx('h-full', b.utilization_ratio >= 1 ? 'bg-[#c0392b]' : b.utilization_ratio >= 0.65 ? 'bg-[#f5b041]' : 'bg-[#1e847f]')}
                                  style={{ width: `${Math.min(100, b.utilization_ratio * 100)}%` }}
                                />
                              </div>
                              <span className="text-xs font-mono text-gray-500">{(b.utilization_ratio * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className="px-6 py-3">
                            {b.is_active_alert ? (
                              <span className="inline-flex items-center gap-1 text-[#c0392b] text-xs font-semibold">
                                <ShieldAlert className="w-3.5 h-3.5" /> Active
                              </span>
                            ) : (
                              <span className="text-gray-400 text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {scenario.bottlenecks.length === 0 && (
                    <div className="text-center py-12 text-gray-500">No bottleneck nodes detected for this scenario.</div>
                  )}
                </div>
                <div className="px-6 py-3 border-t border-gray-100 text-xs text-gray-400 italic">
                  {scenario.data_provenance}
                </div>
              </div>

              <button
                onClick={() => setEvidenceDrawerOpen(true)}
                className="mt-4 self-start text-sm font-medium text-[#1e847f] hover:underline"
              >
                View full recommendation & evidence →
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
};
