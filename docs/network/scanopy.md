# Scanopy — cartographie du réseau

[Scanopy](https://scanopy.net/) découvre les machines et les services du réseau, et en tire des cartes (topologie L2/L3, VM et conteneurs, applications) mises à jour à chaque scan. Édition **Community** : gratuite, open source (AGPL-3.0), un seul site.

Installé le 2026-10-19.

## Accès

- Interface : http://192.168.10.18:60072 (LAN uniquement, **pas** publié via Cloudflare ni NPM)
- Compte admin : créé à la première connexion, à ranger dans Vaultwarden

## Hébergement

| Élément | Valeur |
|---|---|
| Machine | LXC **117** `scanopy` sur Proxmox NIPoGi, non privilégié, `nesting=1,keyctl=1`, démarrage auto |
| Ressources | 2 cœurs, 2 Go RAM, 512 Mo swap, disque 12 Go (`local-lvm`) |
| Réseau | `192.168.10.18/24` statique (hors plage DHCP), passerelle `.1`, DNS `.12` (AdGuard) |
| OS | Debian 12 + Docker (script officiel `get.docker.com`) |
| Stack | `/opt/scanopy/docker-compose.yml` (compose officiel de la v0.18.0, images épinglées via `SCANOPY_VERSION`) |
| Secrets | `/opt/scanopy/.env` (`chmod 600`) : `SCANOPY_VERSION`, `POSTGRES_PASSWORD` (aléatoire), `SCANOPY_PUBLIC_URL` |

Trois conteneurs :

- `scanopy-server-1` : API + interface web, port `60072`
- `scanopy-postgres-1` : base PostgreSQL 17 (volume `postgres_data`)
- `scanopy-daemon` : le scanner, en `network_mode: host` + `privileged` pour voir le LAN directement (port `60073`)

## Commandes utiles

```bash
ssh root@192.168.10.2
pct enter 117
cd /opt/scanopy
docker compose ps
docker compose logs -f daemon
```

**Mise à jour** : changer `SCANOPY_VERSION` dans `.env` (tags `vX.Y.Z` sur `ghcr.io/scanopy/scanopy/server`), puis `docker compose pull && docker compose up -d`.

## Sources de découverte

Sans configuration, le daemon scanne le sous-réseau `192.168.10.0/24` (ARP, ports, empreinte des services). Pour enrichir la carte :

- **Switch D-Link DGS-1100-24** : activer SNMP (lecture seule, communauté autre que `public`) et LLDP → quel appareil sur quel port.
- **pfSense** : Services → SNMP → table ARP et interfaces.
- **Docker des autres machines** (TischNAS3, LXC Docker) : via un daemon Scanopy supplémentaire sur la machine, ou son socket Docker.
- **Deco TP-Link** : ni SNMP ni LLDP, les clients Wi-Fi apparaissent sans leur borne. Sera résolu avec UniFi (voir [[projets-futurs#Wi-Fi UniFi + VLAN]]), que Scanopy sait interroger.

## Noms des machines

Scanopy nomme les machines d'après leur nom d'hôte ou le service détecté, et ne lit pas les réservations DHCP de pfSense : beaucoup apparaissaient sous leur seule IP. Le 2026-10-19, 38 machines ont été renommées via l'API (`PUT /api/hosts/{id}` avec `name`, en recopiant les autres champs ; ports, IP et services sont conservés quand on ne les envoie pas). Convention : nom de la réservation DHCP, suivi de l'ID Proxmox pour les VM et LXC, par exemple `MQTT (LXC 101)`.

À la découverte suivante, une machine nouvelle reprend un nom automatique : la renommer dans l'interface (ou via l'API avec une clé en écriture).

Non découverts au premier scan :

- **Switch D-Link `.20`** : ne répond ni au ping ni en HTTP, et n'apparaît pas dans la table ARP de pfSense. Son IP de gestion n'est sans doute pas `.20` (IP par défaut D-Link : `10.90.90.90`). À retrouver avant d'activer SNMP/LLDP.
- iPhone de Tristan `.97`, LG C1 `.90`, Redmi `.95`, rtxtradingbot `.21` : en veille ou éteints pendant le scan.
