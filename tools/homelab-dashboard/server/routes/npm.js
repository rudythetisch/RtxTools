const express = require('express');
const axios = require('axios');
const router = express.Router();

const NPM_URL = process.env.NPM_URL || 'http://192.168.10.11:81';
const NPM_USER = process.env.NPM_USER || '';
const NPM_PASS = process.env.NPM_PASS || '';

let cache = null;
let cacheAt = 0;
const CACHE_TTL = 5 * 60 * 1000;

async function getToken() {
  const res = await axios.post(`${NPM_URL}/api/tokens`, { identity: NPM_USER, secret: NPM_PASS });
  return res.data.token;
}

async function fetchNpmData() {
  const token = await getToken();
  const headers = { Authorization: `Bearer ${token}` };

  const [hostsRes, certsRes] = await Promise.all([
    axios.get(`${NPM_URL}/api/nginx/proxy-hosts`, { headers }),
    axios.get(`${NPM_URL}/api/nginx/certificates`, { headers }),
  ]);

  const certById = {};
  for (const c of certsRes.data) {
    certById[c.id] = {
      id: c.id,
      name: c.nice_name,
      provider: c.provider,
      expiresOn: c.expires_on,
      daysLeft: Math.floor((new Date(c.expires_on) - Date.now()) / 86400000),
    };
  }

  const hosts = hostsRes.data.map(h => ({
    domains: h.domain_names,
    forwardHost: h.forward_host,
    forwardPort: h.forward_port,
    enabled: h.enabled,
    cert: h.certificate_id ? certById[h.certificate_id] : null,
  }));

  return { hosts, certs: Object.values(certById) };
}

router.get('/', async (req, res) => {
  try {
    if (cache && Date.now() - cacheAt < CACHE_TTL) return res.json(cache);
    cache = await fetchNpmData();
    cacheAt = Date.now();
    res.json(cache);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Returns SSL info for a specific hostname
router.get('/ssl/:hostname', async (req, res) => {
  try {
    if (!cache || Date.now() - cacheAt >= CACHE_TTL) {
      cache = await fetchNpmData();
      cacheAt = Date.now();
    }
    const host = cache.hosts.find(h => h.domains?.includes(req.params.hostname));
    if (!host) return res.json({ found: false });
    res.json({ found: true, ...host });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
