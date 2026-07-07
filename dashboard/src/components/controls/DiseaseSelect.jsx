const LABELS = { ng: 'Gonorrhoea', ct: 'Chlamydia', tv: 'Trichomoniasis', syph: 'Syphilis' };
const DISEASES = ['ng', 'ct', 'tv', 'syph'];

export default function DiseaseSelect({ value, onChange, disabled = false }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-brand-gray mr-1">Disease:</span>
      {DISEASES.map((d) => (
        <button
          key={d}
          disabled={disabled}
          onClick={() => onChange(d)}
          className={`px-3 py-1 rounded-full text-sm border-2 transition-colors ${
            disabled ? 'opacity-40 cursor-not-allowed border-gray-200 text-gray-400' :
            value === d ? 'bg-brand-teal border-brand-teal text-white' : 'border-brand-teal text-brand-teal'
          }`}
        >
          {LABELS[d]}
        </button>
      ))}
    </div>
  );
}
