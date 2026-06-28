import { useEffect, useState } from 'react';

const s = {
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 },
  grid3: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 },
  card: { background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 10, padding: 20 },
  section: { fontSize: 12, fontWeight: 700, color: '#7c83ff', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em' },
  subsection: { fontSize: 11, fontWeight: 600, color: '#475569', marginBottom: 8, marginTop: 14, textTransform: 'uppercase', letterSpacing: '0.05em' },
  row: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '5px 0', borderBottom: '1px solid #1e2235' },
  label: { fontSize: 12, color: '#64748b' },
  value: { fontSize: 12, color: '#e2e8f0', fontWeight: 500 },
  dot: (on) => ({ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: on ? '#22c55e' : '#ef4444', boxShadow: on ? '0 0 5px #22c55e88' : 'none', marginRight: 5 }),
  badge: (type) => {
    const colors = { pass: '#22c55e', block: '#ef4444', reject: '#f59e0b' };
    return { display: 'inline-block', padding: '1px 7px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: (colors[type] || '#64748b') + '22', color: colors[type] || '#94a3b8', border: `1px solid ${(colors[type] || '#64748b')}44`, textTransform: 'uppercase' };
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', fontSize: 10, color: '#475569', padding: '5px 8px', borderBottom: '1px solid #2d3148', textTransform: 'uppercase', letterSpacing: '0.05em' },
  td: { fontSize: 11, color: '#cbd5e1', padding: '7px 8px', borderBottom: '1px solid #1e2235' },
  tdMono: { fontSize: 10, color: '#94a3b8', padding: '7px 8px', borderBottom: '1px solid #1e2235', fontFamily: 'monospace' },
  statBig: { fontSize: 26, fontWeight: 700, color: '#e2e8f0' },
  statRed: { fontSize: 26, fontWeight: 700, color: '#ef4444' },
  statSub: { fontSize: 11, color: '#475569', marginTop: 3 },
  barWrap: { flex: 1, height: 3, background: '#2d3148', borderRadius: 2, margin: '0 10px' },
  bar: (pct) => ({ height: 3, width: `${Math.min(pct, 100)}%`, background: '#ef4444', borderRadius: 2 }),
  sslGreen: { color: '#22c55e', fontSize: 11 },
  sslAmber: { color: '#f59e0b', fontSize: 11 },
  sslRed: { color: '#ef4444', fontSize: 11 },
  timestamp: { fontSize: 11, color: '#334155', marginBottom: 16 },
  spinner: { color: '#64748b', padding: 16, fontSize: 13 },
};

function SvcRow({ label, status }) {
  const on = status === true;
  return (
    <div style={s.row}>
      <span style={s.label}>{label}</span>
      <span style={s.value}><span style={s.dot(on)} />{on ? 'Running' : 'Stopped'}</span>
    </div>
  );
}

function SslDays({ days }) {
  if (days == null) return <span style={{ color: '#475569', fontSize: 11 }}>—</span>;
  const style = days > 30 ? s.sslGreen : days > 7 ? s.sslAmber : s.sslRed;
  return <span style={style}>{days}j</span>;
}

export default function NetworkPage() {
  const [data, setData] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const load = () =>
      fetch('/api/network')
        .then(r => r.json())
        .then(d => { setData(d); setLastUpdate(new Date().toLocaleTimeString('fr-BE')); });
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  if (!data) return <p style={s.spinner}>Chargement…</p>;

  const { pfsense, adguard, npm } = data;
  const wan = pfsense?.wan;
  const maxBlocked = adguard?.topBlocked?.[0]?.count || 1;

  return (
    <div>
      {lastUpdate && <p style={s.timestamp}>Mis à jour à {lastUpdate} — rafraîchi toutes les 60s</p>}

      {/* Row 1: pfSense + AdGuard stats */}
      <div style={s.grid2}>

        {/* pfSense */}
        <div style={s.card}>
          <div style={s.section}>🛡 pfSense</div>

          <div style={s.subsection}>WAN</div>
          {wan ? (
            <>
              <div style={s.row}><span style={s.label}>Statut</span><span style={s.value}><span style={s.dot(wan.status === 'online')} />{wan.status}</span></div>
              <div style={s.row}><span style={s.label}>IP publique</span><span style={{ ...s.value, fontFamily: 'monospace' }}>{wan.ip || '—'}</span></div>
              <div style={s.row}><span style={s.label}>Latence</span><span style={s.value}>{wan.delay || '—'}</span></div>
              <div style={s.row}><span style={s.label}>Perte paquets</span><span style={s.value}>{wan.loss || '—'}</span></div>
            </>
          ) : <p style={{ color: '#475569', fontSize: 12 }}>Indisponible</p>}

          <div style={s.subsection}>Services</div>
          <SvcRow label="DHCP (kea-dhcp4)" status={pfsense.services.dhcp} />
          <SvcRow label="WireGuard" status={pfsense.services.wireguard} />
          <SvcRow label="NTP (ntpd)" status={pfsense.services.ntp} />
          <SvcRow label="SSH (sshd)" status={pfsense.services.ssh} />

          {pfsense.wireguard?.length > 0 && (
            <>
              <div style={s.subsection}>WireGuard tunnels</div>
              {pfsense.wireguard.map(t => (
                <div key={t.name} style={s.row}>
                  <span style={s.label}>{t.name} — {t.description}</span>
                  <span style={s.value}><span style={s.dot(t.enabled)} />port {t.port} · {t.addresses.join(', ')}</span>
                </div>
              ))}
            </>
          )}
        </div>

        {/* AdGuard */}
        {adguard && (
          <div style={s.card}>
            <div style={s.section}>🛡 AdGuard Home</div>

            <div style={s.subsection}>Statistiques (24h)</div>
            <div style={s.row}><span style={s.label}>Requêtes DNS</span><span style={s.value}>{adguard.totalQueries.toLocaleString('fr-BE')}</span></div>
            <div style={s.row}><span style={s.label}>Bloquées</span><span style={{ ...s.value, color: '#ef4444' }}>{adguard.blockedQueries.toLocaleString('fr-BE')} ({adguard.blockRate}%)</span></div>
            <div style={s.row}><span style={s.label}>Protection</span><span style={s.value}><span style={s.dot(adguard.protectionEnabled)} />{adguard.protectionEnabled ? 'Active' : 'Désactivée'}</span></div>
            <div style={s.row}><span style={s.label}>Version</span><span style={s.value}>{adguard.version}</span></div>

            <div style={s.subsection}>Top domaines bloqués</div>
            {adguard.topBlocked.map((item, i) => (
              <div key={item.domain} style={{ display: 'flex', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #1e2235' }}>
                <span style={{ fontSize: 10, color: '#334155', width: 16, flexShrink: 0 }}>{i + 1}</span>
                <span style={{ fontSize: 11, color: '#cbd5e1', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.domain}</span>
                <div style={s.barWrap}><div style={s.bar((item.count / maxBlocked) * 100)} /></div>
                <span style={{ fontSize: 11, color: '#64748b', flexShrink: 0, fontVariantNumeric: 'tabular-nums' }}>{item.count.toLocaleString('fr-BE')}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Row 2: Firewall rules */}
      <div style={{ ...s.card, marginBottom: 16 }}>
        <div style={s.section}>🔥 Règles firewall pfSense ({pfsense.firewallRules.length})</div>
        <table style={s.table}>
          <thead>
            <tr>
              <th style={s.th}>Action</th>
              <th style={s.th}>Interface</th>
              <th style={s.th}>Description</th>
              <th style={s.th}>Proto</th>
              <th style={s.th}>Source</th>
              <th style={s.th}>Destination</th>
            </tr>
          </thead>
          <tbody>
            {pfsense.firewallRules.map((r, i) => (
              <tr key={i}>
                <td style={s.td}><span style={s.badge(r.action)}>{r.action}</span></td>
                <td style={s.tdMono}>{r.interface}</td>
                <td style={s.td}>{r.description || <span style={{ color: '#334155' }}>—</span>}</td>
                <td style={s.tdMono}>{r.protocol}</td>
                <td style={s.tdMono}>{r.source}</td>
                <td style={s.tdMono}>{r.destination}{r.destPort ? `:${r.destPort}` : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Row 3: NPM */}
      {npm && (
        <div style={s.card}>
          <div style={s.section}>🔀 Nginx Proxy Manager ({npm.hosts.length} hosts)</div>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Domaine(s)</th>
                <th style={s.th}>Forward</th>
                <th style={s.th}>SSL</th>
                <th style={s.th}>Cert expire</th>
              </tr>
            </thead>
            <tbody>
              {npm.hosts.map((h, i) => (
                <tr key={i} style={{ opacity: h.enabled ? 1 : 0.4 }}>
                  <td style={s.td}>{h.domains.join(', ')}</td>
                  <td style={s.tdMono}>{h.forwardHost}:{h.forwardPort}</td>
                  <td style={s.td}>{h.cert ? h.cert.name : <span style={{ color: '#334155' }}>—</span>}</td>
                  <td style={s.td}><SslDays days={h.cert?.daysLeft} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
