#!/usr/bin/env python3
"""Étape 1 (lecture seule) : inventaire de BOOKS + métadonnées EPUB.
Usage: scan_books.py /Volumes/DOWNLOADS/BOOKS sortie.json
Ne modifie rien sur le NAS. Lecture limitée (zip central dir + OPF)."""
import os, sys, json, zipfile, re, unicodedata, hashlib
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

root, out = sys.argv[1], sys.argv[2]
EB = {'.epub', '.epu'}
NS = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container',
      'o': 'http://www.idpf.org/2007/opf', 'd': 'http://purl.org/dc/elements/1.1/'}

def epub_meta(p):
    try:
        with zipfile.ZipFile(p) as z:
            c = ET.fromstring(z.read('META-INF/container.xml'))
            rf = c.find('.//c:rootfile', NS).get('full-path')
            o = ET.fromstring(z.read(rf))
        g = lambda t: [e.text.strip() for e in o.findall('.//d:' + t, NS) if e.text and e.text.strip()]
        m = {'title': (g('title') or [None])[0], 'authors': g('creator'), 'lang': (g('language') or [None])[0]}
        for e in o.findall('.//o:meta', NS):
            n = e.get('name')
            if n == 'calibre:series': m['series'] = e.get('content')
            if n == 'calibre:series_index': m['idx'] = e.get('content')
        return m
    except Exception as e:
        return {'err': type(e).__name__}

def partial_hash(p, size):
    h = hashlib.sha1(); h.update(str(size).encode())
    with open(p, 'rb') as f:
        h.update(f.read(1 << 20))
        if size > 2 << 20:
            f.seek(-(1 << 20), 2); h.update(f.read())
    return h.hexdigest()

files = []
for r, d, fs in os.walk(root):
    for n in fs:
        p = os.path.join(r, n)
        try: files.append((os.path.relpath(p, root), os.path.getsize(p)))
        except OSError: pass

def work(item):
    rel, size = item
    p = os.path.join(root, rel)
    ext = os.path.splitext(rel)[1].lower()
    d = {'path': unicodedata.normalize('NFC', rel), 'size': size, 'ext': ext}
    if ext in EB and size > 0: d['meta'] = epub_meta(p)
    return d

with ThreadPoolExecutor(4) as ex: res = list(ex.map(work, files))

# empreinte partielle uniquement pour les fichiers livre de même taille
from collections import defaultdict
BK = EB | {'.pdf', '.mobi', '.mob', '.azw3', '.cbz', '.doc', '.rtf', '.chm'}
bysz = defaultdict(list)
for d in res:
    if d['ext'] in BK and d['size'] > 0: bysz[d['size']].append(d)
for sz, L in bysz.items():
    if len(L) > 1:
        for d in L:
            try: d['ph'] = partial_hash(os.path.join(root, unicodedata.normalize('NFD', d['path'])), sz)
            except Exception:
                try: d['ph'] = partial_hash(os.path.join(root, d['path']), sz)
                except Exception: pass
json.dump(res, open(out, 'w'), ensure_ascii=False)
print(len(res), 'fichiers')
