import React, { useState, useEffect, useCallback } from 'react';
import Map, { Marker, NavigationControl, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useAppStore } from '@/store/appStore';
import { mockNodes } from '@/data/mockData';
import { MapPin, ThermometerSun, IndianRupee, CloudRain, Loader2, AlertTriangle } from 'lucide-react';
import clsx from 'clsx';
import {
  getSEECropMaturity,
  getSEEPriceTrend,
  getSEEWeatherAdvisory,
  type SEECropMaturityResponse,
  type SEEPriceTrendResponse,
  type SEEWeatherAdvisoryResponse,
} from '@/api/client';

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY || '';
// Treat the placeholder value the same as a missing key
const HAS_MAPTILER_KEY = MAPTILER_KEY.length > 0 && !MAPTILER_KEY.startsWith('YOUR_');

const MAP_STYLE = HAS_MAPTILER_KEY
  ? `https://api.maptiler.com/maps/basic-v2/style.json?key=${MAPTILER_KEY}`
  : 'https://demotiles.maplibre.org/style.json'; // fallback: free offline demo style

const TERRAIN_TILES = HAS_MAPTILER_KEY
  ? `https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=${MAPTILER_KEY}`
  : null;

// ── Per-layer async state shape ──────────────────────────────────────────────
interface LayerState<T> {
  loading: boolean;
  error: string | null;
  data: T | null;
}

const initialLayerState = <T,>(): LayerState<T> => ({
  loading: false,
  error: null,
  data: null,
});

// ── Trend direction helper ───────────────────────────────────────────────────
const trendLabel = (dir: string) => {
  if (dir === 'upward') return '↑ Rising';
  if (dir === 'downward') return '↓ Softening';
  return '→ Stable';
};
const trendColor = (dir: string) =>
  dir === 'upward' ? '#1e847f' : dir === 'downward' ? '#c0392b' : '#f5b041';

// ── Data-source label ────────────────────────────────────────────────────────
const sourceLabel = (src: string) =>
  src === 'live_open_meteo' ? 'Live · Open-Meteo' : 'Historical · IMD CSV';

export const RegionalMap = () => {
  const { setSelectedNodeId, selectedNodeId, activeDistrict, activeCrop } = useAppStore();

  // ── Layer toggle booleans ──────────────────────────────────────────────────
  const [layers, setLayers] = useState({ health: false, price: false, weather: false });

  // ── Per-layer async state — independent: one failing must not block others ─
  const [healthState, setHealthState] = useState<LayerState<SEECropMaturityResponse>>(initialLayerState());
  const [priceState, setPriceState]   = useState<LayerState<SEEPriceTrendResponse>>(initialLayerState());
  const [weatherState, setWeatherState] = useState<LayerState<SEEWeatherAdvisoryResponse>>(initialLayerState());

  // ── Fetch helpers — each independent ──────────────────────────────────────

  const fetchCropHealth = useCallback(async () => {
    setHealthState({ loading: true, error: null, data: null });
    const result = await getSEECropMaturity(activeDistrict, activeCrop);
    if ('error' in result && result.error) {
      setHealthState({ loading: false, error: 'Backend not connected', data: null });
    } else {
      setHealthState({ loading: false, error: null, data: result as SEECropMaturityResponse });
    }
  }, [activeDistrict, activeCrop]);

  const fetchPriceTrend = useCallback(async () => {
    setPriceState({ loading: true, error: null, data: null });
    // Market name follows the pattern "{District} Mandi" for Tier 1 districts
    const market = `${activeDistrict} Mandi`;
    const result = await getSEEPriceTrend(activeDistrict, market, activeCrop, 14);
    if ('error' in result && result.error) {
      setPriceState({ loading: false, error: 'Backend not connected', data: null });
    } else {
      setPriceState({ loading: false, error: null, data: result as SEEPriceTrendResponse });
    }
  }, [activeDistrict, activeCrop]);

  const fetchWeather = useCallback(async () => {
    setWeatherState({ loading: true, error: null, data: null });
    const result = await getSEEWeatherAdvisory(activeDistrict, activeCrop);
    if ('error' in result && result.error) {
      setWeatherState({ loading: false, error: 'Backend not connected', data: null });
    } else {
      setWeatherState({ loading: false, error: null, data: result as SEEWeatherAdvisoryResponse });
    }
  }, [activeDistrict, activeCrop]);

  // ── Toggle handler — fires fetch only when turning ON ──────────────────────
  const toggleLayer = (layer: keyof typeof layers) => {
    const newVal = !layers[layer];
    setLayers(prev => ({ ...prev, [layer]: newVal }));
    if (newVal) {
      if (layer === 'health')  fetchCropHealth();
      if (layer === 'price')   fetchPriceTrend();
      if (layer === 'weather') fetchWeather();
    }
  };

  // Re-fetch active layers whenever district/crop changes
  useEffect(() => {
    if (layers.health)  fetchCropHealth();
    if (layers.price)   fetchPriceTrend();
    if (layers.weather) fetchWeather();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDistrict, activeCrop]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden h-full flex flex-col relative">
      {/* Map Header Controls */}
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="bg-white/90 backdrop-blur-sm px-3 py-1.5 rounded-md border border-gray-200 shadow-sm pointer-events-auto">
          <h3 className="font-semibold text-gray-800 text-sm">Regional Twin</h3>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <button
            onClick={() => toggleLayer('health')}
            className={clsx(
              'p-1.5 rounded-md border transition-colors flex items-center gap-1.5 text-xs font-medium bg-white/90 backdrop-blur-sm shadow-sm',
              layers.health ? 'border-[#1e847f] text-[#1e847f]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            <ThermometerSun className="w-3.5 h-3.5" />
            Crop Health
          </button>
          <button
            onClick={() => toggleLayer('price')}
            className={clsx(
              'p-1.5 rounded-md border transition-colors flex items-center gap-1.5 text-xs font-medium bg-white/90 backdrop-blur-sm shadow-sm',
              layers.price ? 'border-[#f5b041] text-[#f5b041]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            <IndianRupee className="w-3.5 h-3.5" />
            Price Trend
          </button>
          <button
            onClick={() => toggleLayer('weather')}
            className={clsx(
              'p-1.5 rounded-md border transition-colors flex items-center gap-1.5 text-xs font-medium bg-white/90 backdrop-blur-sm shadow-sm',
              layers.weather ? 'border-[#2d4a22] text-[#2d4a22]' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            <CloudRain className="w-3.5 h-3.5" />
            Weather
          </button>
        </div>
      </div>

      {/* Layer Data Overlays — each renders independently */}
      {(layers.health || layers.price || layers.weather) && (
        <div className="absolute top-14 right-4 z-10 flex flex-col gap-2 pointer-events-none">

          {/* ── Crop Health overlay ───────────────────────────────────────── */}
          {layers.health && (
            <div className="bg-white/95 backdrop-blur-sm border border-[#1e847f] rounded-lg p-3 shadow-md text-xs w-64">
              <p className="font-bold text-[#1e847f] mb-1.5 flex items-center gap-1.5">
                <ThermometerSun className="w-3.5 h-3.5" /> Crop Health
              </p>
              {healthState.loading ? (
                <div className="flex items-center gap-2 text-gray-500 py-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Loading…</span>
                </div>
              ) : healthState.error ? (
                <div className="flex items-center gap-1.5 text-red-600">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>Backend not connected</span>
                </div>
              ) : healthState.data ? (
                <div className="space-y-1 text-gray-700">
                  <div className="flex justify-between">
                    <span>Season</span>
                    <span className="font-semibold text-right max-w-[130px] truncate">{healthState.data.current_season}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Stage</span>
                    <span className="font-semibold text-right max-w-[130px] truncate">{healthState.data.crop_stage}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Maturity</span>
                    <span className="font-semibold text-[#1e847f]">{healthState.data.estimated_maturity_pct}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Peak harvest in</span>
                    <span className="font-semibold">{healthState.data.days_to_peak_harvest}d</span>
                  </div>
                  {/* Provenance label — shown verbatim, not hidden */}
                  <div className="mt-2 pt-2 border-t border-[#1e847f]/20 text-[10px] text-gray-500 italic leading-tight">
                    {healthState.data.source}
                  </div>
                </div>
              ) : null}
            </div>
          )}

          {/* ── Price Trend overlay ───────────────────────────────────────── */}
          {layers.price && (
            <div className="bg-white/95 backdrop-blur-sm border border-[#f5b041] rounded-lg p-3 shadow-md text-xs w-64">
              <p className="font-bold text-[#f5b041] mb-1.5 flex items-center gap-1.5">
                <IndianRupee className="w-3.5 h-3.5" /> Price Trend
              </p>
              {priceState.loading ? (
                <div className="flex items-center gap-2 text-gray-500 py-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Loading…</span>
                </div>
              ) : priceState.error ? (
                <div className="flex items-center gap-1.5 text-red-600">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>Backend not connected</span>
                </div>
              ) : priceState.data ? (
                <div className="space-y-1 text-gray-700">
                  <div className="flex justify-between">
                    <span>Latest</span>
                    <span className="font-semibold">₹{priceState.data.summary.latest_modal_price_rs}/q</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Range (14d)</span>
                    <span className="font-semibold">
                      ₹{priceState.data.summary.min_modal_price_rs}–{priceState.data.summary.max_modal_price_rs}/q
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Trend</span>
                    <span className="font-semibold" style={{ color: trendColor(priceState.data.summary.trend_direction) }}>
                      {trendLabel(priceState.data.summary.trend_direction)}
                    </span>
                  </div>
                  {/* Data provenance */}
                  <div className="mt-2 pt-2 border-t border-[#f5b041]/20 text-[10px] text-gray-500 italic leading-tight">
                    {priceState.data.data_provenance}
                  </div>
                </div>
              ) : priceState.data && (priceState.data as SEEPriceTrendResponse).status === 'insufficient_data' ? (
                <div className="text-gray-500">No market data for {activeDistrict}</div>
              ) : null}
            </div>
          )}

          {/* ── Weather Advisory overlay ──────────────────────────────────── */}
          {layers.weather && (
            <div className="bg-white/95 backdrop-blur-sm border border-[#2d4a22] rounded-lg p-3 shadow-md text-xs w-64">
              <p className="font-bold text-[#2d4a22] mb-1.5 flex items-center gap-1.5">
                <CloudRain className="w-3.5 h-3.5" /> Weather Advisory
              </p>
              {weatherState.loading ? (
                <div className="flex items-center gap-2 text-gray-500 py-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Loading…</span>
                </div>
              ) : weatherState.error ? (
                <div className="flex items-center gap-1.5 text-red-600">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>Backend not connected</span>
                </div>
              ) : weatherState.data ? (
                <div className="space-y-1 text-gray-700">
                  {/* Advisory sentence — shown verbatim */}
                  <p className="leading-snug">{weatherState.data.advisory_sentence}</p>
                  <div className="flex justify-between mt-1">
                    <span>Rainfall std</span>
                    <span className="font-semibold">{weatherState.data.rainfall_std_mm.toFixed(1)} mm</span>
                  </div>
                  {weatherState.data.has_meaningful_shift && (
                    <div className="flex justify-between">
                      <span>Harvest shift</span>
                      <span className="font-semibold text-[#c0392b]">
                        +{weatherState.data.estimated_harvest_shift_days}d
                      </span>
                    </div>
                  )}
                  {/* Data source label */}
                  <div className="mt-2 pt-2 border-t border-[#2d4a22]/20 text-[10px] text-gray-500 italic">
                    Source: {sourceLabel(weatherState.data.data_source)}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Map Canvas */}
      <div className="flex-1 w-full h-full bg-gray-100 relative">
        {/* Missing MapTiler key warning — shown as an overlay, map still renders with fallback style */}
        {!HAS_MAPTILER_KEY && (
          <div className="absolute top-2 left-1/2 -translate-x-1/2 z-20 bg-amber-50 border border-amber-300 text-amber-800 text-xs px-3 py-1.5 rounded-md shadow pointer-events-none">
            Add <code className="font-mono font-bold">VITE_MAPTILER_KEY</code> to .env.local for full map + terrain
          </div>
        )}

        <Map
          initialViewState={{
            longitude: 76.10,
            latitude: 9.49,   // Alappuzha / Kuttanad
            zoom: 10.5,
            pitch: 45,
            bearing: 0,
          }}
          style={{ width: '100%', height: '100%' }}
          mapStyle={MAP_STYLE}
          {...(TERRAIN_TILES ? { terrain: { source: 'terrain', exaggeration: 1.5 } } : {})}
        >
          {/* MapTiler terrain-RGB source for 3D elevation */}
          {TERRAIN_TILES && (
            <Source
              id="terrain"
              type="raster-dem"
              url={TERRAIN_TILES}
              tileSize={256}
            />
          )}

          <NavigationControl position="bottom-right" />

          {mockNodes.map(node => (
            <Marker
              key={node.id}
              longitude={node.coordinates[0]}
              latitude={node.coordinates[1]}
              anchor="bottom"
              onClick={e => {
                e.originalEvent.stopPropagation();
                setSelectedNodeId(node.id);
              }}
            >
              <div
                className={clsx(
                  'relative group cursor-pointer transform transition-transform',
                  selectedNodeId === node.id ? 'scale-125' : 'hover:scale-110'
                )}
              >
                {/* Occupancy Ring */}
                {node.type !== 'Farm Block' && node.type !== 'FPO' && (
                  <div
                    className="absolute -inset-2 rounded-full border-2 opacity-50 pointer-events-none"
                    style={{
                      borderColor:
                        node.status === 'Critical'
                          ? '#c0392b'
                          : node.status === 'Warning'
                          ? '#f5b041'
                          : '#1e847f',
                    }}
                  />
                )}

                {/* Node Icon */}
                <div
                  className={clsx(
                    'p-2 rounded-full shadow-md flex items-center justify-center',
                    node.type === 'Farm Block'
                      ? 'bg-[#1e847f] text-white'
                      : node.status === 'Critical'
                      ? 'bg-[#c0392b] text-white'
                      : node.status === 'Warning'
                      ? 'bg-[#f5b041] text-white'
                      : 'bg-white text-[#2d3436] border border-gray-200'
                  )}
                >
                  <MapPin className="w-4 h-4" />
                </div>

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-2 py-1 bg-[#1a1e23] text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  {node.name}
                </div>
              </div>
            </Marker>
          ))}
        </Map>
      </div>
    </div>
  );
};
