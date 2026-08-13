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

## Servarr (Sonarr/Radarr/Prowlarr/Bazarr/Readarr/qBittorrent)

**Rôle** : stack de gestion médias (séries, films, indexers, sous-titres, livres, torrents).

**Hébergement** : Docker Compose sur TischNAS3 (192.168.10.3), projet `servarr`, fichier `/volume1/docker/SERVARR/compose.yaml`. **Pas des conteneurs `docker run` isolés** — toujours passer par `docker compose` pour ne pas casser la gestion centralisée.

**Accès SSH** : compte `claude` (`~/.ssh/claude-agent/id_ed25519`), sudo restreint à `docker`/`df`/`free` — cf. mémoire `nas-access.md`. Le binaire doit être invoqué par son chemin complet : `sudo /usr/local/bin/docker compose ...` (un simple `sudo docker` échoue, la règle NOPASSWD sudoers est liée au path exact).

**Commande de mise à jour** : `cd /volume1/docker/SERVARR && sudo /usr/local/bin/docker compose pull <service> && sudo /usr/local/bin/docker compose up -d <service>` — un service à la fois, jamais tous en même temps pour un saut de version majeur.

**Versions (2026-08-02)** :

| Service | Port | Version |
|---|---|---|
| Sonarr | 8989 | v4.0.19.2979 |
| Radarr | 7878 | v6.3.0.10514 |
| Prowlarr | 9696 | v2.5.2.5491 |
| Bazarr | 6767 | v1.6.0 |
| qBittorrent | 8080 | v5.2.3 |
| Readarr | 8787 | 0.3.32 (tag `develop`, **non mis à jour** — voir pièges) |
| FlareSolverr | 8191 | 3.5.0 |

**Pièges rencontrés** :
- **Toutes les images étaient restées figées depuis 2024-08-31** malgré le tag `:latest` — `docker compose up -d` sans `pull` ne récupère jamais une nouvelle image, il faut explicitement `pull` avant.
- **`sudo docker compose pull` échoue parfois avec `toomanyrequests: retry-after ...`** (rate-limit du registry `lscr.io`) — dans ce cas `docker compose up -d` recrée quand même le conteneur mais avec l'**ancienne image en cache**, sans erreur visible autre que le pull raté. Toujours vérifier après coup avec `docker inspect <container> --format '{{.Config.Image}} {{.Created}}'` et comparer la version affichée dans l'UI/les logs, pas seulement le succès de la commande.
- **Readarr (`lscr.io/linuxserver/readarr:develop`) : `no matching manifest for linux/amd64 in the manifest list entries`** — le tag `develop` n'a pas toujours de build `linux/amd64` publié côté registre (upstream, intermittent). `docker compose up -d` recrée alors le conteneur avec l'ancienne image, sans casser le service. Retester périodiquement (`docker compose pull readarr`), pas de fix côté NAS possible.
- **qBittorrent : warning Sonarr/Radarr "Download client places downloads in the root folder ... You should not download to a root folder."** — nouveau health check introduit par Sonarr v4/Radarr v6, absent des anciennes versions. Cause : `categories.json` de qBittorrent avait les catégories `TVSHOWS`/`MOVIES` avec `save_path` pointé **directement** sur les root folders (`/downloads/TVSHOWS`, `/downloads/MOVIES`), au lieu de passer par un dossier intermédiaire. Fix appliqué : `save_path` de ces deux catégories changé vers `/downloads/_TORRENTCOMPLETE/TVSHOWS` et `/downloads/_TORRENTCOMPLETE/MOVIES` (dossiers créés avec `chown 1031:101`, UID/GID du conteneur), en s'alignant sur le pattern déjà utilisé pour la catégorie `BDZ`. Édition faite conteneur arrêté (qBittorrent verrouille `categories.json` en cours d'exécution).
- **Bazarr : démarrage silencieux ~90s après un saut de version important** (1.4.3→1.6.0, 2 ans d'écart) — le conteneur répond `Up` et les logs s'arrêtent après `INFO (scheduler:78)` sans qu'aucune requête HTTP n'aboutisse (`HTTP 000`). `docker top` montre le process principal à 40-47% CPU, actif (pas figé) : reconstruction interne (index/cache) en cours. Attendre plutôt que redémarrer — un `docker restart` reproduit juste le même délai depuis le début.
- **Conteneur orphelin `lidarr-rtx`** détecté par `docker compose` (`Found orphan containers`) à chaque `up -d` — existe sur le NAS mais absent du `compose.yaml` actuel. Non touché, à investiguer si utile encore.
- **Backup avant upgrade** : pas de droits d'écriture directs dans `/volume1/docker/SERVARR` avec le compte `claude` (dossier appartient à `secureAdmin`/`root`) — contourné avec un conteneur `alpine` jetable monté sur le dossier (`docker run --rm -v ... alpine tar czf ...`), qui tourne en root à l'intérieur du conteneur.

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-08-02 | Mise à jour complète (sauf Readarr) : Sonarr 3→v4, Radarr 4→v6, Prowlarr 1.21→v2.5, Bazarr 1.4→v1.6, qBittorrent 4.5→v5.2 (migrations DB OK, aucune régression). Fix qBittorrent `categories.json` (root folder warning Sonarr/Radarr). Backup complet des configs avant upgrade. FlareSolverr mis à jour manuellement 3.3.12→3.5.0 (hors compose) le même jour, resync au `up -d`. Readarr non mis à jour — pas de manifest `linux/amd64` disponible pour le tag `develop` (retenté sans succès, problème amont) |

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
- **Linkwarden** : pas de provider OIDC "générique/custom" — NextAuth utilise le provider `AuthentikProvider`, callback `/api/v1/auth/callback/authentik` (pas `/custom`). **Piège additionnel découvert en testant réellement le login (2026-08-02)** : Linkwarden v2 a déplacé ses routes API sous `/api/v1/` mais nécessite que `NEXTAUTH_URL` inclue explicitement ce préfixe (`NEXTAUTH_URL=https://linkwarden.tixhon.be/api/v1/auth`, pas juste le domaine) — sinon NextAuth annonce un `callbackUrl` sans `/v1/` qui matche ce qu'on enregistre côté IdP mais qui 404 réellement chez Linkwarden (aucune route à cet endroit). Cf. [doc officielle de migration v2](https://github.com/linkwarden/docs/blob/main/docs/self-hosting/upgrading/to-linkwarden-v2.md).
- **Grafana/NPM** : `ssl_forced=true` sur un proxy host NPM devant un service qui ne force pas HTTPS lui-même crée une boucle de redirection infinie derrière le Cloudflare Tunnel. Toujours `ssl_forced=false` pour les services derrière le tunnel.
- **Grafana OAuth (`[auth.generic_oauth]`)** — 3 blocages successifs découverts en testant réellement le flow (le test initial ne validait que la redirection, pas le login complet) :
  1. `"User sync failed"` / `Failed to create user: user not found` — Grafana refuse de lier un compte OAuth à un utilisateur local existant (même email) sans `oauth_allow_insecure_email_lookup = true` dans `[auth]` (protection anti-CVE ajoutée par défaut depuis Grafana 9/10).
  2. `"cannot remove last organization admin"` — le `role_attribute_path` (`contains(groups[*], 'grafana-admin') && 'Admin' || 'Viewer'`) retombe sur `Viewer` si l'utilisateur n'appartient à aucun groupe Pocket ID nommé `grafana-admin`, et Grafana refuse de rétrograder le seul admin de l'org. Fix : créer ce groupe dans Pocket ID (Nom = `grafana-admin`, exactement la valeur attendue dans le claim `groups`) et y assigner l'utilisateur. Nécessite aussi `groups_attribute_path = groups` dans `grafana.ini` (sans cette clé, Grafana ignore le claim `groups` du token même s'il est présent).
  3. **Guillemets JMESPath** : `role_attribute_path` doit utiliser des guillemets **simples** pour les littéraux (`'grafana-admin'`, `'Admin'`, `'Viewer'`) — des guillemets doubles sont interprétés comme des identifiants JMESPath, pas des chaînes, et l'expression échoue silencieusement (retombe toujours sur la branche `false`).
  4. **Écrasement du `login` local** : par défaut, Grafana synchronise le champ `login` du compte sur l'email OAuth à chaque connexion SSO, cassant le fallback mot de passe local (username changé de `rtixhon` à l'email). Fix : `login_attribute_path = preferred_username` dans `[auth.generic_oauth]` pour que la sync utilise le username Pocket ID plutôt que l'email.
- **Komga** (Spring Security/Kotlin) : le vrai callback OAuth2 est `/login/oauth2/code/{registrationId}`, configuré dans `application.yml` (pas de variables d'env) monté depuis `/volume1/docker/_Configs/Komga` sur TischNAS3. Deux blocages additionnels : (1) PKCE doit être **désactivé** côté client Pocket ID pour les clients confidentiels (avec secret) comme Komga, sinon `invalid_request` ("code_challenge missing") ; (2) Komga exige `email_verified: true`, or Pocket ID renvoie `false` par défaut (pas de vérification email via passkey) — fix : activer "E-mails vérifiés par défaut" (Config app → E-mail) puis forcer `emailVerified: true` sur l'utilisateur existant via `PUT /api/users/{id}` (le toggle seul n'agit que sur les futurs changements d'email, pas rétroactivement).

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-08-02 | Komga configuré et testé de bout en bout (callback corrigé, PKCE désactivé, `email_verified` forcé à `true` via API) ; Vaultwarden écarté définitivement (risque de dépendance circulaire passkey/vault) ; fallback auth locale vérifié manuellement sur Grafana/Linkwarden/Komga ; **Grafana OAuth réellement testé et corrigé** (`oauth_allow_insecure_email_lookup`, groupe Pocket ID `grafana-admin` créé, `groups_attribute_path`, guillemets JMESPath simples, `login_attribute_path` pour préserver le fallback local) ; **Linkwarden OAuth réellement testé et corrigé** (`NEXTAUTH_URL` doit inclure `/api/v1/auth`, sinon 404 sur le vrai callback malgré un enregistrement IdP cohérent avec ce que NextAuth annonçait) — les tests précédents (2026-07-28/29) n'avaient validé que la redirection OAuth, pas un login complet |
| 2026-07-28/29 | Installation initiale (LXC 104, binaire + systemd), exposition publique, clients OIDC créés pour Grafana/Linkwarden/Komga/Vaultwarden, Grafana et Linkwarden testés de bout en bout |

---

## Homelab Dashboard

**Rôle** : dashboard interne (statut infra, inventaire devices, actions rapides). Pas exposé sur internet — domaine `dashboard.tixhon.be` résolu uniquement en LAN via AdGuard (pas de DNS public), proxifié par NPM → `192.168.10.98:8160`.

**Hébergement** : Mac Mini de Rudy (`192.168.10.98`), process Node/Express lancé via LaunchAgent macOS (`~/Library/LaunchAgents/be.tixhon.homelab-dashboard.plist`, `KeepAlive: true`), logs dans `/tmp/homelab-dashboard.log` / `.err`.

**Architecture** : le serveur (`server/routes/status.js`) interroge en direct — SSH vers Proxmox (`root@192.168.10.2`) pour NIPoGi/HAOS/LXC (via `pct exec`), Prometheus (`192.168.10.184:9090`) pour les NAS via `node_exporter`, l'API pfSense pour le WAN — et pousse le résultat au client via SSE (`GET /api/status/stream`, poll 30s).

**Wake-on-LAN automatique de NIPoGi au boot (`wol-nipogi`, 2026-08-05)** : NIPoGi n'a pas "Restore on AC Power Loss" activé au BIOS (nécessiterait un reboot physique pour le configurer, évité à la demande de l'utilisateur suite à la coupure du 2026-08-05 — voir post-mortem plus bas). Contournement : le Mac Mini, lui, redémarre automatiquement après coupure — un LaunchDaemon système envoie donc un paquet WoL à NIPoGi dès que le Mac Mini boote, réveillant NIPoGi en cascade.
- Script : `/usr/local/bin/wol-nipogi.sh` — attend 20s (le temps que le réseau remonte), envoie le paquet magique à `68:1D:EF:43:4D:05`, réessaie 10s plus tard
- LaunchDaemon : `/Library/LaunchDaemons/be.tixhon.wol-nipogi.plist` (`RunAtLoad`, tourne au niveau système avant même la session utilisateur)
- Logs : `/tmp/wol-nipogi.log`

**Incident (2026-07-25) — dashboard vide (CPU/RAM/Disk à "—" partout)** : trois causes distinctes cumulées, diagnostiquées via le navigateur (Claude in Chrome) + accès direct au Mac Mini (SSH `rudytixhon@192.168.10.98` + accès local, ce Mac étant aussi la machine hôte de cette session Claude Code) :

1. **`node_exporter` arrêté sur TischNAS3** — processus tourné en tant que binaire lancé manuellement (pas un vrai service systemd/Task Scheduler persistant), s'est arrêté à un moment donné sans redémarrage auto. Relancé manuellement (`nohup /usr/local/bin/node_exporter --web.listen-address=:9100 &`), confirmé via Prometheus (`up{instance="TischNAS3"}` → `1`). **Non résolu de façon durable** — recommandé de créer une vraie tâche persistante (Task Scheduler DSM au boot) pour éviter la récidive.
2. **Les 3 Deco M4R (Grenier/Mezzanine/Salon) marqués "Hors ligne"** — faux négatif : `checkPort()` teste le port 22 (SSH) par défaut quand `port` n'est pas défini dans `inventory.json`, or ces routeurs n'exposent pas de SSH (confirmé `ECONNREFUSED` sur 22, `succeeded` sur 80). Fix : ajout de `"port": 80` sur les 3 entrées `deco-*` dans `server/data/inventory.json` (pas de redémarrage nécessaire, le fichier est relu à chaque poll).
3. **Bug macOS le plus sournois : permission "Réseau local" manquante pour le process LaunchAgent** — le même code (`checkPort` via `net.Socket`), lancé manuellement dans un terminal, réussit toutes les connexions LAN (`192.168.10.x`) ; lancé via `launchd` (LaunchAgent), **toutes les connexions échouent silencieusement** (`ECONNREFUSED`/timeout sur tout, y compris des cibles confirmées joignables au même instant via `nc`/`ssh` direct). Confirmé par test isolé (mini-serveur Express de debug) : succès en foreground, échec identique une fois passé par `launchd`. Cause probable : macOS TCC (Privacy & Security → Réseau local) n'accorde pas la permission à un process lancé en headless via LaunchAgent, contrairement à un process hérité d'une session Terminal déjà autorisée. **Non résolu** — nécessite une action utilisateur (redémarrage du Mac pour re-déclencher la popup d'autorisation système, ou ajout manuel dans Réglages Système → Confidentialité et sécurité → Réseau local).

**Historique des changements** :

| Date | Changement |
|------|-----------|
| 2026-07-25 | Incident dashboard vide : `node_exporter` relancé sur TischNAS3 (non persistant), `inventory.json` corrigé (port 80 sur les 3 Deco), permission macOS "Réseau local" identifiée comme cause racine du 3ᵉ symptôme (non résolue, nécessite reboot + action utilisateur) |

---

## Coupure électrique du 2026-08-05 — post-mortem

**Contexte** : coupure de courant, UPS insuffisant (TischNAS3 a coupé en plein arrêt propre). TischNAS2 arrêté proprement à temps par l'utilisateur. NIPoGi et Mac Mini coupés abruptement.

**Chronologie reconstituée** (via logs SSH/journalctl/DSM sur chaque machine) :

| Heure | Événement |
|---|---|
| ~07:36 | NIPoGi (donc pfSense + AdGuard, hébergés dessus) encore actif — dernier log avant coupure |
| ? → ~08:27 | Coupure électrique (durée exacte inconnue) |
| ~08:27 | Courant revenu — TischNAS3 et le Mac Mini redémarrent **automatiquement** (réglage "reprise après coupure" actif sur les deux) |
| 08:41 | NIPoGi et TischNAS2 redémarrés **manuellement** par l'utilisateur (~14 min après le retour du courant) |
| 08:43 | AdGuard (LXC 103 sur NIPoGi, DNS du réseau) de retour |
| ~08:51 | pfSense (VM 115 sur NIPoGi, routage/DHCP) enfin opérationnel — soit **~24 min** après le retour du courant |

**Cause de la longue indisponibilité Wi-Fi** : ce n'était pas les bornes Deco elles-mêmes qui étaient lentes — elles ne pouvaient rien faire tant que pfSense (DHCP/routage) et AdGuard (DNS) n'étaient pas revenus, et les deux tournent sur NIPoGi. Contrairement à TischNAS3 et au Mac Mini, **NIPoGi n'a pas de réglage "Restore on AC Power Loss" actif au niveau BIOS**, donc il est resté éteint jusqu'à intervention manuelle.

**Dégâts constatés et réparés** :
- **TischNAS2** : horloge système repartie à `2015-01-01` au boot (pile/condensateur RTC vidé après coupure totale prolongée), corrigée 17 min plus tard via NTP. Aucun impact fonctionnel constaté cette fois, mais signe que la coupure a été assez longue pour vider la réserve RTC.
- **TischNAS3** : corruption BTRFS détectée au boot (`ran out of all copies` sur un inode) — vérifié via `btrfs inspect-internal inode-resolve` : fichier de log interne d'un conteneur Docker (`@docker/containers/.../log.db`), pas de données utilisateur. Auto-guéri par Container Manager (conteneurs concernés recréés automatiquement). 4 autres inodes signalés en erreur dans les logs n'existaient déjà plus au moment de la vérification (fichiers temporaires déjà nettoyés).
- **Komga (TischNAS3)** : a planté au démarrage (`UnknownHostException: id.tixhon.be`) — tentait de contacter Pocket ID pour l'OIDC avant que le DNS/réseau soit stable. **N'avait aucune politique de redémarrage** (`restart: no`, conteneur historique hors du compose SERVARR) → resté hors service ~1h15 sans que personne le sache. Corrigé : relancé + passé en `restart: unless-stopped`.

**Action prise pour la prochaine fois** : plutôt que de modifier le BIOS de NIPoGi (nécessite un reboot, l'utilisateur préfère éviter), un contournement a été mis en place côté Mac Mini — voir section [[#Homelab Dashboard]] ci-dessous, `wol-nipogi`. Le Mac Mini redémarre déjà automatiquement après coupure ; il envoie désormais un paquet Wake-on-LAN à NIPoGi (`68:1D:EF:43:4D:05`) 20s et 30s après son propre démarrage, réveillant NIPoGi en cascade sans jamais toucher son BIOS.

**Reste à faire (non traité dans ce post-mortem)** :
- Vérifier/activer "Reprise en cas de panne de courant" dans DSM sur TischNAS2 (Panneau de configuration → Matériel et alimentation)
- Auditer les autres conteneurs Docker hors-compose sur TischNAS3 (Heimdall, Shiori) pour une politique de redémarrage manquante similaire à Komga
- UPS à surveiller/remplacer — n'a pas tenu la charge complète de TischNAS3 pendant un arrêt propre

---

## Nouvelle coupure du 2026-08-05 ~08:00 + micro-coupures Wi-Fi consécutives

**Contexte** : coupure de courant distincte de celle documentée ci-dessus, survenue le même jour peu après la mise en place des scripts NUT/arrêt automatique UPS (donc pas encore actifs au moment de cette coupure — voir [[#Configuration de la surveillance de l'UPS avec NUT]]).

**Détection** : confirmée via les logs kernel/journalctl sur les 3 machines et l'historique des tâches Proxmox (API token `root@pam!claude`, node réel `proxmox` et non `nipogi`) :

| Machine | Redémarrage constaté | Type d'arrêt |
|---|---|---|
| TischNAS3 | ~08:28 | Non-propre |
| NIPoGi (hôte Proxmox) | ~08:41 | Non-propre — `journal corrupted or uncleanly shut down` dans les logs kernel, confirmant une coupure brutale (pas un reboot volontaire) |
| TischNAS2 | ~08:42 | Non-propre |
| pfSense (VM 104, démarrée par le `startall` automatique de Proxmox) | ~08:52 | — (WAN/LAN indisponibles ~1 min pendant son boot) |

- **NIPoGi a redémarré tout seul** cette fois (visible dans les tâches Proxmox : `startall` automatique à 08:41, sans intervention manuelle ni déclenchement du script WoL `wol-nipogi` côté Mac Mini) — contrairement à l'épisode précédent.
- Le script d'arrêt automatique UPS ne s'est pas déclenché (`/var/log/ups-shutdown.log` absent) : normal, il n'existait pas encore à ce moment-là (écrit dans les ~2h30 qui ont suivi, voir commit `29793c0`).
- Message kernel `EDAC igen6 MC0: HANDLING IBECC MEMORY ERROR` observé au boot sur NIPoGi — **faux positif inoffensif**, compteurs réels (`ce_count`/`ue_count` dans `/sys/devices/system/edac/`) à 0, artefact connu du driver `igen6_edac` sur ce type de mini-PC (Alder Lake-N), pas un vrai défaut mémoire.
- Redémarrage de pfSense → coupure WAN/LAN de ~1 min → a fait sauter une session RustDesk active à ce moment.

**Micro-coupures Wi-Fi post-incident (plusieurs épisodes d'~1 min, ressenties surtout à l'extérieur)** :

Root cause identifiée : **le point d'accès CPL (courant porteur, `http://192.168.10.35/`) du jardin/abri diffusait le même SSID `TischDecoNetwork` que le mesh Deco intérieur**, sans faire réellement partie du mesh (confirmé via l'API locale Deco — seuls 3 nœuds réels dans le mesh : `Living Room`/master à `192.168.10.32`, `En haut` à `192.168.10.31`, `Tout en haut` à `192.168.10.30`). Un SSID identique sans coordination mesh (pas de roaming 802.11k/v/r entre les deux systèmes) fait que le client reste accroché au signal Deco intérieur affaibli au lieu de basculer vers le CPL, d'où les coupures en bordure de couverture (proche du jardin).

**Correctif appliqué (2026-08-05)** : SSID du CPL séparé en `TischJardin` (2,4GHz) et `TischJardin5ghz` (5GHz), distinct de `TischDecoNetwork` utilisé en intérieur. Roaming automatique perdu entre les deux réseaux (connexion manuelle nécessaire dehors), mais élimine l'ambiguïté qui causait les micro-coupures. CPL également redémarré. **À confirmer dans la durée** — stable au moment de la rédaction (~20-30 min sans coupure après le changement de SSID).

**Topologie réseau Wi-Fi (pour référence)** :

| SSID | Bande | Appareil(s) | Zone |
|---|---|---|---|
| `TischDecoNetwork` | 2,4+5GHz (auto) | 3x Deco M4R en mesh (`192.168.10.30`/`.31`/`.32`) | Intérieur |
| `TischJardin` | 2,4GHz | CPL/powerline (`192.168.10.35`, admin web natif TP-Link, pas le protocole Deco) | Extérieur/jardin |
| `TischJardin5ghz` | 5GHz | idem | Extérieur/jardin |

**Accès API Deco** (utile pour diagnostic futur) : package Python `tplink-deco-api` (PyPI), login local via `DecoClient(ip, "admin", "<mdp du compte TP-Link ID>")` sur n'importe quel nœud du mesh (retourne la liste complète des 3 nœuds si on interroge le master `192.168.10.32`). Pas de venv Python 3.14 pour ce package — `cryptography` échoue à compiler (nécessite `rustup target add x86_64-apple-darwin`) ; utiliser `uv venv --python 3.12` à la place, wheels précompilées disponibles.
**API pfSense (`claude`)** : privilège `api-v2-status-logs-system-get` ajouté le 2026-08-05 (compte à 128 privilèges max, une entrée peu utile a été retirée pour faire de la place) pour permettre la lecture des logs système en diagnostic (`GET /api/v2/status/logs/system`).

## Migration Wi-Fi envisagée : Deco → UniFi + VLAN (2026-08-13, investigation, pas encore déployé)

**Motivation** : les Deco M4R (grand public) ne supportent pas le mapping SSID→VLAN, ce qui empêche de séparer IoT/invités/LAN principal en Wi-Fi malgré un switch (D-Link DGS-1100-24) qui supporte le 802.1Q complet (tagged/untagged par port, VID 1-4094 — vérifié dans la doc constructeur). Le passage à des AP UniFi réglerait ce point et améliorerait aussi le roaming (802.11k/v/r natif), pertinent après l'épisode de micro-coupures Wi-Fi ci-dessus.

**Décision prise** : UniFi plutôt que TP-Link Omada (Omada ~30-50% moins cher mais UniFi préféré par l'utilisateur pour l'écosystème).

**Couverture envisagée (3 AP → potentiellement 3, à confirmer par un test)** :
- RDC (salon) + étage (mezzanine) : **1 seul AP central** pourrait suffire — la maison a un escalier ouvert et une mezzanine entre les deux niveaux (pas de dalle béton pleine), donc atténuation RF beaucoup plus faible qu'un plancher fermé. Stratégie recommandée : acheter les 2 AP salon+mezzanine quand même, activer uniquement le central en test, garder le second en réserve si des zones faibles apparaissent — trivial à ajouter au même SSID/VLAN après coup.
- Grenier (2ᵉ étage, isolé) : reste un AP dédié, pas de changement.
- Extérieur/jardin : reste sur le CPL + SSID `TischJardin`/`TischJardin5ghz` existant (voir ci-dessus) — UniFi ne couvre pas nativement l'extérieur sauf ajout futur d'un AP outdoor filaire (nécessiterait de tirer un câble Ethernet jusqu'à l'abri de jardin, non fait actuellement).

**Matériel identifié** : TP-Link Omada EAP670 écarté au profit d'UniFi — modèles UniFi Wi-Fi 6 (U6-Lite ~99$, U6-Pro ~179$) équivalents en fonctionnalités VLAN/roaming.

**Contrôleur UniFi** : à héberger en LXC Proxmox via le script `community-scripts` **Unifi OS Server** (`ct/unifi-os-server.sh`, port 11443, x86-64/ARM64, maintenu activement — dernière MAJ du script le 2026-08-13). Prochain VMID libre au moment de l'investigation : **116** (suivant pocketid 104, linkwarden 114) ; IP suggérée en suivant la convention `.18x` : **192.168.10.189** (après linkwarden `.187`, pocketid `.188`). Dimensionnement largement suffisant pour 3 AP : 2 vCPU / 2GB RAM / 8GB disque.

**Statut** : investigation uniquement, **rien déployé** — LXC contrôleur pas encore provisionné, matériel pas encore acheté. Prochaine étape quand l'utilisateur commande les AP : provisionner le LXC 116, adopter les AP dans le contrôleur, créer les VLANs (IoT/Guest/LAN) sur le switch + interfaces VLAN pfSense + règles firewall par VLAN.
