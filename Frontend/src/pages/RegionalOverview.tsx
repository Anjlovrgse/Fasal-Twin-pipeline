import React, { useEffect, useState, useCallback } from 'react';
import { MetricCard } from '@/components/dashboard/MetricCard';
import { ContributingFactors } from '@/components/dashboard/ContributingFactors';
import { RegionalMap } from '@/components/dashboard/RegionalMap';
import { NetworkTable } from '@/components/dashboard/NetworkTable';
import { BottleneckAlert } from '@/components/dashboard/BottleneckAlert';
import { useAppStore } from '@/store/appStore';
import {
  getCapabilityTier,
  getBottleneckDetection,
  getRecommendation,
  type CapabilityTierResponse,
  type BottleneckDetectionResponse,
  type RecommendationResponse,
} from '@/api/client';
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

const VALUE_AT_RISK_RS_PER_TONNE = 28000; // ~ Rs 2,800/quintal, matching the elasticity model's baseline modal price

// ── Main page ─────────────────────────────────────────────────────────────────
export const RegionalOverview = () => {
  const { activeState, activeDistrict, activeCrop } = useAppStore();

  // Real per-node bottleneck data (baseline scenario) drives the metric cards and network table.
  const [bnLoading, setBnLoading] = useState(false);
  const [bnError, setBnError] = useState<string | null>(null);
  const [bnData, setBnData] = useState<BottleneckDetectionResponse | null>(null);

  // Real /analyze evidence chain drives "Top contributing factors".
  const [anLoading, setAnLoading] = useState(false);
  const [anError, setAnError] = useState<string | null>(null);
  const [anData, setAnData] = useState<RecommendationResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setBnLoading(true);
    setBnError(null);
    setBnData(null);
    getBottleneckDetection(activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setBnLoading(false);
      if ('error' in result && result.error) {
        setBnError('Backend not connected');
      } else {
        setBnData(result as BottleneckDetectionResponse);
      }
    });
    return () => { cancelled = true; };
  }, [activeDistrict, activeCrop]);

  useEffect(() => {
    let cancelled = false;
    setAnLoading(true);
    setAnError(null);
    setAnData(null);
    getRecommendation(activeState, activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setAnLoading(false);
      if ('error' in result && result.error) {
        setAnError('Backend not connected');
      } else {
        setAnData(result as RecommendationResponse);
      }
    });
    return () => { cancelled = true; };
  }, [activeState, activeDistrict, activeCrop]);

  const baseline = bnData?.scenarios?.baseline;
  const baselineComputable = baseline?.computable === true;

  const totalArrivals = baselineComputable
    ? baseline!.bottlenecks.reduce((sum, b) => sum + b.forecast_inflow_tonnes, 0)
    : null;
  const mandiCapacity = baselineComputable
    ? baseline!.bottlenecks.filter((b) => b.node_type === 'mandi').reduce((sum, b) => sum + b.capacity_tonnes, 0)
    : null;
  const riskLevel = baselineComputable
    ? (baseline!.max_utilization_ratio >= 1 ? 'High' : baseline!.max_utilization_ratio >= 0.65 ? 'Medium' : 'Low')
    : null;
  const valueAtRiskCr = baselineComputable
    ? (baseline!.total_overshoot_tonnes * VALUE_AT_RISK_RS_PER_TONNE) / 1e7
    : null;

  const networkUnavailableReason = !bnLoading && !bnError && !baselineComputable
    ? (baseline?.reason ?? 'Full network simulation is unavailable for this district — see the capability tier above.')
    : null;

  const evidenceChain = anData?.full_twin_recommendation?.evidence_chain ?? [];
  const evidenceUnavailableReason = !anLoading && !anError && anData && anData.capability_tier !== 'TIER_1_FULL_TWIN'
    ? anData.answer
    : null;

  return (
    <div className="p-6 flex flex-col">
      {/* Tier badge + district switcher row */}
      <div className="flex items-center justify-between mb-4 shrink-0 gap-4 flex-wrap">
        <CapabilityTierBadge />
        <DistrictSwitcher />
      </div>

      {/* Summary Metrics — real, derived from the baseline scenario's actual node-level forecast */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 shrink-0">
        <MetricCard
          label="Expected Crop Arrivals"
          value={bnLoading ? '…' : totalArrivals != null ? `${Math.round(totalArrivals).toLocaleString()} t` : '—'}
          subLabel={bnLoading ? 'Loading…' : baselineComputable ? 'Baseline scenario forecast' : (bnError ?? 'Unavailable for this tier')}
        />
        <MetricCard
          label="Total Mandi Capacity"
          value={bnLoading ? '…' : mandiCapacity != null ? `${Math.round(mandiCapacity).toLocaleString()} t` : '—'}
          subLabel={baselineComputable ? 'Mapped mandi nodes' : undefined}
        />
        <MetricCard
          label="Regional Bottleneck Risk"
          value={bnLoading ? '…' : riskLevel ?? '—'}
          isRisk={riskLevel === 'High'}
        />
        <MetricCard
          label="Projected Value at Risk"
          value={bnLoading ? '…' : valueAtRiskCr != null ? `₹${valueAtRiskCr.toFixed(2)} Cr` : '—'}
          isRisk={true}
        />
      </div>

      {/* Main Content Area — a fixed-ish min-height row (not flex-1/min-h-0) so the
          Network Parameters table below, which can be many rows of real data, pushes
          the page taller instead of squeezing this row's map and factors panel down
          to near-zero height fighting for the same fixed viewport budget. */}
      <div className="flex flex-col lg:flex-row gap-6 mb-6 min-h-[520px]">
        {/* Left Column: Factors */}
        <div className="w-full lg:w-1/3 xl:w-1/4 shrink-0">
          <ContributingFactors
            factors={evidenceChain}
            loading={anLoading}
            error={anError}
            unavailableReason={evidenceUnavailableReason}
          />
        </div>

        {/* Right Column: Map & Table container */}
        <div className="flex-1 flex flex-col min-w-0 gap-6 relative">
          <div className="flex-1 min-h-[400px]">
            <RegionalMap />
          </div>
          <BottleneckAlert />
        </div>
      </div>

      {/* Technical Parameters Table — real per-node data from the baseline scenario */}
      <div className="shrink-0 pb-6">
        <NetworkTable
          nodes={baseline?.bottlenecks ?? []}
          crop={activeCrop}
          loading={bnLoading}
          error={bnError}
          unavailableReason={networkUnavailableReason}
        />
      </div>
    </div>
  );
};
