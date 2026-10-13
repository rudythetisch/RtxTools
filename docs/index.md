# RtxTools

Collection of personal tools and scripts for home infrastructure management.

## Tools

| Tool | Description |
|------|-------------|
| [[rtxcopy/overview\|rtxcopy]] | Copy files/folders to NAS or Proxmox LXC/VM over SSH |
| `tools/homelab-dashboard/` | Dashboard homelab (React + Express) — statut, inventaire, actions rapides |

## Scripts

| Script set | Description |
|------------|-------------|
| [[network/internet-appareils\|network/internet-appareils]] | Coupure Internet par appareil (Apple TV, Switch, iPad, iPhones) + minuteur Apple TV (HA + pfSense) |
| [[network/migration-opnsense\|network/migration-opnsense]] | Plan de migration pfSense (VM) → OPNsense sur appliance dédiée : inventaire, bascule, retour arrière |
| [[network/tischnas3-servarr\|network/tischnas3-servarr]] | Stack Docker Servarr (Radarr/Sonarr/Prowlarr/...) sur TischNAS3 |
| `scripts/guides/` | Setup guides: NUT UPS, SSH key setup |
| `scripts/nipogi-shutdown.sh` | Shutdown NIPoGi server |
| `scripts/synology-shutdown.sh` | Shutdown Synology NAS |

## Infrastructure

- **TischNAS2** — `192.168.10.5` (Synology NAS)
- **TischNAS3** — `192.168.10.3` (Synology NAS)
- **Proxmox node** — `192.168.10.2` — voir [[proxmox/README]]
- **Services** (pfSense, AdGuard, NPM, WireGuard) — voir [[services]]
- **Projets futurs** (disque TischNAS2, OPNsense, RAM TischNAS3, Wi-Fi UniFi + VLAN…) — voir [[projets-futurs]]

## Setup

Tools are self-contained under `tools/<toolname>/`. Prerequisites: `uv` (`brew install uv`).

Scripts under `scripts/` are standalone — see the matching page in `docs/`.
