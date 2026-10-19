# Migration pfSense → OPNsense (appliance dédiée)

Plan rédigé le 2026-10-13, pas encore exécuté.

## Pourquoi

- pfSense CE 2.7.2 tourne en VM (115) sur le NIPoGi. Son LAN passe par un **adaptateur USB** (`cdc_ncm`, `vmbr1`). La sauvegarde Proxmox a saturé cet adaptateur et figé pfSense deux fois : le 2026-08-02 et le 2026-10-11 (`vtnet1: watchdog timeout`), avec un reset manuel de la VM à chaque fois.
- pfSense CE évolue peu, Netgate pousse la version payante Plus. OPNsense publie deux versions majeures par an, avec WireGuard intégré, une API officielle complète et le plugin Tailscale.
- Avec un boîtier séparé, le routeur ne dépend plus de Proxmox (sauvegardes, mises à jour, redémarrages), et le NIPoGi peut retrouver sa carte réseau intégrée pour le LAN.

## Matériel

**Topton N150, boîtier « Big », sans ventilateur, 4× Intel i226-V 2,5 Gb**, 8 Go DDR4 + NVMe 128 Go. 356,39 € sur AliExpress (boutique officielle Topton, relevé le 2026-10-11) : variante « N150 Big DDR4 » + « 8GB Ram 128GB NVMe ».

- Ports : WAN, LAN, et 2 ports libres (futur VLAN enfants ou invités, lien direct vers le NAS).
- Pas de carte réseau Realtek : sous FreeBSD (le système d'OPNsense), leur pilote est le point faible.
- À brancher sur l'onduleur, avec le modem VOO et le switch.

## Inventaire de la config pfSense actuelle

Relevé via l'API le 2026-10-13.

### Interfaces

| | pfSense | OPNsense |
|---|---|---|
| WAN | DHCP (modem VOO en bridge), block private + bogons | Identique, sur le port 1 |
| LAN | `192.168.10.1/24`, statique | Identique, sur le port 2 |
| IPv6 | Aucune | Aucune |
| Nom d'hôte | `pfSense.home.arpa` | `opnsense.home.arpa` |
| DNS système | `192.168.10.12` (AdGuard) | Identique |

### Alias

| Nom | Type | Contenu |
|---|---|---|
| `INTERNET_BLOQUE` | Host | IP coupées par Home Assistant, vide au départ. Voir [[internet-appareils]]. |
| `PUBLIC_DNS` | Host | `8.8.8.8, 8.8.4.4, 1.1.1.1, 1.0.0.1, 9.9.9.9, 149.112.112.112, 208.67.222.222, 208.67.220.220` |

### Règles LAN (dans l'ordre)

1. **Block** IPv4, source `INTERNET_BLOQUE` → destination `!LAN net`, log activé. Description : `Bloquer Internet appareils (alias INTERNET_BLOQUE, piloté par Home Assistant)`.
2. **Pass** UDP, LAN net → `192.168.10.12:53` (AdGuard).
3. **Block** TCP/UDP, any → `PUBLIC_DNS:53` (force le DNS vers AdGuard).
4. **Pass** IPv4, LAN net → any (règle par défaut).
5. (IPv6 LAN → any : inutile, pas d'IPv6)

### Règles WAN

- **Pass** UDP any → WAN address:51820 (WireGuard).
- **Rien d'autre.** Les redirections 80/443 vers NPM ne sont **pas** reprises : tout passe par le tunnel Cloudflare (`cloudflared`, `.16`), qui sort vers Cloudflare et n'a besoin d'aucun port ouvert. Ancienne config, pour mémoire : WAN 80 → `192.168.10.11:80`, WAN 443 → `192.168.10.11:80` (incohérente), et une règle « Let's Encrypt HTTP challenge » orpheline.

### WireGuard

- Tunnel `wg0`, port **51820**, adresse `10.100.0.1/24`, MTU 1420.
- **Reprendre la clé privée du tunnel pfSense** (VPN → WireGuard → Tunnels → `tun_wg0`) : les clients n'auront alors rien à changer. La clé publique actuelle est `4V1U9MG/6vdC+u4YAWpXxkhO1kC0Si0xgdw/NlLWNDg=`. La clé privée n'est pas dans ce repo : la copier dans Vaultwarden au moment de la migration.
- Peers (pas de clé pré-partagée, keepalive 25 sauf Mac12) :

| Peer | IP | Clé publique |
|---|---|---|
| iPhone | `10.100.0.10/32` | `iuaj0LILW0gpY9ibVvvgrldy36xkrIr3pQyHjLFaZVI=` |
| Samsung A54 | `10.100.0.20/32` | `U++OTnAabThb0+wGJ9smvlhQHLzjqgFrmVusyeMjBl4=` |
| Mac12 | `10.100.0.30/32` | `Ooc+hpx25Dv2G2cDTbnbwHHhTRNsJv/rnGp6IlzVcG0=` |
| Mac Mini | `10.100.0.40/32` | `I1Mby8mXMqpY7sGCuaZsfBoYseghtN+R/7sUW1E+WzU=` |
| MacBook Pro Céline | `10.100.0.41/32` | `1ohf2MyE21Uuau82B74q974KuDhJpJ8aWfl8OpADpHU=` |

- Règle sur l'interface WireGuard : pass any → any.
- **NAT sortant** (mode hybride) : source `10.100.0.0/24` → destination `192.168.10.0/24`, sur l'interface LAN, traduit vers l'adresse LAN. Les appareils du LAN répondent ainsi aux clients VPN sans route de retour.
- Procédure pour ajouter un client : voir la note `wireguard-client-setup` (côté OPNsense : VPN → WireGuard → Peers).

### DNS dynamique

- `tischhome.duckdns.org`, mis à jour à chaque changement d'IP WAN. Utilisé comme adresse du serveur dans les configs des clients WireGuard.
- OPNsense : plugin `os-ddclient`, service DuckDNS, token DuckDNS (aujourd'hui dans l'entrée « Custom » de pfSense : Services → Dynamic DNS).

### DHCP (LAN)

- Plage dynamique `192.168.10.200–250`, DNS distribué `192.168.10.12`, passerelle `192.168.10.1`.
- Sur OPNsense, utiliser le service DHCP par défaut de la version installée (Dnsmasq sur les installations récentes), avec les mêmes paramètres.
- IP fixes configurées sur les machines elles-mêmes (pas de réservation) : `.2` Proxmox, `.3` TischNAS3, `.5` TischNAS2, `.10` Home Assistant, `.11` NPM, `.12` AdGuard, `.13` homefinance-db, `.18` Scanopy.
- **32 réservations** :

| IP | MAC | Hostname | Description |
|---|---|---|---|
| 192.168.10.14 | `bc:24:11:7b:6b:12` |  | MQTT |
| 192.168.10.15 | `bc:24:11:05:46:a8` |  | Z2M |
| 192.168.10.16 | `bc:24:11:47:6b:52` | cloudflared | Cloudflared tunnel |
| 192.168.10.17 | `bc:24:11:e8:77:1a` | vw | Vaultwarden (LXC) |
| 192.168.10.20 | `c4:a8:1d:f4:3c:a0` |  | Switch D-LINK DGS-1100-24 |
| 192.168.10.21 | `bc:24:11:81:c5:fc` | rtxtradingbot | rtxtradingbot |
| 192.168.10.22 | `00:11:2a:22:53:38` |  | Niko Home Control 2 (NHC2) |
| 192.168.10.23 | `5c:2f:af:0b:5b:e2` |  | HomeWizard P1 meter |
| 192.168.10.26 | `48:e1:e9:31:fe:cf` |  | Eufy Camera (Cuisine) |
| 192.168.10.30 | `d8:0d:17:c9:6d:98` |  | TP-LINK Deco M4R (Grenier) |
| 192.168.10.31 | `d8:0d:17:c9:78:48` |  | TP-LINK Deco M4R (Etage 1) |
| 192.168.10.32 | `d8:0d:17:c9:7a:34` |  | TP-LINK Deco M4R (Salon) |
| 192.168.10.33 | `6c:5a:b0:e4:93:6e` |  | TP-LINK TL-WR802N (Neato) |
| 192.168.10.35 | `d8:44:89:70:2a:aa` |  | TP-LINK CPL 1 (Salon) |
| 192.168.10.53 | `30:83:98:16:76:73` |  | SMLIGHT SLZB-06M |
| 192.168.10.90 | `b0:37:95:1a:36:95` |  | LG C1 |
| 192.168.10.92 | `5c:0c:e6:28:2c:18` |  | Nintendo Switch |
| 192.168.10.93 | `f0:b3:ec:25:6d:2e` |  | Apple TV 4K |
| 192.168.10.94 | `7c:2f:80:80:6a:73` |  | Gigaset Phone C5310-IP |
| 192.168.10.95 | `3a:38:d5:6f:1a:22` |  | Xiaomi Redmi |
| 192.168.10.96 | `ae:33:8b:ad:c5:93` |  | Apple iPad 5th gen (Cyril) |
| 192.168.10.97 | `0a:2c:db:47:c7:94` |  | iPhone Xs (Tristan) |
| 192.168.10.98 | `5c:1b:f4:9d:cc:76` | macmini-de-rudy | Apple Mac Mini M2 |
| 192.168.10.99 | `de:f0:14:39:bf:cd` |  | iPhone 14 Pro (Elias) |
| 192.168.10.181 | `bc:24:11:66:94:ff` |  | InfluxDB |
| 192.168.10.182 | `bc:24:11:9a:5e:65` |  | Grafana |
| 192.168.10.183 | `bc:24:11:f1:fc:34` |  | Rustdesk Server |
| 192.168.10.184 | `bc:24:11:e9:e5:4d` | Prometheus | Prometheus |
| 192.168.10.185 | `bc:24:11:1a:80:d7` | PAM | Prometheus Alert Manager |
| 192.168.10.186 | `bc:24:11:82:64:9e` | PBE | Prometheus Blackbox Exporter |
| 192.168.10.187 | `bc:24:11:bf:6f:f5` | linkwarden | linkwarden |
| 192.168.10.188 | `bc:24:11:ac:7c:bb` | pocketid | Pocket ID (LXC 104) |

### Non repris

- Résolveur DNS Unbound (désactivé, avec un ancien forward vers `.21`) : c'est AdGuard qui fait le DNS.
- Planification « AllDay », jamais utilisée.
- Paquet REST API pfSense : OPNsense a sa propre API.

## Ce qui dépend de pfSense ailleurs

| Où | Dépendance | Action |
|---|---|---|
| Home Assistant | `rest_command` + sensor `rest` sur l'API pfSense (alias `INTERNET_BLOQUE`, apply, kill states). Voir [[internet-appareils]]. | Réécrire pour l'API OPNsense : ajout ou retrait d'une IP dans l'alias directement (`firewall/alias_util/add` / `delete`), lecture de l'alias, coupure des connexions de l'IP. Nouveau compte API avec une clé et un secret. |
| Dashboard homelab | `server/routes/network.js` et `status.js` (API v2), `actions.js` (API **v1**, déjà obsolète) | Adapter à l'API OPNsense |
| NPM | Proxy host `pfsense.tixhon.be` | Créer `opnsense.tixhon.be` (le certificat existant de NPM suffit) |
| AdGuard | Réécriture DNS `pfsense.tixhon.be` → `.11` | Ajouter `opnsense.tixhon.be` |
| Mémoire Claude | `pfsense-access`, `pfsense-backup-freeze`, `network-topology` | Mettre à jour |

## Déroulement

### 1. Préparation (réseau actuel intact)

1. Sauvegarder la config pfSense (Diagnostics → Backup & Restore) et la ranger sur le NAS.
2. Copier dans Vaultwarden la clé privée du tunnel WireGuard et le token DuckDNS.
3. Installer OPNsense (image USB « vga ») sur le NVMe du boîtier, en ZFS.
4. Brancher un portable sur le port LAN du boîtier, **sans le relier au switch**, et tout configurer selon l'inventaire ci-dessus. Le LAN est déjà en `192.168.10.1`.
5. Créer le compte API pour Home Assistant et préparer la nouvelle version du YAML HA, sans la déployer.

### 2. Bascule (~15 min de coupure, un soir calme)

1. Proxmox : arrêter la VM 115 et désactiver son démarrage automatique (`qm set 115 --onboot 0`).
2. Câble du modem VOO → port WAN du boîtier. Port LAN du boîtier → switch.
3. **Éteindre le modem VOO 1 à 2 minutes**, puis le rallumer : il retient l'adresse MAC de l'ancien routeur et ne donnerait pas d'IP au nouveau boîtier.
4. Vérifier : IP WAN obtenue, Internet depuis le LAN, baux DHCP, résolution DNS via AdGuard.

### 3. Vérifications

- [ ] Internet sur un appareil filaire et un appareil Wi-Fi
- [ ] Les appareils récupèrent leur IP réservée (Apple TV `.93`, Switch `.92`…)
- [ ] Tunnel Cloudflare actif (Vaultwarden, Pocket ID joignables de l'extérieur)
- [ ] WireGuard depuis l'iPhone en 4G : accès au LAN
- [ ] DuckDNS à jour (l'IP WAN a pu changer)
- [ ] Un DNS public forcé (`dig @8.8.8.8`) est bloqué
- [ ] HA : déployer le nouveau YAML, puis tester couper et rétablir un appareil, et un minuteur de 1 min

### 4. Retour arrière

Câble du modem → NIPoGi (`enp1s0`, `vmbr0`), `qm start 115`, éteindre et rallumer le modem. Garder la VM 115 quelques semaines avant de la supprimer.

### 5. Après coup

- NIPoGi : passer le LAN (`vmbr1`) sur la carte intégrée `enp1s0`, libérée du WAN, et débrancher l'adaptateur USB. **Attention** : l'IP de gestion de Proxmox (`.2`) est sur `vmbr1`, donc garder un accès console ou écran pendant l'opération.
- Plus tard, au besoin : VLAN enfants ou invités sur un port libre, plugin Tailscale.
