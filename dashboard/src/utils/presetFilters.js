export function filterPresetSeries(series, presets, selectedKeys) {
  const selectedLabels = new Set(
    presets.filter((p) => selectedKeys.includes(p.key)).map((p) => p.label)
  );
  return series.filter((s) => selectedLabels.has(s.label));
}
