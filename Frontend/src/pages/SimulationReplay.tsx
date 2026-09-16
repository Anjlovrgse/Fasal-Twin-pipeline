import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { Play, Pause, ChevronLeft, FastForward, RotateCcw, Loader2, AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { RegionalMap } from '@/components/dashboard/RegionalMap';
import { motion } from 'framer-motion';
import { getPriceForecast, farmerQuery, type PriceForecastResponse, type FarmerQueryResponse } from '@/api/client';

export const SimulationReplay = () => {
  const navigate = useNavigate();
  const {
    isSimulationPlaying,
    setSimulationPlaying,
    simulationScenario,
    setSimulationScenario,
    interventionEnabled,
    setInterventionEnabled,
    activeState,
    activeDistrict,
    activeCrop,
  } = useAppStore();

  const scenarios = ['Baseline', 'Weather-shift', 'Regional shock', 'Capacity shock'] as const;

  // Price forecast state
  const [priceLoading, setPriceLoading] = useState(false);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [priceData, setPriceData] = useState<PriceForecastResponse | null>(null);

  // Recommendation state (populated when simulation finishes)
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState<string | null>(null);
  const [recData, setRecData] = useState<FarmerQueryResponse | null>(null);

  // Fetch price forecast on mount and on district/crop change
  useEffect(() => {
    let cancelled = false;
    setPriceLoading(true);
    setPriceError(null);
    setPriceData(null);

    getPriceForecast(activeState, activeDistrict, activeCrop, 14).then((result) => {
      if (cancelled) return;
      setPriceLoading(false);
      if ('error' in result && result.error) {
        setPriceError('Backend not connected');
      } else {
        setPriceData(result as PriceForecastResponse);
      }
    });

    return () => { cancelled = true; };
  }, [activeState, activeDistrict, activeCrop]);

  // Mock animation logic: auto-pause after 5 seconds; then fetch recommendation
  useEffect(() => {
    if (isSimulationPlaying) {
      const timer = setTimeout(() => {
        setSimulationPlaying(false);
        // After simulation ends, fetch the recommendation text
        fetchRecommendation();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [isSimulationPlaying, setSimulationPlaying]);

  const fetchRecommendation = async () => {
    setRecLoading(true);
    setRecError(null);
    setRecData(null);
    const question = `What is the recommended intervention for ${activeCrop} in ${activeDistrict}?`;
    const result = await farmerQuery(activeState, activeDistrict, activeCrop, question);
    setRecLoading(false);
    if ('error' in result && result.error) {
      setRecError('Backend not connected');
    } else {
      setRecData(result as FarmerQueryResponse);
    }
  };

  // Derived display values — use API data when available, fallback to illustrative mock
  const valueLoss = priceData
    ? `₹${((priceData.predicted_price_range[0] * 9200) / 1e7).toFixed(2)} Cr`
    : interventionEnabled && isSimulationPlaying
    ? '₹0.42 Cr'
    : '₹1.84 Cr';

  const valueProtected = priceData
    ? `₹${(((priceData.predicted_price_range[1] - priceData.predicted_price_range[0]) * 4500) / 1e7).toFixed(2)} Cr`
    : interventionEnabled && isSimulationPlaying
    ? '₹1.42 Cr'
    : '₹0.00 Cr';

  // The frontend must never present an uncertain number with the same visual confidence
  // as a verified one — when the backend flags a forecast's magnitude as implausible
  // (e.g. a model that fails out-of-sample generalization), the figure gets a muted,
  // warning-flagged treatment instead of the clean bold currency figure.
  const isImplausible = Boolean(priceData?.based_on?.implausible_magnitude);

  const recommendationText = recData
    ? recData.answer
    : `Reroute 4,500 t of ${activeCrop} yield from Block C to Storage Central utilizing Transport Subsidy Scheme (TSS).`;

  return (
    <div className="flex flex-col h-full bg-[#1a1e23]">
      {/* Header */}
      <div className="bg-[#1a1e23] border-b border-[#2d3436] px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4 text-white">
          <button
            onClick={() => navigate('/')}
            className="p-1.5 hover:bg-[#2d3436] rounded-md transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-xl font-bold font-fraunces">Counterfactual Simulation Replay</h2>
            <p className="text-sm text-gray-400">
              Evaluating interventions against projected scenarios —{' '}
              <span className="text-[#f5b041]">{activeDistrict} · {activeCrop}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-[#2d3436] p-1 rounded-lg">
          <button
            onClick={() => setInterventionEnabled(false)}
            className={clsx(
              'px-4 py-1.5 rounded-md text-sm font-medium transition-colors',
              !interventionEnabled ? 'bg-[#c0392b] text-white' : 'text-gray-400 hover:text-white'
            )}
          >
            Do Nothing
          </button>
          <button
            onClick={() => setInterventionEnabled(true)}
            className={clsx(
              'px-4 py-1.5 rounded-md text-sm font-medium transition-colors',
              interventionEnabled ? 'bg-[#1e847f] text-white' : 'text-gray-400 hover:text-white'
            )}
          >
            AI Intervention
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0 relative">
        {/* Left Panel: Scenarios and Metrics */}
        <div className="w-80 border-r border-[#2d3436] p-6 flex flex-col overflow-y-auto shrink-0 bg-[#1a1e23]">
          <h3 className="text-gray-400 text-xs font-semibold uppercase tracking-wider mb-4">
            Scenarios
          </h3>
          <div className="space-y-2 mb-8">
            {scenarios.map((scenario) => (
              <button
                key={scenario}
                onClick={() => setSimulationScenario(scenario)}
                className={clsx(
                  'w-full text-left px-4 py-3 rounded-md text-sm transition-all border',
                  simulationScenario === scenario
                    ? 'bg-[#2d3436] border-[#f5b041] text-white font-medium'
                    : 'border-transparent text-gray-400 hover:bg-[#2d3436] hover:text-white'
                )}
              >
                {scenario}
              </button>
            ))}
          </div>

          <div className="space-y-6 mt-auto">
            {/* Price error banner */}
            {priceError && (
              <div className="flex items-center gap-2 bg-red-900/30 border border-red-600/50 text-red-400 px-3 py-2 rounded-lg text-xs font-medium">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                {priceError}
              </div>
            )}

            <div className="bg-[#2d3436]/50 rounded-lg p-4 border border-[#2d3436]">
              <p className="text-gray-400 text-xs mb-1">Projected Value Loss</p>
              {priceLoading ? (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Loading…</span>
                </div>
              ) : (
                <div className="flex items-baseline gap-2">
                  <span
                    className={clsx(
                      'text-3xl font-bold font-fraunces',
                      isImplausible ? 'text-gray-500 opacity-60' : 'text-[#c0392b]'
                    )}
                  >
                    {interventionEnabled && isSimulationPlaying ? '₹0.42 Cr' : valueLoss}
                  </span>
                  {isImplausible && <AlertTriangle className="w-4 h-4 text-[#f5b041] shrink-0" />}
                </div>
              )}
              {isImplausible && !priceLoading && (
                <p className="text-[10px] text-[#f5b041] mt-1.5">Implausible magnitude — estimate flagged, not guaranteed</p>
              )}
            </div>

            <div className="bg-[#2d3436]/50 rounded-lg p-4 border border-[#2d3436]">
              <p className="text-gray-400 text-xs mb-1">Value Protected</p>
              {priceLoading ? (
                <div className="flex items-center gap-2 text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">Loading…</span>
                </div>
              ) : (
                <div className="flex items-baseline gap-2">
                  <span
                    className={clsx(
                      'text-3xl font-bold font-fraunces',
                      isImplausible ? 'text-gray-500 opacity-60' : 'text-[#1e847f]'
                    )}
                  >
                    {interventionEnabled && isSimulationPlaying ? '₹1.42 Cr' : valueProtected}
                  </span>
                  {isImplausible && <AlertTriangle className="w-4 h-4 text-[#f5b041] shrink-0" />}
                </div>
              )}
              {isImplausible && !priceLoading && (
                <p className="text-[10px] text-[#f5b041] mt-1.5">Implausible magnitude — estimate flagged, not guaranteed</p>
              )}
            </div>

            {/* Recommendation after simulation */}
            {interventionEnabled && !isSimulationPlaying && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-[#1e847f]/20 border border-[#1e847f] rounded-lg p-4"
              >
                <p className="text-[#1e847f] font-bold text-xs uppercase tracking-wider mb-2">
                  Final Recommendation
                </p>
                {recLoading ? (
                  <div className="flex items-center gap-2 text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm">Generating…</span>
                  </div>
                ) : recError ? (
                  <>
                    <div className="flex items-center gap-1.5 text-red-400 text-xs mb-2">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      {recError}
                    </div>
                    <p className="text-sm text-gray-300">{recommendationText}</p>
                  </>
                ) : (
                  <p className="text-sm text-gray-300">{recommendationText}</p>
                )}
              </motion.div>
            )}
          </div>
        </div>

        {/* Right Panel: Cinematic Map View */}
        <div className="flex-1 relative bg-black">
          <div className="absolute inset-0 opacity-80 mix-blend-screen pointer-events-none">
            {/* Custom dark styling and particle animations go here */}
          </div>
          <RegionalMap />

          {/* Animated Route overlay */}
          {isSimulationPlaying && interventionEnabled && (
            <motion.div
              className="absolute inset-0 pointer-events-none z-10"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <svg className="w-full h-full">
                <motion.path
                  d="M 200 400 Q 300 200 500 300"
                  fill="transparent"
                  stroke="#1e847f"
                  strokeWidth="4"
                  strokeDasharray="10 10"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </svg>
            </motion.div>
          )}

          {/* Timeline Controls */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-[#1a1e23] border border-[#2d3436] rounded-full px-6 py-3 flex items-center gap-6 shadow-2xl z-20">
            <button
              onClick={() => {
                setSimulationPlaying(false);
                setInterventionEnabled(false);
                setRecData(null);
                setRecError(null);
              }}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
            <button
              onClick={() => setSimulationPlaying(!isSimulationPlaying)}
              className="bg-[#f5b041] hover:bg-[#e09e30] text-[#1a1e23] p-3 rounded-full transition-transform hover:scale-105"
            >
              {isSimulationPlaying ? (
                <Pause className="w-5 h-5 fill-current" />
              ) : (
                <Play className="w-5 h-5 fill-current ml-0.5" />
              )}
            </button>
            <button className="text-gray-400 hover:text-white transition-colors">
              <FastForward className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
