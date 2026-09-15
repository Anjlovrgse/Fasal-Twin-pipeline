import React from 'react';
import { mockNodes } from '@/data/mockData';
import { useAppStore } from '@/store/appStore';
import { NetworkNode } from '@/types';
import { ChevronRight, Box, Store, Factory, TreePine, Warehouse } from 'lucide-react';
import clsx from 'clsx';

const getNodeIcon = (type: NetworkNode['type']) => {
  switch (type) {
    case 'Farm Block': return <TreePine className="w-4 h-4 text-[#1e847f]" />;
    case 'FPO': return <Store className="w-4 h-4 text-[#f5b041]" />;
    case 'Mandi': return <Store className="w-4 h-4 text-[#c0392b]" />;
    case 'Storage': return <Warehouse className="w-4 h-4 text-gray-500" />;
    case 'Processor': return <Factory className="w-4 h-4 text-gray-500" />;
    default: return <Box className="w-4 h-4" />;
  }
};

const getOccupancyColor = (occupancy: number) => {
  if (occupancy >= 90) return 'bg-[#c0392b]';
  if (occupancy >= 70) return 'bg-[#f5b041]';
  return 'bg-[#1e847f]';
};

export const NetworkTable = () => {
  const { selectedNodeId, setSelectedNodeId } = useAppStore();

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mt-6">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-800">Regional Network Parameters</h3>
        <button className="text-sm text-[#1e847f] font-medium hover:underline flex items-center">
          View All <ChevronRight className="w-4 h-4 ml-0.5" />
        </button>
      </div>
      
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
            {mockNodes.map((node) => (
              <tr 
                key={node.id}
                onClick={() => setSelectedNodeId(node.id)}
                className={clsx(
                  "hover:bg-gray-50 cursor-pointer transition-colors",
                  selectedNodeId === node.id && "bg-[#1e847f]/5"
                )}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {getNodeIcon(node.type)}
                    <span className="font-medium text-gray-900">{node.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">{node.type}</td>
                <td className="px-4 py-3 text-gray-600">{node.crop}</td>
                <td className="px-4 py-3 text-right font-medium text-gray-900">
                  {node.forecastArrivals.toLocaleString()} t
                </td>
                <td className="px-4 py-3 text-right text-gray-600">
                  {node.capacity.toLocaleString()} t
                </td>
                <td className="px-4 py-3">
                  <div className="group relative w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div 
                      className={clsx("h-full transition-all duration-500", getOccupancyColor(node.occupancy))}
                      style={{ width: `${Math.min(node.occupancy, 100)}%` }}
                    />
                    
                    {/* Tooltip */}
                    <div className="absolute hidden group-hover:block bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-3 py-2 bg-[#1a1e23] text-white text-xs rounded z-10 shadow-lg">
                      <p>Absorption Capacity = {node.capacity.toLocaleString()} t</p>
                      <p>Current Forecast = {node.forecastArrivals.toLocaleString()} t</p>
                      <p className="mt-1 font-medium">Status = {node.status}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={clsx(
                    "px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider",
                    node.risk === 'High' ? "bg-red-100 text-[#c0392b]" :
                    node.risk === 'Medium' ? "bg-yellow-100 text-[#f5b041]" :
                    "bg-teal-100 text-[#1e847f]"
                  )}>
                    {node.risk}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-gray-600">
                    <div className={clsx(
                      "w-2 h-2 rounded-full",
                      node.status === 'Critical' ? "bg-[#c0392b]" :
                      node.status === 'Warning' ? "bg-[#f5b041]" :
                      "bg-[#1e847f]"
                    )} />
                    {node.status}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
