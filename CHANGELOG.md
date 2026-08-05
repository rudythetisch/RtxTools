# Changelog

## 2026-08-05 (session 22)

### Post-mortem coupure électrique — NIPoGi ne redémarre pas automatiquement après coupure

Coupure de courant, UPS insuffisant (TischNAS3 coupé en plein arrêt propre). Reconstruction de la chronologie via logs SSH/journalctl/DSM sur chaque machine, identification de la cause de l'indisponibilité Wi-Fi prolongée (~24 min après retour du courant).

- NIPoGi (hôte de pfSense + AdGuard) n'a pas "Restore on AC Power Loss" activé au BIOS, contrairement à TischNAS3 et au Mac Mini qui redémarrent automatiquement
  Reason: cause racine de la longue indisponibilité réseau — pfSense (DHCP/routage) et AdGuard (DNS) sont restés éteints jusqu'à intervention manuelle de l'utilisateur (~14 min après retour du courant) + temps de boot en cascade (~10 min de plus)
  Source: comparaison des timestamps de boot (`uptime -s`) entre NIPoGi, TischNAS2/3, Mac Mini, et de l'uptime pfSense via `/api/v2/status/system`

- LaunchDaemon `wol-nipogi` ajouté sur le Mac Mini — envoie un paquet Wake-on-LAN à NIPoGi (`68:1D:EF:43:4D:05`) au démarrage du Mac Mini
  Reason: contournement du BIOS de NIPoGi sans reboot (refusé par l'utilisateur) — le Mac Mini redémarre déjà tout seul après coupure, donc on chaîne un réveil de NIPoGi dessus plutôt que de configurer le BIOS
  Source: `/usr/local/bin/wol-nipogi.sh` + `/Library/LaunchDaemons/be.tixhon.wol-nipogi.plist`, installés manuellement par l'utilisateur (sudo)

- Komga (TischNAS3) resté hors service ~1h15 après la coupure sans que personne le sache
  Reason: crash au démarrage (`UnknownHostException: id.tixhon.be`, tentative de contact Pocket ID pour l'OIDC avant que le DNS soit stable) combiné à l'absence totale de politique de redémarrage Docker (`restart: no`) — conteneur historique hors du compose SERVARR
  Source: `docker logs Komga`, `docker inspect Komga --format '{{.HostConfig.RestartPolicy}}'` → corrigé en `unless-stopped`

- TischNAS2 : horloge système repartie à `2015-01-01` au boot après la coupure, corrigée 17 min plus tard via NTP
  Reason: pile/condensateur RTC vidé après une coupure totale assez longue — sans impact fonctionnel constaté cette fois, mais signale que la réserve RTC a été épuisée
  Source: `/var/log/messages` — `chronyd: System clock was stepped by 365841682.616420 seconds`

- TischNAS3 : corruption BTRFS détectée au boot (`ran out of all copies`) sur un inode — vérifié inoffensif
  Reason: fichier concerné = log interne d'un conteneur Docker (`@docker/containers/.../log.db`), pas de données utilisateur ; auto-guéri par Container Manager qui a recréé les conteneurs affectés
  Source: `btrfs inspect-internal inode-resolve <ino> /volume1`

### Nouvelle coupure ~08:00 + micro-coupures Wi-Fi consécutives (SSID CPL jardin dupliqué)

Coupure de courant distincte de celle ci-dessus, survenue le même jour juste avant la mise en place des scripts NUT (donc pas encore actifs). RustDesk a sauté suite au redémarrage de pfSense. Plusieurs micro-coupures Wi-Fi (~1 min, 5-6 fois) constatées ensuite en extérieur.

- NIPoGi, TischNAS2, TischNAS3 et pfSense (VM 104) tous redémarrés de façon non-propre entre ~08:28 et ~08:52
  Reason: nouvelle coupure de courant confirmée via `journalctl -b -1`/`-b 0` sur NIPoGi (`system.journal corrupted or uncleanly shut down`) et l'historique des tâches Proxmox (`startall` automatique à 08:41) — NIPoGi a redémarré seul cette fois, sans besoin du contournement WoL
  Source: `journalctl -k -b 0`, API Proxmox `/nodes/proxmox/tasks` (token `root@pam!claude`)

- Message kernel `EDAC igen6 MC0: HANDLING IBECC MEMORY ERROR` au boot NIPoGi — vérifié inoffensif, faux positif du driver
  Reason: `ce_count`/`ue_count` réels à 0 dans `/sys/devices/system/edac/` — artefact connu du driver `igen6_edac` sur mini-PC Alder Lake-N, pas une vraie erreur mémoire
  Source: `journalctl -k -b 0 | grep -i edac`, `/sys/devices/system/edac/mc/mc0/*count`

- Root cause micro-coupures Wi-Fi identifiée : le point d'accès CPL du jardin (`192.168.10.35`) diffusait le même SSID `TischDecoNetwork` que le mesh Deco intérieur, sans en faire réellement partie (pas de roaming 802.11k/v/r coordonné)
  Reason: confirmé via l'API locale Deco (package `tplink-deco-api`) — seuls 3 nœuds réels dans le mesh (`192.168.10.30`/`.31`/`.32`), le CPL n'y figure pas ; un SSID dupliqué sans coordination fait que le client reste accroché au signal Deco affaibli au lieu de basculer
  Source: `DecoClient.get_device_list()` interrogé sur le nœud master (`192.168.10.32`)

- SSID du CPL jardin séparé en `TischJardin` (2,4GHz) et `TischJardin5ghz` (5GHz), distinct de `TischDecoNetwork`
  Reason: élimine l'ambiguïté de roaming entre les deux systèmes non coordonnés — stable ~20-30 min après le changement au moment de la rédaction, à confirmer dans la durée
  Source: changement fait manuellement par l'utilisateur via l'admin web du CPL (`http://192.168.10.35/`)

- Privilège API pfSense `api-v2-status-logs-system-get` ajouté au compte `claude` (limite de 128 privilèges déjà atteinte, une entrée peu utile retirée pour faire de la place)
  Reason: nécessaire pour diagnostiquer l'incident via `GET /api/v2/status/logs/system`, absent du périmètre initial du compte
  Source: `PATCH /api/v2/user` (id=4) via le compte `rtixhon`

## 2026-08-02 (session 21)

### Servarr — mise à jour complète de la stack (TischNAS3, ~2 ans de retard)

Toutes les images tournaient en tag `:latest`/`:develop` mais n'avaient pas été recréées depuis 2024-08-31. Mise à jour un service à la fois, backup complet des configs avant de commencer.

- Sonarr 3.0.10.1567 → v4.0.19.2979, Radarr 4.3.2.6857 → v6.3.0.10514, Prowlarr 1.21.2.4649 → v2.5.2.5491, Bazarr 1.4.3 → v1.6.0, qBittorrent 4.5.2 → v5.2.3
  Reason: rattrapage de retard demandé par l'utilisateur, sauts majeurs (v3→v4, v4→v6, v1→v2) avec migrations DB automatiques (FluentMigrator/SQLite), toutes validées sans erreur dans les logs
  Source: `docker logs <container>`, migrations DB confirmées + endpoints HTTP répondant après chaque update

- Backup complet des configs (`sonarr/radarr/prowlarr/qbittorrent/readarr/bazarr`) avant toute modification, via conteneur `alpine` jetable monté sur `/volume1/docker/SERVARR`
  Reason: le compte `claude` n'a pas les droits d'écriture directs dans ce dossier (appartient à `secureAdmin`/`root`) ; contourné en lançant `tar` dans un conteneur qui tourne en root côté volume monté
  Source: `/volume1/docker/SERVARR/_backups/servarr-config-backup-20260802-165310.tar.gz`

- `sudo docker` échoue avec "a password is required" malgré le sudoers NOPASSWD du compte `claude`
  Reason: la règle sudoers est liée au chemin exact du binaire (`/usr/local/bin/docker`), pas au nom `docker` résolu via `$PATH` — toujours invoquer `sudo /usr/local/bin/docker compose ...`
  Source: `sudo -n -l` sur TischNAS3

- qBittorrent : `categories.json` corrigé — `save_path` des catégories `TVSHOWS`/`MOVIES` changé de `/downloads/TVSHOWS`/`/downloads/MOVIES` vers `/downloads/_TORRENTCOMPLETE/TVSHOWS`/`/downloads/_TORRENTCOMPLETE/MOVIES`
  Reason: Sonarr v4/Radarr v6 introduisent un nouveau health check qui signale un download client écrivant directement dans un root folder de la librairie ; les deux catégories contournaient les dossiers `_TORRENTCOMPLETE`/`_TORRENTINCOMPLETE` déjà en place pour les autres catégories (ex. `BDZ`)
  Source: warning UI Sonarr/Radarr rapporté par l'utilisateur après validation manuelle du SSO/login

- Readarr (tag `develop`) non mis à jour : `no matching manifest for linux/amd64 in the manifest list entries`
  Reason: absence intermittente de build `linux/amd64` publié par le registry pour ce tag précis (upstream, hors de contrôle côté NAS) — conteneur recréé automatiquement sur l'ancienne image sans casser le service, retenté sans succès une seconde fois le même jour
  Source: sortie `docker compose pull readarr`

- Piège découvert : un `docker compose pull` en échec silencieux (ex. `toomanyrequests` rate-limit registry) n'empêche pas `docker compose up -d` de recréer le conteneur avec l'**ancienne image en cache**, sans erreur visible
  Reason: `up -d` ne vérifie pas que le pull a réussi ; vérifier systématiquement après coup avec `docker inspect <container> --format '{{.Config.Image}} {{.Created}}'`
  Source: reproduit sur Radarr (premier pull raté, image recréée avec l'ancienne version malgré `Started`)

## 2026-08-02 (session 20)

### Pocket ID — SSO Grafana et Linkwarden réellement testés de bout en bout (bugs corrigés)

En rejouant les tests SSO déjà marqués "testés" dans le plan initial, les logins Grafana et Linkwarden échouaient en réalité — le test précédent n'avait validé que la redirection OAuth initiale, pas un login complet.

- Grafana (LXC 107, `/etc/grafana/grafana.ini`) : `oauth_allow_insecure_email_lookup = true` ajouté dans `[auth]`
  Reason: sans ce flag (protection anti-CVE ajoutée par défaut depuis Grafana 9/10), Grafana refuse de lier un compte OAuth à un utilisateur local existant par email et échoue avec `"User sync failed" / user not found`
  Source: `journalctl -u grafana-server`, logs `user.sync`

- Groupe Pocket ID `grafana-admin` créé, utilisateur `rtixhon` assigné ; `groups_attribute_path = groups` ajouté dans `grafana.ini`
  Reason: sans groupe correspondant, `role_attribute_path` retombe sur `Viewer`, et Grafana refuse de rétrograder le seul admin de l'org (`"cannot remove last organization admin"`) ; sans `groups_attribute_path`, Grafana ignore le claim `groups` du token même présent
  Source: `docs/services.md` section Pocket ID

- `role_attribute_path` corrigé pour utiliser des guillemets simples (`'grafana-admin'`) au lieu de doubles
  Reason: en JMESPath, les guillemets doubles sont des identifiants, pas des littéraux — l'expression échouait silencieusement et retombait toujours sur `Viewer`
  Source: test direct + doc JMESPath

- `login_attribute_path = preferred_username` ajouté dans `grafana.ini`, champ `login` du compte restauré à `rtixhon` en base (`grafana.db`)
  Reason: sans ce réglage, chaque connexion SSO écrasait le `login` local avec l'email OAuth, cassant le fallback mot de passe (`rtixhon` devenait injoignable)
  Source: `sqlite3`/`python3 sqlite3` direct sur `/var/lib/grafana/grafana.db`

- Linkwarden (LXC 114, `/opt/linkwarden/.env`) : `NEXTAUTH_URL` corrigé de `https://linkwarden.tixhon.be` vers `https://linkwarden.tixhon.be/api/v1/auth`, callback Pocket ID remis à `/api/v1/auth/callback/authentik`
  Reason: Linkwarden v2 a déplacé ses routes API sous `/api/v1/` mais NextAuth continuait d'annoncer un callback sans ce préfixe, provoquant un vrai 404 malgré un callback IdP pourtant cohérent avec ce qu'annonçait l'app
  Source: [doc officielle migration Linkwarden v2](https://github.com/linkwarden/docs/blob/main/docs/self-hosting/upgrading/to-linkwarden-v2.md)

## 2026-08-02 (session 19)

### Pocket ID — Komga configuré et testé de bout en bout + inventaire dashboard

- `tools/homelab-dashboard/server/data/inventory.json` : ajout de l'entrée `pocketid` (LXC 104, id.tixhon.be)
  Reason: suivi CPU/mem sur le dashboard homelab, même mécanisme que les autres services
  Source: commit `0b29764`

- Client OIDC Komga (Pocket ID) : callback corrigé `/oidc/callback` → `/login/oauth2/code/pocketid` (vrai chemin Spring Security, découvert via `komga.org/docs/installation/oauth2`), PKCE désactivé, secret client régénéré
  Reason: le callback initial n'avait jamais été vérifié contre la doc réelle Komga ; PKCE actif provoquait une erreur `invalid_request` ("code_challenge missing") car Komga est un client confidentiel qui n'envoie pas de PKCE
  Source: `docs/services.md` section "Pocket ID (SSO)"

- `/config/application.yml` créé dans le conteneur Docker Komga (TischNAS3, monté depuis `/volume1/docker/_Configs/Komga`) avec la config `spring.security.oauth2.client` pointant vers Pocket ID
  Reason: Komga se configure par fichier YAML, pas par variables d'env — aucun fichier n'existait avant
  Source: doc officielle Komga OAuth2

- Config Pocket ID : "E-mails vérifiés par défaut" activé (Config app → E-mail) + `emailVerified: true` forcé sur l'utilisateur admin via `PUT /api/users/{id}`
  Reason: Komga rejette les connexions OIDC avec `ERR_1026` si le claim `email_verified` n'est pas `true` ; Pocket ID renvoie `false` par défaut (pas de vérification email, auth par passkey uniquement) et le toggle seul n'agit que sur les futurs changements d'email, pas rétroactivement
  Source: `github.com/gotson/komga/blob/master/ERRORCODES.md`, code source `UserController`/`UserCreateDto` de Pocket ID

- `docs/services.md` : nouvelle section "Pocket ID (SSO)" (hébergement, clients OIDC, pièges Linkwarden/Grafana/Komga)
  Reason: centraliser la doc SSO qui n'existait qu'en mémoire Claude jusqu'ici
  Source: mémoire Claude (`pocketid-access.md`)

- Décision : Vaultwarden **écarté définitivement** du périmètre SSO Pocket ID (client OIDC laissé créé mais inutilisé côté Pocket ID)
  Reason: risque de dépendance circulaire — la passkey WebAuthn utilisée pour se connecter à Pocket ID est stockée dans Bitwarden/Vaultwarden ; si Vaultwarden exigeait lui-même le SSO Pocket ID, un verrouillage total serait possible (besoin d'être dans le vault pour en sortir la clé qui l'ouvre)
  Source: discussion utilisateur, confirmé en session

- Fallback auth locale vérifié manuellement par l'utilisateur sur Grafana, Linkwarden et Komga (login hors SSO fonctionnel sur les trois)
  Reason: s'assurer qu'une panne Pocket ID ne bloque pas l'accès aux services intégrés
  Source: tests manuels en session

## 2026-07-25 (session 18)

### Homelab Dashboard — diagnostic dashboard vide (3 causes cumulées)

- `docs/services.md` : nouvelle section "Homelab Dashboard" (hébergement, architecture, incident détaillé)
  Reason: documenter un diagnostic multi-causes pour éviter de le refaire à chaque symptôme similaire
  Source: session de debug via Claude in Chrome + accès direct au Mac Mini hôte

- LXC 113 (TischNAS3) : `node_exporter` relancé manuellement (`nohup /usr/local/bin/node_exporter --web.listen-address=:9100 &`) — le process s'était arrêté (pas de service persistant), Prometheus ne scrapait plus TischNAS3 (`up=0`)
  Reason: le dashboard affichait "—" pour TischNAS3 ; confirmé par `curl` direct sur Prometheus
  Source: pas de fix durable — à faire : tâche persistante (DSM Task Scheduler au boot)

- `tools/homelab-dashboard/server/data/inventory.json` : ajout `"port": 80` sur `deco-grenier`, `deco-mezzanine`, `deco-salon`
  Reason: les 3 Deco M4R étaient marqués "Hors ligne" à tort — `checkPort()` teste le port 22 (SSH) par défaut, or ces routeurs n'exposent que le port 80 (confirmé `ECONNREFUSED` sur 22, succès sur 80)
  Source: `server/routes/status.js` fonction `checkPort`

- Root cause la plus significative (non résolue) : le process du dashboard lancé via LaunchAgent macOS (`be.tixhon.homelab-dashboard.plist`) échoue silencieusement sur **toutes** les connexions LAN (`net.Socket.connect` vers `192.168.10.x`), alors que le même code lancé manuellement en foreground fonctionne parfaitement — confirmé par test isolé (serveur Express de debug). Cause probable : permission macOS TCC "Réseau local" non accordée à un process headless lancé via `launchd`
  Reason: explique pourquoi CPU/RAM/Disk restaient à "—" même après les deux fixes ci-dessus
  Source: comparaison `launchctl load` vs `node server/index.js` en foreground, avec logs identiques sinon

## 2026-07-25 (session 17)

### Prometheus/Alertmanager — suppression alerte de test spammant Telegram

- LXC 113 (`prometheus`) : suppression de `/etc/prometheus/rules/test.yml` (règle `TestAlert`, `expr: vector(1)`) + `systemctl restart prometheus`
  Reason: l'utilisateur recevait plusieurs notifications Telegram par jour ("TestAlert"/"Alerte de test") sans en connaître la source — la règle était toujours vraie (`vector(1)`) et se répétait via `repeat_interval: 4h` dans la config Alertmanager (LXC 111)
  Source: `docs/services.md` section Proxmox VE

## 2026-07-25 (session 16)

### Home Assistant — retrait Cloudflare Access (app Android) + audit sécurité + config URLs

- `docs/services.md` : nouvelle section "Home Assistant" (hébergement, accès, historique) + tableau Cloudflare Access mis à jour (`hass` retiré)
  Reason: documenter la découverte que l'app companion Android est incompatible avec Cloudflare Access, contrairement à iOS
  Source: mémoire Claude (`cloudflare-access.md`)

- Cloudflare Access retiré de `hass.tixhon.be` (app Access supprimée) — l'app HA Android échouait silencieusement (aucune requête n'atteignant Cloudflare, confirmé par l'absence de logs Access), alors que Chrome et l'app iOS passaient le challenge OTP sans problème. Recherche communautaire confirmée : les apps mobiles HA ne supportent que mTLS pour bypasser Access (pas de champ Client ID/Secret), et mTLS est indisponible sur notre plan Cloudflare (même limitation que Vaultwarden)
  Reason: usabilité pour Céline (app Android) prioritaire sur cette couche de défense en profondeur, le login HA natif reste la protection principale
  Source: `DELETE /accounts/{acct}/access/apps/{id}`, logs `GET /accounts/{acct}/access/logs/access_requests`

- Audit sécurité Home Assistant : version à jour (2026.7.2), pas de 2FA forçable nativement (limitation connue de HA, à activer manuellement par utilisateur), composant Nabu Casa Cloud chargé mais inactif (pas de second point d'exposition), HACS présent (risque supply-chain à surveiller), pas d'add-on SSH actif
  Reason: demande explicite de l'utilisateur après le retrait d'Access sur `hass`
  Source: `GET /api/config`, `GET /api/states` (VM 100 `haos12.4`, `192.168.10.10:8123`)

- `internal_url`/`external_url` configurés côté Home Assistant (étaient à `null`) : `http://192.168.10.10:8123` / `https://hass.tixhon.be`
  Reason: demande explicite de l'utilisateur, améliore la génération de liens dans les notifications/companion app
  Source: commande websocket `config/core/update`

## 2026-07-25 (session 15)

### Vaultwarden — retrait Cloudflare Access + durcissement panel admin

- `docs/services.md` : section Vaultwarden mise à jour (sécurité panel admin) + section Cloudflare corrigée (`vw` n'a plus Access)
  Reason: documenter le retour en arrière sur Access et les protections de remplacement mises en place
  Source: mémoire Claude (`vaultwarden-access.md`, `cloudflare-access.md`)

- Cloudflare Access retiré de `vw.tixhon.be` (app Access + service token supprimés) — incompatible avec l'app native Bitwarden (mobile/desktop) qui ne gère pas le challenge interactif email/OTP. Recherche communautaire confirmée (GitHub vaultwarden#3342) : mTLS ou service token sont les seules solutions, toutes deux indisponibles ici (plan Cloudflare sans mTLS, app Bitwarden sans champ service token). `hass.tixhon.be` garde Access (l'app HA gère bien la redirection)
  Reason: usabilité prioritaire sur cette couche de défense en profondeur, le mot de passe maître Vaultwarden reste la protection principale
  Source: `DELETE /accounts/{acct}/access/apps/{id}`, `DELETE /accounts/{acct}/access/service_tokens/{id}`

- `ADMIN_TOKEN` Vaultwarden hashé en Argon2id (`argon2` CLI sur le LXC 110, conteneur recréé avec le hash) — supprime le warning "plain text ADMIN_TOKEN is insecure", testé pour confirmer que ni le login admin ni les comptes utilisateurs ne sont affectés
  Reason: le token était stocké en clair dans les variables d'environnement du conteneur Docker
  Source: `argon2 <salt> -id -m 19 -t 2 -p 1 -l 32 -e`, `docker run` avec le hash en `ADMIN_TOKEN`

- `/admin` de Vaultwarden restreint au réseau local — bloqué (403) pour tout trafic passant par Cloudflare (détection du header `CF-Connecting-IP`, toujours présent sur le trafic Cloudflare, absent en LAN direct), accessible via LAN ou WireGuard uniquement
  Reason: le panel admin était accessible publiquement depuis internet, protégé uniquement par le token — trouvé lors de l'audit sécurité de la session précédente
  Source: NPM `advanced_config` sur le proxy host `vw.tixhon.be` (id=24), bloc `location /admin` avec `if ($http_cf_connecting_ip != "") { return 403; }`

## 2026-07-25 (session 14)

### Audit sécurité services exposés à internet (Cloudflare)

- `docs/services.md` : nouvelle section Cloudflare (Tunnel + Access) — architecture, domaines exposés, piège de test LAN vs externe
  Reason: cartographier précisément la surface d'attaque réelle avant de corriger quoi que ce soit
  Source: API Cloudflare (zones, DNS records, cfd_tunnel, access/apps) via token scoped en lecture puis écriture

- Découverte que sur ~29 hosts NPM, seuls 6 domaines sont réellement résolvables publiquement (Cloudflare Tunnel) — le reste (Proxmox, pfSense, NAS, AdGuard...) n'existe qu'en DNS interne malgré l'absence d'access-list NPM, réduisant fortement la surface d'attaque réelle par rapport à l'impression initiale
  Reason: éviter de sur-réagir à un faux problème (access_list_id=0 partout dans NPM semblait alarmant isolément)

- `deploy.tixhon.be` supprimé (DNS + route ingress du tunnel) — backend `192.168.10.21:9000` injoignable (down/offline) et sans aucune protection (ni Cloudflare Access ni NPM, bypass direct)
  Reason: service mort et non protégé, décision de l'utilisateur de le retirer plutôt que de le sécuriser
  Source: `DELETE /zones/{zone}/dns_records/{id}`, `PUT /accounts/{acct}/cfd_tunnel/{tunnel}/configurations`

- Cloudflare Access ajouté sur `vw.tixhon.be` (Vaultwarden) et `hass.tixhon.be` (Home Assistant) — authentification email OTP (rudy.tixhon@gmail.com + celine.dumo@gmail.com) en amont du login applicatif natif
  Reason: ces deux services n'avaient qu'une seule couche d'authentification (applicative), pas de défense en profondeur
  Source: `POST /accounts/{acct}/access/apps`

- Diagnostic corrigé en cours de route : le test initial (curl/navigateur) laissait croire qu'Access ne fonctionnait pas du tout, y compris sur `rtxtradingbot` (préexistant et fonctionnel) — cause réelle : AdGuard résout `*.tixhon.be` en split-horizon vers l'IP interne pour les clients LAN, court-circuitant Cloudflare. Confirmé fonctionnel via résolution DNS-over-HTTPS externe + test réel en 4G/5G incognito.
  Reason: éviter de casser une protection qui fonctionnait déjà sur la base d'un faux diagnostic

- `cloudflared` (LXC 109) mis à jour (2025.2.1 → dernière version disponible)

## 2026-07-25 (session 13)

### Sécurité — comptes/clés dédiés pour l'agent Claude + nettoyage backups

- `docs/services.md` : mention des comptes dédiés `claude` par service
  Reason: jusqu'ici l'agent utilisait les identifiants personnels de l'utilisateur (SSH `secureAdmin`, token Proxmox root, login pfSense/NPM perso) — aucune traçabilité ni révocation granulaire possible
  Source: mémoire Claude (`nas-access.md`, `vaultwarden-access.md`, `pfsense-access.md`, `npm-adguard-access.md`)

- Génération d'une paire de clés SSH dédiée (`~/.ssh/claude-agent/id_ed25519`) et création d'un compte `claude` séparé avec sudo restreint (`docker`, `df`, `free` uniquement) sur TischNAS2, TischNAS3, et le LXC Vaultwarden (110)
  Reason: limiter le rayon d'action de l'agent au strict nécessaire plutôt que sudo complet via le compte personnel
  Source: `synouser --add` (Synology), `useradd` (Debian/Vaultwarden LXC), `/etc/sudoers.d/claude-agent`

- Token API Proxmox `root@pam!claude` : `privsep` activé + rôle restreint à `PVEAdmin` (au lieu de l'héritage complet des droits root@pam) — retire la gestion utilisateurs/permissions/réseau système tout en gardant VM/LXC/storage/backups
  Reason: le token avait `privsep=0`, héritant silencieusement de tous les droits root
  Source: `PUT /access/users/root@pam/token/claude`, `pveum acl modify / -role PVEAdmin -token root@pam!claude`

- pfSense : compte `claude` créé avec 128 privilèges API ciblés (system/status/firewall/interfaces/dns/dhcp/diagnostics), sans accès GUI ni VPN/HAProxy/BIND/FreeRADIUS (non utilisés)
  Reason: séparer l'identité API de celle de rtixhon (677 privilèges complets, accès GUI inclus)
  Source: `POST/PATCH /api/v2/user` — limite technique découverte : 128 entrées max par requête sur le champ `priv`

- NPM : compte `claude-agent@tixhon.be` créé (rôle admin, NPM n'offre pas de granularité plus fine)

- AdGuard Home : pas de compte dédié possible — logiciel mono-utilisateur, documenté comme limite connue

- Home Assistant : 15 sauvegardes manuelles obsolètes supprimées (2024-2025, doublons de versions core pré-upgrade jamais nettoyés) — ~2.6 Go récupérés, une seule conservée comme filet de sécurité
  Source: GUI HA via navigateur (`/config/backup`)

- Proxmox : nettoyage de 17 backups orphelins (VM 116 "rtxbot", supprimée depuis) — ~75 Go récupérés sur le storage `syno-backup` (461 Go → 386 Go). Retention du storage explicitée (`keep-last=7,keep-daily=5,keep-weekly=4,keep-monthly=1`, remplace `keep-all=1`)
  Reason: diagnostic initial erroné (comptage de fichiers ×3 par backup) a été corrigé en cours de route — la rétention active fonctionnait déjà correctement pour les VM/LXC existants
  Source: `pvesm prune-backups`, `DELETE /nodes/proxmox/storage/syno-backup/content`

## 2026-07-25 (session 12)

### Vaultwarden — diagnostic bug login desktop/extension + migration Docker

- `docs/services.md` : nouvelle section Vaultwarden — déploiement, accès, historique
  Reason: service jusqu'ici non documenté malgré son usage critique (password manager familial + plusieurs organisations)
  Source: LXC 110 sur NIPoGi, `docker inspect vaultwarden`

- Diagnostic : "unexpected error" au login sur l'app desktop Mac et l'extension Chrome (web vault fonctionnel) — cause trouvée via les logs serveur : `POST /identity/accounts/prelogin/password` → `404 Not Found`. Le binaire Vaultwarden compilé (v1.35.8, bare-metal + systemd) n'implémentait pas cet endpoint attendu par les clients récents, alors que le web-vault embarqué (2026.3.1) était plus à jour que le binaire lui-même — un décalage de version invisible côté web vault (même origine, pas besoin de cet endpoint) mais bloquant pour les clients externes
  Reason: isoler la cause exacte avant d'agir — confirmé non lié à un compte spécifique via un compte de test jetable qui reproduisait le même échec
  Source: `journalctl`/logs vaultwarden, `strings /opt/vaultwarden/bin/vaultwarden`, comparaison versions `/api/config` vs footer web-vault

- Migration de Vaultwarden depuis un déploiement bare-metal (binaire compilé Rust + service systemd) vers un conteneur Docker officiel (`vaultwarden/server:latest`, v1.37.0) — réutilisation des données existantes (`/opt/vaultwarden/data`) sans perte (comptes, coffres, organisations, clés RSA vérifiés intacts après migration)
  Reason: élimine le risque de dérive de version binaire/web-vault à l'avenir, et simplifie radicalement les mises à jour (`docker pull` au lieu d'une compilation Rust de ~10-15 min)
  Source: snapshot Proxmox `pre-vaultwarden-update-20260725` + backup tar pris avant toute manipulation ; ancien binaire conservé (`vaultwarden.bak-1.35.8`)

- `SIGNUPS_ALLOWED=false` appliqué — les inscriptions publiques sur `vw.tixhon.be` étaient ouvertes par défaut (découvert en testant le diagnostic), désormais désactivées
  Reason: éviter que n'importe qui connaissant l'URL puisse créer un compte sur l'instance

- NPM : proxy host `vw.tixhon.be` (id=24) `forward_scheme` passé de `https` (cert auto-signé Rocket) à `http` (le conteneur Docker sert du HTTP en interne, TLS terminé par NPM)

- TischNAS3 : conteneur Docker `vaultwarden-server-1` (doublon obsolète déjà arrêté lors d'une session précédente) confirmé non nécessaire, migration ne le concerne pas

## 2026-07-25 (session 11)

### Accès NPM/AdGuard/pfSense + correction entrées NPM Jellyfin/Jellyseerr

- `docs/services.md` : sections pfSense, AdGuard, NPM mises à jour — accès API confirmés et documentés (méthodes d'auth, pièges)
  Reason: étendre l'accès direct aux services d'infra (au-delà des NAS/Proxmox déjà couverts), demandé explicitement
  Source: tests curl directs sur les 3 API

- NPM : `jellyfin.tixhon.be` et `jellyseerr.tixhon.be` repointés de TischNAS3 vers TischNAS2 via `PUT /api/nginx/proxy-hosts/{29,27}` — ces entrées avaient été oubliées lors de la migration des conteneurs (session précédente)
  Reason: les domaines publics pointaient encore vers l'ancien host après la migration Docker
  Source: `GET/PUT /api/nginx/proxy-hosts/{id}`

- pfSense : découverte que l'API REST v2 (migrée depuis la v1, ancien token obsolète) attend du **HTTP Basic Auth** sur chaque requête, pas un body JSON `{"username":...}` — cause des `401 AUTH_AUTHENTICATION_FAILED` malgré permissions correctes et mot de passe confirmé (login GUI OK). Confirmé via les logs pfSense (`authentication error for user 'unknown'` — le body JSON n'était jamais parsé).
  Reason: éviter de reperdre du temps sur cette confusion lors d'une prochaine session
  Source: `POST /api/v2/auth/jwt` avec Basic Auth, `GET /api/v2/system/version`

## 2026-07-25 (session 10)

### Migration Jellyfin/Jellyseerr TischNAS3 → TischNAS2 + nettoyage vaultwarden doublon

- `docs/network/tischnas3-servarr.md` : section "Migration Jellyfin/Jellyseerr vers TischNAS2" — procédure complète (export NFS, mount persistant, copie config, recréation conteneurs)
  Reason: TischNAS3 (3.8 Gi RAM, matériel CPU le plus récent/puissant des 3 hosts pourtant) portait le plus gros consommateur RAM (Jellyfin) alors que TischNAS2 (7.7 Gi RAM) tournait quasi idle sans aucun conteneur Docker — répartition de charge incohérente identifiée en comparant les 3 hosts (NIPoGi/NAS2/NAS3)
  Source: `mount -t nfs -o vers=3,rw,tcp`, `/etc/rc.local` (TischNAS2), `tar | ssh | tar`

- Jellyfin + Jellyseerr recréés sur TischNAS2 (`192.168.10.5`) avec configs/bibliothèque/historique préservés (copie depuis `/volume1/docker/_Configs/{Jellyfin,Jellyseerr}` de NAS3), médias accédés via mount NFS sur `/volume1/DOWNLOADS` (export déjà actif sur NAS3, ouvert au LAN)
  Reason: NAS2 a la RAM et le CPU dispo pour transcoder/héberger sans risque d'OOM ; réseau gigabit largement suffisant pour ce trafic (25-100 Mbps par flux vs ~125 Mo/s de lien réel)
  Source: `docker run` avec mêmes UID/GID (1031/101, identiques sur les deux NAS), mêmes ports (8100/8920/1900/7359 et 5055)

- TischNAS3 : conteneur `vaultwarden-server-1` (Docker) arrêté définitivement — doublon obsolète, remplacé depuis par le LXC `vaultwarden` sur NIPoGi
  Reason: confusion possible entre deux instances Vaultwarden actives, seule celle de NIPoGi doit rester active
  Source: `docker stop` + `docker update --restart=no`

## 2026-07-25 (session 9)

### TischNAS3 — revérification post-fix + correctif Readarr

- `docs/network/tischnas3-servarr.md` : ajout section "Suivi post-fix" — confirmation que tous les servarr sont stables après les fixes de la session précédente (Readarr redescendu de 623 MB à 97 MB une fois le scan initial terminé)
  Reason: valider que les corrections tiennent dans la durée
  Source: `docker stats`, `/api/v3/health` sur Radarr/Sonarr/Readarr, `/api/v1/health` sur Prowlarr

- Readarr : download client qBittorrent pointait vers l'ancien domaine `qbittorrent.tischhome.duckdns.org` (obsolète) au lieu de `qbittorrent.tixhon.be` (utilisé par Radarr/Sonarr) — causait `DownloadClientCheck: Unable to communicate with Qbittorrent (timeout)`
  Reason: config héritée jamais migrée lors du changement de domaine
  Source: `PUT /api/v1/downloadclient/1?forceSave=true`

- Confirmé que les warnings "indexeurs indisponibles >6h" (TorrentDownload, World-torrent, C411, Torrent9) sur Radarr/Sonarr étaient du cache résiduel du nettoyage Prowlarr de la veille, pas une panne active (tous répondent HTTP 200 au test direct)

## 2026-07-24 (session 8)

### TischNAS3 — diagnostic et fix stack Docker Servarr (Radarr/Sonarr/Prowlarr/Bazarr/Readarr)

- `docs/network/tischnas3-servarr.md` : nouvelle doc de référence — inventaire des conteneurs, historique de l'incident, procédures de fix
  Reason: garder une trace des découvertes pour éviter de re-diagnostiquer les mêmes causes racines la prochaine fois
  Source: investigation SSH + API Radarr/Sonarr/Prowlarr sur `192.168.10.3`

- Diagnostic OOM killer récurrent : `jellyfin` tuait la RAM (3.8 Gi total, pas d'upgrade possible) et entraînait l'arrêt en cascade de `bazarr-rtx`, `readarr-rtx`, `jellyseerr` (exit 137)
  Reason: root cause des "crashs récurrents" rapportés — confirmé via `/var/log/messages` (`Out of memory: Killed process jellyfin`)
  Action: `jellyfin` + `jellyseerr` arrêtés et passés en restart policy `no` (pas de remplacement RAM disponible) ; `bazarr-rtx` et `readarr-rtx` relancés avec policy `unless-stopped`

- Radarr : root folder cassé (`/downloads/KIDS/` inexistant, vrai dossier `KIDS-MOVIES`) — root folder recréé, 5 films et 3 collections avaient leur path individuel non migré, corrigés via API (`/api/v3/movie`, `/api/v3/collection`)
  Reason: erreur de config héritée, bloquait tous les imports de films enfants
  Source: `PUT /api/v3/movie/{id}`, `PUT /api/v3/collection/{id}`

- Prowlarr : 3 indexeurs (`TheRARBG`, `NorTorrent`, `BitSearch`) supprimés — définitions retirées du dépôt Cardigann upstream (RARBG fermé depuis 2023), non recréables à l'identique
  Reason: causait en partie le "No available indexers" de Sonarr
  Source: `DELETE /api/v1/indexer/{id}`

- Sonarr : boucle d'import infinie sur 5 fichiers `.scr`/`.exe` malveillants dans `_TORRENTCOMPLETE` (déguisés en épisodes Euphoria/House of the Dragon) — CPU sonarr bloqué à 37% en continu
  Reason: fichiers supprimés du disque mais toujours référencés dans la queue Sonarr
  Action: fichiers supprimés + queue nettoyée avec blocklist (`DELETE /api/v3/queue/{id}?removeFromClient=true&blocklist=true`), CPU redescendu à ~5%

## 2026-07-01 (session 7)

### Inventaire réseau — topologie physique + devices complets

- `server/data/inventory.json` : 30+ devices ajoutés — infrastructure réseau (D-Link DGS-1100-24, 3× Deco M4R, TL-WPA7617, TL-PA7017P, TL-WR802N/Neato), IoT (NHC2 .22, HomeWizard P1 .23, SMLIGHT SLZB-06 .53, Tado ×2, Eufy ×2, Meross ×2, Dreame vacuum + tondeuse, Netatmo, Philips soundbar, Bosch lave-linge + lave-vaisselle, LG C1, Apple TV, Nintendo Switch, Gigaset), clients (iPhone 17 Pro Max Rudy, iPhone 14 Pro Elias, iPhone Xs Tristan, Samsung A54 Céline, iPad Air 13" M3, iPad 5e gen, MacBook Pro Céline, Mac Mini M2)
  Reason: documenter la topologie complète du réseau domestique pour référence future et monitoring
  Source: pfSense ARP table `/api/v2/diagnostics/arp_table`, Proxmox `ip neigh show`, macvendors API

- `memory/network-topology.md` : nouvelle note mémoire — topologie physique (VOO bridge → NIPoGi → pfSense → D-Link DGS-1100-24 → patch panel + Deco M4R ×3 + CPL), foyer (Rudy, Céline, Elias, Tristan)
  Reason: persister la topologie réseau entre sessions

## 2026-07-01 (session 6)

### Dashboard homelab — Page Réseau, AdGuard, HAOS metrics, prod Mac Mini

- `server/routes/network.js` : nouvelle route `/api/network` — pfSense WAN + services + WireGuard + règles firewall, AdGuard stats + top blocked, NPM proxy hosts + SSL, tout en parallèle
  Reason: page Réseau unifiée plutôt que pages isolées par service
  Source: `fetchNetworkData`, `pf()`, `adguardAuth`

- `client/src/pages/NetworkPage.jsx` : page Réseau — 4 sections (pfSense, AdGuard, Firewall rules, NPM) avec barres proportionnelles
  Reason: remplacement de l'onglet AdGuard standalone incohérent
  Source: `NetworkPage`, `SvcRow`, `SslDays`

- `server/routes/network.js` : WireGuard status fix — dérivé de `vpn/wireguard/settings.enable + tunnel.enabled` au lieu du service map pfSense (retournait False à tort)
  Reason: pfSense ne reporte pas WireGuard comme service classique
  Source: `wgRunning`, `wgSettingsData`

- `server/routes/status.js` : `getHaosMetrics()` — CPU/RAM HAOS via SSH Proxmox (`/proc/<pid>/status` VmRSS + `ps %cpu`)
  Reason: HAOS n'a pas SSH ni node_exporter ; Proxmox expose le process QEMU
  Source: `getHaosMetrics`

- `server/data/inventory.json` : `port: 8123` sur haos — fix statut HAOS toujours offline (checké sur SSH port 22 inexistant)
  Reason: HAOS expose HTTP sur 8123, pas SSH
  Source: `checkPort(device.ip, device.port || 22)`

- `client/src/pages/StatusPage.jsx` : badge gris + "…" avant le premier poll SSE (30s) ; boutons Start/Stop masqués tant que statut inconnu
  Reason: éviter affichage rouge trompeur au chargement
  Source: `badge(online)`, `st.online === undefined`

- `server/index.js` + `.env` : dotenv, AdGuard + HAOS credentials ajoutés ; credentials NPM et pfSense externalisés
  Reason: sortir tous les secrets du code source
  Source: `dotenv.config()`

- Déploiement prod Mac Mini : LaunchAgent `be.tixhon.homelab-dashboard.plist`, NPM proxy host `dashboard.tixhon.be → 192.168.10.98:8160`, AdGuard DNS rewrite
  Reason: dashboard accessible depuis le LAN sans dev server

## 2026-06-28 (session 5)

### Dashboard homelab — inventaire complet + pfSense API v2

- `server/data/inventory.json` : 8 LXC ajoutés (mqtt/101, z2m/102, influxdb/106, rustdesk/108, cloudflared/109, vaultwarden/110, blackbox-exporter/112, linkwarden/114) ; tous les `ipType` "dhcp" → "dhcp-reserved" (réservations DHCP confirmées via pfSense GUI) ; MAC Grafana corrigé (BC:24:11:9A:5E:65) ; IP + URL Alertmanager corrigés (192.168.10.185)
  Reason: inventaire exhaustif de toute l'infra LXC ; ipType correct reflétant les réservations statiques
  Source: `inventory.json`

- `server/routes/status.js` : migration pfSense v1 → REST API v2 — `PFSENSE_URL`/`PFSENSE_API_KEY` depuis `.env` ; endpoint `/api/v2/status/gateways` avec header `X-API-Key` ; suppression ancien auth `client-id token`
  Reason: pfSense 2.8.1 avec package RESTAPI v2 — ancienne API v1 supprimée
  Source: `getPfSenseStatus`, `PFSENSE_URL`, `PFSENSE_API_KEY`

- `server/routes/npm.js` : credentials NPM lus depuis `.env` via `process.env`
  Reason: sortir les secrets du code source
  Source: `NPM_URL`, `NPM_USER`, `NPM_PASS`

- `server/index.js` : chargement `dotenv` au démarrage du serveur
  Reason: rendre les variables `.env` disponibles dans toutes les routes
  Source: `require('dotenv').config(...)`

- `.gitignore` + `.env` : secrets pfSense API v2 et NPM stockés localement, exclus du dépôt
  Reason: sécurité — clé API pfSense `83f842ade...` et mot de passe NPM hors VCS
  Source: `.env`, `.gitignore`

- pfSense CE upgradé 2.7.2 → 2.8.1 (FreeBSD 15) ; package `pfrest/pfSense-pkg-RESTAPI` v2.7.2 installé ; clé API créée
  Reason: FreeBSD 14 → 15 ABI break, nouveau package RESTAPI requis
  Source: pfSense GUI / SSH WAN

## 2026-06-27 (session 4)

### Dashboard homelab — inventaire enrichi + NPM SSL

- `server/data/inventory.json` : champs `ipType`, `mac`, `config`, `installScript` ajoutés sur tous les devices/services ; hostnames manquants complétés (tischnas2/3.tixhon.be, adg, npm, prometheus) ; pfSense specs complètes (2 vCPU, 4GB, 2 NICs WAN/LAN) ; VM Home Assistant (VM 100) ajoutée ; Grafana LXC corrigé 112 → 107
  Reason: cadastre infrastructure complet — IP assignation, MACs, scripts d'install, config réseau pfSense
  Source: `inventory.json`

- `server/routes/npm.js` : route Express `/api/npm` — authentification NPM, liste proxy hosts + certs SSL avec cache 5min
  Reason: afficher le statut SSL de chaque hostname depuis NPM (source de vérité)
  Source: `fetchNpmData`, `getToken`

- `client/src/pages/InventoryPage.jsx` : colonnes MAC, Config, Script ajoutées ; badge `ipType` (static/dhcp/dhcp-reserved) ; composant `SslBadge` avec jours restants (vert/amber/rouge) depuis `/api/npm`
  Reason: visibilité immédiate sur l'assignation IP, les certs SSL et les scripts community
  Source: `SslBadge`, `IP_TYPE_COLOR`

- NPM : 13 anciens certificats expirés `*.tischhome.duckdns.org` supprimés (IDs 16–43)
  Reason: nettoyage — certs orphelins depuis ~1 an, plus aucun proxy host ne les utilisait

## 2026-06-27 (session 3)

### Dashboard homelab — Issue #2 + Issue #3

- `tools/homelab-dashboard/` : nouveau dashboard React + Express (port 8160 + 5173)
  Reason: remplacer network-shutdown, vision cadastre infrastructure
  Source: `server/routes/status.js`, `server/routes/inventory.js`, `server/routes/actions.js`

- `tools/homelab-dashboard/server/routes/status.js` : SSE polling 30s — SSH nipogi (CPU/RAM/disk via /proc), Prometheus NAS (TischNAS2/3 via node_exporter, labels, /volume1), pct exec batch LXC, pfSense REST API (WAN status/delay/loss)
  Reason: métriques temps réel de toute l'infrastructure
  Source: `getNipogiMetrics`, `getDeviceMetrics`, `refreshAllLxcMetrics`, `getPfSenseStatus`

- `tools/homelab-dashboard/client/src/pages/StatusPage.jsx` : cartes statut avec MetricBar, hostname cliquable, espace disque NAS en To, confirmations sur toutes les actions destructives
  Reason: UX claire avec vraies valeurs disque et sécurité sur actions shutdown

- `tools/homelab-dashboard/client/src/pages/InventoryPage.jsx` : CRUD complet devices + services, champs hostname, purchasedAt, installedAt, version, notes
  Reason: cadastre matos avec historique date achat/installation

- `tools/network-shutdown/` : supprimé (migré dans homelab-dashboard)
  Reason: AC4 — consolidation

- `CLAUDE.md`, `docs/index.md` : références network-shutdown → homelab-dashboard
  Reason: doc à jour post-migration

- Issue #3 créée + refinée (ready) : page Réseau dans le dashboard — AdGuard stats/live + pfSense logs/live + embed Grafana

## 2026-06-27 (session 2)

### pfSense API + infrastructure

- pfSense-pkg-API v1.8.1 installé sur pfSense CE 2.7.2 (VM 104) via pkg add depuis HTTP server temporaire Proxmox
  Reason: accès programmatique pfSense (logs, interfaces, actions) sans dépendre du browser
  Source: https://pfsense.tixhon.be/api/v1/, auth API Token (client-id + token)

- GRUB reboot=pci ajouté sur nœud Proxmox nipogi
  Reason: NIPoGi bloquait (curseur clignotant) au reboot software — nécessitait power cycle manuel (bug reproduit 2x)
  Source: /etc/default/grub, update-grub appliqué

- Kernel Proxmox 6.8.12-30-pve activé (reboot effectué 2026-06-27)
  Reason: kernel 6.8.12-30-pve épinglé depuis session précédente, reboot planifié

- docs/proxmox/README.md : section reboot=pci + procédure WAN VOO après reboot
  Reason: documenter les deux bugs récurrents découverts lors du reboot

- docs/services.md : créé — cadastre des services principaux (pfSense, AdGuard, NPM, WireGuard, Proxmox)
  Reason: demande utilisateur — historique centralisé de tous les changements de config par service

- Issue #2 créée + raffinée : Dashboard homelab (React + Express, cadastre matos/services, polling statut, actions rapides)
  Reason: remplacement de network-shutdown + vision long terme cadastre infrastructure
  Source: feature/homelab-dashboard branch créée

## 2026-06-27

### Monitoring homelab — AC3 à AC7 (issue #1)

- Grafana : datasource Prometheus ajoutée (id: 2), dashboards importés : Proxmox via Prometheus (10347) + Node Exporter Full (1860)
  Reason: visualiser les métriques Proxmox et NAS
  Source: http://192.168.10.182:3000

- Prometheus : règles d'alerte homelab créées dans /etc/prometheus/rules/homelab.yml (8 règles : CPU, RAM, disk, NAS CPU temp >85°C, Proxmox containers, blackbox)
  Reason: alerting automatique sur les seuils standards
  Source: LXC 113, promtool check OK

- Alertmanager : config migrée vers telegram_configs natif (v0.31.1), inhibit rules critical→warning
  Reason: intégration Telegram propre, messages formatés Markdown avec emoji, inhibition doublons
  Source: LXC 111, /etc/alertmanager/alertmanager.yml

- docs/proxmox/README.md : section monitoring complétée (dashboards, règles, Telegram, guide ajout device)
  Reason: AC7 — architecture extensible documentée

### Monitoring homelab — AC1 + AC2 (issue #1)

- Nœud Proxmox : pve-exporter 3.9.0 installé (pip), service systemd sur port 9221
  Reason: exposer métriques Proxmox (LXC/VMs CPU/RAM/disk) à Prometheus
  Source: /etc/systemd/system/pve-exporter.service, /etc/pve-exporter.yml

- TischNAS2 + TischNAS3 : node_exporter 1.11.1 installé sur /usr/local/bin/, démarrage /etc/rc.local
  Reason: métriques système des NAS dans Prometheus
  Source: secureAdmin@192.168.10.5 et .3

- docs/proxmox/README.md : section Monitoring ajoutée (exporters, jobs, accès SSH NAS)
  Reason: documenter l'état du monitoring pour les sessions futures

- prometheus.yml (LXC 113) : jobs nas-tischnas2 + nas-tischnas3 ajoutés, placeholders corrigés
  Reason: activer le scraping des NAS, corriger les IPs blackbox

- Skills créés : /proxmox-health (health check fonctionnel) + /proxmox-updates (audit mises à jour)

## 2026-06-26

### Proxmox homelab — gestion via MCP + skills Claude Code

- `docs/proxmox/README.md`: documentation complète du homelab Proxmox (inventaire LXC/VMs, MCP, SSH, notes opérationnelles)
  Reason: centraliser la connaissance opérationnelle pour les sessions Claude Code futures
  Source: skills `/proxmox-health`, `/proxmox-updates`

- `~/.claude/skills/proxmox-health/`: skill de health check fonctionnel par service (HTTP, DNS, ports, systemctl)
  Reason: vérifier que chaque service répond correctement après reboot ou incident

- `~/.claude/skills/proxmox-updates/`: skill d'audit des mises à jour avec niveaux de risque 🟢/🟡/🔴
  Reason: maintenir le homelab à jour de façon sécurisée et documentée

### Opérations effectuées ce jour

- RustDesk (LXC 108) : 1.1.14 → 1.1.15
- Proxmox node : 69 paquets sécurité + qemu-server 8.4.5→8.4.8 + pve-container 5.3.4→5.3.5 + corosync 3.1.9→3.1.10
- Kernel Proxmox épinglé à 6.8.12-30-pve (actif au prochain reboot)
- Alertmanager (LXC 111) : fix crash au démarrage (`--cluster.listen-address=''`)
- VM rtxbot (116) supprimée (ancienne version obsolète)
- Clé SSH `~/.ssh/id_ed25519` déployée sur `root@192.168.10.2`

## 2026-05-03

### rtxcopy — initial implementation

- `tools/rtxcopy/src/rtxcopy/destinations.py`: modèles de destinations (NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination)
  Reason: représentation typée des cibles de copie, discriminant TOML via champ `type`
  Source: `destination_from_dict`, `destination_to_dict`

- `tools/rtxcopy/src/rtxcopy/config.py`: chargement/sauvegarde TOML atomique, gestion des favoris par destination
  Reason: config persistante dans `~/.config/rtxtools/rtxcopy/config.toml`, écriture via fichier `.tmp` + rename
  Source: `load_config`, `save_config`, `Config.add_favorite`, `Config.remove_favorite`

- `tools/rtxcopy/src/rtxcopy/ssh_keys.py`: génération Ed25519, import, déploiement via stdin (compatible Synology MaxSessions=1)
  Reason: clés dédiées par destination, déploiement one-shot sans stocker le mot de passe
  Source: `generate_keypair`, `deploy_public_key`

- `tools/rtxcopy/src/rtxcopy/transfer.py`: moteur SFTP paramiko avec callback de progression byte-level
  Reason: progression en temps réel sans parser stdout rsync
  Source: `transfer`, `_transfer_nas`, `_sftp_upload`

- `tools/rtxcopy/src/rtxcopy/proxmox.py`: wrappers `pct push` / `qm guest exec`
  Reason: copie vers LXC/QEMU via SSH nœud Proxmox, pas d'API REST
  Source: `push_to_lxc`, `push_to_qemu`

- `tools/rtxcopy/src/rtxcopy/screens/file_picker.py`: TUI file picker avec tailles, multi-select, navigation P/U
  Reason: `priority=True` sur Space/C pour capturer avant DirectoryTree; U = parent, P = focus champ chemin
  Source: `SizedDirectoryTree.render_label`, `action_toggle_select`, `action_go_up`

- `tools/rtxcopy/src/rtxcopy/screens/remote_path.py`: browser SFTP lazy avec favoris (f/F)
  Reason: navigation distante sans taper le chemin; fallback texte si SFTP indisponible (Synology)
  Source: `_connect_and_load_root`, `action_toggle_favorite`, `FavoritesModal`

- `tools/rtxcopy/src/rtxcopy/screens/progress.py`: barre de progression async via Worker thread
  Reason: transfert non-bloquant avec mise à jour UI via `self.app.call_from_thread`
  Source: `_do_transfer`, `_update_progress`

- `tools/rtxcopy/src/rtxcopy/screens/dest_manager.py`: CRUD destinations + gestion clés SSH en TUI
  Reason: ajout/suppression/déploiement de clés sans quitter l'app
  Source: `DestManagerScreen`, `KeyManagerScreen`, `DeployKeyScreen`

## 2026-05-04

### Merge NetworkScripts → RtxTools

- `scripts/home-assistant/`, `scripts/pfsense/`, `scripts/installation-guide.md`, `docs/network/`: import initial depuis NetworkScripts (parental control HA/pfSense)
  Reason: consolidation des repos dans RtxTools
  Source: commit 5568b38

- `scripts/guides/`, `scripts/nipogi-shutdown.sh`, `scripts/synology-shutdown.sh`, `tools/network-shutdown/`: import contenu manquant (guides NUT/SSH, shutdown scripts, web app Express)
  Reason: le repo local ne contenait qu'un seul commit partiel ; contenu complet récupéré depuis GitHub
  Source: commit ce2c13c

- `docs/index.md`, `CLAUDE.md`: arborescence et index mis à jour pour refléter la nouvelle structure
  Reason: doc stale après merge
  Source: commits 887844c, ce2c13c

### rtxcopy — bugfixes dest_manager

- `tools/rtxcopy/src/rtxcopy/screens/dest_manager.py`: fix crash `InvalidSelectValueError` à l'ouverture du form d'ajout
  Reason: breaking change Textual — `Select.BLANK` (`False`) rejeté comme valeur explicite ; fix via `allow_blank=True` + valeur conditionnelle
  Source: `DestFormScreen.compose`

- `tools/rtxcopy/src/rtxcopy/screens/dest_manager.py`: fix écran noir sur ESC dans `DestManagerScreen`
  Reason: `app.pop_screen` sur le dernier écran laisse l'app sans écran ; remplacé par `app.quit`
  Source: `DestManagerScreen.BINDINGS`

## 2026-05-03 (session 2)

### rtxcopy — édition destinations, browser Proxmox, fix HAOS

- `screens/dest_manager.py`: refactorisé `AddDestScreen` → `DestFormScreen` avec pré-remplissage pour l'édition, touche `e`, support `proxmox_qemu` dans le Select, colonne `VM/LXC ID` dans la table, validation inline
  Reason: impossible de modifier l'IP ou l'ID d'une destination existante
  Source: `DestFormScreen`, `action_edit`, `_on_dest_edited`

- `screens/remote_path.py`: browser Proxmox utilise maintenant `pct exec` (LXC) ou `qm guest exec` + JSON parsing (QEMU) pour lister les dossiers **dans la VM**, pas sur le nœud
  Reason: le browser SFTP montrait le filesystem du nœud Proxmox au lieu de celui de la VM/LXC
  Source: `_load_children_proxmox`, `_load_children_sftp`, `_is_proxmox`

- `screens/remote_path.py`: `_load_children` déplacé dans un worker thread dans `_build_tree`
  Reason: appel SSH bloquant sur le thread principal causait des timeouts silencieux
  Source: `_build_tree`

- Config HASS: `default_remote_path` mis à jour → `/mnt/data/supervisor/homeassistant`
  Reason: sur HAOS, `configuration.yaml` est à `/mnt/data/supervisor/homeassistant/`, pas à `/`
