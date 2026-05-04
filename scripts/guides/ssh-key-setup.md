# SSH Key Setup Guide

The web server runs on your local machine (Windows laptop or macOS)
and SSHs into the 3 devices to trigger shutdowns.
You need to generate one SSH key on the host machine and copy it to each device.

---

## Step 1 — Generate the SSH key

### On macOS (Terminal)

```bash
ssh-keygen -t ed25519 -C "network-shutdown@mac"
```

### On Windows (Git Bash or WSL)

```bash
ssh-keygen -t ed25519 -C "network-shutdown@windows"
```

- Accept the default location (`~/.ssh/id_ed25519`)
- **Leave the passphrase empty** (required for automated scripts)

> If you switch between machines, repeat this guide on each one.

---

## Step 2 — Copy the key to each device

### NIPoGi — Proxmox (`root@192.168.10.2`)

```bash
ssh-copy-id root@192.168.10.2
```

Test:
```bash
ssh -o "PasswordAuthentication=no" root@192.168.10.2
```

---

### Synology DS916+ (`secureAdmin@192.168.10.5`)

**1. Enable SSH on the NAS:**
Control Panel → Terminal & SNMP → Enable SSH service

**2. Copy the key:**

*macOS:*
```bash
ssh-copy-id secureAdmin@192.168.10.5
```

*Windows (Git Bash or WSL):*
```bash
cat ~/.ssh/id_ed25519.pub | ssh secureAdmin@192.168.10.5 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

**3. Test:**
```bash
ssh -o "PasswordAuthentication=no" secureAdmin@192.168.10.5
```

**4. Verify `secureAdmin` has admin rights:**
Control Panel → User & Group → edit `secureAdmin` → check `administrators` group
(required for `sudo synoshutdown --now`)

---

### Synology DS925+ (`secureAdmin@192.168.10.3`)

Same steps as DS916+, different IP:

*macOS:*
```bash
ssh-copy-id secureAdmin@192.168.10.3
```

*Windows (Git Bash or WSL):*
```bash
cat ~/.ssh/id_ed25519.pub | ssh secureAdmin@192.168.10.3 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Test:
```bash
ssh -o "PasswordAuthentication=no" secureAdmin@192.168.10.3
```

---

## Step 3 — Final check

Run all 3 tests to confirm passwordless access:

```bash
ssh -o "PasswordAuthentication=no" root@192.168.10.2 "hostname"
ssh -o "PasswordAuthentication=no" secureAdmin@192.168.10.5 "hostname"
ssh -o "PasswordAuthentication=no" secureAdmin@192.168.10.3 "hostname"
```

All 3 should return the hostname without asking for a password.

---

## Starting the web server

**macOS:**

```bash
chmod +x start-server.sh   # first time only
./start-server.sh
```

**Windows:**
Double-click `start-server.bat`
