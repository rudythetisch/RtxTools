const express = require('express');
const { exec } = require('child_process');
const dgram = require('dgram');
const axios = require('axios');
const https = require('https');

const router = express.Router();

const SSH_OPTS = '-o StrictHostKeyChecking=no -o PasswordAuthentication=no -o ConnectTimeout=10';
const PFSENSE_API = 'https://pfsense.tixhon.be/api/v1';
const PFSENSE_AUTH = '72746978686f6e 3421f597ad3a33ed18976a875491c762';
const httpsAgent = new https.Agent({ rejectUnauthorized: false });

const DEVICE_CMDS = {
  nipogi: {
    ip: '192.168.10.2',
    user: 'root',
    shutdownCmd: "qm list | awk 'NR>1 {print $1}' | while read vmid; do qm shutdown \"$vmid\" --timeout 60 2>/dev/null; done; sleep 5; shutdown -h now",
  },
  tischnas2: {
    ip: '192.168.10.5',
    user: 'secureAdmin',
    shutdownCmd: 'sudo /usr/syno/sbin/synoshutdown -s',
  },
  tischnas3: {
    ip: '192.168.10.3',
    user: 'secureAdmin',
    shutdownCmd: 'sudo /usr/syno/sbin/synoshutdown -s',
  },
};

function sendMagicPacket(mac) {
  return new Promise((resolve, reject) => {
    const macHex = mac.replace(/[:\-]/g, '');
    if (macHex.length !== 12) return reject(new Error(`Adresse MAC invalide : ${mac}`));
    const macBytes = Buffer.from(macHex, 'hex');
    const packet = Buffer.alloc(102);
    packet.fill(0xff, 0, 6);
    for (let i = 0; i < 16; i++) macBytes.copy(packet, 6 + i * 6);
    const socket = dgram.createSocket('udp4');
    socket.once('error', (err) => { socket.close(); reject(err); });
    socket.bind(() => {
      socket.setBroadcast(true);
      socket.send(packet, 0, packet.length, 9, '255.255.255.255', (err) => {
        socket.close();
        if (err) reject(err); else resolve();
      });
    });
  });
}

function sshExec(user, ip, cmd) {
  return new Promise((resolve, reject) => {
    const sshCmd = `ssh ${SSH_OPTS} ${user}@${ip} "${cmd.replace(/"/g, '\\"')}"`;
    exec(sshCmd, { timeout: 30000 }, (err, stdout, stderr) => {
      if (err) reject(new Error(stderr || err.message));
      else resolve(stdout);
    });
  });
}

router.post('/shutdown/:deviceId', async (req, res) => {
  const cfg = DEVICE_CMDS[req.params.deviceId];
  if (!cfg) return res.status(404).json({ error: 'Device not found' });
  try {
    await sshExec(cfg.user, cfg.ip, cfg.shutdownCmd);
    res.json({ ok: true, message: `Shutdown envoyé à ${req.params.deviceId}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/wol/:deviceId', async (req, res) => {
  const { mac } = req.body;
  if (!mac) return res.status(400).json({ error: 'MAC address required' });
  try {
    await sendMagicPacket(mac);
    res.json({ ok: true, message: `Magic packet envoyé à ${req.params.deviceId}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/release-wan', async (req, res) => {
  try {
    await axios.post(`${PFSENSE_API}/interface/wan/apply/`, {}, {
      headers: { Authorization: PFSENSE_AUTH },
      httpsAgent,
      timeout: 10000,
    });
    res.json({ ok: true, message: 'WAN release envoyé' });
  } catch (err) {
    res.status(500).json({ error: err.response?.data?.message || err.message });
  }
});

router.post('/lxc/:lxcId/start', async (req, res) => {
  try {
    await sshExec('root', '192.168.10.2', `pct start ${req.params.lxcId}`);
    res.json({ ok: true, message: `LXC ${req.params.lxcId} démarré` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.post('/lxc/:lxcId/stop', async (req, res) => {
  try {
    await sshExec('root', '192.168.10.2', `pct shutdown ${req.params.lxcId}`);
    res.json({ ok: true, message: `LXC ${req.params.lxcId} arrêté` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
