# Services Homelab

Doc de référence pour les services principaux. Passer par Claude Code pour tout changement de config afin de maintenir un historique.

## Accès dédiés agent Claude (2026-07-25)

Pour toute opération de routine, l'agent utilise des comptes séparés du compte personnel de l'utilisateur (traçabilité + révocation granulaire) :

| Service | Compte dédié | Restriction |
|---|---|---|
| TischNAS2 / TischNAS3 (SSH) | `claude` + clé `~/.ssh/claude-agent/id_ed25519` | sudo limité à `docker`, `df`, `free` |
| Vaultwarden LXC (SSH) | `claude` (non-root) + même clé | sudo limité à `docker` |
| Proxmox (API) | Token `root@pam!claude` | rôle `PVEAdmin` (pas de gestion utilisateurs/réseau système) |
| pfSense (API) | Utilisateur `claude` | 128 privilèges API ciblés, pas de GUI |
| NPM (API) | `claude-agent@tixhon.be` | rôle admin (pas plus granulaire dispo) |
| AdGuard Home | — | impossible, logiciel mono-utilisateur |

Détails et identifiants dans la mémoire Claude (`nas-access.md`, `vaultwarden-access.md`, `pfsense-access.md`, `npm-adguard-access.md`), pas dans ce repo (pas de secrets en clair dans git).

## Vue d'ensemble

| Service | VMID | IP | URL | Techno |
|---------|------|----|-----|--------|
| pfSense | VM 104 | 192.168.10.1 (LAN) | https://pfsense.tixhon.be | pfSense CE 2.7.2 |
| AdGuard Home | LXC 103 | 192.168.10.12 | http://192.168.10.12:3000 | AdGuard Home |
| Nginx Proxy Manager | LXC 105 | 192.168.10.11 | http://192.168.10.11:81 | NPM |
| WireGuard | VM 104 | — | via pfSense | pfSense-pkg-WireGuard 0.2.1 |
| Vaultwarden | LXC 110 | 192.168.10.17 | https://vw.tixhon.be | Vaultwarden (Docker) |
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

## Vaultwarden

**Rôle** : Gestionnaire de mots de passe self-hosted (implémentation Bitwarden-compatible), utilisé par toute la famille + plusieurs organisations partagées (FernelEvents, NAS & Co, IBA, Dumotisch, Saint-Nicolas Pontillas, Ecoledebierwart.be).

**Hébergement** : LXC 110 sur NIPoGi (Proxmox), IP `192.168.10.17`, 4 vCPU / 6 Gi RAM.

**Déploiement** : conteneur Docker `vaultwarden/server:latest` (migré depuis un binaire compilé + service systemd le 2026-07-25).
- Data : `/opt/vaultwarden/data` (host, réutilisé tel quel lors de la migration) → `/data` (conteneur)
- `SIGNUPS_ALLOWED=false` — inscriptions publiques désactivées
- Panel admin accessible via token (voir mémoire Claude `vaultwarden-access`)

**Accès** :
- Web vault : https://vw.tixhon.be
- SSH direct : `ssh root@192.168.10.17` (clé déjà déployée)

**Sécurité panel admin (2026-07-25)** :
- `ADMIN_TOKEN` stocké en Argon2id (hashé via `argon2` CLI, plus de warning "plain text ADMIN_TOKEN") — le hash n'affecte que le login admin, pas les comptes utilisateurs
- `/admin` bloqué pour tout trafic externe (via NPM, détection du header `CF-Connecting-IP` ajouté systématiquement par Cloudflare) — accessible uniquement en LAN direct ou via WireGuard
- Cloudflare Access testé sur `vw.tixhon.be` puis **retiré** : incompatible avec l'app native Bitwarden (mobile/desktop) qui ne gère pas le challenge interactif email/OTP ; mTLS indisponible sur le plan Cloudflare actuel ; service token impossible à configurer côté app (pas de champ dédié dans cette version). Protection assurée par : mot de passe maître + `/admin` restreint réseau. `hass.tixhon.be` garde sa protection Access (l'app companion HA gère bien la redirection, contrairement à Bitwarden).

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Migration bare-metal (binaire v1.35.8, systemd) → Docker (`vaultwarden/server:latest`, v1.37.0). Cause : décalage de version entre le binaire (1.35.8) et le web-vault embarqué (2026.3.1) provoquant un `404` sur `/identity/accounts/prelogin/password`, bloquant la connexion desktop/extension (le web vault fonctionnait car same-origin). Snapshot Proxmox + backup tar pris avant migration. `SIGNUPS_ALLOWED=false` appliqué (inscriptions publiques découvertes ouvertes par défaut). |
| 2026-07-25 | Conteneur Docker `vaultwarden-server-1` obsolète sur TischNAS3 arrêté définitivement (doublon, remplacé par ce LXC) |
| 2026-07-25 | Audit sécurité : `ADMIN_TOKEN` hashé, `/admin` restreint au LAN (bloqué en externe via header `CF-Connecting-IP`), Cloudflare Access testé puis retiré (incompatibilité app Bitwarden native) |

---

## Cloudflare (Tunnel + Access)

**Rôle** : expose sélectivement certains services vers internet sans ouvrir de port entrant — en complément du reverse proxy NPM (lui-même exposé via pfSense NAT 80/443 → 192.168.10.11, mais uniquement pour les domaines réellement présents en DNS public).

**Architecture découverte (audit 2026-07-25)** :
- Sur ~29 hosts configurés dans NPM, **seuls 6 domaines sont résolvables publiquement** (le reste — Proxmox, pfSense, NAS, AdGuard, etc. — n'existe qu'en DNS interne/AdGuard, donc pas exposé à internet malgré l'absence d'access-list NPM)
- **Cloudflare Tunnel** (`cloudflared`, LXC 109 sur NIPoGi, tunnel `nipogi-homelab`) : connexion sortante uniquement, ingress rules gérées depuis le dashboard Cloudflare (pas de config.yml local)
- Domaines tunnelés : `hass`, `vw`, `linkwarden` (→ NPM 192.168.10.11:80), `homeplan` (→ 192.168.10.98:3000), `rtxtradingbot` (→ 192.168.10.98:8000)

**Cloudflare Access (Zero Trust)** — authentification par email OTP en amont du login applicatif :

| Domaine | Protection | Policy |
|---|---|---|
| `rtxtradingbot.tixhon.be` | ✅ Access (préexistant) | rudy.tixhon@gmail.com |
| `hass.tixhon.be` | ❌ Retiré 2026-07-25 (incompatible app companion Android) | — protection via login HA natif, voir section Home Assistant |
| `vw.tixhon.be` | ❌ Retiré 2026-07-25 (incompatible app Bitwarden native) | — protection via `/admin` restreint réseau + mot de passe maître, voir section Vaultwarden |
| `linkwarden.tixhon.be`, `homeplan.tixhon.be` | ❌ Aucune (auth applicative native seulement) | — |

⚠️ **Piège de test important** : depuis le LAN, AdGuard résout `*.tixhon.be` directement vers l'IP interne (split-horizon DNS) — **tout test depuis le réseau local contourne Cloudflare Access entièrement**, donnant une fausse impression que la protection ne fonctionne pas. Pour tester réellement : DNS-over-HTTPS externe (`curl https://cloudflare-dns.com/dns-query?name=...&type=A -H "accept: application/dns-json"`) puis `curl --resolve host:443:<ip-cloudflare>` — ou plus simple, tester en 4G/5G.

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Audit sécurité complet : suppression de `deploy.tixhon.be` (DNS + route tunnel, backend 192.168.10.21:9000 injoignable et sans protection) ; Access ajouté puis retiré sur `vw` (incompatible app Bitwarden native, cf. section Vaultwarden) ; Access ajouté puis retiré sur `hass` (incompatible app companion HA Android, cf. section Home Assistant) ; mise à jour `cloudflared` (2025.2.1 → dernière version) |

---

## Home Assistant

**Rôle** : domotique, automatisations (parental control internet via pfSense, voir `docs/network/`).

**Hébergement** : VM 100 (`haos12.4`, Home Assistant OS) sur Proxmox (nipogi), IP `192.168.10.10:8123`.

**Accès** :
- Web/app : https://hass.tixhon.be (via Cloudflare Tunnel → NPM `192.168.10.11:80` → `192.168.10.10:8123`)
- Pas d'add-on SSH activé (port 22 fermé) — pas d'accès shell direct à la VM

**Cloudflare Access (2026-07-25) — testé puis retiré** : Access (email OTP) fonctionnait très bien sur iPhone (l'app iOS ouvre une session web externe pour le challenge) mais **incompatible avec l'app companion Android** (`2026.6.5-full` testée) — erreur générique "Impossible de se connecter", aucune requête n'atteignant même Cloudflare (confirmé absence totale dans les logs Access). Cause confirmée par la communauté HA : les apps mobiles ne gèrent nativement que mTLS pour bypasser Access, pas de champ Client ID/Secret contrairement à ce qui avait été supposé initialement. mTLS indisponible sur notre plan Cloudflare (même limitation que pour Vaultwarden). Retiré, protection = login HA natif (username/password).

**Sécurité (audit 2026-07-25)** :
- Version 2026.7.2, à jour
- 2FA (TOTP) disponible par utilisateur (Réglages → Personnes → Sécurité) mais **pas de mode "forcé" côté admin** — limitation native de Home Assistant (pas de fonctionnalité pour imposer la MFA à tous les comptes), donc à activer manuellement par chaque utilisateur
- `internal_url` / `external_url` étaient à `null` — configurés via l'API websocket (`config/core/update`) : `internal_url: http://192.168.10.10:8123`, `external_url: https://hass.tixhon.be`
- Composant `cloud` (Nabu Casa) chargé mais aucune entité `remote_ui` active — pas de second point d'exposition externe en parallèle du Tunnel
- HACS installé (intégrations communautaires) — surface d'attaque supply-chain à garder en tête, pas d'action immédiate
- 2 comptes utilisateurs (`rtixhon`, `celine`), pas de compte fantôme

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Cloudflare Access ajouté puis retiré (incompatible app companion Android) ; audit sécurité (2FA non forçable nativement, `internal_url`/`external_url` configurés, Nabu Casa non actif) |

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
