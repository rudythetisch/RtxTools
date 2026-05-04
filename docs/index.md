# RtxTools

Collection of personal tools and scripts for home infrastructure management.

## Tools

| Tool | Description |
|------|-------------|
| [[rtxcopy/overview\|rtxcopy]] | Copy files/folders to NAS or Proxmox LXC/VM over SSH |

## Scripts

| Script set | Description |
|------------|-------------|
| [[network/README\|network/home-assistant]] | Parental control timer system — HA + pfSense integration |
| [[network/README\|network/pfsense]] | pfSense firewall commands and SSH setup |

## Infrastructure

- **TischNAS2** — `192.168.10.5` (Synology NAS)
- **TischNAS3** — `192.168.10.3` (Synology NAS)
- **Proxmox node** — `192.168.10.2`

## Setup

Tools are self-contained under `tools/<toolname>/`. Prerequisites: `uv` (`brew install uv`).

Scripts under `scripts/` are standalone — see each folder's README or `installation-guide.md`.
