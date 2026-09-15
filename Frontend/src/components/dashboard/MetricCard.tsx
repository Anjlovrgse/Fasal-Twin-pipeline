import React from 'react';
import clsx from 'clsx';
import { Metric } from '@/types';

export const MetricCard: React.FC<Metric> = ({ label, value, subLabel, isRisk }) => {
  return (
    <div className={clsx(
      "bg-white rounded-lg p-5 border shadow-sm transition-all hover:shadow-md",
      isRisk ? "border-[#c0392b]/20 bg-red-50/10" : "border-gray-200"
    )}>
      <h3 className="text-sm font-medium text-gray-500 mb-2">{label}</h3>
      <div className="flex items-baseline gap-2">
        <span className={clsx(
          "text-3xl font-bold font-fraunces",
          isRisk ? "text-[#c0392b]" : "text-gray-900"
        )}>
          {value}
        </span>
      </div>
      {subLabel && (
        <p className="text-xs text-gray-400 mt-2">{subLabel}</p>
      )}
    </div>
  );
};
