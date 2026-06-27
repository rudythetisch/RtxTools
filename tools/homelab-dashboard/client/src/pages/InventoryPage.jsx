import { useEffect, useState } from 'react';

const DEVICE_TYPES = ['server', 'nas', 'firewall', 'router', 'switch', 'workstation', 'other'];
const IP_TYPES = ['static', 'dhcp', 'dhcp-reserved'];
const EMPTY_DEVICE = { name: '', type: 'server', ip: '', ipType: 'static', hostname: '', mac: '', specs: '', role: '', sshUser: '', purchasedAt: '', config: '', notes: '', actions: [] };
const EMPTY_SERVICE = { name: '', lxcId: '', ip: '', ipType: 'dhcp', hostname: '', mac: '', port: '', url: '', role: '', installedAt: '', version: '', installScript: '', notes: '' };

const s = {
  section: { fontSize: 12, fontWeight: 600, color: '#7c83ff', marginBottom: 12, marginTop: 24 },
  table: { width: '100%', borderCollapse: 'collapse', marginBottom: 12 },
  th: { textAlign: 'left', fontSize: 11, color: '#475569', padding: '6px 10px', borderBottom: '1px solid #2d3148', fontWeight: 500 },
  td: { fontSize: 13, color: '#cbd5e1', padding: '8px 10px', borderBottom: '1px solid #1e2235', verticalAlign: 'middle' },
  btn: (variant) => ({
    background: variant === 'danger' ? '#450a0a' : variant === 'primary' ? '#312e81' : '#2d3148',
    color: variant === 'danger' ? '#fca5a5' : variant === 'primary' ? '#a5b4fc' : '#cbd5e1',
    border: `1px solid ${variant === 'danger' ? '#7f1d1d' : variant === 'primary' ? '#4338ca' : '#3d4468'}`,
    borderRadius: 5, padding: '4px 10px', fontSize: 12, cursor: 'pointer',
  }),
  modal: { position: 'fixed', inset: 0, background: '#00000088', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 },
  modalBox: { background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 12, padding: 24, width: 480, maxHeight: '90vh', overflowY: 'auto' },
  label: { display: 'block', fontSize: 11, color: '#64748b', marginBottom: 4, marginTop: 12 },
  input: { width: '100%', background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '7px 10px', color: '#e2e8f0', fontSize: 13, outline: 'none' },
  textarea: { width: '100%', background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '7px 10px', color: '#e2e8f0', fontSize: 12, outline: 'none', fontFamily: 'monospace', resize: 'vertical', minHeight: 80 },
  select: { width: '100%', background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '7px 10px', color: '#e2e8f0', fontSize: 13 },
  row: { display: 'flex', gap: 8, marginTop: 16 },
};

function DeviceForm({ initial, onSave, onClose }) {
  const [form, setForm] = useState({ ...EMPTY_DEVICE, ...initial });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div style={s.modal}>
      <div style={s.modalBox}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{initial ? 'Modifier appareil' : 'Ajouter appareil'}</div>
        <label style={s.label}>Nom</label>
        <input style={s.input} value={form.name} onChange={e => set('name', e.target.value)} />
        <label style={s.label}>Type</label>
        <select style={s.select} value={form.type} onChange={e => set('type', e.target.value)}>
          {DEVICE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <label style={s.label}>IP</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input style={{ ...s.input, flex: 1 }} value={form.ip} onChange={e => set('ip', e.target.value)} placeholder="192.168.10.x" />
          <select style={{ ...s.select, width: 'auto', flexShrink: 0 }} value={form.ipType || 'static'} onChange={e => set('ipType', e.target.value)}>
            {IP_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <label style={s.label}>Hostname (optionnel)</label>
        <input style={s.input} value={form.hostname || ''} onChange={e => set('hostname', e.target.value)} placeholder="device.tixhon.be" />
        <label style={s.label}>Adresse MAC (pour WoL)</label>
        <input style={s.input} value={form.mac || ''} onChange={e => set('mac', e.target.value)} placeholder="AA:BB:CC:DD:EE:FF" />
        <label style={s.label}>Specs</label>
        <input style={s.input} value={form.specs || ''} onChange={e => set('specs', e.target.value)} placeholder="CPU, RAM, disque..." />
        <label style={s.label}>Rôle</label>
        <input style={s.input} value={form.role || ''} onChange={e => set('role', e.target.value)} placeholder="Description du rôle" />
        <label style={s.label}>Utilisateur SSH</label>
        <input style={s.input} value={form.sshUser || ''} onChange={e => set('sshUser', e.target.value)} placeholder="root" />
        <label style={s.label}>Date d'achat</label>
        <input style={s.input} value={form.purchasedAt || ''} onChange={e => set('purchasedAt', e.target.value)} type="date" />
        <label style={s.label}>Config réseau (optionnel)</label>
        <textarea style={s.textarea} value={form.config || ''} onChange={e => set('config', e.target.value)} placeholder="Règles firewall, VPN, DNS, accès SSH..." />
        <label style={s.label}>Notes</label>
        <input style={s.input} value={form.notes || ''} onChange={e => set('notes', e.target.value)} placeholder="Observations, garantie, etc." />
        <div style={s.row}>
          <button style={s.btn('primary')} onClick={() => onSave(form)}>Sauvegarder</button>
          <button style={s.btn()} onClick={onClose}>Annuler</button>
        </div>
      </div>
    </div>
  );
}

function ServiceForm({ initial, onSave, onClose }) {
  const [form, setForm] = useState({ ...EMPTY_SERVICE, ...initial });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div style={s.modal}>
      <div style={s.modalBox}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{initial ? 'Modifier service' : 'Ajouter service'}</div>
        <label style={s.label}>Nom</label>
        <input style={s.input} value={form.name} onChange={e => set('name', e.target.value)} />
        <label style={s.label}>LXC ID (Proxmox)</label>
        <input style={s.input} value={form.lxcId || ''} onChange={e => set('lxcId', e.target.value ? Number(e.target.value) : '')} type="number" placeholder="103" />
        <label style={s.label}>IP</label>
        <div style={{ display: 'flex', gap: 8 }}>
          <input style={{ ...s.input, flex: 1 }} value={form.ip || ''} onChange={e => set('ip', e.target.value)} placeholder="192.168.10.x" />
          <select style={{ ...s.select, width: 'auto', flexShrink: 0 }} value={form.ipType || 'dhcp'} onChange={e => set('ipType', e.target.value)}>
            {IP_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <label style={s.label}>Adresse MAC</label>
        <input style={s.input} value={form.mac || ''} onChange={e => set('mac', e.target.value)} placeholder="BC:24:11:XX:XX:XX" />
        <label style={s.label}>Hostname (optionnel)</label>
        <input style={s.input} value={form.hostname || ''} onChange={e => set('hostname', e.target.value)} placeholder="service.tixhon.be" />
        <label style={s.label}>Port</label>
        <input style={s.input} value={form.port || ''} onChange={e => set('port', e.target.value ? Number(e.target.value) : '')} type="number" placeholder="3000" />
        <label style={s.label}>URL</label>
        <input style={s.input} value={form.url || ''} onChange={e => set('url', e.target.value)} placeholder="http://..." />
        <label style={s.label}>Rôle</label>
        <input style={s.input} value={form.role || ''} onChange={e => set('role', e.target.value)} />
        <label style={s.label}>Version</label>
        <input style={s.input} value={form.version || ''} onChange={e => set('version', e.target.value)} placeholder="ex: 0.107.52" />
        <label style={s.label}>Date d'installation</label>
        <input style={s.input} value={form.installedAt || ''} onChange={e => set('installedAt', e.target.value)} type="date" />
        <label style={s.label}>Script d'installation (URL community scripts)</label>
        <input style={s.input} value={form.installScript || ''} onChange={e => set('installScript', e.target.value)} placeholder="https://github.com/tteck/Proxmox/raw/main/ct/..." />
        <label style={s.label}>Notes</label>
        <input style={s.input} value={form.notes || ''} onChange={e => set('notes', e.target.value)} placeholder="Observations, config particulière, etc." />
        <div style={s.row}>
          <button style={s.btn('primary')} onClick={() => onSave(form)}>Sauvegarder</button>
          <button style={s.btn()} onClick={onClose}>Annuler</button>
        </div>
      </div>
    </div>
  );
}

const IP_TYPE_COLOR = { static: '#7c83ff', 'dhcp-reserved': '#f59e0b', dhcp: '#94a3b8' };

function SslBadge({ hostname, npmHosts }) {
  if (!hostname || !npmHosts) return null;
  const entry = npmHosts.find(h => h.domains?.includes(hostname));
  if (!entry) return <span style={{ fontSize: 10, color: '#475569', marginLeft: 5 }}>no proxy</span>;
  if (!entry.cert) return <span style={{ fontSize: 10, color: '#ef4444', marginLeft: 5, border: '1px solid #ef4444', borderRadius: 3, padding: '1px 4px' }}>no SSL</span>;
  const d = entry.cert.daysLeft;
  const color = d > 30 ? '#22c55e' : d > 7 ? '#f59e0b' : '#ef4444';
  return (
    <span title={`Cert: ${entry.cert.name} — expire ${entry.cert.expiresOn}`}
      style={{ fontSize: 10, color, border: '1px solid currentColor', borderRadius: 3, padding: '1px 4px', marginLeft: 5, cursor: 'help' }}>
      SSL {d}j
    </span>
  );
}

export default function InventoryPage() {
  const [inventory, setInventory] = useState({ devices: [], services: [] });
  const [npmHosts, setNpmHosts] = useState(null);
  const [deviceModal, setDeviceModal] = useState(null);
  const [serviceModal, setServiceModal] = useState(null);

  const reload = () => fetch('/api/inventory').then(r => r.json()).then(setInventory);
  useEffect(() => { reload(); }, []);
  useEffect(() => {
    fetch('/api/npm').then(r => r.json()).then(d => setNpmHosts(d.hosts)).catch(() => {});
  }, []);

  async function saveDevice(form) {
    const isEdit = !!form.id;
    await fetch(isEdit ? `/api/inventory/devices/${form.id}` : '/api/inventory/devices', {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    setDeviceModal(null);
    reload();
  }

  async function deleteDevice(id) {
    if (!window.confirm('Supprimer cet appareil ?')) return;
    await fetch(`/api/inventory/devices/${id}`, { method: 'DELETE' });
    reload();
  }

  async function saveService(form) {
    const isEdit = !!form.id;
    await fetch(isEdit ? `/api/inventory/services/${form.id}` : '/api/inventory/services', {
      method: isEdit ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    setServiceModal(null);
    reload();
  }

  async function deleteService(id) {
    if (!window.confirm('Supprimer ce service ?')) return;
    await fetch(`/api/inventory/services/${id}`, { method: 'DELETE' });
    reload();
  }

  return (
    <div>
      {deviceModal !== null && (
        <DeviceForm
          initial={deviceModal === 'new' ? null : deviceModal}
          onSave={saveDevice}
          onClose={() => setDeviceModal(null)}
        />
      )}
      {serviceModal !== null && (
        <ServiceForm
          initial={serviceModal === 'new' ? null : serviceModal}
          onSave={saveService}
          onClose={() => setServiceModal(null)}
        />
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={s.section}>APPAREILS ({inventory.devices.length})</div>
        <button style={s.btn('primary')} onClick={() => setDeviceModal('new')}>+ Ajouter</button>
      </div>
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Nom</th>
            <th style={s.th}>Type</th>
            <th style={s.th}>IP</th>
            <th style={s.th}>MAC</th>
            <th style={s.th}>Specs</th>
            <th style={s.th}>Config</th>
            <th style={s.th}>Acheté</th>
            <th style={s.th}></th>
          </tr>
        </thead>
        <tbody>
          {inventory.devices.map(d => (
            <tr key={d.id}>
              <td style={s.td}>
                <strong>{d.name}</strong>
                {d.hostname && <SslBadge hostname={d.hostname} npmHosts={npmHosts} />}
              </td>
              <td style={s.td}>{d.type}</td>
              <td style={s.td}>
                <code style={{ fontSize: 12 }}>{d.ip}</code>
                {d.ipType && <span style={{ marginLeft: 5, fontSize: 10, color: IP_TYPE_COLOR[d.ipType] || '#94a3b8', border: '1px solid currentColor', borderRadius: 3, padding: '1px 4px' }}>{d.ipType}</span>}
              </td>
              <td style={s.td}><code style={{ fontSize: 11, color: '#64748b' }}>{d.mac || '—'}</code></td>
              <td style={s.td} title={d.specs}>{d.specs?.substring(0, 40) || '—'}</td>
              <td style={s.td}>{d.config ? <span title={d.config} style={{ cursor: 'help', borderBottom: '1px dotted #475569' }}>voir ▾</span> : '—'}</td>
              <td style={s.td}>{d.purchasedAt || '—'}</td>
              <td style={s.td}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button style={s.btn()} onClick={() => setDeviceModal(d)}>Modifier</button>
                  <button style={s.btn('danger')} onClick={() => deleteDevice(d.id)}>Supprimer</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
        <div style={s.section}>SERVICES ({inventory.services.length})</div>
        <button style={s.btn('primary')} onClick={() => setServiceModal('new')}>+ Ajouter</button>
      </div>
      <table style={s.table}>
        <thead>
          <tr>
            <th style={s.th}>Nom</th>
            <th style={s.th}>LXC</th>
            <th style={s.th}>IP:Port</th>
            <th style={s.th}>MAC</th>
            <th style={s.th}>Version</th>
            <th style={s.th}>Installé</th>
            <th style={s.th}>Script</th>
            <th style={s.th}></th>
          </tr>
        </thead>
        <tbody>
          {inventory.services.map(sv => (
            <tr key={sv.id}>
              <td style={s.td}>
                <strong>{sv.name}</strong>
                {sv.hostname && <SslBadge hostname={sv.hostname} npmHosts={npmHosts} />}
              </td>
              <td style={s.td}>{sv.lxcId || '—'}</td>
              <td style={s.td}><code style={{ fontSize: 12 }}>{sv.ip}:{sv.port}</code></td>
              <td style={s.td}><code style={{ fontSize: 11, color: '#64748b' }}>{sv.mac || '—'}</code></td>
              <td style={s.td}>{sv.version || '—'}</td>
              <td style={s.td}>{sv.installedAt || '—'}</td>
              <td style={s.td}>{sv.installScript ? <a href={sv.installScript} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: '#7c83ff', textDecoration: 'none' }}>tteck ↗</a> : '—'}</td>
              <td style={s.td}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button style={s.btn()} onClick={() => setServiceModal(sv)}>Modifier</button>
                  <button style={s.btn('danger')} onClick={() => deleteService(sv.id)}>Supprimer</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
