# Configuration de la surveillance de l'UPS avec NUT

Ce guide explique comment installer et configurer Network UPS Tools (NUT) pour surveiller l'état de votre UPS et automatiser les actions en cas de batterie faible.

> **Vérifié et corrigé le 2026-08-05** — l'installation initiale n'avait jamais réellement fonctionné (paquet jamais installé, câble USB pas branché). Ce guide contenait aussi une étape manquante critique (`MODE` dans `nut.conf`) et une confusion sur le système d'authentification NUT. Voir la section [État actuel](#état-actuel-2026-08-05) en bas.

## Prérequis

- Un serveur Nipogi (Proxmox, `192.168.10.2`) avec accès root.
- L'UPS APC Back-UPS ES BE550G-FR connecté au serveur via **USB** (le port RJ45 "data port" utilise un protocole propriétaire APC non supporté par NUT — ne pas l'utiliser).
- Accès à Internet pour installer les paquets nécessaires.

Vérifier que l'UPS est bien détecté avant de commencer :
```bash
lsusb | grep -i "American Power"
# Doit afficher : Bus 001 Device XXX: ID 051d:0002 American Power Conversion Uninterruptible Power Supply
```
Si rien ne s'affiche, le câble USB n'est pas branché ou pas reconnu — brancher/rebrancher avant de continuer.

## Étapes d'installation

### 1. Installer NUT
```bash
apt update
apt install -y nut
```

### 2. Configurer NUT

#### a. `nut.conf` — **étape indispensable, absente de la version précédente de ce guide**
Sans ça, aucun service NUT ne démarre (le mode par défaut est `none`) :
```bash
sed -i 's/^MODE=.*/MODE=standalone/' /etc/nut/nut.conf
grep -q '^MODE=' /etc/nut/nut.conf || echo 'MODE=standalone' >> /etc/nut/nut.conf
```

#### b. `ups.conf`
Dans `/etc/nut/ups.conf` :
```ini
[apc-nipogi]
    driver = usbhid-ups
    port = auto
    desc = "UPS Principal - APC Back-UPS ES BE550G-FR"
```
(Le champ `product` de la version précédente n'est pas nécessaire — `usbhid-ups` détecte le modèle automatiquement via `port = auto`.)

#### c. `upsd.conf`
```bash
echo 'LISTEN 127.0.0.1 3493' > /etc/nut/upsd.conf
chown root:nut /etc/nut/ups.conf /etc/nut/upsd.conf
chmod 640 /etc/nut/ups.conf /etc/nut/upsd.conf
```

#### d. Démarrer le driver + le serveur (lecture d'état seule, sans monitoring actif)
```bash
systemctl restart nut-server
upsc apc-nipogi
```
Doit afficher `battery.charge`, `ups.status`, etc. À ce stade, **la surveillance batterie faible / arrêt automatique n'est pas encore active** — voir la suite pour ça.

### 3. Configurer les utilisateurs NUT (⚠️ correction — pas des utilisateurs Unix)

**Erreur de la version précédente** : `useradd nutmon` + `passwd nutmon` créait un utilisateur **système Linux**, ce qui n'a aucun rapport avec l'authentification NUT. NUT a son propre système d'utilisateurs, défini dans `/etc/nut/upsd.users` — **ne pas utiliser `useradd`/`passwd` pour ça**.

Dans `/etc/nut/upsd.users` :
```ini
[monuser]
    password = <mot_de_passe_a_choisir>
    upsmon master
```
```bash
chown root:nut /etc/nut/upsd.users
chmod 640 /etc/nut/upsd.users
```

#### `upsmon.conf`
```ini
MONITOR apc-nipogi@localhost 1 monuser <mot_de_passe_choisi_ci-dessus> master
```

### 4. Activer et démarrer le monitoring
```bash
systemctl enable --now nut-server
systemctl enable --now nut-monitor
systemctl status nut-server nut-monitor --no-pager
```

### 5. Tester
```bash
upsc apc-nipogi
# ou depuis un autre hôte du réseau si LISTEN a été ouvert au-delà de 127.0.0.1
```

## Automatisation des actions en cas de batterie faible

Script `/etc/nut/shutdown-script.sh` (chemins réels du repo, à adapter si les scripts sont déplacés) :
```bash
#!/bin/bash
# Script d'arrêt en cas de batterie faible (déclenché par upsmon via SHUTDOWNCMD)
/root/RtxTools/scripts/synology-shutdown.sh   # ou copier/déployer ce script sur chaque NAS
/root/RtxTools/scripts/nipogi-shutdown.sh
```
```bash
chmod +x /etc/nut/shutdown-script.sh
```

Dans `/etc/nut/upsmon.conf` (pas juste "dans la configuration de NUT" — précisément ce fichier) :
```ini
FINALDELAY 5
SHUTDOWNCMD "/etc/nut/shutdown-script.sh"
```

Redémarrer `nut-monitor` après toute modification de `upsmon.conf` :
```bash
systemctl restart nut-monitor
```

## État actuel (2026-08-05)

Suite à une coupure électrique où l'UPS n'a pas tenu la charge d'un arrêt propre (TischNAS3 coupé en plein shutdown), vérification faite : **NUT n'avait en réalité jamais été installé** (paquet absent, câble USB de l'UPS débranché) malgré ce guide déjà rédigé. Corrigé le jour même :

- Paquet `nut` installé, driver `usbhid-ups` + `nut-server` actifs sur NIPoGi — **lecture d'état fonctionnelle** (`upsc apc-nipogi`)
- Batterie relevée à **54% de charge**, ~13,5 min d'autonomie estimée. `battery.mfr.date` affiche février 2012, mais **ne pas s'y fier** : sur les APC USB-HID grand public (dont ce Back-UPS ES), ce champ reflète la date de fabrication du **boîtier**, pas de la batterie, et n'est généralement pas modifiable via NUT après un remplacement de batterie — confirmé par l'utilisateur qui a déjà changé la batterie 2-3 fois sans que ce champ ait jamais bougé.
- **Cause réelle du manque d'autonomie encore à investiguer** : vu que la batterie a déjà été remplacée plusieurs fois sans amélioration durable, suspecter plutôt le circuit de charge du boîtier (qui a ~14 ans, lui) ou une charge connectée trop proche/au-delà de la capacité du 550VA. À vérifier : `ups.load` (actuellement non fiable sur ce modèle via USB-HID, retourne 0), et calculer la consommation réelle (NIPoGi + TischNAS3 + switch + modem, selon ce qui est branché sur cet UPS).
- **`upsmon`/monitoring actif et arrêt automatique (étapes 3-5 + section automatisation) pas encore configurés** — seule la lecture d'état à la demande fonctionne pour l'instant. À faire si on veut un vrai arrêt automatique déclenché par batterie faible.
