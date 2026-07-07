const METRICS = [
  { key: 'prevalence', label: 'Prevalence' },
  { key: 'new_inf', label: 'New infections' },
  { key: 'overtreatment', label: 'Overtreatment' },
  { key: 'notification', label: 'PN over/under-notification' },
];

export default function MetricTabs({ value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-2">
      {METRICS.map((m) => (
        <button
          key={m.key}
          onClick={() => onChange(m.key)}
          className={`px-3 py-1.5 text-sm rounded-md ${
            value === m.key ? 'bg-brand-teal text-white' : 'text-brand-gray hover:bg-brand-grayLight'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
