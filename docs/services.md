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
| Homelab Dashboard | Mac Mini | 192.168.10.98:8160 | http://dashboard.tixhon.be (LAN only) | React + Express (LaunchAgent) |
| Pocket ID | LXC 104 | 192.168.10.188 | https://id.tixhon.be | Pocket ID v2.11.0 (binaire + systemd) |

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
| 2026-07-25 | Suppression de `/etc/prometheus/rules/test.yml` (LXC 113) — règle `TestAlert` (`expr: vector(1)`) toujours active, spammait Telegram toutes les 4h (`repeat_interval` Alertmanager) |
| 2026-06-27 | Kernel reboot → 6.8.12-30-pve, reboot=pci GRUB fix |
| 2026-06-26 | 69 paquets sécurité, qemu-server 8.4.8, kernel épinglé |

---

## Pocket ID (SSO)

**Rôle** : fournisseur d'identité OIDC/OAuth2 self-hosted basé sur les passkeys (WebAuthn), utilisé pour centraliser l'authentification des services qui supportent OIDC nativement. **Ce n'est pas un reverse-proxy à la Authelia/Cloudflare Access** — seules les apps qui parlent OIDC nativement peuvent être protégées ainsi.

**Hébergement** : LXC 104 sur Proxmox (nipogi), Debian 13, IP réservée DHCP `192.168.10.188`, port 1411.

**Installation** : binaire officiel + systemd (`pocketid.service`) — le script `community-scripts/ProxmoxVE` dépend de leur framework interne, pas réutilisable tel quel en SSH standalone.

**Accès** :
- Web : https://id.tixhon.be (NPM → 192.168.10.188:1411 → Cloudflare Tunnel `nipogi-homelab` → DNS proxied)
- Auth admin : passkey (WebAuthn), pas de mot de passe
- API : clé API générée dans Settings → Admin → API Keys, header `X-API-KEY` (pas `Authorization: Bearer`)

**Services intégrés (clients OIDC)** :

| Service | Callback | Statut |
|---|---|---|
| Grafana (LXC 107) | `https://grafana.tixhon.be/login/generic_oauth` | ✅ testé |
| Linkwarden (LXC 114) | `https://linkwarden.tixhon.be/api/v1/auth/callback/authentik` | ✅ testé |
| Komga (Docker TischNAS3) | `https://komga.tixhon.be/login/oauth2/code/pocketid` | ✅ testé |
| Vaultwarden (LXC 110) | `https://vw.tixhon.be/identity/connect/oidc-signin` | ❌ écarté définitivement — risque de dépendance circulaire (la passkey Pocket ID est stockée dans Vaultwarden ; un SSO obligatoire dessus pourrait provoquer un verrouillage total). Client OIDC créé côté Pocket ID mais restera inutilisé, mot de passe maître reste l'unique login Vaultwarden |

**Services écartés (pas de support OIDC réaliste)** : AdGuard Home, NPM, stack Servarr (Sonarr/Radarr/Prowlarr/Bazarr/Readarr/qBittorrent), Home Assistant, pfSense, Prometheus/Alertmanager/Blackbox, MQTT/Zigbee2MQTT, RustDesk Server, Jellyseerr, Jellyfin (plugin communautaire tiers instable, écarté).

**Pièges rencontrés** :
- **Linkwarden** : pas de provider OIDC "générique/custom" — NextAuth utilise le provider `AuthentikProvider`, callback `/api/v1/auth/callback/authentik` (pas `/custom`).
- **Grafana/NPM** : `ssl_forced=true` sur un proxy host NPM devant un service qui ne force pas HTTPS lui-même crée une boucle de redirection infinie derrière le Cloudflare Tunnel. Toujours `ssl_forced=false` pour les services derrière le tunnel.
- **Komga** (Spring Security/Kotlin) : le vrai callback OAuth2 est `/login/oauth2/code/{registrationId}`, configuré dans `application.yml` (pas de variables d'env) monté depuis `/volume1/docker/_Configs/Komga` sur TischNAS3. Deux blocages additionnels : (1) PKCE doit être **désactivé** côté client Pocket ID pour les clients confidentiels (avec secret) comme Komga, sinon `invalid_request` ("code_challenge missing") ; (2) Komga exige `email_verified: true`, or Pocket ID renvoie `false` par défaut (pas de vérification email via passkey) — fix : activer "E-mails vérifiés par défaut" (Config app → E-mail) puis forcer `emailVerified: true` sur l'utilisateur existant via `PUT /api/users/{id}` (le toggle seul n'agit que sur les futurs changements d'email, pas rétroactivement).

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-08-02 | Komga configuré et testé de bout en bout (callback corrigé, PKCE désactivé, `email_verified` forcé à `true` via API) ; Vaultwarden écarté définitivement (risque de dépendance circulaire passkey/vault) ; fallback auth locale vérifié manuellement sur Grafana/Linkwarden/Komga |
| 2026-07-28/29 | Installation initiale (LXC 104, binaire + systemd), exposition publique, clients OIDC créés pour Grafana/Linkwarden/Komga/Vaultwarden, Grafana et Linkwarden testés de bout en bout |

---

## Homelab Dashboard

**Rôle** : dashboard interne (statut infra, inventaire devices, actions rapides). Pas exposé sur internet — domaine `dashboard.tixhon.be` résolu uniquement en LAN via AdGuard (pas de DNS public), proxifié par NPM → `192.168.10.98:8160`.

**Hébergement** : Mac Mini de Rudy (`192.168.10.98`), process Node/Express lancé via LaunchAgent macOS (`~/Library/LaunchAgents/be.tixhon.homelab-dashboard.plist`, `KeepAlive: true`), logs dans `/tmp/homelab-dashboard.log` / `.err`.

**Architecture** : le serveur (`server/routes/status.js`) interroge en direct — SSH vers Proxmox (`root@192.168.10.2`) pour NIPoGi/HAOS/LXC (via `pct exec`), Prometheus (`192.168.10.184:9090`) pour les NAS via `node_exporter`, l'API pfSense pour le WAN — et pousse le résultat au client via SSE (`GET /api/status/stream`, poll 30s).

**Incident (2026-07-25) — dashboard vide (CPU/RAM/Disk à "—" partout)** : trois causes distinctes cumulées, diagnostiquées via le navigateur (Claude in Chrome) + accès direct au Mac Mini (SSH `rudytixhon@192.168.10.98` + accès local, ce Mac étant aussi la machine hôte de cette session Claude Code) :

1. **`node_exporter` arrêté sur TischNAS3** — processus tourné en tant que binaire lancé manuellement (pas un vrai service systemd/Task Scheduler persistant), s'est arrêté à un moment donné sans redémarrage auto. Relancé manuellement (`nohup /usr/local/bin/node_exporter --web.listen-address=:9100 &`), confirmé via Prometheus (`up{instance="TischNAS3"}` → `1`). **Non résolu de façon durable** — recommandé de créer une vraie tâche persistante (Task Scheduler DSM au boot) pour éviter la récidive.
2. **Les 3 Deco M4R (Grenier/Mezzanine/Salon) marqués "Hors ligne"** — faux négatif : `checkPort()` teste le port 22 (SSH) par défaut quand `port` n'est pas défini dans `inventory.json`, or ces routeurs n'exposent pas de SSH (confirmé `ECONNREFUSED` sur 22, `succeeded` sur 80). Fix : ajout de `"port": 80` sur les 3 entrées `deco-*` dans `server/data/inventory.json` (pas de redémarrage nécessaire, le fichier est relu à chaque poll).
3. **Bug macOS le plus sournois : permission "Réseau local" manquante pour le process LaunchAgent** — le même code (`checkPort` via `net.Socket`), lancé manuellement dans un terminal, réussit toutes les connexions LAN (`192.168.10.x`) ; lancé via `launchd` (LaunchAgent), **toutes les connexions échouent silencieusement** (`ECONNREFUSED`/timeout sur tout, y compris des cibles confirmées joignables au même instant via `nc`/`ssh` direct). Confirmé par test isolé (mini-serveur Express de debug) : succès en foreground, échec identique une fois passé par `launchd`. Cause probable : macOS TCC (Privacy & Security → Réseau local) n'accorde pas la permission à un process lancé en headless via LaunchAgent, contrairement à un process hérité d'une session Terminal déjà autorisée. **Non résolu** — nécessite une action utilisateur (redémarrage du Mac pour re-déclencher la popup d'autorisation système, ou ajout manuel dans Réglages Système → Confidentialité et sécurité → Réseau local).

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Incident dashboard vide : `node_exporter` relancé sur TischNAS3 (non persistant), `inventory.json` corrigé (port 80 sur les 3 Deco), permission macOS "Réseau local" identifiée comme cause racine du 3ᵉ symptôme (non résolue, nécessite reboot + action utilisateur) |
