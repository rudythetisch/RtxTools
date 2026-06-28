import { useEffect, useState } from 'react';

const s = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 32 },
  stat: { background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 10, padding: 20 },
  statLabel: { fontSize: 12, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' },
  statValue: { fontSize: 28, fontWeight: 700, color: '#e2e8f0' },
  statSub: { fontSize: 11, color: '#475569', marginTop: 4 },
  section: { fontSize: 12, fontWeight: 600, color: '#7c83ff', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.05em' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', fontSize: 11, color: '#64748b', padding: '6px 10px', borderBottom: '1px solid #2d3148' },
  td: { fontSize: 13, color: '#e2e8f0', padding: '8px 10px', borderBottom: '1px solid #1e2235' },
  tdCount: { textAlign: 'right', fontSize: 13, color: '#94a3b8', padding: '8px 10px', borderBottom: '1px solid #1e2235', fontVariantNumeric: 'tabular-nums' },
  bar: (pct) => ({
    display: 'inline-block', height: 4, width: `${pct}%`, maxWidth: '100%',
    background: '#ef4444', borderRadius: 2, verticalAlign: 'middle', marginLeft: 8,
  }),
  statusDot: (on) => ({
    display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
    background: on ? '#22c55e' : '#ef4444',
    boxShadow: on ? '0 0 6px #22c55e88' : 'none',
    marginRight: 6,
  }),
  card: { background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 10, padding: 20 },
  timestamp: { fontSize: 11, color: '#334155', marginBottom: 16 },
  error: { color: '#ef4444', fontSize: 13, padding: 16 },
};

export default function AdGuardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const load = () =>
      fetch('/api/adguard')
        .then(r => r.json())
        .then(d => { setData(d); setError(null); setLastUpdate(new Date().toLocaleTimeString('fr-BE')); })
        .catch(e => setError(e.message));

    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  if (error) return <p style={s.error}>Erreur : {error}</p>;
  if (!data) return <p style={{ color: '#64748b', padding: 16 }}>Chargement…</p>;

  const maxCount = data.topBlocked[0]?.count || 1;

  return (
    <div>
      {lastUpdate && <p style={s.timestamp}>Mis à jour à {lastUpdate} — rafraîchi toutes les 60s</p>}

      <div style={s.grid}>
        <div style={s.stat}>
          <div style={s.statLabel}>Requêtes DNS</div>
          <div style={s.statValue}>{data.totalQueries.toLocaleString('fr-BE')}</div>
          <div style={s.statSub}>dernières 24h</div>
        </div>
        <div style={s.stat}>
          <div style={s.statLabel}>Requêtes bloquées</div>
          <div style={{ ...s.statValue, color: '#ef4444' }}>{data.blockedQueries.toLocaleString('fr-BE')}</div>
          <div style={s.statSub}>{data.blockRate}% du total</div>
        </div>
        <div style={s.stat}>
          <div style={s.statLabel}>Protection</div>
          <div style={{ ...s.statValue, fontSize: 16, paddingTop: 6 }}>
            <span style={s.statusDot(data.protectionEnabled)} />
            {data.protectionEnabled ? 'Active' : 'Désactivée'}
          </div>
          <div style={s.statSub}>{data.version}</div>
        </div>
      </div>

      <div style={s.card}>
        <div style={s.section}>Top domaines bloqués</div>
        <table style={s.table}>
          <thead>
            <tr>
              <th style={s.th}>#</th>
              <th style={s.th}>Domaine</th>
              <th style={{ ...s.th, textAlign: 'right' }}>Requêtes</th>
            </tr>
          </thead>
          <tbody>
            {data.topBlocked.map((item, i) => (
              <tr key={item.domain}>
                <td style={{ ...s.td, color: '#475569', width: 30 }}>{i + 1}</td>
                <td style={s.td}>
                  {item.domain}
                  <span style={s.bar((item.count / maxCount) * 100)} />
                </td>
                <td style={s.tdCount}>{item.count.toLocaleString('fr-BE')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
