import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/store/appStore';
import { X, ExternalLink, ShieldCheck, FileText, AlertTriangle, Loader2 } from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { mockBottleneckAlert } from '@/data/mockData';
import { getRecommendation, type RecommendationResponse } from '@/api/client';

export const EvidenceDrawer = ({ alert }: { alert?: any } = {}) => {
  const { isEvidenceDrawerOpen, setEvidenceDrawerOpen, activeState, activeDistrict, activeCrop } =
    useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiData, setApiData] = useState<RecommendationResponse | null>(null);

  // Fetch from real API whenever the drawer opens
  useEffect(() => {
    if (!isEvidenceDrawerOpen) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setApiData(null);

    getRecommendation(activeState, activeDistrict, activeCrop).then((result) => {
      if (cancelled) return;
      setLoading(false);
      if ('error' in result && result.error) {
        setError('Backend not connected');
      } else {
        setApiData(result as RecommendationResponse);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [isEvidenceDrawerOpen, activeState, activeDistrict, activeCrop]);

  // Fallback: if API returned data, use it; if prop was passed use that; otherwise use mock
  const data = apiData ?? alert ?? mockBottleneckAlert;

  // Normalize the three possible sources (real API, alert prop, mock) into one view model,
  // since they don't share a field-for-field shape (e.g. mock uses `confidence` + `factors`,
  // the real API uses `confidence_label` + `full_twin_recommendation.evidence_chain`).
  const confidenceLabel: string = apiData
    ? apiData.confidence_label
    : (data.confidence_label ?? data.confidence ?? 'HIGH').toString().toUpperCase();

  const evidenceItems: Array<{ fact: string; source?: string }> = apiData
    ? (apiData.full_twin_recommendation?.evidence_chain ?? [])
    : (data.factors ?? []).map((f: any) => ({ fact: f.description, source: f.source }));

  const recommendedAction: string = apiData
    ? (apiData.full_twin_recommendation?.selected_action ?? apiData.answer)
    : (data.recommendedAction ?? data.answer ?? '');

  const scheme = apiData
    ? (apiData.scheme_advice?.schemes?.[0]
        ? {
            title: apiData.scheme_advice.schemes[0].scheme_name,
            description: apiData.scheme_advice.schemes[0].plain_language_summary,
            source: apiData.scheme_advice.schemes[0].source_document,
            verificationNote: apiData.scheme_advice.schemes[0].mandatory_notice,
          }
        : null)
    : (data.scheme ?? null);

  return (
    <AnimatePresence>
      {isEvidenceDrawerOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setEvidenceDrawerOpen(false)}
            className="fixed inset-0 bg-black/20 z-40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 w-full md:w-[400px] bg-white shadow-2xl z-50 flex flex-col border-l border-gray-200"
          >
            <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gray-50">
              <h2 className="text-xl font-bold font-fraunces text-gray-900">Confidence & Evidence</h2>
              <button
                onClick={() => setEvidenceDrawerOpen(false)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-200 rounded-full transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              {/* Loading state */}
              {loading && (
                <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                  <Loader2 className="w-8 h-8 animate-spin text-[#1e847f] mb-3" />
                  <p className="text-sm">Fetching recommendation…</p>
                </div>
              )}

              {/* Error banner */}
              {!loading && error && (
                <>
                  <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-800 px-4 py-3 rounded-lg text-sm font-medium">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    {error}
                  </div>
                  {/* Still render mock data below so the UI isn't blank */}
                  <p className="text-xs text-gray-400 -mt-4">Showing cached mock data for preview</p>
                </>
              )}

              {/* Data section (shows mock when error, real data when connected) */}
              {!loading && (
                <>
                  {/* Capability tier context (only present when connected to real backend) */}
                  {apiData && (
                    <div className="text-xs text-gray-500 -mb-4">
                      {apiData.district} · {apiData.crop} · <span className="font-mono">{apiData.capability_tier}</span>
                    </div>
                  )}

                  {/* Confidence state — structurally distinct, not just re-colored:
                      LOW renders as a plain bordered warning box (no pill shape at all)
                      so it can never be visually mistaken for a normal HIGH/MEDIUM result. */}
                  <div>
                    <p className="text-sm text-gray-500 font-medium mb-2">Overall Confidence</p>
                    {confidenceLabel === 'LOW' ? (
                      <div className="border border-[#c0392b] px-3 py-1.5 rounded-md text-[#c0392b] font-bold text-sm shadow-sm">
                        Low confidence — estimated, pending model recalibration
                      </div>
                    ) : confidenceLabel === 'MEDIUM' || confidenceLabel === 'MODERATE' ? (
                      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-teal-500 text-teal-500 font-bold text-sm shadow-sm">
                        <ShieldCheck className="w-4 h-4" />
                        Medium Confidence
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#f5b041] text-white font-bold text-sm shadow-sm">
                        <ShieldCheck className="w-4 h-4" />
                        High Confidence
                      </div>
                    )}
                  </div>

                  {/* Evidence chain (Tier 1 full-twin) or contributing factors (mock/prop fallback) */}
                  {evidenceItems.length > 0 && (
                    <div>
                      <p className="text-sm text-gray-500 font-medium mb-3">Forecast Evidence</p>
                      <div className="space-y-4">
                        {evidenceItems.map((item, idx) => (
                          <div key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                            <div className="flex items-start justify-between gap-2">
                              <p className="text-sm font-medium text-gray-800">{item.fact}</p>
                            </div>
                            {item.source && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-[#1e847f] bg-teal-50 px-2 py-0.5 rounded border border-teal-100 mt-2">
                                {item.source}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* API provenance (when connected) */}
                  {apiData && apiData.provenance && (
                    <div>
                      <p className="text-sm text-gray-500 font-medium mb-2">Provenance</p>
                      <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg border border-gray-200">
                        {apiData.provenance}
                      </p>
                    </div>
                  )}

                  {/* Recommendation Logic */}
                  <div>
                    <p className="text-sm text-gray-500 font-medium mb-3">Recommendation Logic</p>
                    {confidenceLabel === 'LOW' ? (
                      <div className="border border-[#c0392b] p-4 rounded-md text-[#c0392b]">
                        <p className="text-sm font-medium mb-2">Estimated Recommendation</p>
                        <p className="text-sm">{recommendedAction}</p>
                      </div>
                    ) : (
                      <div className="bg-white border border-gray-200 p-4 rounded-lg shadow-sm">
                        <div className="pl-0">
                          <p className="text-sm font-bold text-[#1e847f]">
                            Decision: {recommendedAction}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Scheme info */}
                  {scheme && (
                    <div>
                      <p className="text-sm text-gray-500 font-medium mb-3">
                        Relevant Government Scheme
                      </p>
                      <div className="bg-teal-50/50 border border-[#1e847f]/20 p-4 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-4 h-4 text-[#1e847f]" />
                          <h4 className="font-bold text-[#1e847f]">{scheme.title}</h4>
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{scheme.description}</p>
                        <div className="flex flex-col gap-2 pt-3 border-t border-[#1e847f]/10">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-gray-500">Source</span>
                            <span className="text-xs font-medium text-gray-800 flex items-center gap-1">
                              {scheme.source}{' '}
                              <ExternalLink className="w-3 h-3 text-[#1e847f]" />
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-gray-500">Status</span>
                            <span className="text-xs font-medium text-teal-600">
                              {scheme.verificationNote}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
