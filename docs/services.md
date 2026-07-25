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
- REST API package (mis à jour depuis pfSense-pkg-API v1.8.1 → v2, pfSense 2.8.1-RELEASE)

**Procédures importantes** :
- **WAN ne remonte pas après reboot** : Status > Interfaces → cocher "Send a gratuitous DHCP release packet" → Release WAN → Renew WAN. Si échec : reboot modem VOO.
- **DynDNS** : 2 entrées configurées (DNS-O-Matic + Custom) sur l'interface WAN.
- **API REST v2** : auth = **HTTP Basic Auth** sur chaque requête (`curl -u user:pass https://pfsense.tixhon.be/api/v2/...`), pas de body JSON `{"username":...}` (renvoie 401 systématiquement, même avec bonnes permissions — piège classique de ce package). Privilèges requis sur le compte : `WebCfg - All pages` + toutes les perms `REST API - ...` dans User Manager.

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Migration API v1 → v2 constatée (ancien CLIENT-ID/TOKEN obsolète), accès rétabli via Basic Auth |
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
- Version installée : v0.107.52
- Auth API : `POST /control/login` avec `{"name":...,"password":...}`, cookie de session ensuite

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Accès API confirmé et documenté (login + cookie session) |

---

## Nginx Proxy Manager (NPM)

**Rôle** : Reverse proxy HTTPS pour tous les services internes exposés vers l'extérieur.

**Version** : (à vérifier)

**Accès** :
- GUI : http://192.168.10.11:81
- SSH : `ssh root@192.168.10.2 'pct exec 105 -- bash'`

**Proxy hosts configurés** : ~30 hosts sur `*.tixhon.be` (cert Let's Encrypt wildcard), incluant tous les services *arr, dashboard, monitoring, NAS, pfSense, jellyfin/jellyseerr, etc. — liste complète via API `GET /api/nginx/proxy-hosts`.

**Config notable** :
- Auth API : `POST /api/tokens` avec `{"identity":...,"secret":...}` → JWT (expire 1 jour)
- Édition d'un proxy host : `PUT /api/nginx/proxy-hosts/{id}` — retirer `id`, `created_on`, `modified_on`, `owner_user_id`, `meta` du payload GET avant de le renvoyer (sinon 400 "additional properties")

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | `jellyfin.tixhon.be` et `jellyseerr.tixhon.be` repointés de TischNAS3 (192.168.10.3) vers TischNAS2 (192.168.10.5) suite à la migration des conteneurs, mêmes ports (8100/5055). Accès API confirmé et documenté. |

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
