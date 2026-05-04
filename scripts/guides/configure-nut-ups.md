# Configuration de la surveillance de l'UPS avec NUT

Ce guide explique comment installer et configurer Network UPS Tools (NUT) pour surveiller l'état de votre UPS et automatiser les actions en cas de batterie faible.

## Prérequis

- Un serveur Nipogi avec accès root.
- L'UPS APC Back-UPS ES - BE550G-FR connecté au serveur via USB ou via son port RJ45 "data port".
# Note : Le port RJ45 "data port" peut utiliser un protocole propriétaire. Vérifiez la compatibilité avec NUT ou consultez la documentation de l'UPS.
- Accès à Internet pour installer les paquets nécessaires.

## Étapes d'installation

### 1. Installer NUT
Exécutez les commandes suivantes pour installer NUT :
```bash
sudo apt update
sudo apt install nut
```

### 2. Configurer NUT
Modifiez les fichiers de configuration pour adapter NUT à votre UPS.

#### a. `ups.conf`
Ajoutez la configuration de votre UPS dans `/etc/nut/ups.conf` :
```bash
[myups]
    driver = usbhid-ups
    product = "Back-UPS ES 550G"
    port = auto
    desc = "UPS Principal"
```

#### b. `upsd.conf`
Assurez-vous que le fichier `/etc/nut/upsd.conf` contient :
```bash
LISTEN 127.0.0.1 3493
```

#### c. `upsmon.conf`
Ajoutez les détails de surveillance dans `/etc/nut/upsmon.conf` :
```bash
MONITOR myups@localhost 1 monuser secret master
```

### 3. Créer un utilisateur pour NUT
Ajoutez un utilisateur pour NUT :
```bash
sudo useradd -M -s /bin/false nutmon
sudo passwd nutmon
```

### 4. Activer et démarrer NUT
Activez et démarrez les services NUT :
```bash
sudo systemctl enable nut-server
sudo systemctl start nut-server
sudo systemctl enable nut-monitor
sudo systemctl start nut-monitor
```

### 5. Tester la configuration
Vérifiez que NUT fonctionne correctement :
```bash
upsc myups@localhost
```

## Automatisation des actions en cas de batterie faible
Ajoutez un script pour arrêter les périphériques en cas de batterie faible. Ce script sera exécuté par NUT.

### Exemple de script
Créez un fichier `/etc/nut/shutdown-script.sh` :
```bash
#!/bin/bash
# Script d'arrêt en cas de batterie faible
/path/to/scripts/synology-shutdown.sh
/path/to/scripts/nipogi-shutdown.sh
# Replace /path/to/scripts/ with the actual path to the scripts in your system.
```

Rendez-le exécutable :
```bash
chmod +x /etc/nut/shutdown-script.sh
```

Ajoutez ce script dans la configuration de NUT :
```bash
FINALDELAY 5
SHUTDOWNCMD "/etc/nut/shutdown-script.sh"
```

## Conclusion
Votre système est maintenant configuré pour surveiller l'UPS et prendre des mesures en cas de batterie faible.