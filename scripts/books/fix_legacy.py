#!/usr/bin/env python3
"""Tourne SUR le NAS (python3 Synology). Range les livres aux noms corrompus (octets cp850/tronqués)
de _Fantasy-BITLIT et _S.F. ebooks. Usage: fix_legacy.py BOOKS_DIR [--apply]  (journal: BOOKS/_Quarantaine/journal-legacy.csv)"""
import os, sys, re, zipfile, unicodedata, csv
import xml.etree.ElementTree as ET
root = sys.argv[1].encode(); apply = '--apply' in sys.argv
NS = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container', 'o': 'http://www.idpf.org/2007/opf', 'd': 'http://purl.org/dc/elements/1.1/'}
def dec(b):
    try: return b.decode('utf-8')
    except UnicodeDecodeError: return b.decode('cp850')
def nk(s): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower())
def safe(s): return re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', unicodedata.normalize('NFC', s))).strip(' .')[:140] or '_'
def swap(a):
    a = re.split(r'\s+-\s+', a.strip())[0]; a = re.sub(r'\s*\(.*?\)', '', a)
    if ',' in a:
        p = [x.strip() for x in a.split(',') if x.strip()]
        if len(p) == 2: a = p[1] + ' ' + p[0]
    return re.sub(r'\s+', ' ', a).strip()
def meta(p):
    try:
        with zipfile.ZipFile(p) as z:
            rf = ET.fromstring(z.read('META-INF/container.xml')).find('.//c:rootfile', NS).get('full-path')
            o = ET.fromstring(z.read(rf))
        g = lambda t: [e.text.strip() for e in o.findall('.//d:' + t, NS) if e.text and e.text.strip()]
        m = {'t': (g('title') or [None])[0], 'a': (g('creator') or [None])[0]}
        for e in o.findall('.//o:meta', NS):
            if e.get('name') == 'calibre:series': m['s'] = e.get('content')
            if e.get('name') == 'calibre:series_index': m['i'] = e.get('content')
        return m
    except Exception: return None
authors = {nk(dec(d)): dec(d) for d in os.listdir(root) if not d.startswith(b'_') and os.path.isdir(os.path.join(root, d))}
jr = []; used = set()
for top in (b'_Fantasy-BITLIT', b'_S.F. ebooks'):
    for r, ds, fs in os.walk(os.path.join(root, top)):
        ds[:] = [d for d in ds if d != b'@eaDir']
        for f in fs:
            p = os.path.join(r, f); name = dec(f)
            if f in (b'.DS_Store', b'mimetype') or b'@eaDir' in p: continue
            if f.lower().endswith(b'.thmx'): continue
            head = open(p, 'rb').read(5)
            ext = '.pdf' if head.startswith(b'%PDF') else '.epub' if head.startswith(b'PK') else None
            if not ext: continue
            m = meta(p) if ext == '.epub' else None
            if ext == '.epub' and not m and f.lower().endswith((b'.odt', b'.docx', b'.zip', b'.xlsx')): continue
            if m and m.get('a') and m.get('t'):
                a = swap(m['a']); a = authors.get(nk(a), a); t = m['t'].lstrip('- ')
                folder = safe(a); fn = safe(t)
                if m.get('s') and m.get('i'):
                    try: i = float(m['i']); fn = safe(f'{int(i):02d} - {t}'); folder += '/' + safe(m['s'])
                    except ValueError: pass
            else:
                if re.match(r'^[A-Z0-9_]{1,8}~\d\.', name): continue   # nom 8.3 sans métadonnées : on ne devine pas
                base = os.path.splitext(name)[0]
                mm = re.match(r'^(.{3,40}?)\s+-\s+(.+)$', base)
                if mm: a = swap(mm.group(1)); a = authors.get(nk(a), a); folder = safe(a); fn = safe(mm.group(2))
                else: folder = '_À trier'; fn = safe(base)
            dest = f'{folder}/{fn}{ext}'; n = 2
            while dest.lower() in used or os.path.lexists(os.path.join(root, dest.encode())):
                dest = f'{folder}/{fn} ({n}){ext}'; n += 1
            used.add(dest.lower()); jr.append((os.path.relpath(p, root), dest))
for a, b in jr: print(dec(a), '->', b)
if apply:
    w = csv.writer(open(os.path.join(root, b'_Quarantaine/journal-legacy.csv'), 'w', newline='', encoding='utf-8', errors='surrogateescape'))
    w.writerow(['ancien', 'nouveau', 'statut'])
    for a, b in jr:
        d = os.path.join(root, b.encode()); os.makedirs(os.path.dirname(d), exist_ok=True)
        os.rename(os.path.join(root, a), d); w.writerow([a.decode('utf-8', 'surrogateescape'), b, 'OK'])
    print(len(jr), 'déplacés')
