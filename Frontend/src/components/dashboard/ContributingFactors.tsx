import React from 'react';
import type { EvidenceChainItem } from '@/api/client';
import { Loader2, AlertTriangle, Sprout, CloudRain, LineChart, Truck, Gavel, Scale } from 'lucide-react';

const CATEGORY_ICON: Record<string, React.ReactNode> = {
  production: <Sprout className="w-4 h-4 text-[#1e847f]" />,
  meteorology: <CloudRain className="w-4 h-4 text-[#2d4a22]" />,
  econometrics: <LineChart className="w-4 h-4 text-[#f5b041]" />,
  logistics: <Truck className="w-4 h-4 text-[#c0392b]" />,
  decision_rule: <Gavel className="w-4 h-4 text-[#1e847f]" />,
  regret_analysis: <Scale className="w-4 h-4 text-[#f5b041]" />,
};

interface ContributingFactorsProps {
  factors: EvidenceChainItem[];
  loading: boolean;
  error: string | null;
  unavailableReason?: string | null;
}

export const ContributingFactors: React.FC<ContributingFactorsProps> = ({ factors, loading, error, unavailableReason }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-gray-50/50">
        <h3 className="font-semibold text-gray-800">Top contributing factors</h3>
      </div>

      <div className="p-4 flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center gap-2 text-gray-500 py-8 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading evidence…
          </div>
        )}

        {!loading && error && (
          <div className="flex items-center gap-2 text-red-600 py-8 justify-center text-sm text-center px-2">
            <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
          </div>
        )}

        {!loading && !error && unavailableReason && (
          <p className="text-sm text-gray-500 text-center py-8">{unavailableReason}</p>
        )}

        {!loading && !error && !unavailableReason && (
          <div className="space-y-3">
            {factors.map((factor, idx) => (
              <div key={idx} className="group flex gap-3 p-3 rounded-md border border-transparent hover:border-gray-200 hover:bg-gray-50 transition-all">
                <div className="mt-0.5 shrink-0">
                  {CATEGORY_ICON[factor.category] ?? <Sprout className="w-4 h-4 text-gray-400" />}
                </div>
                <div>
                  <p className="text-sm text-gray-700 leading-snug">{factor.fact}</p>
                  <p className="text-xs text-gray-400 mt-1.5">{factor.source}</p>
                </div>
              </div>
            ))}
            {factors.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">No evidence chain available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
