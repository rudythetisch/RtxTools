#!/usr/bin/env python3
"""Étape 1 (lecture seule) : inventaire de AUDIO BOOKS (par dossier de livre) + tags ID3.
Usage (sur le NAS, python3 stdlib seulement) : scan_audiobooks.py "/volume1/DOWNLOADS/AUDIO BOOKS" sortie.json
Ne modifie rien. Lit les tags ID3v2/ID3v1 du premier fichier audio de chaque dossier."""
import os, sys, json, struct, unicodedata, collections

root, out = sys.argv[1], sys.argv[2]
AUDIO = {'.mp3', '.m4b', '.m4a', '.flac', '.ogg', '.wma', '.aac', '.wav'}
SKIP_DIRS = {'@eaDir', '#recycle'}

def dec(b):
    if not b: return ''
    enc = {0: 'latin-1', 1: 'utf-16', 2: 'utf-16-be', 3: 'utf-8'}.get(b[0], 'latin-1')
    try: return b[1:].decode(enc, 'replace').strip('\x00 ').replace('\x00', ' ')
    except Exception: return ''

def id3(p):
    t = {}
    try:
        with open(p, 'rb') as f:
            h = f.read(10)
            if h[:3] == b'ID3':
                ver = h[3]
                size = (h[6] << 21) | (h[7] << 14) | (h[8] << 7) | h[9]
                data = f.read(min(size, 1 << 20)); i = 0
                while i + 10 <= len(data):
                    fid = data[i:i + 4].decode('latin-1')
                    if not fid.strip('\x00'): break
                    if ver == 4: n = (data[i+4] << 21) | (data[i+5] << 14) | (data[i+6] << 7) | data[i+7]
                    else: n = struct.unpack('>I', data[i+4:i+8])[0]
                    body = data[i + 10:i + 10 + n]; i += 10 + n
                    k = {'TPE1': 'artist', 'TPE2': 'album_artist', 'TALB': 'album', 'TIT2': 'title',
                         'TRCK': 'track', 'TCON': 'genre', 'TYER': 'year', 'TDRC': 'year'}.get(fid)
                    if k and k not in t: t[k] = dec(body)
            if not t:
                f.seek(-128, 2); b = f.read(128)
                if b[:3] == b'TAG':
                    g = lambda x: x.split(b'\x00')[0].decode('latin-1', 'replace').strip()
                    t = {'title': g(b[3:33]), 'artist': g(b[33:63]), 'album': g(b[63:93])}
    except Exception as e:
        t['err'] = type(e).__name__
    return {k: v for k, v in t.items() if v}

res = []
for r, ds, fs in os.walk(root):
    ds[:] = [d for d in ds if d not in SKIP_DIRS]
    rel = os.path.relpath(r, root)
    fs = sorted(fs)
    if rel == '.': # fichiers à la racine
        for n in fs:
            p = os.path.join(r, n)
            res.append({'dir': '', 'name': n, 'kind': 'rootfile', 'size': os.path.getsize(p)});
        continue
    exts = collections.Counter(os.path.splitext(n)[1].lower() for n in fs)
    au = [n for n in fs if os.path.splitext(n)[1].lower() in AUDIO]
    d = {'dir': unicodedata.normalize('NFC', rel), 'bad': any(0xDC80 <= ord(c) <= 0xDCFF for c in rel), 'kind': 'dir', 'nfiles': len(fs), 'naudio': len(au),
         'exts': dict(exts), 'subdirs': len(ds),
         'size': sum(os.path.getsize(os.path.join(r, n)) for n in fs if os.path.exists(os.path.join(r, n))),
         'first': au[:2], 'tags': id3(os.path.join(r, au[0])) if au and au[0].lower().endswith('.mp3') else {},
         'others': [n for n in fs if n not in au][:8]}
    # empreinte pour doublons (taille+nb fichiers) ; hash complet fait plus tard si besoin
    d['sig'] = f"{d['size']}:{d['naudio']}"
    res.append(d)
json.dump(res, open(out, 'w'), ensure_ascii=True)  # ASCII : les noms corrompus (surrogates) restent représentables
print(len(res), 'entrées')
