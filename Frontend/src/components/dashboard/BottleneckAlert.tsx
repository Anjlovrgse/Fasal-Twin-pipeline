import React from 'react';
import { useAppStore } from '@/store/appStore';
import { mockBottleneckAlert, mockNodes } from '@/data/mockData';
import { X, PlaySquare, ShieldCheck, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import { useNavigate } from 'react-router-dom';

export const BottleneckAlert = () => {
  const { selectedNodeId, setSelectedNodeId, setEvidenceDrawerOpen } = useAppStore();
  const navigate = useNavigate();

  if (!selectedNodeId) return null;

  // Realistically we'd fetch the alert based on ID. 
  // For now, if it's mandi-a we show the mock alert, otherwise a generic one based on the node.
  const node = mockNodes.find(n => n.id === selectedNodeId);
  if (!node) return null;

  const isAlert = node.status === 'Critical' || node.status === 'Warning';
  const alertData = node.id === 'mandi-a' ? mockBottleneckAlert : {
    ...mockBottleneckAlert,
    nodeId: node.id,
    nodeName: node.name,
    forecastArrivals: node.forecastArrivals,
    capacity: node.capacity,
    risk: node.risk,
    factors: []
  };

  return (
    <div className="absolute bottom-4 left-4 right-4 z-20 bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden animate-in slide-in-from-bottom-4">
      <div className="flex items-start justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div className={clsx(
            "w-10 h-10 rounded-full flex items-center justify-center",
            node.risk === 'High' ? "bg-red-100 text-[#c0392b]" :
            node.risk === 'Medium' ? "bg-yellow-100 text-[#f5b041]" :
            "bg-teal-100 text-[#1e847f]"
          )}>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">{node.crop} — {node.name}</h3>
            <p className="text-sm text-gray-500">Harvest Window: {alertData.harvestWindow}</p>
          </div>
        </div>
        <button 
          onClick={() => setSelectedNodeId(null)}
          className="p-1 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500 mb-1">Expected arrivals</p>
              <p className="text-lg font-bold font-fraunces">{alertData.forecastArrivals.toLocaleString()} t</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Available capacity</p>
              <p className="text-lg font-bold font-fraunces text-gray-700">{alertData.capacity.toLocaleString()} t</p>
            </div>
          </div>
          
          {isAlert && (
            <div className="bg-[#fdfbf7] p-3 rounded-md border border-[#f5b041]/30">
              <p className="text-xs text-[#f5b041] font-bold uppercase tracking-wider mb-1">Recommended Action</p>
              <p className="text-sm text-gray-800 font-medium">{alertData.recommendedAction}</p>
            </div>
          )}
        </div>

        <div className="flex flex-col justify-end gap-2">
          {isAlert ? (
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
    </div>
  );
};
