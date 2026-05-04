const express = require('express');
const { exec } = require('child_process');
const net = require('net');
const dgram = require('dgram');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 8150;

// Middleware
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Load credentials from environment or credentials.env file
function loadCredentials() {
    const envPath = path.join(__dirname, '..', 'scripts', 'credentials.env');
    const credentials = {};

    if (fs.existsSync(envPath)) {
        const content = fs.readFileSync(envPath, 'utf8');
        content.split('\n').forEach(line => {
            const match = line.match(/^([A-Z0-9_]+)="([^"]*)"/);
            if (match) {
                credentials[match[1]] = match[2];
            }
        });
    }

    return credentials;
}

const credentials = loadCredentials();

// SSH options shared across all devices
const SSH_OPTS = '-o StrictHostKeyChecking=no -o PasswordAuthentication=no -o ConnectTimeout=10';

// Device configurations
const devices = {
    nipogi: {
        name: 'NIPoGi Server',
        ip: credentials.NIPOGI_IP || '192.168.1.101',
        sshUser: credentials.NIPOGI_USER || 'root',
        remoteCmd: "qm list | awk 'NR>1 {print $1}' | while read vmid; do qm shutdown \"$vmid\" --timeout 60; done; sleep 10; shutdown -h now"
    },
    ds916: {
        name: 'Synology DS916+',
        ip: credentials.NAS_IP || '192.168.1.100',
        sshUser: credentials.NAS_USER || 'admin',
        mac: credentials.DS916_MAC || null,
        remoteCmd: 'sudo /usr/syno/sbin/synoshutdown -s'
    },
    ds925: {
        name: 'Synology DS925+',
        ip: credentials.DS925_IP || '192.168.1.102',
        sshUser: credentials.NAS_USER || 'admin',
        mac: credentials.DS925_MAC || null,
        remoteCmd: 'sudo /usr/syno/sbin/synoshutdown -s'
    }
};

// Build and send a WoL magic packet via UDP broadcast
function sendMagicPacket(mac) {
    return new Promise((resolve, reject) => {
        // Normalize MAC: accept "AA:BB:CC:DD:EE:FF" or "AA-BB-CC-DD-EE-FF"
        const macHex = mac.replace(/[:\-]/g, '');
        if (macHex.length !== 12) {
            return reject(new Error(`Adresse MAC invalide : ${mac}`));
        }

        const macBytes = Buffer.from(macHex, 'hex');
        // Magic packet: 6x 0xFF + MAC repeated 16 times = 102 bytes
        const packet = Buffer.alloc(102);
        packet.fill(0xff, 0, 6);
        for (let i = 0; i < 16; i++) {
            macBytes.copy(packet, 6 + i * 6);
        }

        const socket = dgram.createSocket('udp4');
        socket.once('error', (err) => { socket.close(); reject(err); });
        socket.bind(() => {
            socket.setBroadcast(true);
            socket.send(packet, 0, packet.length, 9, '255.255.255.255', (err) => {
                socket.close();
                if (err) reject(err);
                else resolve();
            });
        });
    });
}

// Check if a host is reachable on port 22
function checkHost(ip, timeout = 3000) {
    return new Promise((resolve) => {
        const socket = new net.Socket();
        socket.setTimeout(timeout);
        socket.connect(22, ip, () => { socket.destroy(); resolve(true); });
        socket.on('error', () => { socket.destroy(); resolve(false); });
        socket.on('timeout', () => { socket.destroy(); resolve(false); });
    });
}

// Status endpoint
app.get('/api/status', async (req, res) => {
    const results = await Promise.all(
        Object.entries(devices).map(async ([key, config]) => {
            const online = await checkHost(config.ip);
            return [key, { online, ip: config.ip, name: config.name }];
        })
    );
    res.json(Object.fromEntries(results));
});

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Shutdown endpoint
app.post('/api/shutdown/:device', (req, res) => {
    const device = req.params.device;
    const deviceConfig = devices[device];

    if (!deviceConfig) {
        return res.status(400).json({ error: 'Device not found' });
    }

    console.log(`[${new Date().toISOString()}] Shutdown requested for ${deviceConfig.name}`);

    // Build SSH command using Windows built-in ssh.exe (no WSL required)
    const sshCmd = `ssh ${SSH_OPTS} ${deviceConfig.sshUser}@${deviceConfig.ip} "${deviceConfig.remoteCmd.replace(/"/g, '\\"')}"`;

    exec(sshCmd, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing shutdown for ${deviceConfig.name}:`, error);
            return res.status(500).json({
                error: `Failed to shutdown ${deviceConfig.name}`,
                details: stderr || error.message
            });
        }

        console.log(`Shutdown command sent to ${deviceConfig.name}`);
        console.log(stdout);

        res.json({
            success: true,
            message: `Commande d'arrêt envoyée à ${deviceConfig.name}`,
            device: deviceConfig.name
        });
    });
});

// Wake on LAN endpoint
app.post('/api/wol/:device', async (req, res) => {
    const device = req.params.device;
    const deviceConfig = devices[device];

    if (!deviceConfig) {
        return res.status(400).json({ error: 'Appareil introuvable' });
    }
    if (!deviceConfig.mac) {
        return res.status(400).json({ error: `Adresse MAC non configurée pour ${deviceConfig.name}` });
    }

    console.log(`[${new Date().toISOString()}] Wake on LAN demandé pour ${deviceConfig.name} (${deviceConfig.mac})`);

    try {
        await sendMagicPacket(deviceConfig.mac);
        console.log(`Magic packet envoyé à ${deviceConfig.name}`);
        res.json({
            success: true,
            message: `Paquet de réveil envoyé à ${deviceConfig.name}`,
            device: deviceConfig.name
        });
    } catch (err) {
        console.error(`Erreur WoL pour ${deviceConfig.name}:`, err);
        res.status(500).json({ error: err.message });
    }
});

// List devices endpoint
app.get('/api/devices', (req, res) => {
    const deviceList = Object.entries(devices).map(([key, config]) => ({
        id: key,
        name: config.name,
        ip: config.ip
    }));
    res.json(deviceList);
});

// Serve index.html for root path
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Start server
app.listen(PORT, () => {
    console.log(`Network Shutdown Control server running on port ${PORT}`);
    console.log(`Access the web interface at http://localhost:${PORT}`);
});
