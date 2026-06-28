const express = require('express');
const axios = require('axios');
const router = express.Router();

const PFSENSE_URL = process.env.PFSENSE_URL || 'http://192.168.10.1';
const PFSENSE_API_KEY = process.env.PFSENSE_API_KEY || '';
const ADGUARD_URL = process.env.ADGUARD_URL || 'https://adg.tixhon.be';
const ADGUARD_USER = process.env.ADGUARD_USER || '';
const ADGUARD_PASS = process.env.ADGUARD_PASS || '';
const NPM_URL = process.env.NPM_URL || 'http://192.168.10.11:81';
const NPM_USER = process.env.NPM_USER || '';
const NPM_PASS = process.env.NPM_PASS || '';

const pfsenseHeaders = { 'X-API-Key': PFSENSE_API_KEY, 'Accept': 'application/json' };
const adguardAuth = { username: ADGUARD_USER, password: ADGUARD_PASS };

let cache = null;
let cacheAt = 0;
const CACHE_TTL = 60 * 1000;

async function pf(path) {
  const res = await axios.get(`${PFSENSE_URL}/api/v2/${path}`, { headers: pfsenseHeaders, timeout: 5000 });
  return res.data.data;
}

async function fetchNetworkData() {
  const [gatewaysData, servicesData, wgTunnelsData, wgSettingsData, firewallData, adStats, adStatus, npmToken] = await Promise.allSettled([
    pf('status/gateways'),
    pf('status/services'),
    pf('vpn/wireguard/tunnels'),
    pf('vpn/wireguard/settings'),
    pf('firewall/rules'),
    axios.get(`${ADGUARD_URL}/control/stats`, { auth: adguardAuth, timeout: 5000 }),
    axios.get(`${ADGUARD_URL}/control/status`, { auth: adguardAuth, timeout: 5000 }),
    axios.post(`${NPM_URL}/api/tokens`, { identity: NPM_USER, secret: NPM_PASS }, { timeout: 5000 }),
  ]);

  // pfSense — WAN gateway
  const gateways = gatewaysData.status === 'fulfilled' ? gatewaysData.value : [];
  const wan = gateways.find(g => g.name?.toLowerCase().includes('wan')) || null;

  // pfSense — services
  const services = servicesData.status === 'fulfilled' ? servicesData.value : [];
  const serviceMap = {};
  for (const svc of services) serviceMap[svc.name] = svc.status;

  // pfSense — WireGuard tunnels + settings
  const wgTunnels = wgTunnelsData.status === 'fulfilled' ? wgTunnelsData.value : [];
  const wgEnabled = wgSettingsData.status === 'fulfilled' ? wgSettingsData.value.enable : false;
  const wgRunning = wgEnabled && wgTunnels.some(t => t.enabled);

  // pfSense — firewall rules
  const allRules = firewallData.status === 'fulfilled' ? firewallData.value : [];
  const firewallRules = allRules.map(r => ({
    action: r.type || 'pass',
    interface: Array.isArray(r.interface) ? r.interface.join(', ') : (r.interface || '?'),
    description: r.descr || '',
    protocol: r.protocol || 'any',
    source: typeof r.source === 'string' ? r.source : (r.source?.network || 'any'),
    destination: typeof r.destination === 'string' ? r.destination : (r.destination?.network || 'any'),
    destPort: typeof r.destination === 'object' ? (r.destination?.port || '') : '',
  }));

  // AdGuard
  let adguard = null;
  if (adStats.status === 'fulfilled' && adStatus.status === 'fulfilled') {
    const s = adStats.value.data;
    const blocked = s.num_blocked_filtering + (s.num_replaced_safebrowsing || 0) + (s.num_replaced_parental || 0);
    adguard = {
      totalQueries: s.num_dns_queries,
      blockedQueries: blocked,
      blockRate: s.num_dns_queries > 0 ? ((blocked / s.num_dns_queries) * 100).toFixed(1) : '0.0',
      protectionEnabled: adStatus.value.data.protection_enabled,
      version: adStatus.value.data.version,
      topBlocked: (s.top_blocked_domains || []).slice(0, 10).map(e => {
        const [domain, count] = Object.entries(e)[0];
        return { domain, count };
      }),
    };
  }

  // NPM
  let npm = null;
  if (npmToken.status === 'fulfilled') {
    const token = npmToken.value.data.token;
    const headers = { Authorization: `Bearer ${token}` };
    const [hostsRes, certsRes] = await Promise.all([
      axios.get(`${NPM_URL}/api/nginx/proxy-hosts`, { headers, timeout: 5000 }),
      axios.get(`${NPM_URL}/api/nginx/certificates`, { headers, timeout: 5000 }),
    ]);
    const certById = {};
    for (const c of certsRes.data) {
      certById[c.id] = {
        name: c.nice_name,
        expiresOn: c.expires_on,
        daysLeft: Math.floor((new Date(c.expires_on) - Date.now()) / 86400000),
      };
    }
    npm = {
      hosts: hostsRes.data.map(h => ({
        domains: h.domain_names,
        forwardHost: h.forward_host,
        forwardPort: h.forward_port,
        enabled: h.enabled,
        cert: h.certificate_id ? certById[h.certificate_id] : null,
      })),
    };
  }

  return {
    pfsense: {
      wan: wan ? {
        name: wan.name,
        status: wan.status,
        ip: wan.srcip,
        delay: wan.delay != null ? `${parseFloat(wan.delay).toFixed(0)}ms` : null,
        loss: wan.loss != null ? `${wan.loss}%` : null,
      } : null,
      services: {
        dhcp: serviceMap['kea-dhcp4'] ?? null,
        wireguard: wgRunning,
        ntp: serviceMap['ntpd'] ?? null,
        ssh: serviceMap['sshd'] ?? null,
      },
      wireguard: wgTunnels.map(t => ({
        name: t.name,
        enabled: t.enabled,
        description: t.descr,
        port: t.listenport,
        addresses: (t.addresses || []).map(a => `${a.address}/${a.mask}`),
      })),
      firewallRules,
    },
    adguard,
    npm,
  };
}

router.get('/', async (req, res) => {
  try {
    if (cache && Date.now() - cacheAt < CACHE_TTL) return res.json(cache);
    cache = await fetchNetworkData();
    cacheAt = Date.now();
    res.json(cache);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
