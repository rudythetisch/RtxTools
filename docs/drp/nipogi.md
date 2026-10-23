# DRP — perte du NIPoGi

Plan de reprise si le mini-PC NIPoGi (nœud Proxmox `192.168.10.2`) grille, est volé ou ne redémarre plus. Rédigé le 2026-10-20.

Sources : [[services]], [[proxmox/README]], [[network/migration-opnsense]], [[network/scanopy]], `scripts/guides/configure-nut-ups.md`, et l'API Home Assistant (lecture le 2026-10-20). Les points marqués **à vérifier** n'ont pas pu être confirmés depuis le repo.

## En bref

- **Si le NIPoGi meurt, toute la maison perd Internet**, pas seulement la domotique : le routeur (pfSense), le DNS (AdGuard), le tunnel Cloudflare et Vaultwarden tournent dessus.
- **Première heure** : remettre Internet avec la Deco principale en mode routeur (15 à 30 min), puis utiliser le cache hors ligne de Bitwarden pour les mots de passe. Voir [Mode dégradé](#1-mode-dégradé-dans-lheure).
- **Reconstruction** : nouveau mini-PC + Proxmox + restauration des sauvegardes vzdump depuis le NAS. Environ **4 h** de travail une fois le matériel en main.
- **Données** : on perd au plus **24 h** (sauvegarde Proxmox chaque nuit à 3h00).
- **Trous à combler** : config du nœud non sauvegardée, aucune copie hors de la maison, sauvegardes Home Assistant restées dans la VM, secrets de reprise rangés dans Vaultwarden (donc sur le NIPoGi), alertes hébergées sur la machine qu'elles surveillent. Voir [Ce qui manque](#ce-qui-manque).

## Inventaire

### Le matériel

| Élément | Valeur |
|---|---|
| Machine | NIPoGi, Intel N100, 16 Go RAM, NVMe 512 Go |
| Nom du nœud Proxmox | `proxmox` (nom d'hôte `proxmox.tixhon.be`) |
| IP de gestion | `192.168.10.2`, sur `vmbr1` (LAN) |
| WAN | carte intégrée `enp1s0` (Realtek), câble du modem VOO (bridge) |
| LAN | adaptateur USB `cdc_ncm` → `vmbr1` |
| MAC (WoL) | `68:1D:EF:43:4D:05` (utilisée par `wol-nipogi` sur le Mac Mini) |
| USB branchés | onduleur APC BE550G (NUT, sur le nœud), clé RFXtrx433XL (passée à la VM Home Assistant) |
| Kernel | épinglé `6.8.12-30-pve`, GRUB `reboot=pci` (propres à ce matériel) |
| BIOS | « Restore on AC Power Loss » **désactivé** |

### Les VM et LXC

Relevé d'après la doc. La liste exacte est enregistrée chaque nuit par `nipogi-drp-backup.sh` (`info/qm-list.txt`, `info/pct-list.txt`).

| VMID | Type | Service | IP | Criticité | Si absent |
|---|---|---|---|---|---|
| 115 | VM | pfSense (routeur, DHCP, WireGuard, DynDNS) | `.1` | 🔴 | Plus d'Internet ni de DHCP dans la maison |
| 103 | LXC | AdGuard Home (DNS) | `.12` | 🔴 | Plus de résolution de noms |
| 110 | LXC | Vaultwarden | `.17` | 🔴 | Coffre familial et organisations inaccessibles (cache hors ligne seulement) |
| 109 | LXC | cloudflared (tunnel `nipogi-homelab`) | `.16` | 🟠 | Tous les `*.tixhon.be` publics tombent, y compris ceux hébergés sur le Mac Mini et les NAS |
| 105 | LXC | Nginx Proxy Manager | `.11` | 🟠 | Idem, plus les noms internes |
| 100 | VM | Home Assistant OS (2026.10.1) | `.10` | 🟠 | Plus d'automatisations, de coupure Internet des enfants, d'app HA |
| 101 | LXC | Mosquitto MQTT | `.14` | 🟠 | Zigbee2MQTT et HA ne se parlent plus |
| 102 | LXC | Zigbee2MQTT (coordinateur SLZB-06M en Ethernet) | `.15` | 🟠 | Appareils Zigbee non pilotables |
| 104 | LXC | Pocket ID (SSO) | `.188` | 🟡 | Login SSO Grafana, Linkwarden, Komga (les comptes locaux restent) |
| 113 / 111 / 112 | LXC | Prometheus / Alertmanager / Blackbox | `.184` / `.185` / `.186` | 🟡 | Plus d'alertes Telegram |
| 107 / 106 | LXC | Grafana / InfluxDB | `.182` / `.181` | 🟢 | Historiques indisponibles |
| 114 | LXC | Linkwarden | `.187` | 🟢 | Favoris indisponibles |
| 108 | LXC | RustDesk server | `.183` | 🟢 | Prise en main à distance indisponible |
| 116 | LXC | `homefinance-db` : PostgreSQL 15, base `homefinance` (finances perso), créé le 2026-09-11 | `.13` | 🟡 | L'appli de finances (hors NIPoGi) n'a plus de base |
| 117 | LXC | Scanopy | `.18` | 🟢 | Cartographie réseau indisponible |

Inventaire vérifié sur le nœud le 2026-10-23 : tous les invités tournent, tous en démarrage automatique. pfSense est bien la VM 115 (l'ancienne mention « VM 104 » de la doc Proxmox est périmée). Seuls 103, 105, 116 et 117 ont une IP fixe dans leur config ; les autres LXC sont en DHCP et dépendent des réservations de pfSense (incluses dans la sauvegarde de la VM 115).

### Ce qui tourne sur le nœud lui-même (hors VM/LXC)

Rien de tout ça n'est dans les sauvegardes vzdump :

- **NUT** : serveur de l'onduleur (`/etc/nut`, script d'arrêt `/etc/nut/shutdown-script.sh` qui éteint TischNAS2, TischNAS3 puis Proxmox). Sans le NIPoGi, **les NAS ne s'éteignent plus proprement en cas de coupure**.
- **Clé SSH `root@nipogi`** (`id_rsa`), autorisée sur le compte `claude` des deux NAS pour l'arrêt UPS.
- **pve-exporter** (port 9221, service systemd).
- **Réseau** : `/etc/network/interfaces` (`vmbr0`/`vmbr1`, noms de cartes).
- **Job de sauvegarde** : 3h00, débit limité à 40 Mo/s, rétention `keep-last=7, keep-daily=5, keep-weekly=4, keep-monthly=1`, e-mail de rapport.
- **Comptes et jetons** : token API `root@pam!claude` (rôle `PVEAdmin`), utilisateurs Proxmox.

### Hors NIPoGi, mais dépendant de lui

- **Mac Mini** : `wol-nipogi` (MAC du NIPoGi en dur), dashboard homelab (SSH vers `root@192.168.10.2`), et les sites `fmfcompta`, `homeplan`, `rtxtradingbot`, publiés via le tunnel du NIPoGi.
- **TischNAS3** : Komga (login via Pocket ID), et les NAS en général (arrêt UPS piloté par le NIPoGi).
- **Niko Home Control II** : contrôleur autonome, continue de fonctionner sans HA (interrupteurs physiques OK).

## Sauvegardes existantes

| Quoi | Comment | Où | Fréquence | Rétention |
|---|---|---|---|---|
| Toutes les VM et LXC | vzdump (job Proxmox) | Stockage `syno-backup` sur **TischNAS3** (`192.168.10.3`) | Chaque nuit à 3h00 | 7 dernières + 5 jours + 4 semaines + 1 mois |
| Home Assistant | Sauvegarde automatique HA (dernière réussie le 2026-10-20 à 04h53) | **Dans la VM 100 uniquement** : aucun stockage réseau n'est monté dans HA | Chaque jour vers 04h50 | Réglage HA |
| pfSense | Aucune sauvegarde dédiée connue (seulement via le vzdump de la VM) | — | — | — |
| Config du nœud + copie Vaultwarden | `/root/drp/nipogi-drp-backup.sh` (cron `/etc/cron.d/nipogi-drp-backup`), ~5 Mo par nuit | `syno-backup/drp/<date>/` | Chaque nuit à 5h30 (depuis le 2026-10-23) | 14 dernières |
| Contrôle | `/root/drp/check-backups.sh` (cron `/etc/cron.d/nipogi-check-backups`), mail seulement en cas de problème | — | Chaque jour à 8h00 | — |
| Copie hors site (étape 1) | 2e job vzdump « offsite hebdo → pCloud » : tous les invités, `dumpdir /mnt/pve/syno-backup/offsite`, mail en cas d'échec | `syno-backup/offsite/` (~21 Go) | Dimanche 04:30 (depuis le 2026-10-25) | 1 copie (`keep-last=1`) |
| Copie hors site (étape 2) | Conteneur `rclone-offsite` sur TischNAS3 (`/volume1/docker/rclone-offsite/`) : rclone chiffré (`crypt`, noms chiffrés) → pCloud UE (`eapi.pcloud.com`), dossier `RTX-offsite`. `offsite/` → `proxmox/<date>` (10 Mo/s max), `drp/` synchronisé. Marqueur de réussite : `/volume1/proxmox/offsite-status/offsite-last-success` | pCloud (UE) | Dimanche 10:00 (depuis le 2026-10-23) | 4 dates |

À relever une fois et à noter ici (commande sur le nœud : `cat /etc/pve/storage.cfg` et `cat /etc/pve/jobs.cfg`) :

| Info | Valeur |
|---|---|
| NAS qui héberge `syno-backup` | TischNAS3 (`192.168.10.3`), confirmé par Rudy le 2026-10-23 |
| Partage et protocole | NFS `192.168.10.3:/volume1/proxmox`, monté sur `/mnt/pve/syno-backup` (11,2 To, 71 % utilisés au 2026-10-23) |
| Le job vise « tous les invités » ? | Oui : job `backup-5366822d-fbb5`, 03:00, `all 1`, snapshot, zstd, `bwlimit 40960`, mail à chaque fois vers rudy.tixhon@gmail.com |
| Volume total d'une nuit de sauvegarde | 20,6 GiB pour 18 invités (2026-10-23) ; les plus gros : VM 115 pfSense 4,8 Go, VM 100 HA 4,6 Go, LXC 110 et 114 ~2,1 Go. Le job de 03:00 finit vers 03:49 |

TischNAS3 est aussi le NAS le plus chargé (4 Go de RAM, stack Servarr) et il est sur le même onduleur que le NIPoGi : une surtension ou un incendie emporterait les deux. D'où l'importance de la copie hors site (point 3 ci-dessous).

## Ce qui manque

Classé par priorité.

1. ✅ (installé le 2026-10-23) **Config du nœud non sauvegardée.** → Script `scripts/drp/nipogi-drp-backup.sh` (cette PR) : chaque nuit, copie `/etc/pve`, le réseau, NUT, cron, systemd, l'inventaire (VM, MAC, USB, versions) et une copie cohérente de Vaultwarden dans `syno-backup/drp/`.
2. ✅ (installé le 2026-10-23) **Personne ne vérifie que tout est sauvegardé.** → Script `scripts/drp/check-backups.sh` (cette PR) : signale un invité sans sauvegarde de moins de 26 h, un job qui ne vise pas tous les invités, ou une sauvegarde du nœud absente. Un mail seulement en cas de problème.
3. **Aucune copie hors de la maison.** Incendie, vol, surtension ou rançongiciel sur le NAS = tout est perdu, sauvegardes comprises. → Job Proxmox hebdomadaire vers `offsite/` (en place depuis le 2026-10-23), puis copie rclone chiffrée vers pCloud (en place depuis le 2026-10-23, testée sur `drp/`). Les deux mots de passe de chiffrement vont dans le kit d'urgence.
4. **Sauvegardes Home Assistant enfermées dans la VM.** → Dans HA : Paramètres → Système → Stockage → Ajouter un stockage réseau (partage SMB du NAS, usage « Sauvegarde »), puis Paramètres → Système → Sauvegardes → le cocher comme emplacement. On peut alors restaurer HA sur n'importe quelle installation HAOS sans passer par Proxmox.
5. **Les secrets de reprise sont dans Vaultwarden, donc sur le NIPoGi.** → Un kit d'urgence hors NIPoGi (voir plus bas).
6. **Les alertes tournent sur la machine qu'elles surveillent.** Si le NIPoGi meurt, Prometheus et Alertmanager meurent avec lui : aucune alerte Telegram. → Un « dead man's switch » externe : par exemple un ping toutes les 5 min vers healthchecks.io depuis le nœud (alerte Telegram si les pings s'arrêtent), ou Uptime Kuma sur TischNAS3.
7. **Restauration jamais testée.** → Exercice deux fois par an (voir [Tester le plan](#tester-le-plan)).
8. **Pas de matériel de secours.** Un mini-PC équivalent (N100 ou N150, 16 Go, NVMe 512 Go) coûte ~150–250 € et se livre en 1 à 3 jours. Idéalement **deux ports Ethernet intégrés** (Intel i226), pour se passer de l'adaptateur USB.
9. **pfSense dans le NIPoGi.** La migration vers OPNsense sur un boîtier dédié ([[network/migration-opnsense]]) est aussi la meilleure mesure de ce DRP : après elle, la mort du NIPoGi ne coupe plus Internet.

### Kit d'urgence (hors NIPoGi)

À ranger à deux endroits : une copie papier ou une clé USB chiffrée à la maison, et une copie hors de la maison.

- Mot de passe maître Vaultwarden, et un export chiffré du coffre (Outils → Exporter, format « .json chiffré »), refait tous les 3 mois.
- Mot de passe `root` Proxmox.
- Compte du NAS qui héberge `syno-backup` (pour lire le partage depuis un portable).
- Les deux mots de passe rclone `crypt` (fichier `~/Documents/DRP-rclone-pcloud-crypt.txt` du Mac mini, à recopier dans Vaultwarden et sur papier) et les identifiants pCloud : sans eux, la copie hors site est illisible.
- Clé de chiffrement des sauvegardes Home Assistant (Paramètres → Système → Sauvegardes → Configurer).
- Identifiants pfSense (`rtixhon`), Cloudflare, compte TP-Link Deco, et le cas échéant VOO.
- Ce document, imprimé.

## Procédure de reprise

### 1. Mode dégradé (dans l'heure)

**Constater** : Wi-Fi visible mais « pas d'Internet », pas d'IP ou une IP en `169.254.x.x`, `192.168.10.2` ne répond pas au ping. Essayer d'abord : débrancher et rebrancher le NIPoGi, attendre 5 min. S'il ne démarre toujours pas (pas de voyant, pas d'image en HDMI), passer à la suite.

**a. Rendre Internet à la maison (15 à 30 min)** : la Deco principale (Salon, `.32`) en mode routeur.

1. Débrancher le câble du modem VOO du NIPoGi, le brancher sur un port de la **Deco Salon**.
2. App Deco → Plus → Avancé → Mode de fonctionnement → **Routeur**.
3. Si possible, régler l'IP LAN de la Deco sur `192.168.10.1` / `255.255.255.0` (Avancé → Adresse IP LAN) : les NAS, en IP fixe, restent alors joignables. Sinon, la Deco distribue sa propre plage (`192.168.68.x`).
4. **Éteindre le modem VOO 1 à 2 minutes**, puis le rallumer : il retient l'adresse MAC de l'ancien routeur.
5. Vérifier Internet sur un téléphone et un appareil filaire.

Limites : pas de filtrage AdGuard, pas de coupure Internet des enfants, pas de WireGuard, pas d'accès aux services publics `*.tixhon.be`. Plan B si la Deco refuse : partage de connexion 4G d'un téléphone vers le portable de travail.

**b. Mots de passe** : les apps Bitwarden (téléphone, ordinateur, extension) gardent une copie chiffrée du coffre et se déverrouillent hors ligne avec le mot de passe maître. **Ne pas se déconnecter** de ces apps tant que Vaultwarden n'est pas revenu. Lecture seule : les modifications ne seront pas synchronisées.

**c. Prévenir la famille** : domotique HA indisponible (Niko et les interrupteurs physiques fonctionnent), pas de contrôle parental Internet, app Bitwarden en lecture seule.

**d. Onduleur** : l'arrêt automatique des NAS en cas de coupure ne fonctionne plus. Pendant la panne, en cas de coupure de courant, éteindre les NAS à la main depuis DSM.

### 2. Préparer le nouveau matériel

1. Récupérer un mini-PC x86 (16 Go RAM minimum, NVMe 512 Go, idéalement 2 ports Ethernet).
2. Depuis un portable : lire la dernière sauvegarde du nœud sur le NAS, dossier `syno-backup/drp/<date>/` :
   - `info/pveversion.txt` : version de Proxmox à installer (même version majeure) ;
   - `info/storage.txt` et `host/nipogi-etc.tar.gz` → `etc/pve/storage.cfg` : comment le stockage `syno-backup` est monté ;
   - `host/…/etc/network/interfaces` : noms des ponts (`vmbr0`, `vmbr1`) et lequel porte l'IP `.2` ;
   - `info/guests-config.txt` : config de chaque VM/LXC (ponts, disques, USB).
3. Télécharger l'ISO Proxmox VE (proxmox.com/downloads) et la copier sur une clé USB (balenaEtcher ou Ventoy).
4. BIOS du nouveau PC : **Restore on AC Power Loss → Power On**, **Wake-on-LAN activé**, virtualisation (VT-x, VT-d) activée.

### 3. Installer Proxmox (30 min)

Installation standard, avec :

| Paramètre | Valeur |
|---|---|
| Disque | NVMe, `ext4` ou `lvm-thin` comme avant (stockage `local-lvm`) |
| Nom d'hôte | `proxmox.tixhon.be` : le nœud doit s'appeler `proxmox` comme avant |
| Carte de gestion | la carte qui ira vers le **switch** (LAN) |
| IP | `192.168.10.2/24` |
| Passerelle | `192.168.10.1` |
| DNS | `1.1.1.1` pour l'instant (AdGuard n'est pas encore restauré) |

Si la Deco est en mode routeur avec une autre plage, prendre une IP libre dans sa plage pour l'installation, puis repasser en `.2` à l'étape 5.

Puis : nœud → Mises à jour → Dépôts, désactiver le dépôt « enterprise » et ajouter « No-Subscription », puis dans un shell `apt update && apt full-upgrade -y`.

### 4. Réseau et stockage (30 min)

1. **Ponts réseau** : Datacenter → nœud → Système → Réseau. Recréer **les mêmes noms** qu'avant (voir `etc/network/interfaces` de la sauvegarde), car les VM et LXC y sont attachés par leur nom :
   - `vmbr1` = LAN, sur la carte vers le switch, IP `192.168.10.2/24` ;
   - `vmbr0` = WAN, sur la carte vers le modem VOO, **sans IP**.
   Appliquer la configuration.
2. **Stockage des sauvegardes** : Datacenter → Stockage → Ajouter → NFS ou SMB/CIFS, avec **l'ID `syno-backup`**, le même NAS et le même partage qu'avant, contenu « Sauvegarde VZDump ».
3. Vérifier que les sauvegardes sont visibles : `ls /mnt/pve/syno-backup/dump/ | tail`.

### 5. Restaurer les invités (1 à 2 h selon le volume)

Dans l'ordre ci-dessous : chaque étape remet en route ce dont la suivante a besoin. Prendre à chaque fois **le fichier le plus récent** de l'invité dans `/mnt/pve/syno-backup/dump/`. Les adresses MAC sont restaurées avec les VM, donc les réservations DHCP et le modem VOO les reconnaissent.

```bash
D=/mnt/pve/syno-backup/dump
last() { ls -1 "$D"/vzdump-$1-$2-*.{vma,tar}.zst 2>/dev/null | sort | tail -n1; }

# a. Routeur
qmrestore "$(last qemu 115)" 115 --storage local-lvm
qm start 115
```

**a. pfSense (115)** : remettre le câble du modem VOO sur la carte WAN du nouveau PC (et remettre la Deco Salon en mode **point d'accès**, câblée au switch). Éteindre le modem VOO 1 à 2 min puis le rallumer. Vérifier dans pfSense : IP WAN obtenue (sinon Status → Interfaces → Release WAN, puis Renew WAN, voir [[proxmox/README]]), puis Internet depuis le LAN.

```bash
# b. DNS, puis publication des services
pct restore 103 "$(last lxc 103)" --storage local-lvm && pct start 103
pct restore 105 "$(last lxc 105)" --storage local-lvm && pct start 105
pct restore 109 "$(last lxc 109)" --storage local-lvm && pct start 109

# c. Mots de passe
pct restore 110 "$(last lxc 110)" --storage local-lvm && pct start 110

# d. Domotique
pct restore 101 "$(last lxc 101)" --storage local-lvm && pct start 101
pct restore 102 "$(last lxc 102)" --storage local-lvm && pct start 102
qmrestore "$(last qemu 100)" 100 --storage local-lvm
```

**d. Home Assistant (100)** : avant de démarrer la VM, rebrancher la clé RFXtrx433XL et vérifier sa ligne USB (`qm config 100 | grep usb`). Si elle pointe vers un port physique (`host=1-2`), la remplacer par l'identifiant de la clé, qui ne dépend pas du port : `lsusb` → `qm set 100 -usb0 host=<vendor>:<product>`. Puis `qm start 100`.

```bash
# e. Le reste
for id in 104 113 111 112 107 106 114 108 117; do
  pct restore $id "$(last lxc $id)" --storage local-lvm && pct start $id
done
```

Remettre ensuite le DNS du nœud sur AdGuard : `192.168.10.12`.

**Si une sauvegarde manque ou est corrompue** : reprendre la précédente (rétention de 7 jours minimum). Pour Vaultwarden, `drp/<date>/vaultwarden/` contient une copie indépendante (base SQLite + dossier data) restaurable dans n'importe quel conteneur `vaultwarden/server`.

### 6. Reconfigurer le nœud (30 à 45 min)

Extraire l'ancienne config **à côté**, sans écraser `/etc/pve` d'un coup (c'est un système de fichiers spécial, le copier en bloc casse le nœud) :

```bash
mkdir -p /root/old && tar -xzf /mnt/pve/syno-backup/drp/<date>/host/nipogi-etc.tar.gz -C /root/old
```

Puis reprendre point par point :

1. **Job de sauvegarde** : Datacenter → Sauvegarde → Ajouter : tous les invités, 3h00, stockage `syno-backup`, mode snapshot, limite 40 Mo/s (`bwlimit: 40960` dans `/etc/vzdump.conf`), e-mail de rapport. Comparer avec `/root/old/etc/pve/jobs.cfg`.
2. **Onduleur (NUT)** : brancher le câble USB de l'onduleur, `apt install -y nut`, puis recopier `/root/old/etc/nut/*` dans `/etc/nut/` et `systemctl restart nut-server nut-monitor`. Vérifier avec `upsc apc-nipogi@localhost`. Détails : `scripts/guides/configure-nut-ups.md`.
3. **Clé SSH vers les NAS** : `ssh-keygen -t ed25519`, puis ajouter la nouvelle clé publique au fichier `authorized_keys` du compte `claude` sur TischNAS2 et TischNAS3. Tester : `ssh claude@192.168.10.5 'sudo /usr/syno/sbin/synoshutdown --help'`.
4. **Token API** : recréer `root@pam!claude` (Datacenter → Permissions → Jetons API, privilèges séparés, rôle `PVEAdmin` sur `/`), puis mettre à jour le secret là où il sert : pve-exporter, MCP Proxmox, mémoire Claude.
5. **pve-exporter** : réinstaller et reprendre l'unité systemd et la config depuis `/root/old/etc/`.
6. **Cron et scripts** : comparer `/root/old/etc/cron.d`, `/root/old/var/spool/cron/crontabs` et `/root/old/usr/local/bin` avec le nouveau nœud, et réinstaller les scripts DRP (`nipogi-drp-backup.sh`, `check-backups.sh`).
7. **Kernel et GRUB** : ne **pas** reprendre l'épinglage du kernel ni `reboot=pci` par défaut : c'étaient des correctifs pour l'ancien matériel. Ne les remettre que si le même souci réapparaît.
8. **Mac Mini** : mettre la MAC du nouveau PC dans `/usr/local/bin/wol-nipogi.sh`. Dans le repo : `tools/homelab-dashboard/server/data/inventory.json` (entrée `nipogi` : MAC, specs).
9. **Ce document** : mettre à jour la section Inventaire (matériel, MAC, cartes réseau).

### 7. Vérifications

- [ ] Internet sur un appareil filaire et un appareil Wi-Fi, IP réservées récupérées (Apple TV `.93`…)
- [ ] DNS par AdGuard (`nslookup tixhon.be 192.168.10.12`), DNS public forcé bloqué
- [ ] `https://hass.tixhon.be` et `https://vw.tixhon.be` joignables **en 4G** (tunnel Cloudflare)
- [ ] Bitwarden : synchronisation OK sur téléphone et ordinateur
- [ ] Home Assistant : un appareil Zigbee, un store RFXtrx, un appareil Matter, la coupure Internet d'un appareil (pfSense)
- [ ] WireGuard depuis l'iPhone en 4G
- [ ] Prometheus : toutes les cibles `up`, une alerte de test arrive sur Telegram
- [ ] `upsc apc-nipogi@localhost` répond
- [ ] `/proxmox-health` (skill Claude Code) sans erreur
- [ ] Le lendemain matin : e-mail de sauvegarde OK et `scripts/drp/check-backups.sh` sans problème

### Si TischNAS3 est perdu aussi : repartir de pCloud

Sur n'importe quel ordinateur avec [rclone](https://rclone.org/install/) :

```bash
rclone config   # remote "pcloud" (type pcloud, région UE : hostname eapi.pcloud.com)
                # remote "pcloud-crypt" (type crypt, remote pcloud:RTX-offsite,
                #   filename_encryption standard, les 2 mots de passe du kit d'urgence)
rclone lsd pcloud-crypt:proxmox                  # dates disponibles
rclone copy pcloud-crypt:proxmox/<date> ./dump -P
rclone copy pcloud-crypt:drp ./drp -P
```

Mettre `dump/` à disposition du nouveau Proxmox (clé USB, disque ou partage NFS déclaré comme storage `syno-backup`), puis reprendre à l'étape 5.

## RTO et RPO

**RTO** : temps pour revenir en service. **RPO** : quantité de données qu'on accepte de perdre.

| Scénario | RTO estimé | RPO |
|---|---|---|
| Internet de secours (Deco en routeur) | 15–30 min | — |
| Mots de passe (cache Bitwarden hors ligne) | immédiat, lecture seule | — |
| Reprise complète, matériel en main | **~4 h** (installation 30 min, réseau et stockage 30 min, restauration 1–2 h, reconfiguration 45 min, vérifications 30 min) | **24 h** (vzdump de 3h00) |
| Reprise complète, matériel à acheter | **1 à 3 jours** + 4 h | 24 h |
| Sinistre de la maison (incendie, vol, surtension) | 1 à 3 jours (matériel + téléchargement de ~21 Go depuis pCloud) + 4 h | **7 jours** (copie hebdomadaire du dimanche) |

Précisions sur le RPO :

- **Home Assistant** : la sauvegarde HA de ~04h50 est faite *après* le vzdump de 3h00. Elle n'arrive donc sur le NAS que la nuit suivante, dans le vzdump. Le vzdump de la VM reste la référence : 24 h au plus.
- **Vaultwarden** : 24 h au plus. Une entrée créée dans la journée est perdue si elle n'est pas aussi sur un client resté connecté.
- **Config du nœud** : aujourd'hui, rien (à refaire à la main d'après ce document). Avec `nipogi-drp-backup.sh` : 24 h.

**Objectif proposé** : RTO 4 h une fois le matériel en main, RPO 24 h, et une copie hors site hebdomadaire.

## Tester le plan

Deux fois par an, et après chaque changement important (nouveau LXC, migration OPNsense) :

1. `scripts/drp/check-backups.sh` sans problème.
2. Restaurer un LXC sous un autre numéro, **sans réseau** pour éviter un conflit d'IP avec l'original :
   ```bash
   pct restore 910 "$(ls -1 /mnt/pve/syno-backup/dump/vzdump-lxc-110-*.tar.zst | tail -n1)" --storage local-lvm --unique 1
   pct set 910 -delete net0
   pct start 910 && pct exec 910 -- ls -la /opt/vaultwarden/data
   pct stop 910 && pct destroy 910
   ```
3. Chronométrer la restauration de la plus grosse sauvegarde (souvent Home Assistant) et corriger le RTO ci-dessus.
4. Vérifier que le kit d'urgence est complet et à jour.
5. Noter la date du test ci-dessous.

| Date | Test | Résultat |
|---|---|---|
| — | — | — |
