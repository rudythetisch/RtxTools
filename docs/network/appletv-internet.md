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

## pfSense

- **Règle** (LAN) : `block` IPv4, source `192.168.10.93`, destination `!lan`, log activé, description `Bloquer Internet Apple TV (pilotée par Home Assistant)`. Placée avant `Default allow LAN`. Désactivée = Internet autorisé.
- La règle est retrouvée par sa description (filtre `descr__contains=Apple TV`), pas par son ID : l'ID de l'API v2 est la position dans la liste et change si on réordonne les règles. **Ne pas renommer la règle sans adapter le sensor.**
- Pas d'IPv6 global sur le LAN : le blocage IPv4 suffit. À revoir si l'IPv6 est activé un jour.
- **Compte API** `ha-appletv`, avec 6 privilèges seulement : `firewall-rules-get`, `firewall-rule-get`, `firewall-rule-patch`, `firewall-apply-post`, `firewall-states-get`, `firewall-states-delete`.
- HA passe par `https://pfsense.tixhon.be` (NPM, certificat valide) : l'API n'est pas servie en HTTPS sur `192.168.10.1`.

### Piège : l'apply est asynchrone

`POST /firewall/apply` répond en ~100 ms (`applied: true`), mais pfSense recharge le filtre en arrière-plan. pf ne bloque que les **nouvelles** connexions. Si on coupe les connexions avant que la règle soit chargée, l'Apple TV se reconnecte aussitôt et ses nouvelles connexions survivent au blocage. Le 2026-10-09, au premier essai, le stream Prime Video a continué pour cette raison, et le rechargement n'avait toujours pas eu lieu 3 min plus tard. D'où les pauses et le second apply dans le script.

Diagnostic : `pfctl -sr | grep Apple` (Diagnostics > Command Prompt) doit montrer la règle quand elle est active. On peut aussi vérifier la date de `/tmp/rules.debug`.

Un stream en cours peut continuer 1 à 2 minutes sur le tampon de lecture même quand le blocage fonctionne. Pour vérifier, avancer dans le film.

## Home Assistant

- YAML (`rest_command` + sensor `rest`) : [scripts/home-assistant/appletv-internet.yaml](../../scripts/home-assistant/appletv-internet.yaml), à coller dans `configuration.yaml`, avec les secrets `pfsense_ha_user` / `pfsense_ha_password` dans `secrets.yaml`.
- `script.appletv_internet` et `switch.internet_apple_tv` sont créés via l'API/UI (pas dans le YAML).

## Historique

La règle `block_kids_inet` (alias `KID_DEVICES`) du plan [[parental-control-timer-plan]] n'a jamais fonctionné. Elle a été réutilisée pour cette règle Apple TV, à la même position. L'alias `KID_DEVICES` existe encore mais n'est plus utilisé. Attention, il contenait `192.168.10.98`, c'est-à-dire le Mac Mini.
