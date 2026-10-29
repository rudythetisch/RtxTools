#!/bin/bash
# probe.sh — sonde de disponibilité du homelab, pour mesurer les temps d'arrêt et de reprise.
#
# À lancer sur une machine qui reste allumée pendant le test (le Mac mini, hors UPS).
# Un test par appareil et par service, chaque seconde, résultat horodaté dans un TSV :
#     epoch_s <TAB> cible <TAB> test <TAB> ok|ko
# Analyse ensuite avec report.sh.
#
# Usage :
#     UPSTEST_DIR=/chemin/dossier ./probe.sh start        # lance en arrière-plan
#     UPSTEST_DIR=/chemin/dossier ./probe.sh mark T0      # pose un repère horodaté
#     UPSTEST_DIR=/chemin/dossier ./probe.sh mark RALLUMAGE "bouton UPS"
#     UPSTEST_DIR=/chemin/dossier ./probe.sh status       # dernières lignes + taille
#     UPSTEST_DIR=/chemin/dossier ./probe.sh stop
#
# Repères reconnus par report.sh : T0 (déclenchement) et RALLUMAGE (UPS/NIPoGi rallumé).
# Tout autre repère apparaît dans la chronologie.

set -u
DIR="${UPSTEST_DIR:-$PWD}"
PIDF="$DIR/probe.pid"
CUR="$DIR/probe.current"
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

now() { date +%s; }
rec() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$LOG"; }

# --- tests unitaires ---------------------------------------------------------
c_ping() { ping -c1 -W 1000 "$1"; }
c_tcp()  { nc -z -G 1 "$1" "$2"; }
c_dns()  { dig +time=1 +tries=1 +short @"$1" example.com A | grep -q .; }
c_link() { ifconfig en0 | grep -q 'status: active'; }
# Tunnel Cloudflare : on force l'IP publique de Cloudflare pour ne pas passer par la
# réécriture DNS locale d'AdGuard (qui renverrait directement vers NPM).
c_cf()   { [ "$(curl -s -o /dev/null -m 5 -w '%{http_code}' \
            --resolve fmfcompta.tixhon.be:443:104.21.28.238 https://fmfcompta.tixhon.be/)" = 302 ]; }

# watch NOM TEST INTERVALLE CMD...
watch() {
  local name=$1 test=$2 every=$3; shift 3
  while :; do
    local t; t=$(now)
    if "$@" >/dev/null 2>&1; then rec "$t" "$name" "$test" ok; else rec "$t" "$name" "$test" ko; fi
    sleep "$every"
  done
}

run() {
  mkdir -p "$DIR"
  LOG="$DIR/probe-$(date +%Y%m%d-%H%M%S).tsv"
  echo "$LOG" > "$CUR"
  # Ne jamais utiliser `kill 0` : le script est lancé sans nouveau groupe de processus,
  # il tuerait aussi le shell appelant.
  trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM
  rec "$(now)" MARK "SONDE_DEMARREE" "-"

  # nom | ip | ports TCP (séparés par des virgules)
  while IFS='|' read -r name ip ports; do
    [ -z "$name" ] && continue
    watch "$name" ping 1 c_ping "$ip" &
    if [ -n "$ports" ]; then
      for p in ${ports//,/ }; do watch "$name" "tcp$p" 1 c_tcp "$ip" "$p" & done
    fi
  done <<'EOF'
NIPoGi|192.168.10.2|8006
pfSense|192.168.10.1|80
AdGuard|192.168.10.12|
NPM|192.168.10.11|80
RustDesk|192.168.10.183|21116
Cloudflared|192.168.10.16|
HomeAssistant|192.168.10.10|8123
MQTT|192.168.10.14|1883
Z2M|192.168.10.15|
Vaultwarden|192.168.10.17|
Scanopy|192.168.10.18|
HomefinanceDB|192.168.10.13|
InfluxDB|192.168.10.181|
Grafana|192.168.10.182|
Prometheus|192.168.10.184|
Alertmanager|192.168.10.185|
Blackbox|192.168.10.186|
Linkwarden|192.168.10.187|
PocketID|192.168.10.188|
TischNAS2|192.168.10.5|6751
TischNAS3|192.168.10.3|6751
Switch24p|192.168.10.20|
Deco-Grenier|192.168.10.30|
Deco-Mezzanine|192.168.10.31|
Deco-Salon|192.168.10.32|
Internet|1.1.1.1|
EOF
  watch AdGuard dns 2 c_dns 192.168.10.12 &
  watch Tunnel-Cloudflare http 10 c_cf &
  watch MacMini-lien link 1 c_link &
  wait
}

case "${1:-}" in
  run)   run ;;
  start)
    mkdir -p "$DIR"
    [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null && { echo "Déjà lancée (pid $(cat "$PIDF"))."; exit 1; }
    UPSTEST_DIR="$DIR" nohup caffeinate -i "$SELF" run >/dev/null 2>&1 &
    echo $! > "$PIDF"; disown
    sleep 2
    echo "Sonde lancée (pid $(cat "$PIDF")). Journal : $(cat "$CUR")" ;;
  mark)
    LOG="$(cat "$CUR")"; shift
    label="${1:-MARQUE}"; shift
    rec "$(now)" MARK "$label${*:+ $*}" "-"
    echo "Repère « $label${*:+ $*} » posé à $(date '+%H:%M:%S')." ;;
  status)
    LOG="$(cat "$CUR")"
    if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then echo "Sonde active (pid $(cat "$PIDF"))."; else echo "Sonde arrêtée."; fi
    echo "Journal : $LOG ($(wc -l < "$LOG") lignes)"; tail -3 "$LOG" ;;
  stop)
    if [ -f "$PIDF" ]; then
      pid=$(cat "$PIDF"); pkill -P "$pid" 2>/dev/null; kill "$pid" 2>/dev/null
      pkill -f "$SELF run" 2>/dev/null; rm -f "$PIDF"; echo "Sonde arrêtée."
    else echo "Pas de sonde en cours."; fi ;;
  *) echo "Usage : probe.sh {start|mark LABEL [texte]|status|stop}"; exit 2 ;;
esac
