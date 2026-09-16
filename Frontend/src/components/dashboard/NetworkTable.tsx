import React from 'react';
import { useAppStore } from '@/store/appStore';
import type { BottleneckNode } from '@/api/client';
import { riskFromUtilizationRatio } from '@/lib/risk';
import { ChevronRight, Box, Store, Factory, TreePine, Warehouse, Loader2, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';

const getNodeIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'fpo': return <TreePine className="w-4 h-4 text-[#1e847f]" />;
    case 'mandi': return <Store className="w-4 h-4 text-[#c0392b]" />;
    case 'storage': return <Warehouse className="w-4 h-4 text-gray-500" />;
    case 'processor': return <Factory className="w-4 h-4 text-gray-500" />;
    default: return <Box className="w-4 h-4" />;
  }
};

const getOccupancyColor = (occupancyPct: number) => {
  if (occupancyPct >= 100) return 'bg-[#c0392b]';
  if (occupancyPct >= 70) return 'bg-[#f5b041]';
  return 'bg-[#1e847f]';
};

interface NetworkTableProps {
  nodes: BottleneckNode[];
  crop: string;
  loading: boolean;
  error: string | null;
  unavailableReason?: string | null;
}

export const NetworkTable: React.FC<NetworkTableProps> = ({ nodes, crop, loading, error, unavailableReason }) => {
  const { selectedNodeId, setSelectedNodeId } = useAppStore();

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mt-6">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800">Regional Network Parameters</h3>
        <button className="text-sm text-[#1e847f] font-medium hover:underline flex items-center">
          View All <ChevronRight className="w-4 h-4 ml-0.5" />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 text-gray-500 py-10 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading network topology…
        </div>
      )}

      {!loading && error && (
        <div className="flex items-center gap-2 text-red-600 py-10 justify-center text-sm">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {!loading && !error && unavailableReason && (
        <div className="text-center py-10 text-gray-500 text-sm px-6">{unavailableReason}</div>
      )}

      {!loading && !error && !unavailableReason && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 font-medium">Node</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Crop</th>
                <th className="px-4 py-3 font-medium text-right">Forecast Arrivals</th>
                <th className="px-4 py-3 font-medium text-right">Absorption Cap.</th>
                <th className="px-4 py-3 font-medium w-48">Occupancy</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {nodes.map((node) => {
                const occupancyPct = node.utilization_ratio * 100;
                const risk = riskFromUtilizationRatio(node.utilization_ratio);
                const status = node.is_active_alert ? 'Critical' : occupancyPct >= 70 ? 'Warning' : 'Normal';
                return (
                  <tr
                    key={node.node_id}
                    onClick={() => setSelectedNodeId(node.node_id)}
                    className={clsx(
                      'hover:bg-gray-50 cursor-pointer transition-colors',
                      selectedNodeId === node.node_id && 'bg-[#1e847f]/5'
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getNodeIcon(node.node_type)}
                        <span className="font-medium text-gray-900">{node.node_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 capitalize">{node.node_type}</td>
                    <td className="px-4 py-3 text-gray-600">{crop}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">
                      {node.forecast_inflow_tonnes.toLocaleString()} t
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {node.capacity_tonnes.toLocaleString()} t
                    </td>
                    <td className="px-4 py-3">
                      <div className="group relative w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={clsx('h-full transition-all duration-500', getOccupancyColor(occupancyPct))}
                          style={{ width: `${Math.min(occupancyPct, 100)}%` }}
                        />
                        <div className="absolute hidden group-hover:block bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-3 py-2 bg-[#1a1e23] text-white text-xs rounded z-10 shadow-lg">
                          <p>Absorption Capacity = {node.capacity_tonnes.toLocaleString()} t</p>
                          <p>Current Forecast = {node.forecast_inflow_tonnes.toLocaleString()} t</p>
                          <p className="mt-1 font-medium">Status = {status}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider',
                        risk === 'High' ? 'bg-red-100 text-[#c0392b]' :
                        risk === 'Medium' ? 'bg-yellow-100 text-[#f5b041]' :
                        'bg-teal-100 text-[#1e847f]'
                      )}>
                        {risk}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-xs font-medium text-gray-600">
                        <div className={clsx(
                          'w-2 h-2 rounded-full',
                          status === 'Critical' ? 'bg-[#c0392b]' :
                          status === 'Warning' ? 'bg-[#f5b041]' :
                          'bg-[#1e847f]'
                        )} />
                        {status}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {nodes.length === 0 && (
            <div className="text-center py-10 text-gray-500 text-sm">No network nodes reported for this scenario.</div>
          )}
        </div>
      )}
    </div>
  );
};
