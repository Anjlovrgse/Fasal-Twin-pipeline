import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';

export const NotFound = () => {
  const navigate = useNavigate();
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 text-center p-6">
      <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center">
        <Compass className="w-7 h-7 text-gray-400" />
      </div>
      <div>
        <h2 className="text-xl font-bold font-fraunces text-gray-900">Page not found</h2>
        <p className="text-gray-500 text-sm mt-1">That route doesn't exist in Fasal Twin.</p>
      </div>
      <button
        onClick={() => navigate('/')}
        className="mt-2 px-4 py-2 bg-[#1e847f] text-white rounded-md text-sm font-medium hover:bg-[#166b67] transition-colors"
      >
        Back to Regional Overview
      </button>
    </div>
  );
};
