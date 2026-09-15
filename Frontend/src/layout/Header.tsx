import React from 'react';
import { useAppStore } from '@/store/appStore';
import { ChevronRight, RefreshCw, Calendar, MapPin, Wheat } from 'lucide-react';

export const Header = () => {
  const { activeDistrict, activeCrop, dateRange } = useAppStore();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Breadcrumb & Title */}
        <div>
          <div className="flex items-center text-xs text-gray-500 mb-1">
            <span>Fasal Twin</span>
            <ChevronRight className="w-3 h-3 mx-1" />
            <span className="text-gray-900 font-medium">Regional Overview</span>
          </div>
          <h2 className="text-2xl font-bold font-fraunces text-gray-900">Regional Overview</h2>
        </div>

        {/* Selectors */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm">
            <MapPin className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">District:</span>
            <select className="bg-transparent border-none focus:outline-none font-semibold text-gray-900 cursor-pointer">
              <option>{activeDistrict}</option>
              <option>Idukki</option>
              <option>Palakkad</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm">
            <Wheat className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">Crop:</span>
            <select className="bg-transparent border-none focus:outline-none font-semibold text-gray-900 cursor-pointer">
              <option>{activeCrop}</option>
              <option>Paddy</option>
              <option>Cardamom</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-gray-50 border border-gray-200 rounded-md px-3 py-1.5 text-sm">
            <Calendar className="w-4 h-4 text-gray-500" />
            <span className="font-medium text-gray-700">Period:</span>
            <select className="bg-transparent border-none focus:outline-none font-semibold text-gray-900 cursor-pointer">
              <option>{dateRange}</option>
              <option>Nov 01-10</option>
            </select>
          </div>

          <button className="flex items-center justify-center p-2 rounded-md border border-gray-200 hover:bg-gray-50 text-gray-600 transition-colors tooltip-trigger" title="Refresh Data">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
