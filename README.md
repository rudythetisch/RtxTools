# RtxTools

Collection of home-lab tools and scripts for managing a self-hosted network (NAS, Proxmox, pfSense, Home Assistant).

## Contents

```
RtxTools/
├── tools/
│   ├── rtxcopy/            TUI file-copy tool (Python + Textual)
│   └── network-shutdown/   Web UI for shutting down network devices (Node.js)
├── scripts/
│   ├── home-assistant/     HA automations, dashboard, and scripts
│   ├── pfsense/            pfSense firewall commands and SSH setup
│   ├── guides/             Setup guides (NUT UPS, SSH keys)
│   ├── nipogi-shutdown.sh
│   └── synology-shutdown.sh
├── docs/                   Markdown documentation (synced to Obsidian)
└── shared/rtxlib/          Future shared library
```

---

## rtxcopy

Terminal UI for copying files to a NAS or Proxmox LXC/VM over SSH.

**Features**
- File picker with multi-select and size display
- Destinations: Synology/TrueNAS (SFTP), Proxmox LXC (`pct push`), Proxmox QEMU (`qm guest exec`)
- Remote path browser with favorites
- Ed25519 SSH key generation and one-shot deployment per destination
- Real-time byte-level progress bar (no rsync stdout parsing)
- Persistent config at `~/.config/rtxtools/rtxcopy/config.toml`

**Requirements:** Python ≥ 3.11, [`uv`](https://github.com/astral-sh/uv)

```bash
cd tools/rtxcopy
uv sync                # install dependencies
uv run rtxcopy         # launch TUI
uv run rtxcopy manage  # destination manager
uv run pytest          # run tests
uv tool install .      # install globally as `rtxcopy`
```

---

## network-shutdown

Web interface (Express.js, port 8150) to trigger graceful shutdown of network devices: NIPoGi mini-PC and Synology NAS.

Credentials are loaded from a `credentials.env` file (not committed).

```bash
cd tools/network-shutdown
npm install
npm start              # or ./start-server.sh
```

---

## scripts

### home-assistant

YAML configuration for a parental-control timer automation:
- `automations.yaml` — start/stop kids screen-time timer, toggle pfSense firewall rules via SSH
- `scripts.yaml` — HA script definitions
- `dashboard.yaml` — Lovelace dashboard
- `configuration.yaml` — HA configuration snippets

### pfsense

- `firewall-commands.md` — pfSense shell commands for managing firewall rules
- `setup-ssh-access.sh` — SSH key setup for pfSense access from Home Assistant

### guides

- `configure-nut-ups.md` — NUT UPS setup for network-aware shutdown
- `ssh-key-setup.md` — SSH key generation and deployment reference

### standalone scripts

| Script | Purpose |
|---|---|
| `nipogi-shutdown.sh` | Graceful shutdown of the NIPoGi mini-PC |
| `synology-shutdown.sh` | Graceful shutdown of the Synology NAS |

---

## Infrastructure

| Host | IP |
|---|---|
| TischNAS2 | 192.168.10.5 |
| TischNAS3 | 192.168.10.3 |
| Proxmox node | 192.168.10.2 |

---

## Documentation

`docs/` contains Markdown files intended for Obsidian sync. See [`docs/index.md`](docs/index.md) for the full index.
