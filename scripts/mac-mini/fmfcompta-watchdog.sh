#!/bin/bash
# Watchdog fmfcompta (Mac mini), lancé toutes les 2 min par le LaunchAgent be.tixhon.fmfcompta-watchdog.
#
# Teste l'appli compta via NPM (le vrai chemin du tunnel Cloudflare), pas via localhost :
# le 2026-10-27, l'appli répondait en local mais plus aux requêtes venant de NPM (504 Cloudflare).
# Si fmfcompta échoue mais que homeplan (même Mac, même NPM) répond, le souci vient de l'appli :
# on la relance. Si les deux échouent, c'est NPM ou le réseau : on ne touche à rien.
set -uo pipefail

NPM="http://192.168.10.11/"
TIMEOUT=15
JOB="gui/$(id -u)/be.fernelevents.compta"
TAG="[fmfcompta-watchdog $(date '+%Y-%m-%d %H:%M:%S')]"

probe() { curl -s -o /dev/null -w "%{http_code}" -m "$TIMEOUT" -H "Host: $1" "$NPM"; }
ok() { case "$1" in 200|302|307) return 0 ;; *) return 1 ;; esac; }

code=$(probe fmfcompta.tixhon.be)
ok "$code" && exit 0

# Seconde chance, pour ne pas relancer sur un raté isolé.
sleep 10
code=$(probe fmfcompta.tixhon.be)
ok "$code" && exit 0

ref=$(probe homeplan.tixhon.be)
if ! ok "$ref"; then
  echo "$TAG fmfcompta KO ($code) mais homeplan aussi ($ref) : NPM/réseau, pas de relance"
  exit 0
fi

echo "$TAG fmfcompta KO via NPM (http_code=$code), homeplan OK : relance $JOB"
launchctl kickstart -k "$JOB"
