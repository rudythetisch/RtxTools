#!/bin/bash
# Copie de référence de /etc/nut/shutdown-script.sh (NIPoGi, Proxmox 192.168.10.2).
# Déclenché par upsmon (SHUTDOWNCMD) : batterie critique, ou arrêt anticipé 15 s après
# le passage sur batterie (upssched.conf). Voir scripts/guides/configure-nut-ups.md.
#
# Historique :
#   2026-08-05  création (séquentiel : NAS, attente 30 s, VM, LXC, NIPoGi)
#   2026-10-29  appels NAS avec timeout + horodatage de chaque étape
#   2026-10-29  (après le premier test réel : 189 s pour 165 s de batterie)
#               NAS, VM et LXC arrêtés en parallèle, plus d'attente fixe de 30 s.
#
# Essai à blanc (n'arrête rien, journal dans /tmp) :  DRY_RUN=1 /etc/nut/shutdown-script.sh

if [ -n "$DRY_RUN" ]; then LOG=/tmp/ups-shutdown-dry.log; : > "$LOG"; else LOG=/var/log/ups-shutdown.log; fi
T_START=$(date +%s)
ts()  { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(ts) - $*" >> "$LOG"; }
el()  { echo "+$(( $(date +%s) - T_START ))s"; }

log "DECLENCHEMENT arret d'urgence UPS${DRY_RUN:+ (ESSAI A BLANC)}"

SSH_OPTS="-o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=2"

stop_nas() {  # $1 = nom, $2 = ip
  log "Arret $1 ($2)"
  if [ -n "$DRY_RUN" ]; then sleep 2; rc=0
  else timeout 20 ssh $SSH_OPTS claude@"$2" 'sudo -n /usr/syno/sbin/synoshutdown --shutdown' >> "$LOG" 2>&1; rc=$?
  fi
  log "$1 : commande d'arret terminee, code $rc ($(el))"
}

stop_guest() {  # $1 = vm|ct, $2 = id
  if [ -n "$DRY_RUN" ]; then sleep $(( RANDOM % 4 + 1 )); rc=0
  elif [ "$1" = vm ]; then qm shutdown "$2" --timeout 60 >> "$LOG" 2>&1; rc=$?
  else pct shutdown "$2" --timeout 40 >> "$LOG" 2>&1; rc=$?
  fi
  log "  - $1 $2 arrete, code $rc ($(el))"
}

# Tout part en même temps : les NAS (les plus longs à s'éteindre) reçoivent leur ordre
# pendant que les VM et LXC s'arrêtent. Les NAS sont joints en L2 via le switch, ils ne
# dépendent ni de pfSense ni des LXC.
stop_nas TischNAS2 192.168.10.5 &
stop_nas TischNAS3 192.168.10.3 &

log "Arret en parallele des VM et LXC Proxmox ($(el))"
for id in $(qm list | awk 'NR>1 {print $1}'); do stop_guest vm "$id" & done
for id in $(pct list | awk 'NR>1 {print $1}'); do stop_guest ct "$id" & done
wait

log "Arret NIPoGi lui-meme ($(el) depuis le declenchement du script)"
[ -n "$DRY_RUN" ] && { log "ESSAI A BLANC : pas d'arret reel"; exit 0; }
shutdown -h now
