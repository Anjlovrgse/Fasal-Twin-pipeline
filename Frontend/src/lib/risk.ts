export type RiskLevel = 'High' | 'Medium' | 'Low';

/**
 * Classifies a node's utilization ratio (forecast inflow / capacity — can exceed
 * 1.0 when a node is over capacity) into a risk band. Shared across every place
 * that reads a BottleneckNode's utilization_ratio, so the High/Medium/Low cutoff
 * can't silently drift between the map, the network table, and the alert card.
 */
export function riskFromUtilizationRatio(ratio: number): RiskLevel {
  if (ratio >= 1) return 'High';
  if (ratio >= 0.65) return 'Medium';
  return 'Low';
}

/**
 * Classifies a composite 0.0-1.0 bottleneck risk score (the blended
 * utilization/overshoot/alert-count score /priority-view returns) into a risk
 * band. Deliberately a different function from riskFromUtilizationRatio: a
 * composite score is always 0-1, while a raw utilization ratio commonly exceeds
 * 1.0, so the two are not interchangeable even though the thresholds differ.
 */
export function riskFromCompositeScore(score: number): RiskLevel {
  if (score >= 0.65) return 'High';
  if (score >= 0.35) return 'Medium';
  return 'Low';
}
