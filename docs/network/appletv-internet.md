# Coupure Internet de l'Apple TV

tvOS n'a pas de contrôle du temps d'écran : on coupe donc Internet à l'Apple TV au niveau de pfSense, depuis un interrupteur Home Assistant. Mis en place le 2026-10-09.

L'Apple TV garde l'accès au LAN (AirPlay, HomeKit, médias locaux) : seul Internet est bloqué.

## Chaîne de commande

```
Dashboard HA (Accueil → Actions rapides → "Apple TV")
  → switch.internet_apple_tv            (helper template, créé dans l'UI)
  → script.appletv_internet (bloquer: true/false)
      1. rest_command.pfsense_appletv_rule   PATCH disabled sur la règle pfSense
      2. rest_command.pfsense_apply          applique le filtre
      3. pause 5 s, puis rest_command.pfsense_appletv_kill_states  (seulement au blocage) coupe les connexions ouvertes
      4. pause 10 s, second apply + seconde coupure des connexions
      5. rafraîchit sensor.regle_pfsense_apple_tv
  ← sensor.regle_pfsense_apple_tv       (rest, interroge pfSense toutes les 60 s : "bloqué" / "autorisé")
```

L'état affiché vient toujours de pfSense : si la règle est basculée depuis la GUI pfSense, HA le reflète en moins d'une minute.

## Minuteur (temps d'écran)

Carte « Temps d'écran Apple TV » sur le dashboard Accueil : boutons 10 min / 15 min / 30 min / 1 h / 1 h 30 / 2 h, et « Couper ».

- `script.appletv_minuteur` (champ `minutes`) : ouvre Internet si c'est coupé, puis lance `timer.temps_ecran_apple_tv` (`restore: true`, survit à un redémarrage de HA). Relancer une durée remplace la précédente.
- Automation `appletv_avertissement_5min` : déclenchée au démarrage du minuteur, attend jusqu'à 5 min de la fin (au lieu d'un trigger template `now()`, réévalué seulement chaque minute), puis affiche une alerte « Plus que 5 minutes ! » sur la TV LG.
- Automation `appletv_temps_ecoule` : sur `timer.finished`, coupe Internet, affiche une alerte sur la TV et notifie l'iPhone de Rudy.
- Automation `appletv_coupure_manuelle` : une coupure manuelle (bouton) annule le minuteur en cours.

**Messages sur la TV** : `notify.lg_webos_tv_oled65c11lb` (toast) et `system.notifications/createToast` ne s'affichent **pas** quand l'entrée HDMI de l'Apple TV est à l'écran. Seule une alerte passe, via `webostv.command`, commande `system.notifications/createAlert` avec un bouton OK. Elle reste à l'écran jusqu'à ce qu'on appuie sur OK (télécommande LG).

Tout est créé via l'API/UI de HA, pas dans le YAML. Testé le 2026-10-09 avec un minuteur de 2 min.

## pfSense

- **Règle** (LAN) : `block` IPv4, source `192.168.10.93`, destination `!lan`, log activé, description `Bloquer Internet Apple TV (pilotée par Home Assistant)`. Placée avant `Default allow LAN`. Désactivée = Internet autorisé.
- La règle est retrouvée par sa description (filtre `descr__contains=Apple TV`), pas par son ID : l'ID de l'API v2 est la position dans la liste et change si on réordonne les règles. **Ne pas renommer la règle sans adapter le sensor.**
- Pas d'IPv6 global sur le LAN : le blocage IPv4 suffit. À revoir si l'IPv6 est activé un jour.
- **Compte API** `ha-appletv`, avec 6 privilèges seulement : `firewall-rules-get`, `firewall-rule-get`, `firewall-rule-patch`, `firewall-apply-post`, `firewall-states-get`, `firewall-states-delete`.
- HA passe par `https://pfsense.tixhon.be` (NPM, certificat valide) : l'API n'est pas servie en HTTPS sur `192.168.10.1`.

### Piège : `rest_command` sans `content_type` → 415

Sans `content_type`, un `rest_command` HA sans payload envoie `application/octet-stream`. L'API pfSense répond alors `415 CONTENT_HANDLER_CANNOT_DECODE_CONTENT` et ne recharge rien. HA ne remonte pas d'erreur si on ne lit pas la réponse. C'était la vraie cause des coupures et rétablissements sans effet du 2026-10-09. Correctif : `content_type: application/json` + `payload: "{}"` sur `pfsense_apply`. Le script vérifie maintenant `apply.status`.

### Piège : l'apply est asynchrone

`POST /firewall/apply` répond en ~100 ms (`applied: true`), mais pfSense recharge le filtre en arrière-plan. pf ne bloque que les **nouvelles** connexions : si on coupe les connexions avant que la règle soit chargée, l'Apple TV se reconnecte et ses nouvelles connexions survivent au blocage. D'où la pause de 5 s avant la coupure, puis le second passage 10 s plus tard.

Diagnostic : `pfctl -sr | grep Apple` (Diagnostics > Command Prompt) doit montrer la règle quand elle est active. On peut aussi vérifier la date de `/tmp/rules.debug`.

Un stream en cours peut continuer 1 à 2 minutes sur le tampon de lecture même quand le blocage fonctionne. Pour vérifier, avancer dans le film.

## Home Assistant

- YAML (`rest_command` + sensor `rest`) : [scripts/home-assistant/appletv-internet.yaml](../../scripts/home-assistant/appletv-internet.yaml), à coller dans `configuration.yaml`, avec les secrets `pfsense_ha_user` / `pfsense_ha_password` dans `secrets.yaml`.
- `script.appletv_internet` et `switch.internet_apple_tv` sont créés via l'API/UI (pas dans le YAML).

## Historique

La règle `block_kids_inet` (alias `KID_DEVICES`) d'un ancien plan de contrôle parental n'a jamais fonctionné : SSH vers pfSense bloqué depuis le LAN, rien déployé dans HA. Elle a été réutilisée pour cette règle Apple TV, à la même position. Le 2026-10-09, on a supprimé l'alias `KID_DEVICES` (il contenait par erreur le Mac Mini `.98`), la règle désactivée `block_old_ipad` et les fichiers de l'ancien plan (récupérables dans l'historique git). Les comptes pfSense `homeassistant` et `hass_scripter`, membres du groupe admins avec une clé SSH et jamais utilisés depuis janvier selon les logs d'auth, ont aussi été supprimés.
