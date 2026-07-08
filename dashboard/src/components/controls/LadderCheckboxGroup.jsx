export default function LadderCheckboxGroup({ label, levels, selected, onChange }) {
  function toggle(level) {
    if (selected.includes(level)) {
      if (selected.length === 1) return;
      onChange(selected.filter((l) => l !== level));
    } else {
      onChange([...selected, level]);
    }
  }
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <span className="text-sm font-medium text-brand-gray mr-1">{label}:</span>
      {levels.map((level) => (
        <label
          key={level}
          className="flex items-center gap-1.5 text-sm text-brand-gray capitalize cursor-pointer"
        >
          <input
            type="checkbox"
            checked={selected.includes(level)}
            onChange={() => toggle(level)}
            className="accent-brand-blue"
          />
          {level}
        </label>
      ))}
    </div>
  );
}
