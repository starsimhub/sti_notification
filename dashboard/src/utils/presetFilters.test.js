import { describe, it, expect } from 'vitest';
import { filterPresetSeries } from './presetFilters.js';

const PRESETS = [
  { key: 'soc', label: 'SOC' },
  { key: 'poc', label: 'POC alone', care_level: 'baseline', pn_level: 'baseline', bp_level: 'none' },
  { key: 'pn_high', label: 'POC + PN high', care_level: 'baseline', pn_level: 'high', bp_level: 'none' },
];

const SERIES = [
  { label: 'SOC', isSoc: true, median: 0.1 },
  { label: 'POC alone', isSoc: false, median: 0.08 },
  { label: 'POC + PN high', isSoc: false, median: 0.05 },
];

describe('filterPresetSeries', () => {
  it('returns only the series entries whose label matches a selected preset key', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['soc', 'pn_high']);
    expect(result).toEqual([
      { label: 'SOC', isSoc: true, median: 0.1 },
      { label: 'POC + PN high', isSoc: false, median: 0.05 },
    ]);
  });

  it('preserves the original series order, not the order keys were selected in', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['pn_high', 'soc']);
    expect(result.map((r) => r.label)).toEqual(['SOC', 'POC + PN high']);
  });

  it('returns an empty array when no keys are selected', () => {
    expect(filterPresetSeries(SERIES, PRESETS, [])).toEqual([]);
  });

  it('returns all entries when all keys are selected', () => {
    const result = filterPresetSeries(SERIES, PRESETS, ['soc', 'poc', 'pn_high']);
    expect(result).toHaveLength(3);
  });
});
