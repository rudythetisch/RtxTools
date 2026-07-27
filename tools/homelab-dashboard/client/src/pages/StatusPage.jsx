import { useEffect, useState } from 'react';
import MetricBar from '../components/MetricBar.jsx';
import ActionButton from '../components/ActionButton.jsx';

const TYPE_ICON = { server: '🖥', nas: '🗄', firewall: '🛡', ap: '📡', client: '💻', default: '📦' };

const FAMILY_LABEL = {
  infra: 'INFRASTRUCTURE',
  network: 'RÉSEAU & WI-FI',
  iot: 'IOT & DOMOTIQUE',
  appliances: 'ÉLECTROMÉNAGER',
  media: 'MÉDIA & DIVERTISSEMENT',
  clients: 'APPAREILS CLIENTS',
};

const SI = 'https://cdn.simpleicons.org';
const FAV = (domain) => `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;

// [url, isMonochrome] — Simple Icons need brightness invert, favicons don't
const DEVICE_LOGO = {
  nipogi:               [SI + '/proxmox/slate',       true],
  pfsense:              [SI + '/pfsense/slate',        true],
  haos:                 [SI + '/homeassistant/slate',  true],
  tischnas2:            [SI + '/synology/slate',       true],
  tischnas3:            [SI + '/synology/slate',       true],
  'deco-salon':         [SI + '/tp-link/slate',        true],
  'deco-mezzanine':     [SI + '/tp-link/slate',        true],
  'deco-grenier':       [SI + '/tp-link/slate',        true],
  'cpl-tplink':         [SI + '/tp-link/slate',        true],
  'cpl-pa7017p':        [SI + '/tp-link/slate',        true],
  'neato-router':       [SI + '/tp-link/slate',        true],
  nhc2:                 [FAV('niko.eu'),                false],
  'homewizard-p1':      [FAV('homewizard.com'),         false],
  'smlight-slzb06':     [FAV('smlight.tech'),           false],
  netatmo:              [FAV('netatmo.com'),             false],
  'tado-ac-1':          [FAV('tado.com'),               false],
  'tado-ac-2':          [FAV('tado.com'),               false],
  'meross-plug-1':      [FAV('meross.com'),             false],
  'meross-plug-2':      [FAV('meross.com'),             false],
  'meross-plug-3':      [FAV('meross.com'),             false],
  'eufy-doorbell':      [FAV('eufylife.com'),           false],
  'eufy-cam-mezzanine': [FAV('eufylife.com'),           false],
  'eufy-cam-cuisine':   [FAV('eufylife.com'),           false],
  'dreame-vacuum':      [FAV('dreame.tech'),            false],
  'dreame-mower':       [FAV('dreame.tech'),            false],
  'bosch-lavelinge':    [FAV('bosch-home.com'),         false],
  'bosch-lavevaisselle':[FAV('bosch-home.com'),         false],
  'lg-tv-c1':           [SI + '/lg/slate',              true],
  'philips-soundbar':   [FAV('philips.com'),            false],
  'appletv-salon':      [SI + '/apple/slate',           true],
  'nintendo-switch':    [SI + '/nintendo/slate',        true],
  macmini:              [SI + '/apple/slate',           true],
  'macbook-celine':     [SI + '/apple/slate',           true],
  'mac-unknown':        [SI + '/apple/slate',           true],
  'ipad-air-13-m3':     [SI + '/apple/slate',           true],
  'ipad-5gen':          [SI + '/apple/slate',           true],
  'iphone-rudy':        [SI + '/apple/slate',           true],
  'iphone-elias':       [SI + '/apple/slate',           true],
  'iphone-tristan':     [SI + '/apple/slate',           true],
  'samsung-a54-celine': [SI + '/samsung/slate',         true],
};

function DeviceLogo({ id, type }) {
  const entry = DEVICE_LOGO[id];
  const [err, setErr] = useState(false);
  if (!entry || err) {
    const emoji = TYPE_ICON[type] || TYPE_ICON.default;
    return <span style={{ fontSize: 20, lineHeight: 1 }}>{emoji}</span>;
  }
  const [src, mono] = entry;
  return <img src={src} alt="" width={22} height={22} onError={() => setErr(true)}
    style={{ opacity: mono ? 0.6 : 0.85, filter: mono ? 'brightness(0) invert(1)' : 'none', flexShrink: 0 }} />;
}

const ipToNum = ip => ip ? ip.split('.').reduce((n, oct) => n * 256 + parseInt(oct, 10), 0) : 0;

function groupByFamily(devices) {
  const order = ['infra', 'network', 'iot', 'appliances', 'media', 'clients'];
  const groups = {};
  for (const d of devices) {
    const f = d.family || 'other';
    if (!groups[f]) groups[f] = [];
    groups[f].push(d);
  }
  return order.filter(f => groups[f]).map(f => ({
    family: f,
    devices: groups[f].slice().sort((a, b) => ipToNum(a.ip) - ipToNum(b.ip)),
  }));
}

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
  const [hiddenFamilies, setHiddenFamilies] = useState(new Set());

  const toggleFamily = (f) => setHiddenFamilies(prev => {
    const next = new Set(prev);
    next.has(f) ? next.delete(f) : next.add(f);
    return next;
  });

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

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {groupByFamily(inventory.devices).map(({ family }) => (
          <button key={family} onClick={() => toggleFamily(family)} style={{
            padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer',
            border: '1px solid', transition: 'all 0.15s',
            background: hiddenFamilies.has(family) ? 'transparent' : '#7c83ff22',
            borderColor: hiddenFamilies.has(family) ? '#334155' : '#7c83ff',
            color: hiddenFamilies.has(family) ? '#475569' : '#7c83ff',
          }}>
            {hiddenFamilies.has(family) ? '○' : '●'} {FAMILY_LABEL[family] || family}
          </button>
        ))}
      </div>

      {groupByFamily(inventory.devices).map(({ family, devices }) => hiddenFamilies.has(family) ? null : ( // eslint-disable-line
        <div key={family}>
          <div style={s.section}>{FAMILY_LABEL[family] || family.toUpperCase()}</div>
          <div style={s.grid}>
            {devices.map(device => {
              const st = deviceStatus(device.id);
              const icon = TYPE_ICON[device.type] || TYPE_ICON.default;
              return (
                <div key={device.id} style={s.card}>
                  <div style={s.cardHeader}>
                    <div style={s.badge(st.online)} />
                    <DeviceLogo id={device.id} type={device.type} />
                    <div>
                      <div style={s.name}>{device.name}</div>
                      <div style={s.ip}>
                        {device.hostname ? (
                          <a href={`https://${device.hostname}`} target="_blank" rel="noreferrer"
                            style={{ color: '#475569', textDecoration: 'none' }}>{device.hostname}</a>
                        ) : device.ip || '—'}
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
                      <ActionButton label="Shutdown" endpoint={`/api/actions/shutdown/${device.id}`} confirm />
                    )}
                    {device.actions?.includes('wol') && device.mac && (
                      <ActionButton label="Wake (WoL)" endpoint={`/api/actions/wol/${device.id}`} body={{ mac: device.mac }} confirm />
                    )}
                    {device.actions?.includes('release-wan') && (
                      <ActionButton label="Release WAN" endpoint="/api/actions/release-wan" confirm />
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {renderServiceSection('SERVICES LXC', inventory.services.filter(s2 => s2.lxcId), serviceStatus)}
      {renderServiceSection('SERVICES DOCKER (NAS)', inventory.services.filter(s2 => !s2.lxcId && s2.dockerContainer), serviceStatus)}
    </div>
  );
}

function renderServiceCard(service, st) {
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
}

function renderServiceSection(title, services, serviceStatus) {
  if (!services.length) return null;
  return (
    <>
      <div style={s.section}>{title}</div>
      <div style={s.grid}>
        {services.map(service => renderServiceCard(service, serviceStatus(service.id)))}
      </div>
    </>
  );
}
