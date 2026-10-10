# Coupure Internet par appareil (Apple TV, Switch, iPad, iPhones)

On coupe Internet appareil par appareil au niveau de pfSense, depuis des interrupteurs Home Assistant. tvOS n'a pas de contrôle du temps d'écran, d'où le besoin pour l'Apple TV. Mis en place le 2026-10-09 pour l'Apple TV, puis étendu le 2026-10-10 aux appareils des enfants.

Les appareils coupés gardent l'accès au LAN (AirPlay, HomeKit, médias locaux) : seul Internet est bloqué.

## Appareils

| Appareil | Utilisateur | IP (réservation DHCP) | MAC | Interrupteur HA |
|---|---|---|---|---|
| Apple TV 4K | salon | 192.168.10.93 | f0:b3:ec:25:6d:2e | `switch.internet_apple_tv` |
| Nintendo Switch | | 192.168.10.92 | 5c:0c:e6:28:2c:18 | `switch.internet_switch` |
| iPad 5th gen | Cyril | 192.168.10.96 | ae:33:8b:ad:c5:93 (privée, « Fixe ») | `switch.internet_ipad_cyril` |
| iPhone Xs | Tristan | 192.168.10.97 | 0a:2c:db:47:c7:94 (privée, « Fixe ») | `switch.internet_iphone_tristan` |
| iPhone 14 Pro | Elias | 192.168.10.99 | de:f0:14:39:bf:cd (privée, « Fixe ») | `switch.internet_iphone_elias` |

**Ajouter un appareil** : réservation DHCP dans pfSense, puis un helper template switch dans HA (même modèle que les autres, avec l'IP), puis un bouton sur le dashboard. Aucun YAML à modifier.

### Limites

- **Adresse Wi-Fi privée (iOS)** : elle doit rester sur « Fixe » ou « Désactivée ». En « Rotative », la MAC change, donc l'IP aussi, et l'appareil échappe à la coupure. pfSense CE ne filtre pas par MAC (les règles Ethernet n'existent que dans pfSense Plus), et ça ne servirait à rien puisque c'est justement la MAC qui change. La seule vraie parade est « Deny unknown clients » sur le DHCP, trop contraignant sur un réseau partagé : à envisager avec un Wi-Fi/VLAN enfants séparé.
- **Données mobiles** : un iPhone avec de la data bascule en 4G/5G. Pour ça, il faut le Temps d'écran d'Apple.
- « Limiter le suivi de l'adresse IP » (iOS) n'a aucun impact : ce trafic passe aussi par pfSense.

## Chaîne de commande

```
Dashboard HA (Accueil) → switch.internet_<appareil>   (helpers template, créés dans l'UI)
  → script.internet_appareil (ip, bloquer)            mode queued : les appareils sont traités un par un
      1. rafraîchit sensor.appareils_internet_coupe et calcule la nouvelle liste d'IP
      2. rest_command.pfsense_alias_set     PATCH de l'alias INTERNET_BLOQUE (vérifie status 200)
      3. rest_command.pfsense_apply         recharge le filtre (vérifie status 200)
      4. au blocage seulement : pause 5 s → rest_command.pfsense_kill_states(ip), pause 10 s → kill à nouveau
      5. rafraîchit le capteur
  ← sensor.appareils_internet_coupe (rest, toutes les 60 s) : nombre d'appareils coupés, attributs `id` et `address`
  ← chaque switch : on = l'IP n'est PAS dans `address`
```

`script.appletv_internet` (champ `bloquer`) est un raccourci vers `script.internet_appareil` avec l'IP .93. Il est utilisé par le switch Apple TV et par le minuteur.

## Dashboard (vue Accueil)

- **Actions rapides → « Apple TV »** : bascule Internet de l'Apple TV.
- **Temps d'écran Apple TV** : minuteur, voir plus bas.
- **Internet des enfants** : un bouton par appareil (iPhone Elias, iPhone Tristan, iPad Cyril, Switch), plus « Tout couper » et « Tout rétablir ». Comme les appareils sont traités un par un, « Tout couper » prend environ 1 min.

## Minuteur (temps d'écran Apple TV)

Carte « Temps d'écran Apple TV » : boutons 10 min / 15 min / 30 min / 1 h / 1 h 30 / 2 h, et « Couper ».

- `script.appletv_minuteur` (champ `minutes`) : ouvre Internet si c'est coupé, puis lance `timer.temps_ecran_apple_tv` (`restore: true`, survit à un redémarrage de HA). Relancer une durée remplace la précédente.
- Automation `appletv_avertissement_5min` : déclenchée au démarrage du minuteur, attend jusqu'à 5 min de la fin, puis affiche une alerte « Plus que 5 minutes ! » sur la TV LG. On utilise une attente plutôt qu'un trigger template `now()`, qui n'est réévalué qu'une fois par minute.
- Automation `appletv_temps_ecoule` : sur `timer.finished`, coupe Internet, affiche une alerte sur la TV et notifie l'iPhone de Rudy.
- Automation `appletv_coupure_manuelle` : une coupure manuelle annule le minuteur en cours.

**Messages sur la TV** : `notify.lg_webos_tv_oled65c11lb` (toast) et `system.notifications/createToast` ne s'affichent **pas** quand l'entrée HDMI de l'Apple TV est à l'écran. Seule une alerte passe, via `webostv.command`, commande `system.notifications/createAlert` avec un bouton OK. Elle reste à l'écran jusqu'à ce qu'on appuie sur OK (télécommande LG).

## pfSense

- **Règle** (LAN, position 4, avant `Default allow LAN`) : `block` IPv4, source alias `INTERNET_BLOQUE`, destination `!lan`, log activé, toujours active. Description : `Bloquer Internet appareils (alias INTERNET_BLOQUE, piloté par Home Assistant)`.
- **Alias** `INTERNET_BLOQUE` (host) : contient les IP actuellement coupées, géré uniquement par HA. Ne pas l'éditer à la main, sauf en cas de dépannage ; HA le relit toutes les 60 s.
- Pas d'IPv6 global sur le LAN : le blocage IPv4 suffit. Les iPhones ont des adresses IPv6 ULA (`fdf9:…`), non routables vers Internet. À revoir si l'IPv6 est activé un jour.
- **Compte API** `ha-appletv`, avec 9 privilèges seulement : `firewall-rules-get`, `firewall-rule-get`, `firewall-rule-patch`, `firewall-apply-post`, `firewall-states-get`, `firewall-states-delete`, `firewall-aliases-get`, `firewall-alias-get`, `firewall-alias-patch`. Le nom date de la première version, Apple TV seule.
- HA passe par `https://pfsense.tixhon.be` (NPM, certificat valide) : l'API n'est pas servie en HTTPS sur `192.168.10.1`.

Diagnostic : `GET /api/v2/diagnostics/table?id=INTERNET_BLOQUE` montre ce que pf a réellement chargé. Après un apply, la table doit correspondre à l'alias.

### Piège : `rest_command` sans `content_type` → 415

Sans `content_type`, un `rest_command` HA sans payload envoie `application/octet-stream`. L'API pfSense répond alors `415 CONTENT_HANDLER_CANNOT_DECODE_CONTENT` et ne recharge rien. HA ne remonte pas d'erreur si on ne lit pas la réponse. C'était la vraie cause des coupures et rétablissements sans effet du 2026-10-09. Correctif : `content_type: application/json` + `payload: "{}"` sur `pfsense_apply`. Le script vérifie les statuts.

### Piège : l'apply est asynchrone

`POST /firewall/apply` répond en ~100 ms (`applied: true`), mais pfSense recharge le filtre en arrière-plan. pf ne bloque que les **nouvelles** connexions : si on coupe les connexions avant que le filtre soit rechargé, l'appareil se reconnecte et ses nouvelles connexions survivent au blocage. D'où la pause de 5 s avant la coupure, puis le second passage 10 s plus tard.

Un stream en cours peut continuer 1 à 2 minutes sur le tampon de lecture même quand le blocage fonctionne. Pour vérifier, avancer dans le film.

## Home Assistant

- YAML (`rest_command` + sensor `rest`) : [scripts/home-assistant/internet-appareils.yaml](../../scripts/home-assistant/internet-appareils.yaml), en fin de `/config/configuration.yaml`. Secrets `pfsense_ha_user` / `pfsense_ha_password` dans `secrets.yaml`.
- Édition des fichiers : add-on « Advanced SSH & Web Terminal », `ssh rtixhon@192.168.10.10` (clé du Mac Mini), `sudo` pour écrire dans `/config`. Après modification : `POST /api/config/core/check_config`, puis recharger `rest_command` et `rest`.
- Scripts, switches, timer, automations et dashboard sont créés via l'API/UI (pas dans le YAML).

## Historique

- 2026-10-09 : règle Apple TV seule, activée ou désactivée par HA. Elle réutilise la règle `block_kids_inet` d'un ancien plan de contrôle parental qui n'a jamais fonctionné : SSH vers pfSense bloqué depuis le LAN, rien déployé dans HA. Suppression de l'alias `KID_DEVICES` (il contenait par erreur le Mac Mini `.98`), de la règle désactivée `block_old_ipad`, des fichiers de l'ancien plan (récupérables dans l'historique git) et des comptes pfSense `homeassistant` et `hass_scripter` (groupe admins + clé SSH, jamais utilisés depuis janvier selon les logs d'auth).
- 2026-10-10 : passage à l'alias `INTERNET_BLOQUE` et extension à la Switch, l'iPad et les deux iPhones. Réservation .97 corrigée (nouvelle MAC privée de l'iPhone Xs) et réservation .99 créée (iPhone 14 Pro). Testé sur l'iPhone de Tristan : 0 connexion pendant la coupure, reconnexion immédiate au rétablissement.
