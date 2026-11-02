// A horizontal bar showing value / max, with an optional marker (e.g. the unlock threshold).
export default function ProgressBar({ value, max, marker = null, label, small = false }) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  const markerPercent = max > 0 && marker !== null ? Math.min(100, (marker / max) * 100) : null;
  const reached = marker !== null && value >= marker;

  return (
    <div
      className={`progress ${small ? "progress-small" : ""}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <div className={`progress-fill ${reached ? "reached" : ""}`} style={{ width: `${percent}%` }} />
      {markerPercent !== null && <div className="progress-marker" style={{ left: `${markerPercent}%` }} />}
    </div>
  );
}
