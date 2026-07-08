export default function PresetToggleGroup({ presets, selected, onChange }) {
  function toggle(key) {
    if (selected.includes(key)) {
      if (selected.length === 1) return;
      onChange(selected.filter((k) => k !== key));
    } else {
      onChange([...selected, key]);
    }
  }
  return (
    <div className="flex items-center gap-3 flex-wrap mb-4">
      {presets.map(({ key, label }) => (
        <label
          key={key}
          className="flex items-center gap-1.5 text-sm text-brand-gray cursor-pointer"
        >
          <input
            type="checkbox"
            checked={selected.includes(key)}
            onChange={() => toggle(key)}
            className="accent-brand-blue"
          />
          {label}
        </label>
      ))}
    </div>
  );
}
