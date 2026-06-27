import { useState } from 'react';

export default function ActionButton({ label, endpoint, method = 'POST', body, confirm: needsConfirm, onDone }) {
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  async function run() {
    if (needsConfirm && !window.confirm(`Confirmer : ${label} ?`)) return;
    setLoading(true);
    setMsg(null);
    try {
      const res = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await res.json();
      setMsg(data.message || data.error || (res.ok ? 'OK' : 'Erreur'));
      if (onDone) onDone(data);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setLoading(false);
      setTimeout(() => setMsg(null), 4000);
    }
  }

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', gap: 2 }}>
      <button
        onClick={run}
        disabled={loading}
        style={{
          background: '#2d3148', border: '1px solid #3d4468', borderRadius: 5,
          color: '#cbd5e1', padding: '4px 10px', fontSize: 12, cursor: loading ? 'wait' : 'pointer',
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? '…' : label}
      </button>
      {msg && <span style={{ fontSize: 11, color: '#94a3b8' }}>{msg}</span>}
    </div>
  );
}
