# Proxmox Homelab

Gestion du nœud Proxmox (`192.168.10.2`) via Claude Code + MCP.

## Infrastructure

| VMID | Type | Nom | IP | Description |
|------|------|-----|----|-------------|
| 100 | VM | haos12.4 | 192.168.10.10 | Home Assistant OS |
| 101 | LXC | mqtt | 192.168.10.14 | Mosquitto MQTT broker |
| 102 | LXC | z2m | 192.168.10.15 | Zigbee2MQTT |
| 103 | LXC | adguard | 192.168.10.12 | AdGuard Home (DNS + ad blocking) |
| 104 | VM | pfSense | 192.168.10.1 | Firewall / routeur |
| 105 | LXC | nginxproxymanager | 192.168.10.11 | Nginx Proxy Manager (reverse proxy) |
| 106 | LXC | influxdb | 192.168.10.181 | InfluxDB (time series) |
| 107 | LXC | grafana | 192.168.10.182 | Grafana (dashboards) |
| 108 | LXC | rustdeskserver | 192.168.10.183 | RustDesk server (hbbs + hbbr) |
| 109 | LXC | cloudflared | 192.168.10.16 | Cloudflare tunnel |
| 110 | LXC | vaultwarden | 192.168.10.17 | Vaultwarden (gestionnaire de mots de passe) |
| 111 | LXC | prometheus-alertmanager | 192.168.10.185 | Prometheus Alertmanager |
| 112 | LXC | prometheus-blackbox-exporter | 192.168.10.186 | Blackbox Exporter |
| 113 | LXC | prometheus | 192.168.10.184 | Prometheus |
| 114 | LXC | linkwarden | 192.168.10.187 | Linkwarden (bookmarks) |

## MCP Proxmox

Le MCP `proxmox-mcp-server` est configuré dans `.mcp.json` (projet et global `~/.claude/`).

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uvx",
      "args": ["proxmox-mcp-server"],
      "env": {
        "PROXMOX_HOST": "192.168.10.2",
        "PROXMOX_TOKEN_NAME": "claude",
        "PROXMOX_TOKEN_VALUE": "<secret>",
        "PROXMOX_VERIFY_SSL": "false"
      }
    }
  }
}
```

Token API : `root@pam!claude` — créé dans Proxmox UI → Datacenter → API Tokens.

## Accès SSH

Clé `~/.ssh/id_ed25519` autorisée sur `root@192.168.10.2`.

Commandes utiles :
```bash
# Exécuter une commande dans un LXC
ssh root@192.168.10.2 'pct exec <VMID> -- <commande>'

# Pousser un fichier dans un LXC
ssh root@192.168.10.2 'pct push <VMID> /src /dst'
```

## Skills Claude Code

| Skill | Usage |
|-------|-------|
| `/proxmox-health` | Health check fonctionnel de chaque LXC et VM (ports, HTTP, DNS, systemctl) |
| `/proxmox-updates` | Audit des mises à jour disponibles avec niveaux de risque (🟢/🟡/🔴) |

### /proxmox-health
Teste que chaque service **répond correctement** — à lancer après un reboot ou pour vérifier l'état du homelab.

### /proxmox-updates
Audite les paquets disponibles sur le nœud Proxmox, tous les LXC et les VMs. Produit un rapport avec recommandations et commandes d'installation. À lancer hebdomadairement.

## Monitoring

Stack : Prometheus (LXC 113) + Grafana (LXC 107) + Alertmanager (LXC 111) + Blackbox (LXC 112).

### Exporters installés

| Target | Exporter | Port | Notes |
|--------|----------|------|-------|
| Proxmox node | pve-exporter 3.9.0 | 9221 | Service systemd sur le nœud, token root@pam!claude |
| TischNAS2 | node_exporter 1.11.1 | 9100 | /usr/local/bin/, démarrage via /etc/rc.local |
| TischNAS3 | node_exporter 1.11.1 | 9100 | idem |

### Accès SSH NAS

- `ssh secureAdmin@192.168.10.5` / `ssh secureAdmin@192.168.10.3`
- Clé Ed25519 déployée, sudo disponible (password requis)
- Root SSH désactivé sur les deux NAS

### Jobs Prometheus actifs

```
prometheus, proxmox, blackbox, nas-tischnas2, nas-tischnas3, homeassistant
```

Config : `/etc/prometheus/prometheus.yml` dans LXC 113.

### En cours (issue #1)
- [ ] AC3 : Dashboard Grafana Proxmox (communautaire)
- [ ] AC4 : Dashboard Grafana Synology (communautaire)
- [ ] AC5 : Règles d'alerte Prometheus
- [ ] AC6 : Alertmanager → Telegram bot dédié homelab
- [ ] AC7 : Architecture extensible documentée

## Notes opérationnelles

### Alertmanager (LXC 111)
Le service peut crasher au démarrage après un reboot (race condition réseau). Fix appliqué : `--cluster.listen-address=''` dans `/etc/systemd/system/alertmanager.service`.

### Vaultwarden (LXC 110)
Écoute sur `:8000` mais répond en HTTP/0.9 (Rocket framework). `curl` refuse ce protocol — tester via `systemctl is-active vaultwarden`. Accès réel via NPM (HTTPS).

### Kernel Proxmox
Kernel épinglé à `6.8.12-30-pve` via `proxmox-boot-tool kernel pin`. Actif au prochain reboot.

### Mise à jour RustDesk (LXC 108)
Procédure : télécharger les `.deb` sur le nœud Proxmox puis `pct push` + `dpkg -i` dans le container (pas d'accès Internet direct depuis le LXC).
```bash
ssh root@192.168.10.2 'wget -O /tmp/hbbr.deb <url> && wget -O /tmp/hbbs.deb <url>'
ssh root@192.168.10.2 'pct push 108 /tmp/hbbr.deb /tmp/hbbr.deb && pct push 108 /tmp/hbbs.deb /tmp/hbbs.deb'
ssh root@192.168.10.2 'pct exec 108 -- dpkg -i /tmp/hbbr.deb /tmp/hbbs.deb'
```
