import React from 'react';
import { useLocation } from 'react-router-dom';
import { useAppStore } from '@/store/appStore';
import { ChevronRight, RefreshCw, MapPin, Wheat } from 'lucide-react';

// Route -> page title, so the header reflects the actual page instead of a
// hardcoded "Regional Overview" no matter where the user navigates.
const PAGE_TITLES: Record<string, string> = {
  '/': 'Regional Overview',
  '/priority': 'Multi-District Priority',
  '/backtest': 'Historical Backtest',
  '/alerts': 'Bottleneck Alerts',
  '/schemes': 'Scheme Advisor',
  '/settings': 'System Status',
  '/sowing': 'Sowing Advisory',
};

export const Header = () => {
  const { activeState, activeDistrict, activeCrop, dateRange } = useAppStore();
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] ?? 'Fasal Twin';

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">

        {/* Breadcrumb & Title */}
        <div>
          <div className="flex items-center text-xs text-gray-500 mb-1">
            <span>Fasal Twin</span>
            <ChevronRight className="w-3 h-3 mx-1" />
            <span className="text-gray-900 font-medium">{title}</span>
          </div>
          <h2 className="text-2xl font-bold font-fraunces text-gray-900">{title}</h2>
        </div>

        {/* Current analysis context — read-only, mirrors the Zustand store. The
            editable switcher lives on Regional Overview to avoid two controls
            silently fighting over the same state. */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm">
            <MapPin className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">District:</span>
            <span className="font-semibold text-gray-900">{activeDistrict}</span>
          </div>

          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm">
            <Wheat className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">Crop:</span>
            <span className="font-semibold text-gray-900">{activeCrop}</span>
          </div>

          <div className="hidden lg:flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm text-gray-500">
            {activeState} &middot; {dateRange}
          </div>

          <button
            onClick={() => window.location.reload()}
            className="flex items-center justify-center p-2 rounded-md border border-gray-200 hover:bg-gray-50 text-gray-600 transition-colors"
            title="Refresh all data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
