import React, { useState, useEffect } from 'react';
import { Search, Filter, AlertTriangle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';
import clsx from 'clsx';
import { getPriorityView, type PriorityDistrictItem } from '@/api/client';
import { riskFromCompositeScore as getRiskCategory } from '@/lib/risk';

// Confidence label → badge element
const getConfidenceBadge = (label: string) => {
  const norm = label?.toUpperCase();
  if (norm === 'HIGH') {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#f5b041] text-white">High</span>;
  }
  if (norm === 'MODERATE' || norm === 'MEDIUM') {
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border border-[#1e847f] text-[#1e847f]">Moderate</span>;
  }
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border border-[#c0392b] text-[#c0392b]">Low</span>;
};

const getRiskColor = (risk: 'High' | 'Medium' | 'Low') => {
  if (risk === 'High') return 'bg-[#c0392b]';
  if (risk === 'Medium') return 'bg-[#f5b041]';
  return 'bg-[#1e847f]';
};

export const PriorityView = () => {
  const navigate = useNavigate();
  const { activeCrop, setActiveDistrict, setActiveCrop } = useAppStore();

  const [searchTerm, setSearchTerm] = useState('');
  const [filterConfidence, setFilterConfidence] = useState<string>('All');

  // API state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PriorityDistrictItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getPriorityView(activeCrop).then(result => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setError('Backend not connected');
      } else {
        const res = result as import('@/api/client').PriorityViewResponse;
        setData(res.districts_ranked ?? []);
      }
    });

    return () => { cancelled = true; };
  }, [activeCrop]);

  const filteredData = data.filter(item => {
    const matchesSearch =
      item.district.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.crop.toLowerCase().includes(searchTerm.toLowerCase());
    const normConf = item.confidence_tier?.toUpperCase();
    const matchesConf =
      filterConfidence === 'All' ||
      (filterConfidence === 'High' && normConf === 'HIGH') ||
      (filterConfidence === 'Moderate' && (normConf === 'MODERATE' || normConf === 'MEDIUM')) ||
      (filterConfidence === 'Low' && (normConf === 'LOW' || normConf === 'INSUFFICIENT'));
    return matchesSearch && matchesConf;
  });

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold font-fraunces text-gray-900">Multi-District Priority View</h2>
          <p className="text-gray-500 text-sm mt-1">Monitor risk across all connected regions — live from backend</p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              id="priority-search"
              placeholder="Search district or crop..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-[#1e847f]"
            />
          </div>

          <div className="flex items-center gap-2 border border-gray-300 rounded-md px-3 py-2 text-sm bg-white">
            <Filter className="w-4 h-4 text-gray-500" />
            <select
              value={filterConfidence}
              onChange={(e) => setFilterConfidence(e.target.value)}
              className="bg-transparent border-none focus:outline-none text-gray-700 font-medium"
            >
              <option value="All">All Confidence</option>
              <option value="High">High</option>
              <option value="Moderate">Moderate</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error} — showing no data
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col relative">
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
            <div className="flex items-center gap-3 text-gray-500">
              <Loader2 className="w-6 h-6 animate-spin text-[#1e847f]" />
              <span className="text-sm">Loading priority data…</span>
            </div>
          </div>
        )}

        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider sticky top-0 z-10">
              <tr>
                <th className="px-6 py-4 font-medium">Rank</th>
                <th className="px-6 py-4 font-medium">District</th>
                <th className="px-6 py-4 font-medium">Crop</th>
                <th className="px-6 py-4 font-medium w-48">Risk Level</th>
                <th className="px-6 py-4 font-medium">Confidence</th>
                <th className="px-6 py-4 font-medium">Utilization</th>
                <th className="px-6 py-4 font-medium">Top Bottleneck</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {filteredData.map((item, idx) => {
                const riskCat = getRiskCategory(item.bottleneck_risk_score ?? 0);
                return (
                  <tr
                    key={`${item.district}-${item.crop}-${idx}`}
                    onClick={() => {
                      setActiveDistrict(item.district);
                      setActiveCrop(item.crop);
                      navigate('/');
                    }}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 text-gray-400 font-mono text-xs">#{item.priority_rank ?? idx + 1}</td>
                    <td className="px-6 py-4 font-medium text-gray-900">{item.district}</td>
                    <td className="px-6 py-4 text-gray-600">{item.crop}</td>
                    <td className="px-6 py-4">
                      {item.computable === false ? (
                        <span className="text-xs text-gray-400 italic">{item.reason ?? 'Not computable'}</span>
                      ) : (
                        <div className="flex items-center gap-3">
                          <span
                            className={clsx(
                              'text-xs font-bold w-14',
                              riskCat === 'High' ? 'text-[#c0392b]' :
                              riskCat === 'Medium' ? 'text-[#f5b041]' : 'text-[#1e847f]'
                            )}
                          >
                            {riskCat}
                          </span>
                          <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={clsx('h-full', getRiskColor(riskCat))}
                              style={{ width: `${Math.round((item.bottleneck_risk_score ?? 0) * 100)}%` }}
                            />
                          </div>
                          <span className="text-gray-400 text-xs font-mono">
                            {((item.bottleneck_risk_score ?? 0) * 100).toFixed(0)}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">{getConfidenceBadge(item.confidence_tier)}</td>
                    <td className="px-6 py-4 font-mono text-xs text-gray-700">
                      {item.max_utilization_ratio != null
                        ? `${(item.max_utilization_ratio * 100).toFixed(0)}%`
                        : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {riskCat === 'High' && <AlertTriangle className="w-4 h-4 text-[#c0392b]" />}
                        <span className="text-gray-700 font-medium">
                          {item.top_bottleneck_node && item.top_bottleneck_node !== 'None'
                            ? item.top_bottleneck_node
                            : `${item.active_alerts_count ?? 0} alert${item.active_alerts_count !== 1 ? 's' : ''}`}
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {!loading && filteredData.length === 0 && !error && (
            <div className="text-center py-12 text-gray-500">
              No districts match your filters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
