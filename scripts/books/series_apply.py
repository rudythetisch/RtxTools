#!/usr/bin/env python3
"""Range les livres d'un auteur dans des dossiers de série numérotés d'après un référentiel (JSON).
Usage: series_apply.py BOOKS_DIR référentiel.json [--apply]
référentiel: {"Auteur": {"Série": [[num, "Titre", ["alias",...]], ...]}}  (num: nombre ou null)"""
import os, re, sys, json, unicodedata, csv, collections
n = lambda s: unicodedata.normalize('NFC', s)
nk = lambda s: re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
B = sys.argv[1].rstrip('/') + '/'; ref = json.load(open(sys.argv[2])); apply = '--apply' in sys.argv
def mk(p):
    try: os.makedirs(p, exist_ok=True)
    except FileExistsError: pass
def sh(s): return re.sub(r'[\\/:*?"<>|]', '_', s)
def clean(st, author):
    s = re.sub(r'\(\d+\)\s*$', '', st)
    s = re.sub(r'^\d+(\.\d+)?\s*-\s*', '', s)
    s = re.sub(r'\b(French Edition|roman|Roman|Tome\s*\d+|T\d+)\b', ' ', s)
    s = re.sub(r'\([^)]*\)', ' ', s)
    s = re.sub(re.escape(author), ' ', s, flags=re.I)
    return nk(s)
plan = []; unmatched = []
for author, series in ref.items():
    base = None
    for lvl in ('Auteurs principaux', 'Autres auteurs'):
        if os.path.isdir(B + lvl):
            for d in os.listdir(B + lvl):
                if n(d) == author: base = B + lvl + '/' + d
    if not base: print('auteur absent', author); continue
    cand = []
    for s, items in series.items():
        for num, title, al in items:
            for t in [title] + al: cand.append((nk(t), s, num, title))
    cand.sort(key=lambda x: -len(x[0]))
    for r, ds, fs in os.walk(base):
        for f in fs:
            if f.startswith('.'): continue
            st, ext = os.path.splitext(f); c = clean(n(st), author); hit = None
            for k, s, num, title in cand:
                if c == k or (len(k) >= 6 and (c.startswith(k) or k in c)): hit = (s, num, title); break
            if not hit: unmatched.append(n(os.path.relpath(os.path.join(r, f), base))); continue
            s, num, title = hit
            if num is None: nm = f'{sh(title)}{ext.lower()}'
            else:
                fl = float(num); nm = (f'{int(fl):02d}' if fl == int(fl) else str(num)) + f' - {sh(title)}{ext.lower()}'
            plan.append((os.path.join(r, f), base + '/' + sh(s) + '/' + nm))
    print(author, len(plan), 'matchés;', len(unmatched), 'restants')
if apply:
    w = csv.writer(open(B + '_Quarantaine/journal-series-' + os.path.basename(sys.argv[2]) + '.csv', 'w', newline=''))
    w.writerow(['ancien', 'nouveau']); moved = 0
    for p, d in plan:
        if os.path.abspath(p) == os.path.abspath(d): continue
        d = unicodedata.normalize('NFD', d); mk(os.path.dirname(d)); k = 2; tgt = d
        while os.path.exists(tgt): b, x = os.path.splitext(d); tgt = f'{b} ({k}){x}'; k += 1
        os.rename(p, tgt); w.writerow([n(p), n(tgt)]); moved += 1
    for lvl in ('Auteurs principaux', 'Autres auteurs'):
        for r, ds, fs in os.walk(B + lvl, topdown=False):
            try: os.rmdir(r)
            except OSError: pass
    print(moved, 'déplacés')
else:
    for p, d in plan[:15]: print(os.path.relpath(p, B)[-60:], '->', os.path.relpath(d, B)[-60:])
print('NON TRAITÉS:', unmatched)
