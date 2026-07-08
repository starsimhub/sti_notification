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

export function crossProductCombos(selectedLevels) {
  const combos = [];
  for (const care of selectedLevels.care) {
    for (const pn of selectedLevels.pn) {
      for (const bp of selectedLevels.bp) {
        combos.push({
          care_level: care,
          pn_level: pn,
          bp_level: bp,
          label: `${care} / ${pn} / ${bp}`,
        });
      }
    }
  }
  return combos;
}

export function crossProductBarSeries(scenarios, { combos, disease, metric }) {
  const socRows = filterRows(scenarios, { poc: false });
  const soc = medIqr(socRows.map((r) => getMetricValue(r, { disease, metric })));
  const entries = combos.map((combo) => {
    const rows = filterRows(scenarios, {
      poc: true,
      care_level: combo.care_level,
      pn_level: combo.pn_level,
      bp_level: combo.bp_level,
    });
    const stats = medIqr(rows.map((r) => getMetricValue(r, { disease, metric })));
    return { label: combo.label, isSoc: false, ...stats };
  });
  return [{ label: 'SOC', isSoc: true, ...soc }, ...entries];
}

export function crossProductNotificationSeries(scenarios, { combos }) {
  const socRows = filterRows(scenarios, { poc: false });
  const socOver = medIqr(socRows.map((r) => r.notification.over_notification_rate));
  const socUnder = medIqr(socRows.map((r) => r.notification.under_notification_rate));
  const entries = combos.map((combo) => {
    const rows = filterRows(scenarios, {
      poc: true,
      care_level: combo.care_level,
      pn_level: combo.pn_level,
      bp_level: combo.bp_level,
    });
    return {
      label: combo.label,
      isSoc: false,
      over: medIqr(rows.map((r) => r.notification.over_notification_rate)),
      under: medIqr(rows.map((r) => r.notification.under_notification_rate)),
    };
  });
  return [{ label: 'SOC', isSoc: true, over: socOver, under: socUnder }, ...entries];
}

export function timeSeriesForCombos(timeseries, { combos, disease, metric }) {
  const byYear = (a, b) => a.year - b.year;
  const socPoints = timeseries
    .filter((r) => r.poc === false && r.disease === disease && r.metric === metric)
    .sort(byYear)
    .map((r) => ({ year: r.year, value: r.value }));
  const entries = combos.map((combo) => {
    const points = timeseries
      .filter((r) =>
        r.poc === true &&
        r.disease === disease &&
        r.metric === metric &&
        r.care_level === combo.care_level &&
        r.pn_level === combo.pn_level &&
        r.bp_level === combo.bp_level
      )
      .sort(byYear)
      .map((r) => ({ year: r.year, value: r.value }));
    return { label: combo.label, isSoc: false, points };
  });
  return [{ label: 'SOC', isSoc: true, points: socPoints }, ...entries];
}
