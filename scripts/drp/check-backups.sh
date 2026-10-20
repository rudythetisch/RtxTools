#!/bin/bash
# Vérifie que chaque VM/LXC du NIPoGi a une sauvegarde vzdump récente sur le
# NAS, et que la sauvegarde du nœud (nipogi-drp-backup.sh) tourne.
# Sort en code 1 s'il manque quelque chose : avec cron + MAILTO, on reçoit
# un mail uniquement en cas de problème.
#
#   /etc/cron.d/nipogi-check-backups :
#   MAILTO=root
#   0 8 * * * root /root/RtxTools/scripts/drp/check-backups.sh --quiet
#
# Variables : DRP_STORAGE (défaut syno-backup), MAX_AGE_H (défaut 26),
#             DRP_DEST (défaut /mnt/pve/$DRP_STORAGE/drp)

set -uo pipefail

DRP_STORAGE="${DRP_STORAGE:-syno-backup}"
MAX_AGE_H="${MAX_AGE_H:-26}"
DUMP_DIR="/mnt/pve/$DRP_STORAGE/dump"
DRP_DEST="${DRP_DEST:-/mnt/pve/$DRP_STORAGE/drp}"
QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

problems=()
report=()
now=$(date +%s)
max_age=$((MAX_AGE_H * 3600))

age_h() { echo $(( (now - $1) / 3600 )); }

if ! mountpoint -q "/mnt/pve/$DRP_STORAGE"; then
  echo "ERREUR: /mnt/pve/$DRP_STORAGE n'est pas monté"
  exit 1
fi

# Sauvegarde la plus récente d'un invité, d'après le nom de fichier vzdump
# (vzdump-qemu-100-2026_10_20-03_00_02.vma.zst). Affiche l'epoch, ou rien.
latest_dump() {
  local kind="$1" id="$2" f ts
  f=$(find "$DUMP_DIR" -maxdepth 1 -type f -name "vzdump-$kind-$id-*" \
        ! -name '*.log' ! -name '*.notes' ! -name '*.tmp' -printf '%f\n' 2>/dev/null | sort | tail -n1)
  [ -n "$f" ] || return 0
  ts=$(sed -E 's/^vzdump-[a-z]+-[0-9]+-([0-9]{4})_([0-9]{2})_([0-9]{2})-([0-9]{2})_([0-9]{2})_([0-9]{2}).*/\1-\2-\3 \4:\5:\6/' <<<"$f")
  date -d "$ts" +%s 2>/dev/null
}

check_guest() {
  local kind="$1" id="$2" name="$3" ts
  ts=$(latest_dump "$kind" "$id")
  if [ -z "$ts" ]; then
    problems+=("$kind $id ($name) : aucune sauvegarde dans $DUMP_DIR")
  elif [ $((now - ts)) -gt "$max_age" ]; then
    problems+=("$kind $id ($name) : dernière sauvegarde il y a $(age_h "$ts") h")
  else
    report+=("OK  $kind $id ($name) : il y a $(age_h "$ts") h")
  fi
}

while read -r id name _; do
  check_guest qemu "$id" "$name"
done < <(qm list 2>/dev/null | awk 'NR>1 {print $1, $2}')

while read -r id _ _ name; do
  check_guest lxc "$id" "${name:-?}"
done < <(pct list 2>/dev/null | awk 'NR>1 {print $1, $2, $3, $NF}')

# Le job de sauvegarde doit viser tous les invités, pour ne pas oublier
# un LXC créé après coup.
if [ -f /etc/pve/jobs.cfg ] && ! awk '/^vzdump:/{j=1} j&&/^[[:space:]]+all[[:space:]]+1/{f=1} END{exit !f}' /etc/pve/jobs.cfg; then
  problems+=("aucun job vzdump en mode « tous les invités » (all 1) dans /etc/pve/jobs.cfg")
fi

# Sauvegarde du nœud lui-même
last_drp=$(find "$DRP_DEST" -mindepth 1 -maxdepth 1 -type d -name '20*' -printf '%T@\n' 2>/dev/null | sort -n | tail -n1)
if [ -z "$last_drp" ]; then
  problems+=("aucune sauvegarde du nœud dans $DRP_DEST (nipogi-drp-backup.sh)")
else
  last_drp=${last_drp%.*}
  if [ $((now - last_drp)) -gt "$max_age" ]; then
    problems+=("sauvegarde du nœud : la plus récente date de $(age_h "$last_drp") h")
  else
    report+=("OK  nœud (config + Vaultwarden) : il y a $(age_h "$last_drp") h")
  fi
fi

if [ "$QUIET" = 0 ] || [ ${#problems[@]} -gt 0 ]; then
  printf '%s\n' "${report[@]}"
fi
if [ ${#problems[@]} -gt 0 ]; then
  echo
  echo "PROBLÈMES (${#problems[@]}) :"
  printf '  - %s\n' "${problems[@]}"
  exit 1
fi
[ "$QUIET" = 1 ] || echo "Tout est sauvegardé (moins de $MAX_AGE_H h)."
exit 0
