import { useEffect, useState } from 'react';
import MetricBar from '../components/MetricBar.jsx';
import ActionButton from '../components/ActionButton.jsx';

const TYPE_ICON = { server: '🖥', nas: '🗄', firewall: '🛡', default: '📦' };

const s = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginBottom: 32 },
  card: { background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 10, padding: 16 },
  cardHeader: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 },
  badge: (online) => ({
    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
    background: online === undefined ? '#475569' : online ? '#22c55e' : '#ef4444',
    boxShadow: online ? '0 0 6px #22c55e88' : 'none',
  }),
  name: { fontWeight: 600, fontSize: 14, color: '#e2e8f0' },
  ip: { fontSize: 11, color: '#475569', marginTop: 1 },
  section: { fontSize: 12, fontWeight: 600, color: '#7c83ff', marginBottom: 10, marginTop: 16 },
  actions: { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 },
  timestamp: { fontSize: 11, color: '#334155', marginBottom: 16 },
};

export default function StatusPage() {
  const [data, setData] = useState(null);
  const [inventory, setInventory] = useState({ devices: [], services: [] });
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetch('/api/inventory').then(r => r.json()).then(setInventory);
  }, []);

  useEffect(() => {
    const es = new EventSource('/api/status/stream');
    es.onmessage = (e) => {
      setData(JSON.parse(e.data));
      setLastUpdate(new Date().toLocaleTimeString('fr-BE'));
    };
    return () => es.close();
  }, []);

  const deviceStatus = (id) => data?.devices?.[id] || {};
  const serviceStatus = (id) => data?.services?.[id] || {};

  return (
    <div>
      {lastUpdate && <div style={s.timestamp}>Dernière mise à jour : {lastUpdate} (polling 30s)</div>}

      <div style={s.section}>APPAREILS</div>
      <div style={s.grid}>
        {inventory.devices.map(device => {
          const st = deviceStatus(device.id);
          const icon = TYPE_ICON[device.type] || TYPE_ICON.default;
          return (
            <div key={device.id} style={s.card}>
              <div style={s.cardHeader}>
                <div style={s.badge(st.online)} />
                <div>
                  <div style={s.name}>{icon} {device.name}</div>
                  <div style={s.ip}>
                    {device.hostname ? (
                      <a href={`https://${device.hostname}`} target="_blank" rel="noreferrer"
                        style={{ color: '#475569', textDecoration: 'none' }}>{device.hostname}</a>
                    ) : device.ip}
                    {' · '}{st.online === undefined ? '…' : st.online ? 'En ligne' : 'Hors ligne'}
                  </div>
                  {device.hostname && <div style={{ ...s.ip, fontSize: 10 }}>{device.ip}</div>}
                </div>
              </div>
              <MetricBar label="CPU" value={st.cpu} />
              <MetricBar label="RAM" value={st.mem} />
              {device.type !== 'firewall' && (
                <>
                  <MetricBar label="Disk" value={st.disk} />
                  {st.diskUsedTB && (
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                      {st.diskUsedTB} To / {st.diskTotalTB} To utilisés
                    </div>
                  )}
                </>
              )}
              {device.id === 'pfsense' && (
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
                  WAN: <span style={{ color: st.wanStatus === 'online' ? '#22c55e' : '#f59e0b' }}>{st.wanStatus || '—'}</span>
                  {st.wanIp && ` · ${st.wanIp}`}
                  {st.wanDelay && ` · ${st.wanDelay}`}
                  {st.wanLoss != null && ` · perte ${st.wanLoss}`}
                </div>
              )}
              <div style={s.actions}>
                {device.actions?.includes('shutdown') && (
                  <ActionButton
                    label="Shutdown"
                    endpoint={`/api/actions/shutdown/${device.id}`}
                    confirm
                  />
                )}
                {device.actions?.includes('wol') && device.mac && (
                  <ActionButton
                    label="Wake (WoL)"
                    endpoint={`/api/actions/wol/${device.id}`}
                    body={{ mac: device.mac }}
                    confirm
                  />
                )}
                {device.actions?.includes('release-wan') && (
                  <ActionButton
                    label="Release WAN"
                    endpoint="/api/actions/release-wan"
                    confirm
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div style={s.section}>SERVICES LXC</div>
      <div style={s.grid}>
        {inventory.services.map(service => {
          const st = serviceStatus(service.id);
          return (
            <div key={service.id} style={s.card}>
              <div style={s.cardHeader}>
                <div style={s.badge(st.online)} />
                <div>
                  <div style={s.name}>📦 {service.name}</div>
                  <div style={s.ip}>
                    {service.hostname ? (
                      <a href={`https://${service.hostname}`} target="_blank" rel="noreferrer"
                        style={{ color: '#475569', textDecoration: 'none' }}>{service.hostname}</a>
                    ) : `${service.ip}:${service.port}`}
                    {' · '}{st.online === undefined ? '…' : st.online ? 'En ligne' : 'Hors ligne'}
                  </div>
                  {service.hostname && <div style={{ ...s.ip, fontSize: 10 }}>{service.ip}:{service.port}</div>}
                </div>
              </div>
              <MetricBar label="CPU" value={st.cpu} />
              <MetricBar label="RAM" value={st.mem} />
              {service.url && (
                <div style={{ marginTop: 8 }}>
                  <a href={service.url} target="_blank" rel="noreferrer"
                    style={{ fontSize: 11, color: '#7c83ff', textDecoration: 'none' }}>
                    Ouvrir →
                  </a>
                </div>
              )}
              <div style={s.actions}>
                {service.lxcId && st.online === false && (
                  <ActionButton label="Start" endpoint={`/api/actions/lxc/${service.lxcId}/start`} />
                )}
                {service.lxcId && st.online === true && (
                  <ActionButton label="Stop" endpoint={`/api/actions/lxc/${service.lxcId}/stop`} confirm />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
