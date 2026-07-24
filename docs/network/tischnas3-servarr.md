# TischNAS3 — Stack Docker Servarr

Doc de référence pour le stack Docker (Container Manager Synology) tournant sur TischNAS3 (`192.168.10.3`).

## Contexte

RAM du NAS très limitée : **3.8 Gi total**, pas d'extension possible (slot fixe). Toute optimisation doit passer par la réduction de charge des conteneurs, pas par du hardware.

## Conteneurs

| Nom | Rôle | Restart policy | RAM typique |
|-----|------|-----------------|-------------|
| radarr-rtx | Gestion films | unless-stopped | ~135 MB |
| sonarr-rtx | Gestion séries | unless-stopped | ~180-200 MB |
| readarr-rtx | Gestion livres | unless-stopped | ~160-620 MB (pic au démarrage/scan) |
| prowlarr-rtx | Agrégateur indexeurs | unless-stopped | ~140-175 MB |
| bazarr-rtx | Sous-titres | unless-stopped | ~25 MB |
| qbittorrent-rtx | Client torrent | unless-stopped | ~20 MB |
| flaresolverr-rtx | Bypass Cloudflare pour indexeurs | unless-stopped | ~4 MB |
| jellyfin | Serveur média/transcoding | **no** (arrêté volontairement) | — |
| jellyseerr | Requêtes médias (frontend Jellyfin) | **no** (arrêté volontairement) | — |
| influxdb.syno.bak | À vérifier — nom suggère backup/doublon oublié | — | ~65 MB |

Mounts clés : `/volume1/DOWNLOADS` (host) → `/downloads` (containers). Sous-dossiers : `MOVIES`, `KIDS-MOVIES`, `TVSHOWS`, `KIDS-TVSHOWS`, `_TORRENTCOMPLETE`, `_TORRENTINCOMPLETE`, `_TORRENTWATCH`, etc.

## Historique incident — juillet 2026

**Symptôme rapporté** : crashs récurrents des services Docker (Radarr/Sonarr notamment).

**Cause racine** : OOM killer du kernel, RAM insuffisante (3.8 Gi) saturée notamment par Jellyfin (transcoding vidéo, gros consommateur RAM). Confirmé via `/var/log/messages` :
```
Out of memory: Killed process XXXX (jellyfin) ...
```
Récurrent sur plusieurs dates (17, 22, 25, 29 mai 2026).

**Conteneurs impactés** (exit code 137 = SIGKILL, cohérent avec OOM) :
- `jellyfin`, `jellyseerr` — arrêtés volontairement (restart policy `no`), pas de remplacement RAM disponible
- `bazarr-rtx` — restart policy était passée à `no` (probablement suite à un crash), corrigée en `unless-stopped` et relancé
- `readarr-rtx` — resté down 7 semaines malgré `unless-stopped`, relancé manuellement

**Bugs applicatifs trouvés en marge de l'incident** (non liés à la RAM) :

1. **Radarr — root folder cassé** : root folder `/downloads/KIDS/` n'existait pas (le vrai dossier est `KIDS-MOVIES`). Corrigé :
   - Root folder recréé (`/downloads/KIDS-MOVIES`, via API `/api/v3/rootfolder`)
   - 5 films (Sonic 1/2/3, Lego Movie, Super Mario) avaient leur `path` individuel encore sur l'ancien chemin — corrigés via `PUT /api/v3/movie/{id}`
   - 3 collections (Sonic the Hedgehog, Lego Movie, Super Mario) avaient leur `rootFolderPath` sur l'ancien chemin — corrigées via `PUT /api/v3/collection/{id}`

2. **Prowlarr — 3 indexeurs morts** : `TheRARBG`, `NorTorrent`, `BitSearch` avaient leurs définitions supprimées du dépôt Cardigann upstream (RARBG a fermé en 2023). Supprimés via API (`DELETE /api/v1/indexer/{id}`), pas de définition disponible pour les recréer à l'identique. 9 indexeurs actifs restants (Pirate Bay, Torrent9, Nyaa.si, C411, BlueRoms, GamesTorrents, CrackingPatching, TorrentDownload, World-torrent).

3. **Sonarr — CPU à 37% en continu** : boucle infinie de tentatives d'import sur 5 fichiers `.scr`/`.exe` déguisés en épisodes (Euphoria S03E05-07, House of the Dragon S03E04/06) traînant dans `_TORRENTCOMPLETE` — pattern classique de faux torrent/malware. Fichiers supprimés du disque + retirés de la queue Sonarr avec blocklist (`DELETE /api/v3/queue/{id}?removeFromClient=true&blocklist=true`). CPU redescendu à ~5%.

**Fichiers supprimés** (confirmés malveillants/factices) :
```
_TORRENTCOMPLETE/Euphoria US S03E05 1080p AMZN WEB-DL DDP5 1 H 264-FLUX.scr
_TORRENTCOMPLETE/Euphoria US S03E06 1080p AMZN WEB-DL DDP5 1 H 264-FLUX.scr
_TORRENTCOMPLETE/Euphoria US S03E07 1080p AMZN WEB-DL DDP5 1 H 264-FLUX.scr
_TORRENTCOMPLETE/House of the Dragon S03E04 1080p HEVC x265-MeGusta.exe
_TORRENTCOMPLETE/House of the Dragon S03E06 1080p HEVC x265-MeGusta.scr
TVSHOWS/Brooklyn Nine-Nine/*/RARBG_DO_NOT_MIRROR.exe (×8, dummy RARBG, inoffensif mais nettoyé)
```
Conservés : les `.exe` sous `TRAINING/` (packages .NET de formation, cracks UML) — non liés à l'incident.

**Suivi post-fix (2026-07-25)** — revérification complète après relance :
- Tous les servarr up et stables (Radarr 128 MB, Sonarr 243 MB, Prowlarr 108 MB, Bazarr 56 MB, Readarr 97 MB — le pic de 620 MB était bien transitoire, lié au scan de bibliothèque après 7 semaines d'arrêt)
- 4. **Readarr — download client sur un domaine obsolète** : le client qBittorrent de Readarr pointait vers `qbittorrent.tischhome.duckdns.org` (ancien domaine DuckDNS), alors que Radarr/Sonarr utilisent `qbittorrent.tixhon.be` (domaine actuel) — d'où l'erreur `DownloadClientCheck: Unable to communicate with Qbittorrent (timeout)`. Corrigé via `PUT /api/v1/downloadclient/1?forceSave=true`, connexion testée OK.
- Les warnings "indexeurs indisponibles >6h" (TorrentDownload, World-torrent, C411, Torrent9) sur Radarr/Sonarr étaient du cache "long-term status" résiduel du nettoyage Prowlarr de la veille — tous répondent HTTP 200 au test direct, pas de panne réelle.

## Pistes d'optimisation RAM restantes (pas de upgrade hardware possible)

- Si Jellyfin doit être relancé un jour : fixer une limite mémoire dure (`docker update --memory=1g jellyfin`) pour éviter un nouvel OOM global qui tue les autres conteneurs.
- Vérifier `influxdb.syno.bak` — nom suggère un conteneur de backup/doublon oublié, RAM récupérable si inutile.
- `homebridge` (natif DSM, hors Docker, ~30 MB) — à garder seulement si utilisé.

## Accès

Voir [[nas-access]] (mémoire Claude) pour les identifiants SSH/sudo. API keys des services (`Radarr`, `Sonarr`, `Prowlarr`) : `docker exec <container> cat /config/config.xml | grep -i apikey`.
