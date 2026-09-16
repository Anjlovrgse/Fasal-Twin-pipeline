import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/store/appStore';
import { getFullRecommendation, getSchemeAdvice, type FullRecommendationResponse, type SchemeAdvisorResponse } from '@/api/client';
import { Loader2, AlertTriangle, FileText, ExternalLink, Info } from 'lucide-react';

// Scheme Advisor is action-triggered by design — it explains the schemes matched
// to the system's actual current recommendation, not a standalone chat interface.
// This page reproduces that same real call chain (recommendation -> matched
// schemes) so it stays grounded even when reached directly from the sidebar.
export const SchemeAdvisorView = () => {
  const { activeDistrict, activeCrop } = useAppStore();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<FullRecommendationResponse | null>(null);
  const [advice, setAdvice] = useState<SchemeAdvisorResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRecommendation(null);
    setAdvice(null);

    (async () => {
      const recResult = await getFullRecommendation(activeDistrict, activeCrop);
      if (cancelled) return;
      if ('error' in recResult && recResult.error) {
        setLoading(false);
        setError('Backend not connected');
        return;
      }
      const rec = recResult as FullRecommendationResponse;
      setRecommendation(rec);

      const adviceResult = await getSchemeAdvice(rec.recommendation_id);
      if (cancelled) return;
      setLoading(false);
      if ('error' in adviceResult && adviceResult.error) {
        setError('Backend not connected');
      } else {
        setAdvice(adviceResult as SchemeAdvisorResponse);
      }
    })();

    return () => { cancelled = true; };
  }, [activeDistrict, activeCrop]);

  return (
    <div className="p-6 h-full flex flex-col overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold font-fraunces text-gray-900">Scheme Advisor</h2>
        <p className="text-gray-500 text-sm mt-1">
          Government schemes matched to the current recommended action for {activeCrop} in {activeDistrict}
        </p>
      </div>

      <div className="flex items-start gap-2 bg-gray-50 border border-gray-200 text-gray-600 px-4 py-3 rounded-lg text-xs mb-6">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <span>
          By design, Scheme Advisor is action-triggered rather than a standalone chat: every match below is
          grounded in the system's real current recommendation, shown for reference on this page.
        </span>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded-lg text-sm font-medium mb-4">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex items-center gap-3 text-gray-500">
            <Loader2 className="w-7 h-7 animate-spin text-[#1e847f]" />
            <span className="text-sm">Resolving current recommendation and matched schemes…</span>
          </div>
        </div>
      )}

      {!loading && recommendation && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm mb-6">
          <p className="text-xs text-gray-500 font-medium mb-1">Matched against recommendation</p>
          <p className="text-sm font-bold text-[#1e847f]">{recommendation.selected_action}</p>
          <p className="text-xs text-gray-400 mt-1">
            Confidence: {recommendation.confidence_label} · Action type: {recommendation.action_type}
          </p>
        </div>
      )}

      {!loading && advice && advice.schemes.length > 0 && (
        <div className="space-y-4">
          {advice.schemes.map((scheme) => (
            <div key={scheme.scheme_id} className="bg-teal-50/50 border border-[#1e847f]/20 p-5 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-[#1e847f]" />
                <h4 className="font-bold text-[#1e847f] font-fraunces text-lg">{scheme.scheme_name}</h4>
              </div>
              {scheme.ministry && <p className="text-xs text-gray-500 mb-3">{scheme.ministry}</p>}
              <p className="text-sm text-gray-700 mb-4 leading-relaxed">{scheme.plain_language_summary}</p>
              <div className="flex items-center justify-between pt-3 border-t border-[#1e847f]/10">
                <span className="text-xs font-medium text-gray-500 flex items-center gap-1">
                  {scheme.source_document} <ExternalLink className="w-3 h-3 text-[#1e847f]" />
                </span>
              </div>
            </div>
          ))}
          <div className="border border-[#c0392b]/30 bg-red-50/40 text-[#c0392b] text-sm font-medium px-4 py-3 rounded-md">
            {advice.mandatory_notice}
          </div>
        </div>
      )}

      {!loading && advice && advice.schemes.length === 0 && (
        <div className="text-center py-12 text-gray-500 text-sm">No schemes matched the current recommended action.</div>
      )}
    </div>
  );
};
