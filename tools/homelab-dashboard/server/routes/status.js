const express = require('express');
const { exec, execFile } = require('child_process');
const net = require('net');
const axios = require('axios');
const https = require('https');
const fs = require('fs');
const path = require('path');

const router = express.Router();
const DATA_FILE = path.join(__dirname, '../data/inventory.json');

const PROMETHEUS_URL = 'http://192.168.10.184:9090';
const PFSENSE_URL = process.env.PFSENSE_URL || 'http://192.168.10.1';
const PFSENSE_API_KEY = process.env.PFSENSE_API_KEY || '';

const httpsAgent = new https.Agent({ rejectUnauthorized: false });

function checkPort(ip, port = 22, timeout = 3000) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(timeout);
    socket.connect(port, ip, () => { socket.destroy(); resolve(true); });
    socket.on('error', () => { socket.destroy(); resolve(false); });
    socket.on('timeout', () => { socket.destroy(); resolve(false); });
  });
}

async function prometheusQuery(query) {
  try {
    const res = await axios.get(`${PROMETHEUS_URL}/api/v1/query`, {
      params: { query },
      timeout: 5000,
    });
    return res.data.data.result;
  } catch {
    return [];
  }
}

async function getDeviceMetrics(instance) {
  const [cpuResults, memTotalResults, memCachedResults, memBuffersResults, diskAvailResults, diskSizeResults] = await Promise.all([
    prometheusQuery(`100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",instance="${instance}"}[2m])) * 100)`),
    prometheusQuery(`node_memory_MemTotal_bytes{instance="${instance}"}`),
    prometheusQuery(`node_memory_Cached_bytes{instance="${instance}"}`),
    prometheusQuery(`node_memory_Buffers_bytes{instance="${instance}"}`),
    prometheusQuery(`node_filesystem_avail_bytes{instance="${instance}",mountpoint="/volume1"}`),
    prometheusQuery(`node_filesystem_size_bytes{instance="${instance}",mountpoint="/volume1"}`),
  ]);
  let mem = null;
  if (memTotalResults[0] && memCachedResults[0] && memBuffersResults[0]) {
    const total = parseFloat(memTotalResults[0].value[1]);
    const cached = parseFloat(memCachedResults[0].value[1]);
    const buffers = parseFloat(memBuffersResults[0].value[1]);
    mem = (((total - cached - buffers) / total) * 100).toFixed(1);
  }
  let disk = null, diskUsedTB = null, diskTotalTB = null;
  if (diskAvailResults[0] && diskSizeResults[0]) {
    const avail = parseFloat(diskAvailResults[0].value[1]);
    const size = parseFloat(diskSizeResults[0].value[1]);
    disk = ((1 - avail / size) * 100).toFixed(1);
    diskUsedTB = ((size - avail) / 1e12).toFixed(1);
    diskTotalTB = (size / 1e12).toFixed(1);
  }
  return {
    cpu: cpuResults[0] ? parseFloat(cpuResults[0].value[1]).toFixed(1) : null,
    mem,
    disk,
    diskUsedTB,
    diskTotalTB,
  };
}

async function getNipogiMetrics() {
  return new Promise((resolve) => {
    const remoteCmd = `awk '{u=$2+$4;t=$2+$3+$4+$5; if(NR==1){u1=u;t1=t} else printf "%.1f\\n",(u-u1)*100/(t-t1)}' <(grep -m1 cpu /proc/stat) <(sleep 0.5; grep -m1 cpu /proc/stat); free -m | awk 'NR==2{printf "%.1f\\n",$3/$2*100}'; df / | awk 'NR==2{printf "%.1f\\n",$5}'`;
    execFile('ssh', [
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'ConnectTimeout=5',
      'root@192.168.10.2',
      remoteCmd,
    ], { timeout: 10000 }, (err, stdout) => {
      if (err) return resolve({ cpu: null, mem: null, disk: null });
      const [cpu, mem, disk] = stdout.trim().split('\n');
      resolve({
        cpu: cpu ? parseFloat(cpu).toFixed(1) : null,
        mem: mem ? parseFloat(mem).toFixed(1) : null,
        disk: disk ? parseFloat(disk).toFixed(1) : null,
      });
    });
  });
}

async function getPfSenseStatus() {
  try {
    const res = await axios.get(`${PFSENSE_URL}/api/v2/status/gateways`, {
      headers: { 'X-API-Key': PFSENSE_API_KEY, 'Accept': 'application/json' },
      timeout: 5000,
    });
    const gateways = res.data.data || [];
    const wan = gateways.find(g => g.name?.toLowerCase().includes('wan'));
    return {
      wanStatus: wan?.status || 'unknown',
      wanIp: wan?.srcip || null,
      wanDelay: wan?.delay != null ? `${parseFloat(wan.delay).toFixed(0)}ms` : null,
      wanLoss: wan?.loss != null ? `${wan.loss}%` : null,
    };
  } catch {
    return { wanStatus: 'error', wanIp: null };
  }
}

let lxcMetricsCache = {};

async function refreshAllLxcMetrics(lxcIds) {
  return new Promise((resolve) => {
    const parts = lxcIds.map(id =>
      `echo "LXC:${id}"; pct exec ${id} -- sh -c 'nproc; free -m | awk NR==2; cat /proc/loadavg' 2>/dev/null; echo "---"`
    ).join('; ');
    execFile('ssh', [
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'ConnectTimeout=5',
      'root@192.168.10.2',
      parts,
    ], { timeout: 15000 }, (err, stdout) => {
      if (err || !stdout) return resolve({});
      const result = {};
      const blocks = stdout.split('LXC:').filter(Boolean);
      for (const block of blocks) {
        const lines = block.trim().split('\n');
        const id = parseInt(lines[0]);
        const nproc = parseInt(lines[1]) || 1;
        const memLine = lines[2] ? lines[2].trim().split(/\s+/) : [];
        const loadLine = lines[3] ? lines[3].trim().split(' ') : [];
        const memUsed = parseFloat(memLine[2]) || 0;
        const memTotal = parseFloat(memLine[1]) || 1;
        const load1m = parseFloat(loadLine[0]) || 0;
        result[id] = {
          cpu: Math.min(load1m / nproc * 100, 100).toFixed(1),
          mem: (memUsed / memTotal * 100).toFixed(1),
        };
      }
      resolve(result);
    });
  });
}

router.get('/stream', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const send = (data) => res.write(`data: ${JSON.stringify(data)}\n\n`);

  async function poll() {
    const inventory = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    const results = { devices: {}, services: {}, timestamp: new Date().toISOString() };

    await Promise.all([
      ...inventory.devices.map(async (device) => {
        const online = await checkPort(device.ip, device.port || 22);
        let metrics = { cpu: null, mem: null, disk: null };
        let extra = {};

        if (online) {
          if (device.id === 'nipogi') {
            metrics = await getNipogiMetrics();
          } else if (device.type === 'nas') {
            const nasInstance = device.id === 'tischnas2' ? 'TischNAS2' : 'TischNAS3';
            metrics = await getDeviceMetrics(nasInstance);
          } else if (device.id === 'pfsense') {
            extra = await getPfSenseStatus();
          }
        }

        results.devices[device.id] = { online, ...metrics, ...extra };
      }),
      (async () => {
        const lxcIds = inventory.services.filter(s => s.lxcId).map(s => s.lxcId);
        const lxcMetrics = lxcIds.length ? await refreshAllLxcMetrics(lxcIds) : {};

        await Promise.all(inventory.services.map(async (service) => {
          const portToCheck = service.port || 80;
          const online = await checkPort(service.ip, portToCheck, 3000);
          const metrics = service.lxcId ? (lxcMetrics[service.lxcId] || { cpu: null, mem: null }) : { cpu: null, mem: null };
          results.services[service.id] = { online, ...metrics };
        }));
      })(),
    ]);

    send(results);
  }

  poll();
  const interval = setInterval(poll, 30000);
  req.on('close', () => clearInterval(interval));
});

module.exports = router;
