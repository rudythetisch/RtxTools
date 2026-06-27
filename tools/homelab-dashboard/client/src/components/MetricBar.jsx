export default function MetricBar({ label, value }) {
  if (value === null || value === undefined) return (
    <div style={{ fontSize: 11, color: '#475569' }}>{label}: —</div>
  );
  const pct = parseFloat(value);
  const color = pct > 85 ? '#ef4444' : pct > 60 ? '#f59e0b' : '#22c55e';
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>
        <span>{label}</span><span>{pct.toFixed(0)}%</span>
      </div>
      <div style={{ background: '#1e2235', borderRadius: 3, height: 4, overflow: 'hidden' }}>
        <div style={{ width: `${Math.min(pct, 100)}%`, background: color, height: '100%', transition: 'width 0.5s' }} />
      </div>
    </div>
  );
}
