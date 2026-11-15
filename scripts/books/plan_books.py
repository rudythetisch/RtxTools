#!/usr/bin/env python3
"""Étape 1 (lecture seule) : produit le plan de réorganisation de BOOKS en CSV.
Usage: plan_books.py inv.json plan.csv [stats.txt]
Schéma : <Auteur>/[<Série>/]<[NN - ]Titre>.<ext>
Aucun accès NAS ; seul inv.json (scan_books.py) est lu."""
import sys, json, re, os, csv, unicodedata, collections

inv, out = sys.argv[1], sys.argv[2]
D = json.load(open(inv))
BOOK = {'.epub', '.epu', '.pdf', '.mobi', '.mob', '.azw3', '.cbz', '.doc', '.rtf', '.chm', '.djvu'}
FIXEXT = {'.epu': '.epub', '.mob': '.mobi'}   # extensions DOS tronquées (8.3)
MEDIA = {'.mp3', '.m4b', '.mp4', '.cue', '.m4a', '.flac', '.mkv', '.avi', '.zip', '.thmx'}
# dossiers racine = collections thématiques (pas d'auteur unique) -> _Collections/<nom>/
COLL = [(r'nuls', 'Pour les Nuls'), (r'ldvelh|dont vous .tes le h.ro|d.fisfantastiques', 'Livres dont vous êtes le héros'),
        (r'^jdr', 'Jeux de rôle'), (r'magazines|^_revues', 'Revues'), (r'hacking|devops|agile|lightroom|trade|day trading|futures|manuels pratiques|r.parez', 'Informatique et pratique'),
        (r'larousse|cocktail|tiki', 'Cuisine et boissons'), (r'__third', 'Jeux de rôle')]
CAL = 'Calibre Library/'

def nk(s):  # clé de comparaison : sans accents/ponctuation/casse
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '', s)

def swap(a):
    a = a.strip()
    a = re.split(r'\s+-\s+', a)[0]            # "Robin Hobb - Assassin royal - 1"
    a = re.sub(r'\s*\(.*?\)', '', a)
    if ',' in a:
        p = [x.strip() for x in a.split(',') if x.strip()]
        if len(p) == 2 and len(p[0].split()) <= 3: a = f'{p[1]} {p[0]}'
    a = re.sub(r'\b([A-Z])\.\s*(?=[A-Z])', r'\1. ', a)
    return re.sub(r'\s+', ' ', a).strip()

def safe(s, n=140):
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', s).strip(' .')
    return s[:n].rstrip(' .') or '_'

JUNK = re.compile(r'[\.\s_-]*(french|fr|epub|pdf|mobi|ebook|nogrp|alexandriz|www\.[^ ]+)\b.*$', re.I)
def title_from_file(base, author):
    t = re.sub(r'\s*\[[^\]]*\]\s*', ' ', base)   # [Série-3]
    t = re.sub(r'\(\d{4}\)$', '', t.strip())
    t = t.replace('_', ' ')
    if author:
        a = re.escape(author)
        t = re.sub(rf'^\s*{a}\s*[-–]\s*', '', t, flags=re.I)
        t = re.sub(rf'\s*[-–]\s*{a}\s*$', '', t, flags=re.I)
    t = re.sub(r'^\s*[-–]\s*', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def collection_for(path):
    top = path.split('/')[0].lower()
    for rx, name in COLL:
        if re.search(rx, top): return name
    return None

# --- 1. auteurs : forme canonique = la plus fréquente par clé normalisée
cnt = collections.Counter(); forms = collections.defaultdict(collections.Counter)
for d in D:
    m = d.get('meta') or {}
    if m.get('authors'):
        a = swap(m['authors'][0]); d['_a'] = a
        forms[nk(a)][a] += 1
canon = {k: c.most_common(1)[0][0] for k, c in forms.items()}
# inversions "Prénom Nom" / "Nom Prénom" : même ensemble de mots
bysorted = collections.defaultdict(list)
for k, c in forms.items():
    toks = '|'.join(sorted(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKD', canon[k]).encode('ascii', 'ignore').decode().lower())))
    bysorted[toks].append(k)
for ks in bysorted.values():
    if len(ks) > 1:
        best = max(ks, key=lambda k: sum(forms[k].values()))
        for k in ks: canon[k] = canon[best]

rows = []
for d in D:
    p, ext, sz = d['path'], d['ext'], d['size']
    base = os.path.basename(p); stem = os.path.splitext(base)[0]
    r = {'ancien': p, 'taille': sz, 'action': '', 'nouveau': '', 'raison': '', 'auteur_source': '', 'ph': d.get('ph', '')}
    rows.append(r)
    if base in ('.DS_Store', 'Thumbs.db', 'desktop.ini') or sz == 0 or ext in ('.nfo', '.db', '.nzb', '.url', '.db', '.xml', '.opf', '.html', '.htm', '.jpg', '.png', '.txt', '.sfv', '.diz'):
        r.update(action='QUARANTAINE', nouveau='_Quarantaine/Annexes/' + p, raison='annexe/fichier parasite (jamais supprimé)'); continue
    if ext in MEDIA:
        r.update(action='HORS_PERIMETRE', raison='audio/vidéo/archive : à décider'); continue
    if ext not in BOOK:
        r.update(action='REVOIR', raison='extension inconnue'); continue
    ext2 = FIXEXT.get(ext, ext)
    m = d.get('meta') or {}
    coll = collection_for(p)
    parts = p.split('/')
    author = ''; src = ''
    if d.get('_a'): author = canon.get(nk(d['_a']), d['_a']); src = 'epub'
    else:
        mm = re.match(r'^\s*(?:Pour\.Les\.Nul\s*-\s*)?([^-–_\[\]]{3,40}?)\s+[-–]\s+\S', stem)
        tr = re.match(r'^(.+?)\s+-\s+([^-–,]{2,30},\s*[^-–,]{2,25})\s*$', stem)
        if tr: author = swap(tr.group(2)); src = 'nom'; stem = tr.group(1)
        elif mm and len(mm.group(1).split()) <= 4 and not re.search(r'\d', mm.group(1)): author = swap(mm.group(1)); src = 'nom'
        elif len(parts) > 1 and re.match(r"^[A-ZÉ][\w'’.-]+(\s[\w'’.-]+){1,3}$", parts[-2]) and not re.search(r'\d|Collection|Pack|nuls', parts[-2], re.I):
            author = swap(parts[-2]); src = 'dossier'
        if author: author = canon.get(nk(author), author)
    r['auteur_source'] = src
    if re.search(r'nuls', author or '', re.I): author = ''; coll = 'Pour les Nuls'
    title = m.get('title') or title_from_file(stem, author)
    title = re.sub(r'^\s*[-–]\s*', '', title)
    series = m.get('series'); idx = m.get('idx')
    if series and idx:
        try: i = float(idx); idx = f'{int(i):02d}' if i == int(i) else f'{i:04.1f}'
        except ValueError: idx = None
    if coll and (not author or coll in ('Pour les Nuls', 'Revues', 'Livres dont vous êtes le héros', 'Jeux de rôle', 'Informatique et pratique', 'Cuisine et boissons')):
        # collection thématique : on range par collection, nom = "Titre"
        folder = f'_Collections/{coll}'
        name = safe(title if m.get('title') else title_from_file(stem, author))
    elif author:
        folder = safe(author)
        if series and idx: folder += '/' + safe(series); name = safe(f'{idx} - {title}')
        else: name = safe(title)
    else:
        folder = '_À trier'; name = safe(title_from_file(stem, ''))
        r['raison'] = 'auteur introuvable'
    r.update(action='DEPLACER', nouveau=f'{folder}/{name}{ext2}', _series=series if idx else '')
    r['_key'] = (folder, name, ext2)

# --- 2. doublons exacts (même empreinte) et collisions de nom
by_ph = collections.defaultdict(list)
for r in rows:
    if r['ph']: by_ph[r['ph']].append(r)
def prio(r):  # quel exemplaire garder
    return (r['ancien'].startswith(CAL) is False, r['action'] != 'DEPLACER', r['ancien'].count('/') * -1, len(r['ancien']))
for g in by_ph.values():
    if len(g) > 1:
        g.sort(key=prio)
        for r in g[1:]:
            if r['action'] == 'DEPLACER':
                r.update(action='QUARANTAINE', nouveau='_Quarantaine/Doublons/' + r['ancien'], raison=f"doublon exact de : {g[0]['ancien']}")
seen = {}
for r in rows:
    if r['action'] != 'DEPLACER': continue
    k = r['nouveau'].lower()
    if k in seen:
        base, e = os.path.splitext(r['nouveau']); n = 2
        while f'{base} ({n}){e}'.lower() in seen: n += 1
        r['nouveau'] = f'{base} ({n}){e}'; r['raison'] = (r['raison'] + '; ' if r['raison'] else '') + f'collision avec {seen[k]} (contenu différent)'; k = r['nouveau'].lower()
    seen[k] = r['ancien']
# les doublons "ancien" Calibre déjà gardés occupent leur place : on ne les confond pas

for r in rows: r.pop('_key', None); r.pop('_series', None)
cols = ['action', 'ancien', 'nouveau', 'taille', 'auteur_source', 'raison']
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
c = collections.Counter(r['action'] for r in rows)
print(dict(c))
print('sources auteur', collections.Counter(r['auteur_source'] for r in rows if r['action'] == 'DEPLACER'))
