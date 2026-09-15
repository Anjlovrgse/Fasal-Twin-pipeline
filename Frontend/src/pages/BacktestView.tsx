import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { useAppStore } from '@/store/appStore';
import { getBacktestReplay, type BacktestReplayPoint, type BacktestReplayResponse } from '@/api/client';
import { Loader2, AlertTriangle, ChevronDown } from 'lucide-react';

const AVAILABLE_YEARS = ['2021-22', '2022-23', '2023-24'];

export const BacktestView = () => {
  const { activeDistrict, activeCrop } = useAppStore();
  const [selectedYear, setSelectedYear] = useState('2022-23');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BacktestReplayResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    getBacktestReplay(activeDistrict, activeCrop, selectedYear).then(result => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setError('Backend not connected');
      } else {
        setData(result as BacktestReplayResponse);
      }
    });

    return () => { cancelled = true; };
  }, [activeDistrict, activeCrop, selectedYear]);

  // Map replay_timeline → chart-ready format
  const chartData = (data?.replay_timeline ?? []).map((pt: BacktestReplayPoint) => ({
    date: pt.week_start_date ?? `W${pt.week}`,
    predictedArrivals: pt.flow_predicted_tonnes,
    actualArrivals:    pt.flow_actual_tonnes,
    bottleneckPredicted: pt.bottleneck_predicted ? pt.flow_predicted_tonnes : undefined,
    bottleneckActual:    pt.bottleneck_actual    ? pt.flow_actual_tonnes    : undefined,
  }));

  const accuracyPct  = data?.overall_accuracy_pct ?? null;
  const totalWeeks   = data?.total_weeks ?? 0;
  const statusOk     = data?.status === 'success';

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold font-fraunces text-gray-900">Historical Backtest</h2>
          <p className="text-gray-500 text-sm mt-1">
            {activeCrop} predictions vs actuals — {activeDistrict}
            {data && statusOk && accuracyPct != null && (
              <span className="ml-2 text-[#1e847f] font-semibold">
                · {accuracyPct.toFixed(1)}% weekly accuracy ({totalWeeks} weeks)
              </span>
            )}
          </p>
        </div>

        {/* Year selector */}
        <div className="relative flex items-center">
          <label htmlFor="backtest-year" className="text-sm text-gray-500 mr-2 shrink-0">Season:</label>
          <select
            id="backtest-year"
            value={selectedYear}
            onChange={e => setSelectedYear(e.target.value)}
            className="appearance-none pl-3 pr-8 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white shadow-sm focus:outline-none focus:ring-1 focus:ring-[#1e847f] cursor-pointer"
          >
            {AVAILABLE_YEARS.map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 absolute right-2 pointer-events-none" />
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Status / reason banner (when backend returned non-success status) */}
      {!loading && !error && data && !statusOk && (
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-300 text-amber-800 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {data.reason ?? 'Backtest could not be computed for this district/year combination.'}
        </div>
      )}

      {/* Loading overlay */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-gray-500">
            <Loader2 className="w-7 h-7 animate-spin text-[#1e847f]" />
            <span className="text-sm">Running backtest replay for {selectedYear}…</span>
          </div>
        </div>
      )}

      {/* Charts */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">

          {/* Left Panel: Predicted */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col p-4">
            <div className="mb-4">
              <h3 className="font-semibold text-gray-800 border-b border-gray-100 pb-2">What we predicted</h3>
            </div>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#888' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#888' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    labelStyle={{ fontWeight: 'bold', color: '#1a1e23' }}
                    formatter={(val: number) => [`${val?.toFixed(0)} t`, '']}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Line
                    type="monotone"
                    dataKey="predictedArrivals"
                    name="Predicted Arrivals (t)"
                    stroke="#1e847f"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                  {/* Highlight bottleneck-predicted weeks */}
                  {chartData.filter(d => d.bottleneckPredicted != null).map((d, i) => (
                    <ReferenceLine key={i} x={d.date} stroke="#c0392b" strokeDasharray="4 2" strokeOpacity={0.4} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600 border border-gray-100">
              {statusOk && data?.replay_timeline?.length ? (
                <>
                  <span className="font-medium text-gray-800">Predicted outcome: </span>
                  {data.replay_timeline.filter(p => p.bottleneck_predicted).length} bottleneck week(s) flagged
                  {' '}across {totalWeeks} weeks — {activeCrop} in {activeDistrict} ({selectedYear}).
                </>
              ) : (
                <span className="text-gray-400">No replay data available for this combination.</span>
              )}
            </div>
          </div>

          {/* Right Panel: Actuals */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex flex-col p-4">
            <div className="mb-4">
              <h3 className="font-semibold text-gray-800 border-b border-gray-100 pb-2">What actually happened</h3>
            </div>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#888' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#888' }} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    labelStyle={{ fontWeight: 'bold', color: '#1a1e23' }}
                    formatter={(val: number) => [`${val?.toFixed(0)} t`, '']}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Line
                    type="monotone"
                    dataKey="actualArrivals"
                    name="Actual Arrivals (t)"
                    stroke="#2d4a22"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6 }}
                  />
                  {/* Highlight bottleneck-actual weeks */}
                  {chartData.filter(d => d.bottleneckActual != null).map((d, i) => (
                    <ReferenceLine key={i} x={d.date} stroke="#c0392b" strokeDasharray="4 2" strokeOpacity={0.4} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded text-sm text-gray-600 border border-gray-100">
              {statusOk && data?.replay_timeline?.length ? (
                <>
                  <span className="font-medium text-gray-800">Actual outcome: </span>
                  {data.replay_timeline.filter(p => p.bottleneck_actual).length} actual bottleneck week(s)
                  {' '}— {accuracyPct != null ? `${accuracyPct.toFixed(1)}% prediction accuracy` : ''}.
                </>
              ) : (
                <span className="text-gray-400">No actuals data available for this combination.</span>
              )}
            </div>
          </div>

        </div>
      )}

      {/* Provenance footer */}
      {!loading && data?.data_provenance && (
        <p className="text-xs text-gray-400 mt-4 shrink-0 italic">{data.data_provenance}</p>
      )}
    </div>
  );
};
