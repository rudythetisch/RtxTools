# Alertes disque des LXC du NiPoGi

Mis en place le 2026-10-27, après le disque plein du LXC Grafana (107) qui bloquait ses mises à jour.

## Chaîne

```
pve-exporter (nœud 192.168.10.2:9221, chemin /pve)
  → Prometheus (LXC 113, 192.168.10.184:9090)
  → Alertmanager (LXC 111, 192.168.10.185:9093)
  → Telegram (bot existant, receiver "telegram")
```

Correctif du 2026-10-27 : le job `proxmox` de `prometheus.yml` lisait `/metrics` (métriques internes de l'exporter) au lieu de `/pve`. Aucune métrique Proxmox n'était donc collectée et les alertes `ProxmoxContainerDown` / `ProxmoxNodeHighCPU` ne pouvaient pas se déclencher. Ajout de `metrics_path: /pve` et des paramètres `cluster=1`, `node=1`.

## Règles

Fichier : `/etc/prometheus/rules/proxmox-disk.yml` (copie dans le repo : `scripts/monitoring/prometheus/rules/proxmox-disk.yml`).

| Alerte | Condition | Délai | Sévérité |
|---|---|---|---|
| LXCDiskWarning | rootfs > 85 % | 10 min | warning |
| LXCDiskCritical | rootfs > 95 % | 5 min | critical |
| LXCDiskFillingUp | plein dans < 3 jours (tendance 6 h) et > 50 % | 1 h | warning |
| LXCDiskFillingUpFast | plein dans < 12 h (tendance 1 h) et > 70 % | 15 min | critical |
| PVEStorageWarning | stockage Proxmox > 85 % | 15 min | warning |
| PVEStorageFillingUp | stockage plein dans < 7 jours (tendance 12 h) et > 60 % | 2 h | warning |

Les VM QEMU (HA 100, 115) sont exclues : sans agent invité, PVE rapporte un usage disque de 0.

Dans Alertmanager, une règle d'inhibition masque l'avertissement d'un LXC quand l'alerte critique du même LXC est active (`equal: [id]`, car le label `instance` est commun à tous les LXC).

Autres ajustements dans `homelab.yml` : `ProxmoxContainerDown` limité aux LXC/VM avec leur nom, `ProxmoxNodeHighCPU` limité au nœud (sinon un LXC à 100 % de ses vCPU déclenchait l'alerte « nœud »).

## Réagir à une alerte

Sur le NiPoGi :

```bash
pct resize <id> rootfs +2G
```

L'agrandissement se fait à chaud, sans redémarrer le LXC. Penser à vérifier `local-lvm` (thin pool) avant.

## État au 2026-10-27

- z2m (102) : 91 % → déclenche LXCDiskWarning, agrandi 4 → 6 Go le jour même (64 %)
- local-lvm est surprovisionné (379 Go alloués pour 349 Go de pool), couvert par PVEStorageWarning / PVEStorageFillingUp
- adguard (103) : 75 %
- influxdb (106) : 69 %
- linkwarden (114) : 67 %
- syno-backup : 70 %, local-lvm : 40 %

## Requêtes utiles

```promql
sort_desc(pve:lxc_disk_used:ratio)
pve:storage_disk_used:ratio
```
