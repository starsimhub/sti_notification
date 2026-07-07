export function quantile(sortedArr, q) {
  const pos = (sortedArr.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sortedArr[base + 1] !== undefined) {
    return sortedArr[base] + rest * (sortedArr[base + 1] - sortedArr[base]);
  }
  return sortedArr[base];
}

export function medIqr(values) {
  const nums = values.filter((v) => v !== null && v !== undefined && !Number.isNaN(v))
    .slice().sort((a, b) => a - b);
  if (nums.length === 0) return { median: null, p25: null, p75: null };
  return {
    median: quantile(nums, 0.5),
    p25: quantile(nums, 0.25),
    p75: quantile(nums, 0.75),
  };
}

export function filterRows(scenarios, filters) {
  return scenarios.filter((row) =>
    Object.entries(filters).every(([key, value]) => value === undefined || row[key] === value)
  );
}

export function getMetricValue(row, { disease, metric }) {
  const d = row.diseases[disease];
  if (!d) return null;
  switch (metric) {
    case 'prevalence': return d.prev_end;
    case 'new_inf': return d.new_inf;
    case 'overtreatment': return d.overtreatment_rate;
    default: throw new Error(`Unknown metric: ${metric}`);
  }
}

const AXIS_TO_FIELD = { care: 'care_level', pn: 'pn_level', bp: 'bp_level' };

export function groupedSeries(scenarios, { varyAxis, disease, metric, fixed, levels }) {
  const varyField = AXIS_TO_FIELD[varyAxis];
  const socRows = filterRows(scenarios, { poc: false });
  const soc = medIqr(socRows.map((r) => getMetricValue(r, { disease, metric })));
  const entries = levels.map((level) => {
    const rows = filterRows(scenarios, { poc: true, [varyField]: level, ...fixed });
    const stats = medIqr(rows.map((r) => getMetricValue(r, { disease, metric })));
    return { label: level, isSoc: false, ...stats };
  });
  return [{ label: 'SOC', isSoc: true, ...soc }, ...entries];
}

export function notificationSeries(scenarios, { varyAxis, fixed, levels }) {
  const varyField = AXIS_TO_FIELD[varyAxis];
  const socRows = filterRows(scenarios, { poc: false });
  const socOver = medIqr(socRows.map((r) => r.notification.over_notification_rate));
  const socUnder = medIqr(socRows.map((r) => r.notification.under_notification_rate));
  const entries = levels.map((level) => {
    const rows = filterRows(scenarios, { poc: true, [varyField]: level, ...fixed });
    return {
      label: level,
      isSoc: false,
      over: medIqr(rows.map((r) => r.notification.over_notification_rate)),
      under: medIqr(rows.map((r) => r.notification.under_notification_rate)),
    };
  });
  return [{ label: 'SOC', isSoc: true, over: socOver, under: socUnder }, ...entries];
}
