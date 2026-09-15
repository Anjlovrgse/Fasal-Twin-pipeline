import React, { useEffect, useState, useCallback } from 'react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { ContributingFactors } from '@/components/dashboard/ContributingFactors';
import { RegionalMap } from '@/components/dashboard/RegionalMap';
import { NetworkTable } from '@/components/dashboard/NetworkTable';
import { BottleneckAlert } from '@/components/dashboard/BottleneckAlert';
import { useAppStore } from '@/store/appStore';
import { getCapabilityTier, type CapabilityTierResponse } from '@/api/client';
import { Loader2, AlertTriangle, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

// ── District / crop presets for the switcher ─────────────────────────────────
interface DistrictPreset {
  label: string;
  state: string;
  district: string;
  crop: string;
}

const DISTRICT_PRESETS: DistrictPreset[] = [
  { label: 'Kerala · Alappuzha · Rice (Tier 1)',   state: 'Kerala', district: 'Alappuzha', crop: 'Rice'   },
  { label: 'Kerala · Kottayam · Rice (Tier 1)',    state: 'Kerala', district: 'Kottayam',  crop: 'Rice'   },
  { label: 'Kerala · Ernakulam · Tomato (Tier 2)', state: 'Kerala', district: 'Ernakulam', crop: 'Tomato' },
  { label: 'Kerala · Palakkad · Wheat (Tier 3)',   state: 'Kerala', district: 'Palakkad',  crop: 'Wheat'  },
];

// ── Tier badge styling ────────────────────────────────────────────────────────
const TIER_CONFIG: Record<string, { label: string; classes: string; dotClass: string }> = {
  TIER_1_FULL_TWIN:       { label: 'Tier 1 · Full Digital Twin',   classes: 'bg-[#1e847f] text-white border-[#1e847f]',         dotClass: 'bg-white' },
  TIER_2_LIVE_SNAPSHOT:   { label: 'Tier 2 · Live Snapshot',        classes: 'border-[#f5b041] text-[#f5b041] bg-amber-50',      dotClass: 'bg-[#f5b041]' },
  TIER_3_INSUFFICIENT:    { label: 'Tier 3 · Insufficient Data',    classes: 'border-[#c0392b] text-[#c0392b] bg-red-50',       dotClass: 'bg-[#c0392b]' },
};

// ── CapabilityTierBadge (inline component) ────────────────────────────────────
const CapabilityTierBadge: React.FC = () => {
  const { activeState, activeDistrict, activeCrop } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tierData, setTierData] = useState<CapabilityTierResponse | null>(null);

  const fetchTier = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await getCapabilityTier(activeState, activeDistrict, activeCrop);
    setLoading(false);
    if ('error' in result && result.error) {
      setError('Backend not connected');
    } else {
      setTierData(result as CapabilityTierResponse);
    }
  }, [activeState, activeDistrict, activeCrop]);

  useEffect(() => { fetchTier(); }, [fetchTier]);

  const config = tierData ? (TIER_CONFIG[tierData.tier] ?? TIER_CONFIG['TIER_3_INSUFFICIENT']) : null;

  return (
    <div className="flex items-center gap-2">
      {loading && (
        <div className="flex items-center gap-1.5 text-gray-400 text-xs">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Resolving tier…</span>
        </div>
      )}
      {!loading && error && (
        <div className="flex items-center gap-1.5 text-red-500 text-xs border border-red-300 bg-red-50 px-2.5 py-1 rounded-full">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>Backend not connected</span>
        </div>
      )}
      {!loading && !error && config && (
        <div
          title={tierData?.explanation}
          className={clsx(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-semibold select-none',
            config.classes
          )}
        >
          <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', config.dotClass)} />
          {config.label}
        </div>
      )}
    </div>
  );
};

// ── DistrictSwitcher (inline component) ──────────────────────────────────────
const DistrictSwitcher: React.FC = () => {
  const { activeState, activeDistrict, activeCrop, setActiveState, setActiveDistrict, setActiveCrop } = useAppStore();

  const currentPresetIndex = DISTRICT_PRESETS.findIndex(
    p => p.state === activeState && p.district === activeDistrict && p.crop === activeCrop
  );
  const selectedValue = currentPresetIndex >= 0 ? String(currentPresetIndex) : 'custom';

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const idx = parseInt(e.target.value, 10);
    if (!isNaN(idx) && DISTRICT_PRESETS[idx]) {
      const p = DISTRICT_PRESETS[idx];
      setActiveState(p.state);
      setActiveDistrict(p.district);
      setActiveCrop(p.crop);
    }
  };

  return (
    <div className="relative flex items-center">
      <select
        id="district-switcher"
        value={selectedValue}
        onChange={handleChange}
        className="appearance-none pl-3 pr-8 py-1.5 rounded-md border border-gray-300 text-xs font-medium text-gray-700 bg-white shadow-sm focus:outline-none focus:ring-1 focus:ring-[#1e847f] cursor-pointer"
      >
        {DISTRICT_PRESETS.map((p, i) => (
          <option key={i} value={String(i)}>{p.label}</option>
        ))}
        {selectedValue === 'custom' && (
          <option value="custom">{activeState} · {activeDistrict} · {activeCrop} (custom)</option>
        )}
      </select>
      <ChevronDown className="w-3.5 h-3.5 text-gray-400 absolute right-2 pointer-events-none" />
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
export const RegionalOverview = () => {
  return (
    <div className="p-6 h-full flex flex-col min-h-0">
      {/* Tier badge + district switcher row */}
      <div className="flex items-center justify-between mb-4 shrink-0 gap-4 flex-wrap">
        <CapabilityTierBadge />
        <DistrictSwitcher />
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 shrink-0">
        <MetricCard
          label="Expected Crop Arrivals"
          value="18,400 t"
          subLabel="Oct 18-26 window"
        />
        <MetricCard
          label="Total Mandi Capacity"
          value="13,900 t"
          subLabel="Within 50km radius"
        />
        <MetricCard
          label="Regional Bottleneck Risk"
          value="High"
          isRisk={true}
        />
        <MetricCard
          label="Projected Value at Risk"
          value="₹1.84 Cr"
          isRisk={true}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        {/* Left Column: Factors */}
        <div className="w-full lg:w-1/3 xl:w-1/4 shrink-0 h-64 lg:h-auto">
          <ContributingFactors />
        </div>

        {/* Right Column: Map & Table container */}
        <div className="flex-1 flex flex-col min-w-0 gap-6 h-full relative">
          <div className="flex-1 min-h-[400px]">
            <RegionalMap />
          </div>
          <BottleneckAlert />
        </div>
      </div>

      {/* Technical Parameters Table */}
      <div className="shrink-0 pb-6">
        <NetworkTable />
      </div>
    </div>
  );
};
