import React from 'react';
import { useAppStore } from '@/store/appStore';
import { mockFactors } from '@/data/mockData';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

export const ContributingFactors = () => {
  const { setSelectedNodeId } = useAppStore();

  // Group factors by location
  const groupedFactors = mockFactors.reduce((acc, factor) => {
    if (!acc[factor.location]) {
      acc[factor.location] = [];
    }
    acc[factor.location].push(factor);
    return acc;
  }, {} as Record<string, typeof mockFactors>);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 bg-gray-50/50">
        <h3 className="font-semibold text-gray-800">Top contributing factors</h3>
      </div>
      
      <div className="p-4 flex-1 overflow-y-auto">
        {Object.entries(groupedFactors).map(([location, factors]) => (
          <div key={location} className="mb-6 last:mb-0">
            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3 px-1">{location}</h4>
            <div className="space-y-3">
              {factors.map((factor) => (
                <div 
                  key={factor.id} 
                  className="group flex gap-3 p-3 rounded-md border border-transparent hover:border-gray-200 hover:bg-gray-50 cursor-pointer transition-all"
                  onClick={() => setSelectedNodeId(factor.nodeId)}
                >
                  <div className="mt-0.5">
                    {factor.isPositive ? (
                      <TrendingUp className="w-4 h-4 text-[#1e847f]" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-[#f5b041]" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-gray-700 font-medium group-hover:text-gray-900">
                      {factor.description}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-xs text-gray-400">
                      <span>{factor.date}</span>
                      {factor.source && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            {factor.source}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
