#!/bin/bash
# Sauvegarde "reprise après sinistre" du NIPoGi (nœud Proxmox).
#
# Les sauvegardes vzdump couvrent les VM et LXC, mais pas le nœud lui-même.
# Ce script copie sur le NAS ce qu'il faut pour reconstruire le nœud sur un
# nouveau matériel :
#   - host/      config du nœud (/etc/pve, réseau, GRUB, NUT, cron, systemd...)
#   - info/      inventaire lisible (versions, VM/LXC, MAC, USB, disques, jobs)
#   - vaultwarden/  copie cohérente des données Vaultwarden (LXC 110),
#                restaurable sans Proxmox
#
# À lancer en root sur le nœud, par exemple chaque nuit après le vzdump :
#   /etc/cron.d/nipogi-drp-backup :
#   MAILTO=root
#   30 5 * * * root /root/RtxTools/scripts/drp/nipogi-drp-backup.sh >> /var/log/nipogi-drp-backup.log 2>&1
#
# Variables (toutes optionnelles) :
#   DRP_STORAGE         stockage Proxmox monté sous /mnt/pve (défaut : syno-backup)
#   DRP_DEST            dossier de destination (défaut : /mnt/pve/$DRP_STORAGE/drp)
#   DRP_KEEP            nombre de sauvegardes à garder (défaut : 14)
#   VW_CTID             LXC Vaultwarden (défaut : 110, vide pour ignorer)
#   VW_DATA             dossier data dans le LXC (défaut : /opt/vaultwarden/data)
#   VW_CONTAINER        conteneur Docker Vaultwarden (défaut : vaultwarden)
#   INCLUDE_SSH_PRIVATE 1 pour inclure les clés privées de /root/.ssh (défaut : 0)

set -euo pipefail
umask 077

DRP_STORAGE="${DRP_STORAGE:-syno-backup}"
DRP_DEST="${DRP_DEST:-/mnt/pve/$DRP_STORAGE/drp}"
DRP_KEEP="${DRP_KEEP:-14}"
VW_CTID="${VW_CTID-110}"
VW_DATA="${VW_DATA:-/opt/vaultwarden/data}"
VW_CONTAINER="${VW_CONTAINER:-vaultwarden}"
INCLUDE_SSH_PRIVATE="${INCLUDE_SSH_PRIVATE:-0}"

log() { echo "[$(date '+%F %T')] $*"; }
fail() { log "ERREUR: $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "à lancer en root sur le nœud Proxmox"
command -v pveversion >/dev/null || fail "pveversion introuvable : ce n'est pas un nœud Proxmox"

# Le NAS doit être monté, sinon on écrirait sur le disque local du NIPoGi
# (qui est justement ce qu'on veut pouvoir perdre).
mount_root="/mnt/pve/$DRP_STORAGE"
if [ -z "${DRP_DEST##"$mount_root"*}" ]; then
  mountpoint -q "$mount_root" || fail "$mount_root n'est pas monté (stockage $DRP_STORAGE)"
fi

stamp="$(date +%F_%H%M)"
work="$DRP_DEST/.inprogress-$stamp"
final="$DRP_DEST/$stamp"
mkdir -p "$work/host" "$work/info"
trap 'rm -rf "$work"' EXIT

# --- 1. Config du nœud -------------------------------------------------------
log "Config du nœud"
host_paths=(
  /etc/pve
  /etc/network/interfaces /etc/network/interfaces.d
  /etc/hosts /etc/hostname /etc/resolv.conf /etc/timezone
  /etc/default/grub /etc/kernel/cmdline /etc/kernel/proxmox-boot-pin
  /etc/modules /etc/modprobe.d /etc/udev/rules.d
  /etc/nut
  /etc/vzdump.conf
  /etc/cron.d /var/spool/cron/crontabs
  /etc/systemd/system
  /etc/sudoers.d
  /etc/apt/sources.list /etc/apt/sources.list.d
  /etc/prometheus-pve-exporter /etc/pve-exporter /etc/pve-exporter.yml
  /usr/local/bin /usr/local/sbin
  /root/.ssh/authorized_keys /root/.ssh/known_hosts /root/.ssh/config
)
existing=()
for p in "${host_paths[@]}"; do [ -e "$p" ] && existing+=("$p"); done
if [ "$INCLUDE_SSH_PRIVATE" = "1" ] && [ -d /root/.ssh ]; then
  existing+=(/root/.ssh)
else
  for pub in /root/.ssh/*.pub; do [ -e "$pub" ] && existing+=("$pub"); done
fi
# /etc/pve est un système de fichiers FUSE (pmxcfs) : tar le lit sans souci.
tar -czf "$work/host/nipogi-etc.tar.gz" --ignore-failed-read "${existing[@]}" 2>/dev/null \
  || log "avertissement: tar a signalé des fichiers illisibles (archive créée quand même)"

# --- 2. Inventaire lisible ---------------------------------------------------
log "Inventaire"
run() { local out="$1"; shift; { echo "\$ $*"; "$@" 2>&1 || true; } > "$work/info/$out"; }
run pveversion.txt        pveversion -v
run storage.txt           pvesm status
run qm-list.txt           qm list
run pct-list.txt          pct list
run ip-link.txt           ip -br link
run ip-addr.txt           ip -br addr
run bridges.txt           bridge link
run lsusb.txt             lsusb
run lsblk.txt             lsblk -f
run cmdline.txt           cat /proc/cmdline
run kernels.txt           proxmox-boot-tool kernel list
run jobs.txt              cat /etc/pve/jobs.cfg
run root-crontab.txt      crontab -l
run packages.txt          dpkg --get-selections
run dmi.txt               cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name /sys/class/dmi/id/board_name

{
  for id in $(qm list 2>/dev/null | awk 'NR>1 {print $1}'); do
    echo "===== VM $id"; qm config "$id" 2>&1 || true; echo
  done
  for id in $(pct list 2>/dev/null | awk 'NR>1 {print $1}'); do
    echo "===== LXC $id"; pct config "$id" 2>&1 || true; echo
  done
} > "$work/info/guests-config.txt"

# --- 3. Vaultwarden ----------------------------------------------------------
if [ -n "$VW_CTID" ] && pct status "$VW_CTID" 2>/dev/null | grep -q running; then
  log "Vaultwarden (LXC $VW_CTID)"
  mkdir -p "$work/vaultwarden"
  ct_tmp="/tmp/vw-drp-$stamp"
  # Copie cohérente de la base SQLite sans arrêter le service si possible,
  # sinon arrêt de quelques secondes du conteneur.
  pct exec "$VW_CTID" -- env VW_DATA="$VW_DATA" CT_TMP="$ct_tmp" VW_CONTAINER="$VW_CONTAINER" bash -s <<'INNER'
set -euo pipefail
mkdir -p "$CT_TMP"
db="$VW_DATA/db.sqlite3"
stopped=0
restart() { if [ "$stopped" = 1 ]; then docker start "$VW_CONTAINER" >/dev/null; stopped=0; fi; }
trap restart EXIT
if [ -f "$db" ]; then
  if command -v sqlite3 >/dev/null; then
    sqlite3 "$db" ".backup '$CT_TMP/db.sqlite3'"
  elif command -v python3 >/dev/null; then
    python3 - "$db" "$CT_TMP/db.sqlite3" <<'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
  else
    docker stop "$VW_CONTAINER" >/dev/null
    stopped=1
    cp -a "$db" "$CT_TMP/db.sqlite3"
  fi
fi
tar -czf "$CT_TMP/vaultwarden-data.tar.gz" -C "$VW_DATA" \
  --exclude='./db.sqlite3' --exclude='./db.sqlite3-wal' --exclude='./db.sqlite3-shm' \
  --exclude='./icon_cache' --exclude='./tmp' .
restart
if [ -f "$CT_TMP/db.sqlite3" ]; then gzip -f "$CT_TMP/db.sqlite3"; fi
# Fichiers de déploiement (compose / .env) s'ils existent à côté du dossier data
for f in "$(dirname "$VW_DATA")"/docker-compose.y*ml "$(dirname "$VW_DATA")"/compose.y*ml "$(dirname "$VW_DATA")"/.env; do
  if [ -f "$f" ]; then cp -a "$f" "$CT_TMP/"; fi
done
docker inspect "$VW_CONTAINER" > "$CT_TMP/docker-inspect.json" 2>/dev/null || true
INNER
  for f in db.sqlite3.gz vaultwarden-data.tar.gz docker-compose.yml docker-compose.yaml compose.yml compose.yaml .env docker-inspect.json; do
    if pct exec "$VW_CTID" -- test -f "$ct_tmp/$f"; then
      pct pull "$VW_CTID" "$ct_tmp/$f" "$work/vaultwarden/$f"
    fi
  done
  pct exec "$VW_CTID" -- rm -rf "$ct_tmp"
  [ -f "$work/vaultwarden/vaultwarden-data.tar.gz" ] || fail "copie Vaultwarden absente"
else
  log "Vaultwarden ignoré (LXC ${VW_CTID:-non défini} arrêté ou absent)"
fi

# --- 4. Finalisation + rétention --------------------------------------------
( cd "$work" && find . -type f -print0 | sort -z | xargs -0 sha256sum > ../.sums-"$stamp" && mv ../.sums-"$stamp" SHA256SUMS )
mv "$work" "$final"
trap - EXIT
log "Sauvegarde écrite dans $final ($(du -sh "$final" | cut -f1))"

mapfile -t olds < <(find "$DRP_DEST" -mindepth 1 -maxdepth 1 -type d -name '20*' | sort | head -n -"$DRP_KEEP")
for d in "${olds[@]}"; do
  log "Rétention: suppression de $d"
  rm -rf -- "$d"
done
find "$DRP_DEST" -mindepth 1 -maxdepth 1 -type d -name '.inprogress-*' -mtime +1 -exec rm -rf -- {} +
log "Terminé"
