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
- **Cause probable identifiée** : `ups.load` n'est pas fiable sur ce modèle via USB-HID (retourne toujours 0). Appareils confirmés branchés sur cet UPS (2026-08-05) : NIPoGi, TischNAS2, TischNAS3 (2 NAS 4 baies), modem VOO, switch PoE 5 ports, switch 24 ports, antenne Somfy 2,4GHz. Consommation estimée ~145-225W en fonctionnement (potentiellement plus selon charge PoE), sous les 330W nominaux du 550VA en continu mais **UPS objectivement sous-dimensionné** pour ce volume d'équipement (un 550VA grand public est conçu pour un PC + écran, pas 2 NAS 4 baies + infra réseau complète). Combiné à l'âge du boîtier (~14 ans, circuit de charge qui vieillit indépendamment des remplacements de batterie), l'autonomie insuffisante malgré plusieurs changements de batterie s'explique probablement par ce sous-dimensionnement plutôt que par la seule batterie. **Recommandation : UPS plus costaud (1000-1500VA) plutôt que remplacer encore la batterie.**
- **Monitoring actif + arrêt automatique configurés le 2026-08-05** : `upsd.users` (utilisateur NUT `monuser`, mode `master`) et `upsmon.conf` en place, `nut-monitor` actif et confirmé sans erreur (`UPS: apc-nipogi@localhost (primary)` dans les logs).
- **Ordre d'arrêt du script `/etc/nut/shutdown-script.sh`** (déclenché par `SHUTDOWNCMD` en cas de batterie critique) : TischNAS2 → TischNAS3 (SSH + `sudo synoshutdown --shutdown`, les plus longs à arrêter proprement) → attente 30s → VMs Proxmox (`qm shutdown`) → LXC Proxmox (`pct shutdown`) → NIPoGi lui-même (`shutdown -h now`). Logs dans `/var/log/ups-shutdown.log` sur NIPoGi.
- **Droit sudo ajouté** au compte `claude` sur les deux NAS : `NOPASSWD: /usr/syno/sbin/synoshutdown` (en plus de `docker`/`df`/`free` déjà en place) — nécessaire pour que le script d'arrêt fonctionne sans mot de passe interactif. Clé publique de `root@nipogi` (`id_rsa.pub`) ajoutée aux `authorized_keys` `claude` des deux NAS pour permettre l'appel SSH sortant depuis NIPoGi.
- **Non testé en conditions réelles** (débrancher l'UPS pour de vrai) — le risque d'un test complet (arrêt effectif de tout le homelab) n'a pas été jugé nécessaire ; chaque maillon (SSH+sudo vers les 2 NAS, énumération VM/LXC, service upsmon actif) a été vérifié individuellement à la place.
