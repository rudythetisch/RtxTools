#!/bin/bash
# Réveille les NAS Synology (Wake-on-LAN) au démarrage de NIPoGi.
# Après un arrêt propre (NUT -> synoshutdown), un NAS ne redémarre pas seul au retour du courant :
# NIPoGi (BIOS en "Power On") démarre, puis envoie un paquet magique aux NAS qui ne répondent pas.
#   wol-nas.sh        : pour chaque NAS éteint (pas de ping), un paquet toutes les 20 s, 15 min max
#   FORCE=1 wol-nas.sh : envoie un paquet à chaque NAS une seule fois (test)
NAS="TischNAS2|192.168.10.5|00:11:32:6d:d9:09 TischNAS3|192.168.10.3|90:09:d0:90:0d:c7"
BCAST=192.168.10.255

say() { logger -t wol-nas "$*"; echo "$(date +%T) $*"; }
magic() {
  python3 - "$1" "$BCAST" <<'PY'
import socket, sys
mac = bytes.fromhex(sys.argv[1].replace(":", ""))
pkt = b"\xff" * 6 + mac * 16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
for port in (9, 7):
    s.sendto(pkt, (sys.argv[2], port))
PY
}
up() { ping -c1 -W1 "$1" >/dev/null 2>&1; }

if [ -n "$FORCE" ]; then
  for e in $NAS; do IFS='|' read -r n ip mac <<< "$e"; magic "$mac"; say "TEST : paquet envoyé à $n ($mac)"; done
  exit 0
fi

end=$(( $(date +%s) + 900 ))
while [ "$(date +%s)" -lt "$end" ]; do
  pending=0
  for e in $NAS; do
    IFS='|' read -r n ip mac <<< "$e"
    if up "$ip"; then continue; fi
    pending=1; magic "$mac"; say "$n ne répond pas : paquet de réveil envoyé ($mac)"
  done
  [ "$pending" = 0 ] && { say "tous les NAS répondent, terminé"; exit 0; }
  sleep 20
done
say "abandon après 15 min : au moins un NAS ne répond toujours pas"
