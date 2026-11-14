#!/usr/bin/env python3
"""Étape 1 (lecture seule) : plan dry-run de AUDIO BOOKS -> CSV (source,destination,action,raison).
Usage: plan_audiobooks.py inv.json plan.csv   (inv.json = scan_audiobooks.py ; aucun accès NAS)
Unité = dossier de livre (déplacé en bloc, sous-dossiers CD1/Partie inclus). Schéma :
  Auteur/Série/NN - Titre   |   Auteur/Titre   |   _Collections/<thème>/Titre
Table de correspondance explicite (106 dossiers, revue à la main) : plus fiable que des regex."""
import sys, json, csv, collections
inv, out = sys.argv[1:3]
D = json.load(open(inv))
JK, HP, LT = 'J.K. Rowling', 'Harry Potter', 'H.P. Lovecraft'
M = {  # source -> (destination relative, raison/remarque)
 'Albert Camus - La Peste': ('Albert Camus/La Peste', ''),
 'Bernard Werber - L\'ultime Secret': ('Bernard Werber/L\'Ultime Secret', ''),
 'Brigitte Aubert - La Mort Des Bois': ('Brigitte Aubert/La Mort des bois', ''),
 'Brigitte Aubert - La morsure des ténébres': ('Brigitte Aubert/La Morsure des ténèbres', 'faute corrigée (ténébres)'),
 '[ECOUTÉ] Brigitte Aubert - Ténèbres sur Jacksonville': ('Brigitte Aubert/Ténèbres sur Jacksonville', 'préfixe [ECOUTÉ] retiré -> statut noté dans ecoutes.csv'),
 'Franck Thilliez - Le syndrome E': ('Franck Thilliez/Le Syndrome E', ''),
 'Franck Thilliez - Puzzle': ('Franck Thilliez/Puzzle', 'sous-dossiers Partie 1/2 conservés'),
 'H.P. Lovecraft - L\'affaire Charles Dexter Ward (1927)': (f'{LT}/L\'Affaire Charles Dexter Ward', 'année retirée'),
 'H.P. Lovecraft - L\'appel de Cthulhu': (f'{LT}/L\'Appel de Cthulhu', ''),
 'H.P. Lovecraft - Le Sceau de Rlyeh': (f'{LT}/Le Sceau de Rlyeh', 'AMBIGU : existe aussi dans 11 nouvelles (taille différente 76M/143M)'),
 'H.P. Lovecraft - Le cauchemar d\'Innsmouth': (f'{LT}/Le Cauchemar d\'Innsmouth', ''),
 'H.P. Lovecraft - Le monstre sur le seuil': (f'{LT}/Le Monstre sur le seuil', 'AMBIGU : existe aussi dans 11 nouvelles (64M/84M)'),
 'H.P. Lovecraft - Le retour d\'Hastur': (f'{LT}/Le Retour d\'Hastur', 'AMBIGU : existe aussi dans 11 nouvelles (77M/142M)'),
 'H.P. Lovecraft - Quelque chose en bois': (f'{LT}/Quelque chose en bois', 'AMBIGU : existe aussi dans 11 nouvelles (38M/17M)'),
 '[ECOUTÉ] H.P. Lovecraft - 2 Histoires': (f'{LT}/2 Histoires', 'statut écouté -> ecoutes.csv'),
 '[ECOUTÉ] H.P. Lovecraft - La maison dans la vallée': (f'{LT}/La Maison dans la vallée', 'AMBIGU : existe aussi dans 11 nouvelles (126M/237M)'),
 '[ECOUTÉ] H.P. Lovecraft - Les Montagnes Hallucinées': (f'{LT}/Les Montagnes hallucinées', 'statut écouté -> ecoutes.csv'),
 '[ECOUTÉ] H.P. Lovecraft - Les engoulevents de la colline': (f'{LT}/Les Engoulevents de la colline', 'AMBIGU : existe aussi dans 11 nouvelles (91M/172M)'),
 'Histoire de France pour les nuls': ('_Collections/Pour les Nuls/Histoire de France pour les nuls', 'collection thématique (comme BOOKS)'),
 'JRR Tolkien - Le Hobbit - sKa [mp3][312]': ('J.R.R. Tolkien/Le Hobbit', 'tag release (sKa) retiré'),
 'Jean Christophe Grange - La Foret Des Manes (2009)': ('Jean-Christophe Grangé/La Forêt des mânes', ''),
 'Jean-Christophe Grange - L empire des loups': ('Jean-Christophe Grangé/L\'Empire des loups', 'CD1/CD2 conservés'),
 'Jean-Louis Feitjane - Le Pas de Merlin': ('Jean-Louis Fetjaine/Le Pas de Merlin/01 - Le Pas de Merlin', 'AMBIGU : auteur "Feitjane" -> graphie officielle Fetjaine ; T1 déduit (pas de numéro)'),
 'Jean-Louis Feitjane - Le Pas De Merlin T2 - Broceliande': ('Jean-Louis Fetjaine/Le Pas de Merlin/02 - Brocéliande', 'auteur corrigé en Fetjaine'),
 'Ken Folett - Peur Blanche': ('Ken Follett/Peur blanche', 'faute corrigée (Folett)'),
 'Ken Follett - Code Zero': ('Ken Follett/Code Zéro', ''),
 'Ken Follett - Les piliers de la terre T3-Un monde sans fin': ('Ken Follett/Kingsbridge/02 - Un monde sans fin', 'AMBIGU : nom dit "Piliers de la terre T3" mais Un monde sans fin = tome 2 de Kingsbridge ; Piliers (T1) absent'),
 'La Captive De L\'hiver': ('Serge Brussolo/La Captive de l\'hiver', 'auteur lu dans les tags ID3'),
 'Livre audio - 21 histoires - Walt Disney - L\'histoire et les dialogues (MP3.128Kbps)': ('_Collections/Contes et histoires pour enfants/21 histoires Walt Disney', 'recueil'),
 'Livre audio - 34 contes classiques pour enfants (lus par Marlène Jobert, Mp3 en 192kbs)': ('_Collections/Contes et histoires pour enfants/34 contes classiques (Marlène Jobert)', 'recueil'),
 'Marc Levy - Le premier jour': ('Marc Levy/Les Enfants de la liberté/..', ''),  # corrigé plus bas
 'Marc Levy - Les enfants de la liberté': ('Marc Levy/Les Enfants de la liberté', ''),
 'Maxime Chattam - Le Sang Du Temps': ('Maxime Chattam/Le Sang du temps', ''),
 'Maxime Chattam-Le Sang Du Temps [128kbps]': ('_Quarantaine/Doublons/Maxime Chattam-Le Sang Du Temps [128kbps]', 'DOUBLON EXACT (44 mp3, md5 identiques) de "Maxime Chattam - Le Sang Du Temps"'),
 'Maxime Chattam - Les arcanes du chaos': ('Maxime Chattam/Les Arcanes du chaos', 'CD1/CD2 conservés'),
 'Maxime Chattam - T4 - Entropia - 2011': ('Maxime Chattam/Autre-Monde/04 - Entropia', 'T1-T3 absents (L\'Alliance des Trois, Malronce, Le Cœur de la Terre : dans la liste "écoutés")'),
 'Maxime Chattam - T5 - Oz - 2012': ('Maxime Chattam/Autre-Monde/05 - Oz', ''),
 'Maxime Gillio - Bienvenue a Dunkerque - L abattoir dans la dune': ('Maxime Gillio/Bienvenue à Dunkerque - L\'Abattoir dans la dune', ''),
 'Michael Byrnes - Le mystere de l arche sacree': ('Michael Byrnes/Le Mystère de l\'arche sacrée', ''),
 'Michael Connelly - Dans la ville en feu': ('Michael Connelly/Dans la ville en feu', ''),
 'Michael Connelly - Mariachi Plaza': ('Michael Connelly/Mariachi Plaza', ''),
 'N.V. Peale - Le pouvoir de la pensee positive': ('Norman Vincent Peale/Le Pouvoir de la pensée positive', 'auteur développé (tag ID3)'),
 'Patricia Cornwell - Les Mémoires Mortes': ('Patricia Cornwell/Les Mémoires mortes', ''),
 'Serge Brussolo - L armure de vengeance': ('Serge Brussolo/L\'Armure de vengeance', ''),
 'Serge Brussolo - Le chateau des poisons': ('Serge Brussolo/Le Château des poisons', ''),
 'Six contes de Grimm lus par Anny Duperey [mp3 128 Kbps]': ('Jacob et Wilhelm Grimm/Six contes de Grimm (lus par Anny Duperey)', 'CD1/CD2 conservés'),
 'Stephen King Sale gosse.par2': ('Stephen King/Sale gosse', 'AMBIGU : suffixe ".par2" parasite ; tags = narrateur (Julien Chatelet), auteur non confirmé'),
 'Stephen King - Bazaar [mp3-64K]': ('Stephen King/Bazaar', ''),
 'Sun Tzu - L\'art de la guerre': ('Sun Tzu/L\'Art de la guerre', ''),
 '[ECOUTÉ] Arnaldur Indridason - Hypothermie (2011)': ('Arnaldur Indridason/Hypothermie', 'année retirée ; statut écouté -> ecoutes.csv'),
 'Andrzej Sapkowski -  Le Sorceleur T1 - Le Dernier vœu': ('Andrzej Sapkowski/Le Sorceleur/01 - Le Dernier vœu', 'double espace dans le nom source'),
 'Rick Riordan - Le Voleur de foudre - Percy Jackson 1 [mp3]': ('Rick Riordan/Percy Jackson/01 - Le Voleur de foudre', ''),
}
M['Marc Levy - Le premier jour'] = ('Marc Levy/Le Premier jour', 'dossier "Les Enfants de la liberté" = livre distinct')
NARNIA = {  # ordre de lecture (numéro porté dans les noms sources)
 'C.S. Lewis - Le Neveu du Magicien - Narnia 1 [mp3-128]': '01 - Le Neveu du magicien',
 'C.S. Lewis - Le Lion, la Sorcière Blanche et l\'Armoire magique - Narnia 2 [mp3-128]': '02 - Le Lion, la Sorcière blanche et l\'Armoire magique',
 'C.S. Lewis - Le Monde de Narnia 3 - Le Cheval et son écuyer [mp3-64]': '03 - Le Cheval et son écuyer',
 'C.S. Lewis - Le Prince Caspian - Le Monde de Narnia 4 [mp3-64]': '04 - Le Prince Caspian',
 'C.S. Lewis - Le Monde de Narnia 5 - L\'Odyssée du Passeur d\'Aurore [mp3-64]': '05 - L\'Odyssée du Passeur d\'Aurore',
 'C.S. Lewis - Le Monde de Narnia 6 - Le Fauteuil d\'argent': '06 - Le Fauteuil d\'argent',
 'C.S. Lewis - Le Monde de Narnia 7 - La Dernière Bataille': '07 - La Dernière Bataille'}
for s, t in NARNIA.items(): M[s] = (f"C.S. Lewis/Le Monde de Narnia/{t}", 'numérotation de lecture (Narnia N) ; tag qualité retiré')
# conteneurs : on déplace les enfants, le conteneur vide est laissé (supprimé seulement à l'exécution si vide)
HPR = 'J.K. Rowling - Harry Potter - Intégrale - 7 Tomes [mp3 64kbps]/'
HPT = {'T1': "01 - À l'école des sorciers", 'T2': '02 - La Chambre des secrets', 'T3': "03 - Le Prisonnier d'Azkaban", 'T4': '04 - La Coupe de feu',
       'T5': "05 - L'Ordre du Phénix", 'T6': '06 - Le Prince de sang-mêlé', 'T7': '07 - Les Reliques de la Mort'}
LOT = {'01': '01 - La Communauté de l\'Anneau', '02': '02 - Les Deux Tours', '03': '03 - Le Retour du Roi'}
WOT = {  # numéro, titre
 '1': "01 - L'Œil du monde", '2': '02 - La Grande Quête', '3': '03 - Le Dragon réincarné', '4': '04 - Un lever de ténèbres', '5': '05 - Les Feux du ciel',
 '6': '06 - Le Seigneur du chaos', '7': "07 - Une couronne d'épées", '8': '08 - Le Chemin des dagues', '9': "09 - Le Cœur de l'hiver", '10': '10 - Le Carrefour du crépuscule'}
import re
ACH = '_Agatha Christie (complet)/'
def child(d):
    dr = d['dir']; p = dr.split('/')
    if dr.startswith(HPR) and len(p) == 2: return f"{JK}/{HP}/{HPT[p[1][:2]]}", 'T-n -> NN ; tag qualité retiré'
    if dr.startswith('JRR Tolkien Le Seigneur') and len(p) == 2:
        n = re.search(r'Anneaux (\d\d)', p[1]).group(1); return f"J.R.R. Tolkien/Le Seigneur des anneaux/{LOT[n]}", 'version conteur féminin (nom du parent perdu -> à garder dans ecoutes/notes ?)'
    if dr.startswith('Jordan - La roue du temps/') and len(p) == 2:
        m = re.search(r'(?:[Tt]emps|T)\s*(\d+)(?:\s*\[|\s*$)', p[1]) or re.search(r'[Tt]emps (\d+)', p[1])
        return f"Robert Jordan/La Roue du temps/{WOT[m.group(1)]}", 'numéro extrait du nom source ; tag qualité retiré'
    if dr.startswith('H.P. Lovecraft - 11 nouvelles/') and len(p) == 2:
        return f"{LT}/11 nouvelles/{p[1].replace(' (adaptation radiophonique)', '')}", 'recueil conservé tel quel (chevauche des titres isolés)'
    if dr.startswith(ACH + 'Hercule Poirot/') and len(p) == 3:
        return f"Agatha Christie/Hercule Poirot/{p[2][:2]} - {p[2][3:]}", 'séparateur " - " ajouté'
    if dr == ACH + 'Hercule Poirot': return None
    if dr == ACH + 'Miss Marple': return 'Agatha Christie/Miss Marple', 'AMBIGU : 12 fichiers, album "Audio Thélème" -> titre inconnu'
    if dr.startswith(ACH + 'Autres  romans/') and len(p) == 3:
        n = p[2].replace('[ECOUTÉ] ', '')
        return f"Agatha Christie/{n[3:]}", ('hors série (n° 01/02/03 = ordre du dossier, pas une série) ; ' + ('statut écouté -> ecoutes.csv' if 'ECOUTÉ' in p[2] else '')).rstrip('; ')
    if dr.startswith(ACH + 'Agatha Christie - Cinq petits'): return 'Agatha Christie/Hercule Poirot/Cinq petits cochons', 'série Poirot déduite (roman de Poirot) ; AMBIGU : n° tome non fourni'
    if dr.startswith(ACH + 'Agatha Christie - Meurtre en Mes'): return 'Agatha Christie/Hercule Poirot/Meurtre en Mésopotamie (lu par Guillaume Gallienne)', 'AMBIGU : doublon probable de "05 - Meurtre en Mésopotamie" (autre lecteur, 407M vs 203M) -> garder les deux'
    return None
rows = []; used = set()
for d in D:
    if d['kind'] == 'rootfile':
        act = 'GARDER' if d['name'].endswith('.txt') else 'IGNORER'
        rows.append((d['name'], d['name'], act, 'liste des livres écoutés (Latin-1) : à convertir en UTF-8 / ecoutes.csv' if act == 'GARDER' else 'fichier macOS')); continue
    dr = d['dir']
    if dr.count('/') == 0 and dr in M:
        dst, why = M[dr]; used.add(dr)
        act = 'QUARANTAINE' if dst.startswith('_Quarantaine') else 'DEPLACER'
        rows.append((dr, dst, act, why)); continue
    # enfants de conteneurs
    top = dr.split('/')[0]
    if top in M or d['naudio'] == 0 and d['nfiles'] and not d['subdirs'] and dr.count('/') == 0:
        pass
    if dr.count('/') == 0 and top not in M and d['naudio'] == 0 and d['subdirs'] == 0:
        rows.append((dr, '', 'HORS_PERIMETRE', 'archive RAR + nzb non extraits (aucun mp3) : à extraire ou supprimer après accord')); continue
    r = child(d)
    if r: rows.append((dr, r[0], 'DEPLACER', r[1]))
# dossiers de premier niveau MIS en bloc : ne pas dupliquer les sous-dossiers
whole = {s for s in M}
rows = [r for r in rows if not (r[0].count('/') >= 1 and r[0].split('/')[0] in whole)]
# conteneurs (HP, Jordan, LOTR, 11 nouvelles, Agatha): lignes par enfant, ok. Contrôle destinations uniques
c = collections.Counter(r[1] for r in rows if r[1]); dup = [k for k, v in c.items() if v > 1]
assert not dup, dup
# LIVRES ECOUTES : nom des dossiers déplacés ailleurs que dans le plan
with open(out, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['source', 'destination', 'action', 'raison']); w.writerows(rows)
print(collections.Counter(r[2] for r in rows), len(rows))
# vérification de couverture : tout dossier avec audio doit être couvert (lui-même ou parent déplacé)
src = {r[0] for r in rows}
miss = [d['dir'] for d in D if d['kind'] == 'dir' and d['naudio'] and not any(d['dir'] == s or d['dir'].startswith(s + '/') for s in src)]
print('non couverts:', miss)
