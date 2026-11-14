#!/usr/bin/env python3
"""BDZ — plan dry-run niveau dossiers de série (lecture seule).
Usage: plan_bdz.py files.tsv plan.csv   (files.tsv = 'taille<TAB>./chemin' produit par find sur le NAS)
Colonnes: ancien, nouveau, nb_fichiers, section, action (DEPLACER | FUSION | INCHANGE).
FUSION = plusieurs dossiers vers le même nouveau chemin (fusion sans écrasement à l'exécution)."""
import sys, csv, re, unicodedata, collections
ENF, MAN, COM = '_BD de mon enfance', '_Mangas', '_Comics'
def fold(s):
    s = unicodedata.normalize('NFD', s.lower()); return ''.join(c for c in s if not unicodedata.combining(c))
KW = {ENF: ['tintin', 'natacha', 'quick et flupke', 'gastoon', 'tif et tondu', 'bob morane', 'ric hochet', 'yoko tsuno',
            'rahan', 'tuniques bleues', 'blueberry', 'barbe rouge', 'barbe-rouge', 'valerian', 'papyrus', 'scrameustache',
            'timoleon', 'kid paddle', 'titeuf', 'robin dubois', 'fred et bob', 'mortadel', 'brunelle et colin', 'alix senator',
            'grands classiques', 'joe bar team', 'gendarmes', 'pompiers', 'fuzz et fizzbi', 'captain biceps',
            'leo loden', 'cotton kid', 'lieutenant mac fly', 'peter pan', 'petit prince', 'adele blanc-sec', 'canardo',
            'quete de l\'oiseau du temps', 'astro', 'spirou', 'gaston', 'lucky luke', 'asterix'],
      MAN: ['mangas', 'claymore', 'attack on titan', 'attaque des titans', 'one piece', 'ken le survivant',
            'chevaliers du zodique', 'albator', 'goldorak'],
      COM: ['star wars', 'walking dead', 'fables', 'watchmen', 'we3', 'prophet', 'slaine', 'tony stark', 'walk of the dead']}
def section(t):
    f = fold(re.sub(r'^_+', '', t))
    for sec in (MAN, COM, ENF):
        if any(k in f for k in KW[sec]): return sec
    return ''
def clean(n):
    n = re.sub(r'^_+', '', n)
    n = re.sub(r'\s*\[(HD|V\d[^\]]*)\]', '', n)
    n = re.sub(r'\s*\((\d+-\d+|\d+)\)\s*$', '', n)
    n = re.sub(r'\s*\[?Integral\]?\s*$', '', n, flags=re.I)
    return re.sub(r'\s+', ' ', n).strip()
SPECIAL = {'_A trier': '_À trier', '____IMPORTED': '_IMPORTED (à classer)'}
cnt = collections.Counter()
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    s, p = l.rstrip('\n').split('\t', 1); p = unicodedata.normalize('NFC', p[2:])
    if '/' in p: cnt[p.split('/')[0]] += 1
rows = []
for t in sorted(cnt):
    if t in SPECIAL: new, sec = SPECIAL[t], ''
    else: new, sec = clean(t), section(t)
    rows.append([t, (sec + '/' if sec else '') + new, cnt[t], sec])
tg = collections.Counter(r[1].lower() for r in rows)
with open(sys.argv[2], 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['ancien', 'nouveau', 'nb_fichiers', 'section', 'action'])
    for r in rows:
        a = 'FUSION' if tg[r[1].lower()] > 1 else ('INCHANGE' if r[0] == r[1] else 'DEPLACER')
        w.writerow(r + [a])
