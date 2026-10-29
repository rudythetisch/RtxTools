#!/bin/bash
# report.sh — analyse le journal de probe.sh : temps d'arrêt et de remise en service par appareil.
#
# Usage : ./report.sh JOURNAL.tsv [T0_epoch] [RALLUMAGE_epoch]
#   T0 et RALLUMAGE sont lus dans les repères posés avec `probe.sh mark T0` / `mark RALLUMAGE`
#   (les arguments les remplacent si fournis).
#
# Définitions (par cible et par test, « perte » / « retour » = 3 résultats identiques d'affilée) :
#   arrêt          = première perte après T0, moins T0
#   retour         = premier retour après la perte, moins T0
#   indisponibilité= retour - perte
#   /rallumage     = retour moins RALLUMAGE (si le repère existe)  → temps de remise en service

[ $# -ge 1 ] || { echo "Usage : $0 JOURNAL.tsv [T0_epoch] [RALLUMAGE_epoch]"; exit 2; }

python3 -I - "$@" <<'PY'
import sys, collections

log = sys.argv[1]
arg_t0 = int(sys.argv[2]) if len(sys.argv) > 2 else None
arg_ra = int(sys.argv[3]) if len(sys.argv) > 3 else None

series = collections.defaultdict(list)
marks = []
for line in open(log, encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) != 4:
        continue
    try:
        t = int(p[0])
    except ValueError:
        continue
    if p[1] == "MARK":
        marks.append((t, p[2]))
    else:
        series[(p[1], p[2])].append((t, p[3]))

def mark_time(key):
    for t, label in marks:
        if label.split()[0] == key:
            return t
    return None

t0 = arg_t0 or mark_time("T0")
ra = arg_ra or mark_time("RALLUMAGE")
if t0 is None:
    sys.exit("Pas de repère T0 dans le journal (probe.sh mark T0) et pas d'argument.")

def first_run(seq, state, start, n=3):
    run, first = 0, None
    for t, s in sorted(seq):
        if t < start:
            continue
        if s == state:
            run += 1
            if run == 1:
                first = t
            if run >= n:
                return first
        else:
            run, first = 0, None
    return None

def mmss(s):
    if s is None:
        return "—"
    sign = "-" if s < 0 else ""
    s = abs(int(s))
    return f"{sign}{s // 60}:{s % 60:02d}"

rows = []
for (name, test), seq in series.items():
    down = first_run(seq, "ko", t0)
    up = first_run(seq, "ok", down) if down is not None else None
    rows.append((name, test, down, up))

rows.sort(key=lambda r: (r[2] is None, r[2] or 0, r[0], r[1]))

print(f"T0 (déclenchement) : repère {mmss(0)}  |  RALLUMAGE : "
      + ("non posé" if ra is None else f"+{mmss(ra - t0)} après T0"))
print()
hdr = f"{'cible':<18}{'test':<9}{'arrêt':>8}{'indispo':>9}{'retour':>8}{'/rallumage':>12}"
print(hdr)
print("-" * len(hdr))
for name, test, down, up in rows:
    if down is None:
        print(f"{name:<18}{test:<9}{'jamais tombé':>37}")
        continue
    d = down - t0
    if up is None:
        print(f"{name:<18}{test:<9}{mmss(d):>8}{'—':>9}{'NON REVENU':>20}")
        continue
    since_ra = mmss(up - ra) if ra is not None else "—"
    print(f"{name:<18}{test:<9}{mmss(d):>8}{mmss(up - down):>9}{mmss(up - t0):>8}{since_ra:>12}")

# Chronologie
events = [(t, f"REPÈRE  {label}") for t, label in marks]
for name, test, down, up in rows:
    if down is not None:
        events.append((down, f"perte   {name} ({test})"))
    if up is not None:
        events.append((up, f"retour  {name} ({test})"))
events.sort()
print("\nChronologie (temps depuis T0, m:ss) :")
for t, label in events:
    print(f"  {mmss(t - t0):>7}  {label}")

backs = [u for _, _, d, u in rows if d is not None and u is not None]
nevers = [f"{n} ({t})" for n, t, d, u in rows if d is not None and u is None]
print()
if backs:
    last = max(backs)
    extra = f", {mmss(last - ra)} après le rallumage" if ra is not None else ""
    print(f"Dernier retour confirmé : +{mmss(last - t0)} après T0{extra}.")
if nevers:
    print("Jamais revenus : " + ", ".join(nevers))
PY
