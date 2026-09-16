import { describe, it, expect } from 'vitest';
import { riskFromUtilizationRatio, riskFromCompositeScore } from './risk';

describe('riskFromUtilizationRatio', () => {
  it('classifies a node comfortably under capacity as Low', () => {
    expect(riskFromUtilizationRatio(0.3)).toBe('Low');
    expect(riskFromUtilizationRatio(0)).toBe('Low');
  });

  it('classifies a node approaching capacity as Medium', () => {
    expect(riskFromUtilizationRatio(0.65)).toBe('Medium');
    expect(riskFromUtilizationRatio(0.9)).toBe('Medium');
  });

  it('classifies a node at or over capacity as High', () => {
    expect(riskFromUtilizationRatio(1)).toBe('High');
    // Real Alappuzha Mandi M1 baseline scenario overshoots to ~600% utilization —
    // this must never be silently clamped or misclassified as Medium.
    expect(riskFromUtilizationRatio(6.0031)).toBe('High');
  });

  it('treats the 0.65 and 1.0 boundaries as inclusive on the higher band', () => {
    expect(riskFromUtilizationRatio(0.649999)).toBe('Low');
    expect(riskFromUtilizationRatio(0.999999)).toBe('Medium');
  });
});

describe('riskFromCompositeScore', () => {
  it('classifies a low composite score as Low', () => {
    expect(riskFromCompositeScore(0)).toBe('Low');
    expect(riskFromCompositeScore(0.34)).toBe('Low');
  });

  it('classifies a mid composite score as Medium', () => {
    expect(riskFromCompositeScore(0.35)).toBe('Medium');
    expect(riskFromCompositeScore(0.64)).toBe('Medium');
  });

  it('classifies a high composite score as High', () => {
    expect(riskFromCompositeScore(0.65)).toBe('High');
    expect(riskFromCompositeScore(1)).toBe('High');
  });

  it('uses different cutoffs than riskFromUtilizationRatio (they are not interchangeable)', () => {
    // A composite score of 0.9 is High, but the same numeric value fed to the
    // utilization classifier as a ratio (90% of capacity) is only Medium.
    expect(riskFromCompositeScore(0.9)).toBe('High');
    expect(riskFromUtilizationRatio(0.9)).toBe('Medium');
  });
});
