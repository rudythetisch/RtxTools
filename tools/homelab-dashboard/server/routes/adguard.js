const express = require('express');
const axios = require('axios');
const router = express.Router();

const ADGUARD_URL = process.env.ADGUARD_URL || 'https://adg.tixhon.be';
const ADGUARD_USER = process.env.ADGUARD_USER || '';
const ADGUARD_PASS = process.env.ADGUARD_PASS || '';

const auth = { username: ADGUARD_USER, password: ADGUARD_PASS };

let cache = null;
let cacheAt = 0;
const CACHE_TTL = 60 * 1000;

async function fetchAdGuardStats() {
  const [statsRes, statusRes] = await Promise.all([
    axios.get(`${ADGUARD_URL}/control/stats`, { auth, timeout: 5000 }),
    axios.get(`${ADGUARD_URL}/control/status`, { auth, timeout: 5000 }),
  ]);

  const s = statsRes.data;
  const blocked = s.num_blocked_filtering + (s.num_replaced_safebrowsing || 0) + (s.num_replaced_parental || 0);
  const blockRate = s.num_dns_queries > 0
    ? ((blocked / s.num_dns_queries) * 100).toFixed(1)
    : '0.0';

  const topBlocked = (s.top_blocked_domains || []).slice(0, 10).map(entry => {
    const [domain, count] = Object.entries(entry)[0];
    return { domain, count };
  });

  return {
    totalQueries: s.num_dns_queries,
    blockedQueries: blocked,
    blockRate,
    protectionEnabled: statusRes.data.protection_enabled,
    version: statusRes.data.version,
    topBlocked,
  };
}

router.get('/', async (req, res) => {
  try {
    if (cache && Date.now() - cacheAt < CACHE_TTL) return res.json(cache);
    cache = await fetchAdGuardStats();
    cacheAt = Date.now();
    res.json(cache);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
