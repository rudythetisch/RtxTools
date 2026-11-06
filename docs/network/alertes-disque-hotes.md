# Alertes disque des hôtes (NAS, Mac) et supervision des cibles

Mis en place le 2026-11-06. Complète [[alertes-disque-lxc]] (LXC et stockages Proxmox, via pve-exporter).

Chaîne : `node_exporter` (hôte) → Prometheus (LXC 113) → Alertmanager (LXC 111) → Telegram.

## Ce qui est surveillé

| Hôte | Exporter | Job Prometheus |
|---|---|---|
| TischNAS2 | binaire `/usr/local/bin/node_exporter`, démarré par `/etc/rc.local` | `nas-tischnas2` |
| TischNAS3 | conteneur Docker `node-exporter-rtx` (`--restart unless-stopped`) | `nas-tischnas3` |
| Mac mini | `brew services` (`node_exporter`, flags dans `/opt/homebrew/etc/node_exporter.args`) | `mac-mini` |
| MacBook Pro (192.168.10.243) | `brew install node_exporter && brew services start node_exporter` à lancer sur le portable | `mac-portable` (exclu de TargetDown) |
| LXC / VM Proxmox, stockages | pve-exporter | `proxmox` |

Les VM QEMU (HA 100, 115) n'ont pas d'alerte disque (pas d'agent invité).

## Règles (`scripts/monitoring/prometheus/rules/node-disk.yml`)

| Alerte | Condition | Délai | Sévérité |
|---|---|---|---|
| NodeDiskWarning | > 80 % | 10 min | warning |
| NodeDiskCritical | > 90 % | 5 min | critical |
| NodeDiskFillingUp | plein dans < 3 j (tendance 6 h) et > 50 % | 1 h | warning |
| NodeDiskFillingUpFast | plein dans < 12 h (tendance 1 h) et > 70 % | 15 min | critical |
| TargetDown | `up == 0` (hors homeassistant et mac-portable) | 5 min | critical |

Ces règles remplacent `DiskSpaceWarning/Critical` de `homelab.yml` (groupe `homelab-disk` retiré).
La série `node:filesystem_used:percent` exclut les types virtuels/réseau, les montages en lecture
seule (images .dmg, volume système macOS scellé) et les montages techniques Synology (`/volumeN/@*`).
Une règle d'inhibition Alertmanager masque l'avertissement quand la critique du même
`instance` + `mountpoint` est active. Critiques répétées toutes les heures.

## Pièges

- **Synology** : la mise à jour DSM du 2026-10-27 a supprimé `/etc/rc.local` sur TischNAS3, node_exporter
  n'a plus redémarré après et la cible est restée `down` sans alerte (cause de l'ajout de TargetDown).
  TischNAS2 dépend encore de `rc.local` : s'il disparaît, TargetDown préviendra. Remède durable : même
  conteneur Docker que NAS3.
  `docker run -d --name node-exporter-rtx --restart unless-stopped --net host --pid host -v /:/host:ro quay.io/prometheus/node-exporter:v1.9.1 --path.rootfs=/host` (sans `rslave`, non supporté par DSM).
- **macOS** : `df /` montre le volume système (38 %), pas l'occupation réelle. Le conteneur APFS est
  partagé : l'alerte porte sur `/System/Volumes/Data`.
- **Home Assistant** : le job `homeassistant` est `down` en permanence (`/metrics` en 404, intégration
  Prometheus non activée dans HA), d'où son exclusion de TargetDown.

## Réagir

- Mac : Réglages Système > Général > Stockage ; `du -xhd1 ~ | sort -h`.
- NAS : `sudo df -h`, purger les images Docker (`docker image prune -a`), vérifier `/volume1/@recycle`.
