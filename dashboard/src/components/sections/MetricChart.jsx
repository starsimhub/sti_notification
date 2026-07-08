import {
  Bar, BarChart, CartesianGrid, Cell, ErrorBar, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const SOC_COLOR = '#555555';
const SOC_UNDER_COLOR = '#999999';
const SERIES_COLORS = { median: '#0E7490', over: '#B35806', under: '#2E86C1' };
const PALETTE = [
  '#0E7490', '#B35806', '#2E86C1', '#6A9F58', '#A6449B',
  '#C2871C', '#D6604D', '#4F6D7A', '#8C6D31', '#7570B3',
];

function paletteColor(index) {
  return PALETTE[index % PALETTE.length];
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

  if (mode === 'timeseries') {
    const years = Array.from(
      new Set(data.flatMap((row) => row.points.map((p) => p.year)))
    ).sort((a, b) => a - b);
    const chartData = years.map((year) => {
      const point = { year };
      data.forEach((row, i) => {
        const found = row.points.find((p) => p.year === year);
        point[`series_${i}`] = found ? found.value : null;
      });
      return point;
    });
    return (
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 16, right: 16, left: 48, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="year" tick={{ fontSize: 12 }} />
          <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <Tooltip formatter={(v) => (v == null ? '—' : v.toFixed(3))} />
          <Legend />
          {data.map((row, i) => (
            <Line
              key={row.label}
              type="monotone"
              dataKey={`series_${i}`}
              name={row.label}
              stroke={row.isSoc ? SOC_COLOR : paletteColor(i)}
              strokeWidth={row.isSoc ? 2.5 : 1.75}
              dot={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  const chartData = data.map((row) => ({
    label: row.label,
    isSoc: row.isSoc,
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
        <Bar dataKey="overMedian" name="Over-notification" maxBarSize={40}>
          {chartData.map((row) => (
            <Cell key={row.label} fill={row.isSoc ? SOC_COLOR : SERIES_COLORS.over} />
          ))}
          <ErrorBar dataKey="overRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
        <Bar dataKey="underMedian" name="Under-notification" maxBarSize={40}>
          {chartData.map((row) => (
            <Cell key={row.label} fill={row.isSoc ? SOC_UNDER_COLOR : SERIES_COLORS.under} />
          ))}
          <ErrorBar dataKey="underRange" width={4} strokeWidth={1.5} stroke="#333" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
