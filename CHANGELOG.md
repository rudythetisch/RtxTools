# Changelog

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
