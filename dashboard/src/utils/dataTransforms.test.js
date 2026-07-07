import { describe, it, expect } from 'vitest';
import { quantile, medIqr, filterRows, getMetricValue, groupedSeries, notificationSeries } from './dataTransforms.js';

describe('quantile', () => {
  it('returns the median for q=0.5 on an odd-length array', () => {
    expect(quantile([1, 2, 3, 4, 5], 0.5)).toBe(3);
  });
  it('interpolates between points for q not landing exactly on an index', () => {
    expect(quantile([1, 2, 3, 4], 0.25)).toBeCloseTo(1.75, 5);
  });
});

describe('medIqr', () => {
  it('computes median/p25/p75 over numeric values, ignoring nulls', () => {
    const result = medIqr([1, 2, 3, 4, 5, null, undefined]);
    expect(result.median).toBe(3);
    expect(result.p25).toBeCloseTo(2, 5);
    expect(result.p75).toBeCloseTo(4, 5);
  });
  it('returns nulls for an empty or all-null input', () => {
    expect(medIqr([null, null])).toEqual({ median: null, p25: null, p75: null });
  });
});

const MOCK_ROWS = [
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, draw: 1,
    diseases: { ng: { prev_end: 0.10, new_inf: 100, overtreatment_rate: 0.5 } },
    notification: { over_notification_rate: 0.5, under_notification_rate: 0.3 } },
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, draw: 2,
    diseases: { ng: { prev_end: 0.12, new_inf: 110, overtreatment_rate: 0.6 } },
    notification: { over_notification_rate: 0.6, under_notification_rate: 0.4 } },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.08, new_inf: 90, overtreatment_rate: 0.3 } },
    notification: { over_notification_rate: 0.3, under_notification_rate: 0.2 } },
  { care_level: 'baseline', pn_level: 'moderate', bp_level: 'none', poc: true, draw: 1,
    diseases: { ng: { prev_end: 0.06, new_inf: 80, overtreatment_rate: 0.2 } },
    notification: { over_notification_rate: 0.2, under_notification_rate: 0.1 } },
];

describe('filterRows', () => {
  it('filters on the given keys only, leaving omitted keys unconstrained', () => {
    expect(filterRows(MOCK_ROWS, { poc: false }).length).toBe(2);
    expect(filterRows(MOCK_ROWS, { poc: true, pn_level: 'low' }).length).toBe(1);
  });
});

describe('getMetricValue', () => {
  it('reads the prevalence field for a disease', () => {
    expect(getMetricValue(MOCK_ROWS[0], { disease: 'ng', metric: 'prevalence' })).toBe(0.10);
  });
  it('reads the overtreatment rate for a disease', () => {
    expect(getMetricValue(MOCK_ROWS[0], { disease: 'ng', metric: 'overtreatment' })).toBe(0.5);
  });
});

describe('groupedSeries', () => {
  it('prepends a SOC entry, then one entry per level of the varying axis', () => {
    const result = groupedSeries(MOCK_ROWS, {
      varyAxis: 'pn', disease: 'ng', metric: 'prevalence',
      fixed: { care_level: 'baseline', bp_level: 'none' },
      levels: ['baseline', 'low', 'moderate', 'high'],
    });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true, median: 0.11 });
    expect(result.find(r => r.label === 'low')).toMatchObject({ median: 0.08 });
    expect(result.find(r => r.label === 'moderate')).toMatchObject({ median: 0.06 });
    // 'high' has no matching rows in the mock data -> median null, not thrown
    expect(result.find(r => r.label === 'high')).toMatchObject({ median: null });
  });
});

describe('notificationSeries', () => {
  it('returns SOC plus one entry per level, each with over and under sub-series', () => {
    const result = notificationSeries(MOCK_ROWS, {
      varyAxis: 'pn',
      fixed: { care_level: 'baseline', bp_level: 'none' },
      levels: ['baseline', 'low', 'moderate', 'high'],
    });
    expect(result[0].label).toBe('SOC');
    expect(result[0].over.median).toBeCloseTo(0.55, 5);
    expect(result.find(r => r.label === 'low').under.median).toBe(0.2);
  });
});
