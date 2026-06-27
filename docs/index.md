# RtxTools

Collection of personal tools and scripts for home infrastructure management.

## Tools

| Tool | Description |
|------|-------------|
| [[rtxcopy/overview\|rtxcopy]] | Copy files/folders to NAS or Proxmox LXC/VM over SSH |
| `tools/network-shutdown/` | Web UI (Node.js/Express) for shutting down network devices |

## Scripts

| Script set | Description |
|------------|-------------|
| [[network/README\|network/home-assistant]] | Parental control timer system — HA + pfSense integration |
| [[network/README\|network/pfsense]] | pfSense firewall commands and SSH setup |
| `scripts/guides/` | Setup guides: NUT UPS, SSH key setup |
| `scripts/nipogi-shutdown.sh` | Shutdown NIPoGi server |
| `scripts/synology-shutdown.sh` | Shutdown Synology NAS |

## Infrastructure

- **TischNAS2** — `192.168.10.5` (Synology NAS)
- **TischNAS3** — `192.168.10.3` (Synology NAS)
- **Proxmox node** — `192.168.10.2` — voir [[proxmox/README]]
- **Services** (pfSense, AdGuard, NPM, WireGuard) — voir [[services]]

## Setup

Tools are self-contained under `tools/<toolname>/`. Prerequisites: `uv` (`brew install uv`).

Scripts under `scripts/` are standalone — see each folder's README or `installation-guide.md`.
