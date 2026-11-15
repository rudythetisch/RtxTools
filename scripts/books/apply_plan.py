#!/usr/bin/env python3
"""Exécute plan.csv (DEPLACER/QUARANTAINE) avec journal d'annulation. Jamais de suppression.
Usage: apply_plan.py ROOT plan.csv journal.csv   |   apply_plan.py --undo ROOT journal.csv"""
import sys, os, csv, unicodedata
def real(root, rel):
    for f in ('NFC', 'NFD'):
        p = os.path.join(root, unicodedata.normalize(f, rel))
        if os.path.lexists(p): return p
    return None
if sys.argv[1] == '--undo':
    root, jr = sys.argv[2:4]
    for r in reversed(list(csv.DictReader(open(jr)))):
        if r['statut'] != 'OK': continue
        src, dst = os.path.join(root, r['nouveau']), os.path.join(root, r['ancien'])
        if os.path.exists(src) and not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst), exist_ok=True); os.rename(src, dst)
    sys.exit()
root, plan, jr = sys.argv[1:4]
rows = [r for r in csv.DictReader(open(plan)) if r['action'] in ('DEPLACER', 'QUARANTAINE') and r['nouveau']]
with open(jr, 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['ancien', 'nouveau', 'statut']); f.flush()
    ok = ko = 0
    for r in rows:
        src = real(root, r['ancien']); dst = os.path.join(root, r['nouveau'])
        if not src or os.path.lexists(dst): w.writerow([r['ancien'], r['nouveau'], 'SKIP']); ko += 1; continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True); os.rename(src, dst)
            w.writerow([r['ancien'], r['nouveau'], 'OK']); ok += 1
        except OSError as e:
            w.writerow([r['ancien'], r['nouveau'], 'ERR ' + str(e)]); ko += 1
        f.flush()
print(ok, 'déplacés,', ko, 'ignorés/erreurs')
