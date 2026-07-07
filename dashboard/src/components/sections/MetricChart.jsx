import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts';

const SOC_COLOR = '#555555';
const SERIES_COLORS = { median: '#0E7490', over: '#B35806', under: '#2E86C1' };

function withErrorBar(row, key) {
  const lo = row[`${key}`]?.p25 ?? row.p25;
  const hi = row[`${key}`]?.p75 ?? row.p75;
  const med = row[`${key}`]?.median ?? row.median;
  return { median: med, errorRange: med == null || lo == null || hi == null ? null : [med - lo, hi - med] };
}

export default function MetricChart({ data, mode = 'single', yLabel }) {
  if (mode === 'single') {
    const chartData = data.map((row) => ({
      label: row.label,
      isSoc: row.isSoc,
      median: row.median,
      errorRange: row.median == null || row.p25 == null || row.p75 == null
        ? null : [row.median - row.p25, row.p75 - row.median],
    }));
    return (
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
          <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
          <Bar dataKey="median" maxBarSize={60}>
            {chartData.map((row) => <Cell key={row.label} fill={row.isSoc ? SOC_COLOR : SERIES_COLORS.median} />)}
            <ErrorBar dataKey="errorRange" width={4} strokeWidth={1.5} stroke="#333" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  const chartData = data.map((row) => ({
    label: row.label,
    isSoc: row.isSoc,
    ...withErrorBar(row, 'over'),
    overMedian: row.over.median,
    overRange: row.over.median == null || row.over.p25 == null || row.over.p75 == null
      ? null : [row.over.median - row.over.p25, row.over.p75 - row.over.median],
    underMedian: row.under.median,
    underRange: row.under.median == null || row.under.p25 == null || row.under.p75 == null
      ? null : [row.under.median - row.under.p25, row.under.p75 - row.under.median],
  }));

  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
        <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
        <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
        <Legend />
        <Bar dataKey="overMedian" name="Over-notification" fill={SERIES_COLORS.over} maxBarSize={40}>
          <ErrorBar dataKey="overRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
        <Bar dataKey="underMedian" name="Under-notification" fill={SERIES_COLORS.under} maxBarSize={40}>
          <ErrorBar dataKey="underRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
