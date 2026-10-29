# Test d'arrêt / reprise du homelab — 2026-10-29

Test de l'arrêt d'urgence NUT (voir `scripts/guides/configure-nut-ups.md`), déclenché sur secteur via `touch /run/nut/fsd-request` à **13:51:16 (T0)**, UPS non débranché.

## ⚠️ Ce qui limite la valeur du test

- **Le courant de toute la maison a été coupé** pendant le test (pour un branchement électrique), **après** que l'UPS a coupé ses prises (13:56:05), puis rétabli avant ~13:57:30 (le Mac mini a redémarré à 13:57:54 : la coupure a donc duré moins que les « 2 minutes après » estimées de mémoire). La **phase d'arrêt est fiable** (terminée avant), mais la **reprise ne teste pas l'UPS** : modem, Decos et Mac mini ont redémarré à cause de la maison.
- **Établi** : l'UPS a bien coupé ses prises en fin d'arrêt, à 13:56:05, soit **60 s après l'extinction de NIPoGi** (13:55:05) et non 20 s comme `ups.delay.shutdown` le laissait penser.
- **Non établi** : si l'UPS aurait rallumé ses prises tout seul, secteur présent. La coupure de la maison est intervenue avant. À confirmer par un nouveau test sans coupure externe.
- **La sonde (`scripts/ups-test/probe.sh`) a été perdue** : le Mac mini a perdu le courant et son `/tmp` a été vidé au redémarrage (boot 13:57:54). Le Mac mini n'est donc pas protégé contre une coupure générale. Les mesures ci-dessous viennent des journaux des serveurs (`ups-shutdown.log`, tâches Proxmox, `uptime -s`) et des relevés manuels, pas de la sonde.

## Arrêt (fiable) — temps depuis T0 = 13:51:16

| Heure | T0+ | Événement |
|---|---|---|
| 13:51:16 | 0:00 | FSD pris en compte par `upsmon` (relais systemd OK) |
| 13:51:31 | 0:15 | Script d'arrêt lancé (`FINALDELAY` 15 s) |
| 13:51:33 | 0:17 | Commandes d'arrêt envoyées aux 2 NAS en parallèle (2 s, code 0) |
| ~13:51:3x | ~0:30? | NAS2 éteint (heure exacte non relevée) |
| 13:52:03 | 0:47 | Fin de l'attente fixe de 30 s |
| 13:53:04 | 1:48 | VM 100 Home Assistant arrêtée (**60 s : tout le timeout**) |
| 13:53:23 | 2:07 | VM 115 pfSense arrêtée → **Internet coupé** |
| 13:53:30 | 2:14 | NAS3 éteint (relevé au rack) |
| 13:53:33 | 2:17 | LXC 103 AdGuard arrêté → plus de DNS |
| 13:53:53 | 2:37 | LXC 108 RustDesk arrêté |
| 13:53:57 | 2:41 | LXC 109 cloudflared arrêté |
| 13:54:40 | 3:24 | Dernier LXC (117) arrêté, `shutdown -h now` |
| 13:55:03 | 3:47 | NIPoGi éteint (relevé au rack 13:55:05) |

Durée du script : **189 s** (VM 100 → 60 s, 16 LXC → 76 s, attente fixe → 30 s). Plus lents : LXC 113 Prometheus 15 s, LXC 117 Scanopy 14 s, LXC 105 NPM 7 s.

### Verdict par rapport au budget batterie
Autonomie annoncée par l'UPS : **165 s**. Avec le minuteur de 15 s, l'arrêt complet (T0 → NIPoGi éteint) prendrait **~245 s** en vrai : **trop long**. Le critère « ≤ ~130 s » n'est pas atteint.
- Les NAS seraient éteints à temps (NAS3 éteint à T0+2:14, soit ~2:29 avec le minuteur : limite).
- Home Assistant, pfSense et les LXC seraient coupés net par la batterie vide avant la fin.

## Reprise (partielle, contaminée par la coupure de la maison)

| Heure | Événement |
|---|---|
| ~13:57:30 | Courant de la maison rétabli (Mac mini en `kernel boot` 13:57:54, modem VOO et Decos redémarrent seuls) |
| ~13:58:00 | **NAS2, NAS3 et NIPoGi ne redémarrent pas seuls** : démarrage manuel au bouton (constat utilisateur) |
| 13:58:37 / 13:58:41 / 13:58:49 | Démarrage noyau : NAS3 / NIPoGi / NAS2 |
| 13:58:50 → 13:59:44 | `startall` Proxmox : 54 s, **séquentiel, sans ordre**. VM 100 HA à 13:58:51, **pfSense seulement à 13:59:33**, cloudflared à 13:59:15 |
| 13:59:23 → 13:59:33 | cloudflared : erreurs DNS (démarré avant pfSense et AdGuard) |
| 14:04:50 | **Tunnel Cloudflare enregistré** : Internet et DNS de retour, ~5 min après pfSense (probablement la resynchronisation du modem VOO ; les Decos ont aussi mis longtemps à retrouver Internet) |

Après reprise : NAS3 `[UUUU]`, NAS2 md3 toujours `[UU_]` (inchangé, pas pire), services du Mac mini revenus seuls malgré la coupure sèche (launchd : fmfcompta 8734, homeplan 8710, dashboard 8160, homefinance 8735).

## Constats et pistes

1. **Redémarrage automatique à activer** : BIOS de NIPoGi (« Restore on AC power loss » → Power On) et DSM sur les deux NAS (« Redémarrer automatiquement après une panne de courant »). Sans ça, après une vraie coupure avec rallumage des prises de l'UPS, tout reste éteint jusqu'à l'intervention manuelle. **Priorité.**
2. **Raccourcir l'arrêt** : supprimer l'attente fixe de 30 s (les NAS reçoivent leur ordre en 2 s) et arrêter VM/LXC **en parallèle** au lieu d'un par un. Le goulot restera Home Assistant (jusqu'à 60 s). Estimation : ~70 s au lieu de 189 s, soit ~100 s depuis le déclenchement, sous les 165 s de batterie.
3. **Ordre de démarrage Proxmox** : `startup: order=1` pour pfSense (VM 115), `order=2` pour AdGuard (LXC 103). Gain estimé ~40 s sur le retour d'Internet et fin des erreurs DNS de cloudflared.
4. **Home Assistant (VM 100)** met 60 s à s'arrêter (tout le timeout) : à examiner (agent invité, add-ons).
5. **Mac mini hors protection** contre une coupure générale : l'UPS actuel (550 VA) est déjà sous-dimensionné ; si le Mac mini y est branché un jour, prévoir un UPS plus gros.
6. **À refaire** après les points 1 à 3 : test FSD sur secteur, **sans coupure externe**, sonde sur une machine qui reste alimentée, journal enregistré dans `~/ups-test` (pas `/tmp`, vidé au redémarrage).

## Suivi — appliqué le 2026-10-29 à 14:19

- **Point 2 (arrêt en parallèle)** : `/etc/nut/shutdown-script.sh` réécrit (copie de référence : `scripts/nut/shutdown-script.sh`, ancienne version sauvegardée en `.bak-20261029-141931`). NAS, VM et LXC partent en même temps, plus d'attente de 30 s. Essai à blanc (`DRY_RUN=1`) : 18 invités traités, rien d'arrêté. **Durée réelle à mesurer au prochain test** ; attendue : ~70 s (limitée par Home Assistant, jusqu'à 60 s).
- **Point 3 (ordre de démarrage)** : `qm set 115 --startup order=1,up=20` (pfSense) et `pct set 103 --startup order=2,up=5` (AdGuard). Les autres invités démarrent ensuite. Retour arrière : `qm set 115 --delete startup` / `pct set 103 --delete startup`.
- **Point 1 (redémarrage automatique)** : à faire à la main (BIOS NIPoGi : AMI Aptio 5.26, UEFI ; DSM sur NAS2 et NAS3).
- **Question ouverte** : l'UPS rallume-t-il ses prises tout seul, secteur présent ? `upscmd -l` ne liste pas `shutdown.return` pour ce modèle (seulement `shutdown.reboot` et `shutdown.stop`). À observer au prochain test.
- **Decos** : le temps de retour « en ligne » n'a pas été mesuré (sonde perdue). Hypothèse : ils attendent un Internet fonctionnel, donc le modem VOO (tunnel Cloudflare revenu à 14:04:50).
