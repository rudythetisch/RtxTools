import { useState } from 'react';
import StatusPage from './pages/StatusPage.jsx';
import InventoryPage from './pages/InventoryPage.jsx';
import NetworkPage from './pages/NetworkPage.jsx';

const NAV = [
  { id: 'status', label: 'Statut' },
  { id: 'inventory', label: 'Inventaire' },
  { id: 'network', label: 'Réseau' },
];

const s = {
  app: { display: 'flex', flexDirection: 'column', minHeight: '100vh' },
  header: { background: '#1a1d27', borderBottom: '1px solid #2d3148', padding: '0 24px', display: 'flex', alignItems: 'center', gap: 32, height: 52 },
  title: { fontSize: 16, fontWeight: 700, color: '#7c83ff', letterSpacing: '-0.02em' },
  nav: { display: 'flex', gap: 4 },
  navBtn: (active) => ({
    background: active ? '#2d3148' : 'transparent',
    color: active ? '#e2e8f0' : '#64748b',
    border: 'none',
    borderRadius: 6,
    padding: '6px 14px',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: active ? 600 : 400,
  }),
  main: { flex: 1, padding: 24 },
};

export default function App() {
  const [page, setPage] = useState('status');

  return (
    <div style={s.app}>
      <header style={s.header}>
        <span style={s.title}>⚡ Homelab</span>
        <nav style={s.nav}>
          {NAV.map(n => (
            <button key={n.id} style={s.navBtn(page === n.id)} onClick={() => setPage(n.id)}>
              {n.label}
            </button>
          ))}
        </nav>
      </header>
      <main style={s.main}>
        {page === 'status' && <StatusPage />}
        {page === 'inventory' && <InventoryPage />}
        {page === 'network' && <NetworkPage />}
      </main>
    </div>
  );
}
