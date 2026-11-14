#!/usr/bin/env python3
"""Exécute plan.csv (niveau dossiers) avec journal d'annulation CSV. Jamais de suppression, jamais d'écrasement.
Usage: apply_dirs.py ROOT plan.csv journal.csv   |   apply_dirs.py --undo ROOT journal.csv
FUSION: les enfants du dossier source sont déplacés dans la cible; en cas de collision, l'enfant reste (statut SKIP)."""
import sys, os, csv, unicodedata
def real(d, name):
    n = unicodedata.normalize('NFC', name)
    for e in os.listdir(d):
        if unicodedata.normalize('NFC', e) == n: return e
def mv(root, a, b, w):
    try:
        os.makedirs(os.path.dirname(os.path.join(root, b)), exist_ok=True)
        os.rename(os.path.join(root, a), os.path.join(root, b)); w.writerow([a, b, 'OK'])
    except OSError as e: w.writerow([a, b, 'ERR ' + str(e)])
if sys.argv[1] == '--undo':
    root, jr = sys.argv[2:4]
    for r in reversed(list(csv.DictReader(open(jr, encoding='utf-8')))):
        if r['statut'] != 'OK': continue
        s, d = os.path.join(root, r['nouveau']), os.path.join(root, r['ancien'])
        if os.path.exists(s) and not os.path.exists(d):
            os.makedirs(os.path.dirname(d), exist_ok=True); os.rename(s, d)
    sys.exit()
root, plan, jr = sys.argv[1:4]
rows = [r for r in csv.DictReader(open(plan, encoding='utf-8')) if r['action'] != 'INCHANGE']
with open(jr, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['ancien', 'nouveau', 'statut'])
    for r in rows:
        a = real(root, r['ancien'])
        if not a: w.writerow([r['ancien'], r['nouveau'], 'SKIP absent']); continue
        n = r['nouveau']
        if a == n: continue
        if os.path.lexists(os.path.join(root, n)) or r['action'] == 'FUSION' and os.path.isdir(os.path.join(root, n)):
            if not os.path.isdir(os.path.join(root, n)): w.writerow([a, n, 'SKIP existe']); continue
            for c in sorted(os.listdir(os.path.join(root, a))):
                dst = os.path.join(n, c)
                if os.path.lexists(os.path.join(root, dst)): w.writerow([os.path.join(a, c), dst, 'SKIP collision'])
                else: mv(root, os.path.join(a, c), dst, w)
            try: os.rmdir(os.path.join(root, a))  # uniquement si vide
            except OSError: pass
        else: mv(root, a, n, w)
    f.flush()
