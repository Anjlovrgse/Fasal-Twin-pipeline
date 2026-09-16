import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { getBottleneckDetection, type BottleneckNode } from '@/api/client';
import { X, PlaySquare, ShieldCheck, AlertTriangle, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { useNavigate } from 'react-router-dom';

// Real per-node data, looked up from the same /bottleneck dataset the map
// markers and Network Table now both render from — this used to look nodes up
// in a hardcoded mock array under a different ID namespace than the live
// backend, so a real node_id (e.g. "M1") never matched and the card silently
// never appeared for anything but the map's own decorative mock markers.
export const BottleneckAlert = () => {
  const { selectedNodeId, setSelectedNodeId, setEvidenceDrawerOpen, activeDistrict, activeCrop } = useAppStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [node, setNode] = useState<BottleneckNode | null>(null);

  useEffect(() => {
    if (!selectedNodeId) {
      setNode(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getBottleneckDetection(activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setNode(null);
        return;
      }
      const detection = result as import('@/api/client').BottleneckDetectionResponse;
      const baseline = detection.scenarios.baseline;
      const found = baseline?.bottlenecks?.find((b) => b.node_id === selectedNodeId) ?? null;
      setNode(found);
    });
    return () => { cancelled = true; };
  }, [selectedNodeId, activeDistrict, activeCrop]);

  if (!selectedNodeId) return null;

  const risk = node
    ? node.utilization_ratio >= 1 ? 'High' : node.utilization_ratio >= 0.65 ? 'Medium' : 'Low'
    : null;

  return (
    <div className="absolute bottom-4 left-4 right-4 z-20 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-4">
      <div className="flex items-start justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-full flex items-center justify-center',
            risk === 'High' ? 'bg-red-100 text-[#c0392b]' :
            risk === 'Medium' ? 'bg-yellow-100 text-[#f5b041]' :
            'bg-teal-100 text-[#1e847f]'
          )}>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">
              {activeCrop} — {node?.node_name ?? (loading ? 'Loading…' : selectedNodeId)}
            </h3>
            {node && <p className="text-sm text-gray-500 capitalize">{node.node_type} node, {node.district}</p>}
          </div>
        </div>
        <button
          onClick={() => setSelectedNodeId(null)}
          className="p-1 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {loading && (
        <div className="p-6 flex items-center justify-center gap-2 text-gray-500 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading node data…
        </div>
      )}

      {!loading && !node && (
        <div className="p-6 text-center text-sm text-gray-500">
          No bottleneck data for this node in the current scenario.
        </div>
      )}

      {!loading && node && (
        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Forecast inflow</p>
                <p className="text-lg font-bold font-fraunces">{node.forecast_inflow_tonnes.toLocaleString()} t</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Rated capacity</p>
                <p className="text-lg font-bold font-fraunces text-gray-700">{node.capacity_tonnes.toLocaleString()} t</p>
              </div>
            </div>

            {node.is_active_alert && (
              <div className="bg-[#fdfbf7] p-3 rounded-md border border-[#f5b041]/30">
                <p className="text-xs text-[#f5b041] font-bold uppercase tracking-wider mb-1">Overshoot</p>
                <p className="text-sm text-gray-800 font-medium">
                  +{node.overshoot_tonnes.toLocaleString()} t ({node.overshoot_pct.toFixed(0)}% over capacity)
                </p>
              </div>
            )}
          </div>

          <div className="flex flex-col justify-end gap-2">
            {node.is_active_alert ? (
              <>
                <button
                  onClick={() => navigate('/simulation')}
                  className="w-full py-2 px-4 bg-[#2d4a22] text-white rounded-md text-sm font-medium hover:bg-[#1a2d13] transition-colors flex items-center justify-center gap-2"
                >
                  <PlaySquare className="w-4 h-4" />
                  Run Simulation
                </button>
                <button
                  onClick={() => setEvidenceDrawerOpen(true)}
                  className="w-full py-2 px-4 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                >
                  <ShieldCheck className="w-4 h-4" />
                  View Evidence
                </button>
              </>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-500 border border-dashed border-gray-200 rounded-md">
                Node operating normally. No actions required.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
