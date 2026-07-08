import { describe, it, expect } from 'vitest';
import {
  quantile, medIqr, filterRows, getMetricValue,
  crossProductCombos, crossProductBarSeries, crossProductNotificationSeries, timeSeriesForCombos,
} from './dataTransforms.js';

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

describe('crossProductCombos', () => {
  it('returns the cartesian product of the three selected-level arrays', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['baseline', 'low'], bp: ['none'] });
    expect(combos).toHaveLength(2);
    expect(combos[0]).toMatchObject({ care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' });
    expect(combos[1]).toMatchObject({ care_level: 'baseline', pn_level: 'low', bp_level: 'none' });
  });
  it('gives each combo a distinct, stable label', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    expect(combos[0].label).toBe('baseline / low / none');
  });
});

describe('crossProductBarSeries', () => {
  it('prepends SOC, then one entry per combo', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low', 'moderate'], bp: ['none'] });
    const result = crossProductBarSeries(MOCK_ROWS, { combos, disease: 'ng', metric: 'prevalence' });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true, median: 0.11 });
    expect(result.find((r) => r.label === combos[0].label)).toMatchObject({ median: 0.08 });
    expect(result.find((r) => r.label === combos[1].label)).toMatchObject({ median: 0.06 });
  });
});

describe('crossProductNotificationSeries', () => {
  it('prepends SOC with over/under sub-series, then one entry per combo', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    const result = crossProductNotificationSeries(MOCK_ROWS, { combos });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true });
    expect(result[0].over.median).toBeCloseTo(0.55, 5);
    expect(result[1].under.median).toBe(0.2);
  });
});

const MOCK_TIMESERIES = [
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, disease: 'ng', metric: 'prevalence', year: 2027, value: 0.10 },
  { care_level: 'baseline', pn_level: 'baseline', bp_level: 'none', poc: false, disease: 'ng', metric: 'prevalence', year: 2028, value: 0.11 },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, disease: 'ng', metric: 'prevalence', year: 2027, value: 0.08 },
  { care_level: 'baseline', pn_level: 'low', bp_level: 'none', poc: true, disease: 'ng', metric: 'prevalence', year: 2028, value: 0.06 },
];

describe('timeSeriesForCombos', () => {
  it('returns SOC plus one entry per combo, each with year-sorted points', () => {
    const combos = crossProductCombos({ care: ['baseline'], pn: ['low'], bp: ['none'] });
    const result = timeSeriesForCombos(MOCK_TIMESERIES, { combos, disease: 'ng', metric: 'prevalence' });
    expect(result[0]).toMatchObject({ label: 'SOC', isSoc: true });
    expect(result[0].points).toEqual([{ year: 2027, value: 0.10 }, { year: 2028, value: 0.11 }]);
    expect(result[1].points).toEqual([{ year: 2027, value: 0.08 }, { year: 2028, value: 0.06 }]);
  });
});
