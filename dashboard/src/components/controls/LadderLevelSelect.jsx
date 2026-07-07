export default function LadderLevelSelect({ label, levels, value, onChange, labels }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-brand-gray mr-1">{label}:</span>
      {levels.map((level) => (
        <button
          key={level}
          onClick={() => onChange(level)}
          className={`px-3 py-1 rounded-full text-sm border-2 transition-colors ${
            labels?.[level] ? '' : 'capitalize'
          } ${
            value === level ? 'bg-brand-blue border-brand-blue text-white' : 'border-brand-blue text-brand-blue'
          }`}
        >
          {labels?.[level] ?? level}
        </button>
      ))}
    </div>
  );
}
