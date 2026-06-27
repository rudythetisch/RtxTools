# Services Homelab

Doc de référence pour les services principaux. Passer par Claude Code pour tout changement de config afin de maintenir un historique.

## Vue d'ensemble

| Service | VMID | IP | URL | Techno |
|---------|------|----|-----|--------|
| pfSense | VM 104 | 192.168.10.1 (LAN) | https://pfsense.tixhon.be | pfSense CE 2.7.2 |
| AdGuard Home | LXC 103 | 192.168.10.12 | http://192.168.10.12:3000 | AdGuard Home |
| Nginx Proxy Manager | LXC 105 | 192.168.10.11 | http://192.168.10.11:81 | NPM |
| WireGuard | VM 104 | — | via pfSense | pfSense-pkg-WireGuard 0.2.1 |
| Proxmox | node | 192.168.10.2 | https://192.168.10.2:8006 | Proxmox VE |

---

## pfSense

**Rôle** : Firewall, routeur, NAT, DHCP, DNS (forwarder vers AdGuard), WireGuard VPN, DynDNS.

**Version** : CE 2.7.2-RELEASE (FreeBSD 14.0) — dernière version CE. pfSense Plus (payant) serait 2.8.x+.

**Accès** :
- GUI : https://pfsense.tixhon.be — user `rtixhon` (admin désactivé)
- API REST : `https://pfsense.tixhon.be/api/v1/` — package pfSense-pkg-API v1.8.1 (installé 2026-06-27)
- SSH : port 22, accessible depuis WAN uniquement (LAN bloqué par firewall)

**Packages installés** :
- WireGuard 0.2.1
- pfSense-pkg-API 1.8.1 (REST API)

**Procédures importantes** :
- **WAN ne remonte pas après reboot** : Status > Interfaces → cocher "Send a gratuitous DHCP release packet" → Release WAN → Renew WAN. Si échec : reboot modem VOO.
- **DynDNS** : 2 entrées configurées (DNS-O-Matic + Custom) sur l'interface WAN.

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-06-27 | Installation pfSense-pkg-API v1.8.1, configuration API Token auth |

---

## AdGuard Home

**Rôle** : DNS avec blocage de publicités et tracking pour tout le réseau local.

**Version** : (à vérifier)

**Accès** :
- GUI : http://192.168.10.12:3000
- SSH : `ssh root@192.168.10.2 'pct exec 103 -- bash'`

**Config notable** :
- pfSense forwarde le DNS vers AdGuard (192.168.10.12)
- Upstream DNS : (à documenter)

**Historique des changements** :

| Date | Changement |
|------|-----------|
| — | — |

---

## Nginx Proxy Manager (NPM)

**Rôle** : Reverse proxy HTTPS pour tous les services internes exposés vers l'extérieur.

**Version** : (à vérifier)

**Accès** :
- GUI : http://192.168.10.11:81
- SSH : `ssh root@192.168.10.2 'pct exec 105 -- bash'`

**Proxy hosts configurés** : (à documenter au prochain changement)

**Historique des changements** :

| Date | Changement |
|------|-----------|
| — | — |

---

## WireGuard VPN

**Rôle** : VPN pour accès distant au réseau local.

**Version** : pfSense-pkg-WireGuard 0.2.1

**Accès** : Géré via pfSense GUI → VPN > WireGuard

**Config** :
- Tunnel : `tun_wg0` — VPN-WireGuard
- Port : 51820
- Peers actifs : 0 au repos (connectés à la demande)

**Historique des changements** :

| Date | Changement |
|------|-----------|
| — | — |

---

## Proxmox VE

Voir [[proxmox/README]] pour la documentation complète du nœud et des LXC/VMs.

**Résumé rapide** :
- Node : nipogi — 192.168.10.2 — Proxmox VE (kernel 6.8.12-30-pve depuis 2026-06-27)
- 13 LXC + 2 VMs
- Monitoring : Prometheus + Grafana + Alertmanager → Telegram

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-06-27 | Kernel reboot → 6.8.12-30-pve, reboot=pci GRUB fix |
| 2026-06-26 | 69 paquets sécurité, qemu-server 8.4.8, kernel épinglé |
