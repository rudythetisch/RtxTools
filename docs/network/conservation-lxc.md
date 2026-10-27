# Conservation des logs et caches des LXC du NiPoGi

Mis en place le 2026-10-27, suite aux [[alertes-disque-lxc]] (z2m à 91 %, Grafana plein le même jour).

## Diagnostic (2026-10-27)

Trois causes de croissance, communes à presque tous les LXC :

| Cause | Taille par LXC | Pourquoi ça grossit |
|---|---|---|
| journald (`/var/log/journal`) | 100 à 620 Mo | Aucune limite : par défaut 10 % du disque, plafonné à 4 Go |
| Cache apt (`/var/cache/apt`) | 100 à 360 Mo | Les `.deb` restent après chaque mise à jour |
| Données propres à l'application | variable | Voir les cas particuliers ci-dessous |

Cas particuliers :

- **AdGuard (103)** : historique des requêtes DNS gardé 90 jours (`querylog.json`, 2,3 Go) et `/var/log/AdGuardHome.err` de 460 Mo, sans rotation.
- **InfluxDB (106)** : 3,9 Go dans `/var/lib/influxdb/engine`. Durée de conservation du bucket non vérifiée (il faut un jeton Influx, `influx bucket list -o <org>`).
- **Vaultwarden (110)** : 4,3 Go de restes de compilation dans `/root` (`.rustup` 2,6 Go, `vaultwarden-1.37.0/target` 1,3 Go). Laissés en place : disque de 20 Go, et la toolchain sert aux mises à jour depuis les sources.
- **Linkwarden (114)** : `/root/.rustup` 1,4 Go, `/root/.cache/ms-playwright` 1,2 Go. Laissés en place pour la même raison.
- **z2m (102)** : caches pnpm/npm dans `/root` (~1 Go), recréés à chaque mise à jour.

## Changements appliqués sur les 16 LXC

### journald

`/etc/systemd/journald.conf.d/50-rtx-retention.conf` :

```ini
[Journal]
SystemMaxUse=100M
MaxRetentionSec=30day
```

Puis `systemctl restart systemd-journald` et `journalctl --vacuum-size=100M --vacuum-time=30d`.

### apt

`/etc/apt/apt.conf.d/99-rtx-no-cache` :

```
APT::Keep-Downloaded-Packages "false";
Binary::apt::APT::Keep-Downloaded-Packages "false";
```

Puis `apt-get clean`. Les `.deb` sont supprimés après chaque installation.

### Espace libéré

| LXC | Libéré |
|---|---|
| 101 mqtt | 332 Mo |
| 102 z2m | 633 Mo |
| 103 adguard | 226 Mo (+ voir AdGuard) |
| 104 pocketid | 163 Mo |
| 105 nginxproxymanager | 837 Mo |
| 106 influxdb | 634 Mo |
| 107 grafana | 473 Mo |
| 108 rustdeskserver | 359 Mo |
| 109 cloudflared | 319 Mo |
| 110 vaultwarden | 309 Mo |
| 111 prometheus-alertmanager | 291 Mo |
| 112 prometheus-blackbox-exporter | 430 Mo |
| 113 prometheus | 358 Mo |
| 114 linkwarden | 507 Mo |
| 116 homefinance-db | 209 Mo |
| 117 scanopy | 362 Mo |

Total : environ 6,9 Go, rendus au thin pool `local-lvm` par `pct fstrim <id>` (40,8 % → 39,3 %).

## AdGuard (LXC 103)

- Historique des requêtes : `querylog.interval` passé de `90d` à `720h` (30 jours) dans `/opt/AdGuardHome/AdGuardHome.yaml`. Sauvegarde : `AdGuardHome.yaml.bak-20261027`. Modifié service arrêté, car AdGuard réécrit son fichier de configuration en s'arrêtant.
- L'historique existant a été coupé au 2026-09-27 (2,46 Go → 1,6 Go). Il sera ensuite renouvelé automatiquement par rotation tous les 30 jours.
- `/var/log/AdGuardHome.err` vidé (460 Mo, contenu datant de 2024) et mis en rotation par `/etc/logrotate.d/adguardhome` : hebdomadaire, 50 Mo maximum, 4 archives compressées, `copytruncate`.
- Piège : l'API (`POST /control/login`) a renvoyé 403 depuis le Mac mini ce jour-là, d'où la modification par fichier.

Résultat : 80 % → 46 %.

## Occupation après intervention

Linkwarden 63 %, InfluxDB 61 %, z2m 49 % (après agrandissement à 6 Go), AdGuard 46 %, tous les autres sous 45 %.

## Pour un nouveau LXC

Reprendre les deux fichiers `50-rtx-retention.conf` et `99-rtx-no-cache` ci-dessus dès la création. Les scripts « Proxmox helper scripts » ne les posent pas.
