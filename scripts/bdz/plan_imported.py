#!/usr/bin/env python3
"""Plan de classement de '_IMPORTED (à classer)'. Usage: plan_imported.py imp.tsv imp-md5.txt plan.csv
Chaque entrée de premier niveau -> dossier de série cible (contenu fusionné, jamais écrasé). Doublons internes (hash) -> _Quarantaine."""
import sys, csv, collections, unicodedata
SRC = '_IMPORTED (à classer)/'
M = {  # entrée -> dossier cible (relatif à BDZ)
 "1629... ou l'effrayante histoire des naufragés du Jakarta T01.cbz": "1629 ou l'effrayante histoire des naufragés du Jakarta",
 '7 secondes': '7 secondes', 'BD- La Colere de Fantomas L Integrale CBZ': 'Fantomas',
 'Barracuda - Integrale (2019)': 'Barracuda', 'BlackStone [HD]': 'BlackStone',
 "Capitaine Albator - Mémoires de l'Arcadia T01 .cbz": '_Mangas/Albator', 'ELFES.T23.cbr': 'Elfes',
 'Fab.The.wolf.am.us.1.cbr': '_Comics/Fables/Fables - The Wolf Among Us(2014-2015)', 'From Hell.cbz': '_Comics/From Hell',
 'Géopolitique - Histoire et Théories': 'Géopolitique - Histoire et Théories', 'HawkmoonBD.pdf': 'Hawkmoon', 'Hypericon.cbz': 'Hypericon',
 "L'or des Belges": "L'or des Belges", 'La Brigade Chimérique Ultime Renaissance (Lehman, de Caneva) [2022]': 'La Brigade Chimérique',
 'La Cathédrale des Abymes': 'La Cathédrale des Abymes', 'La malédiction de Rascar Capac.cbr': '_À trier',
 'La véritable Histoire du Moyen Âge - En 20 dates clés.pdf': 'La véritable Histoire du Moyen Âge',
 'Le Château des animaux - T01-03': 'Le Château des animaux',
 'Le Cimetière Des Innocents - T01 - Oriane et l\'Ordre des morts.pdf': 'Le Cimetière des Innocents',
 'Le Cimetière des Innocents (01-03)': 'Le Cimetière des Innocents', 'Le Jour où - BD Tome 1 à 6 (BéKa,Marko) [CBZ] FR': 'Le Jour où',
 "Le dernier Secret d'Hitler": "Le dernier Secret d'Hitler", 'Les 5 Terres - T01-09': 'Les 5 Terres',
 'Long John Silver - Intégrale (2019)': 'Long John Silver', 'Maus - L\'intégrale (Spiegelman) (Flammarion).cbr': 'Maus',
 'Nains-T14.pdf': 'Nains', 'Naufrageurs.cbz': 'Naufrageurs', 'Old_Man_Logan.cbr': '_Comics/Old Man Logan',
 'Paris Maléfices - Intégrale (01-03)': 'Paris Maléfices', 'Raven - Tome 01 - 2020 - CBZ - [PRiNTER]': 'Raven',
 'Raven - Tome 02 - 2021 - CBZ - [PRiNTER]': 'Raven', 'Renaissance - BD Tome 1 à 4 (Duval,Emem) {CBR] FR': 'Renaissance',
 'Sept - BD Intégrale 21 Tomes (Collectif) [CBR] FR': 'Sept', 'Terra Prime - BD Tome 1 à 4 (Ogaki) [CBR & CBZ] FR': 'Terra Prime',
 'UNDERTAKER (Dargaud) - Les 5 TOMES parus - Bds - Fr - PDF': 'Undertaker', 'Undertaker - T06 - Salvaje.cbr': 'Undertaker',
 '__SAINT SEIYA': '_Mangas/Saint Seiya Deluxe', 'zzMes quatorze ans.cbr': 'Mes quatorze ans'}
N = lambda s: unicodedata.normalize('NFC', s)
M = {N(k): v for k, v in M.items()}
hs = collections.defaultdict(list)
for l in open(sys.argv[2], encoding='utf-8', errors='replace'):
    h, p = l.rstrip('\n').split('  ', 1); hs[h].append(N(p[2:]))
dup = {}
for v in hs.values():
    for p in sorted(v, key=lambda x: (len(x), x))[1:]: dup[p] = True
rows = []
for l in open(sys.argv[1], encoding='utf-8', errors='replace'):
    s, p = l.rstrip('\n').split('\t', 1); p = N(p[2:])
    if p.endswith('.DS_Store'): continue
    top = p.split('/')[0]; rest = p.split('/', 1)[1] if '/' in p else None
    if top not in M: rows.append([SRC + p, '', 'INCONNU']); continue
    name = rest if rest else top
    # aplatir : conserver la sous-arborescence interne, sauf pour fichier seul
    if top == '__SAINT SEIYA' and rest and rest.startswith('Saint Seiya Deluxe/'): rest = rest.split('/', 1)[1]
    new = M[top] + '/' + (rest if rest else top)
    if p in dup: rows.append([SRC + p, '_Quarantaine/' + SRC + p, 'QUARANTAINE'])
    else: rows.append([SRC + p, new, 'DEPLACER'])
csv.writer(open(sys.argv[3], 'w', newline='', encoding='utf-8')).writerows([['ancien', 'nouveau', 'action']] + rows)
print(collections.Counter(r[2] for r in rows))
