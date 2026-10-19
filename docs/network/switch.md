# Switch D-Link DGS-1100-24 (buanderie)

| Élément | Valeur |
|---|---|
| Modèle | D-Link DGS-1100-24, 24 ports Gigabit, **révision matérielle A1**, firmware 1.10.011 |
| Emplacement | Buanderie |
| Nom système | `switch-24p` |
| IP de gestion | `192.168.10.20/24` statique, passerelle `.1` (depuis le 2026-10-19 ; avant : `10.90.90.90/8`, IP d'usine) |
| MAC | `c4:a8:1d:f4:3c:a0` (réservation DHCP `.20` dans pfSense, pour mémoire) |
| Interface | http://192.168.10.20 (compte `admin`, mot de passe changé par l'utilisateur, dans Vaultwarden) |

## Ce que le switch sait faire (ou pas)

- **Oui** : VLAN 802.1Q (actif, tout en VLAN 1), trunking, IGMP snooping, mirroring, détection de boucle, QoS, diagnostic de câble, table MAC.
- **Non** : **ni SNMP ni LLDP** sur cette révision A1 (la page « Trap Settings » ne sert qu'à l'outil Windows SmartConsole). Scanopy ne peut donc pas en tirer la carte physique.
- **Non** : pas de PoE (la version PoE est la DGS-1100-24P).
- Délai de session web : 5 minutes d'inactivité. Après un changement, **Save → Save Configuration**, sinon perdu au redémarrage.

## Ports (relevé de la table MAC, 2026-10-19)

Déduit de la table « Dynamic Forwarding Table » croisée avec l'ARP de pfSense. Les ports non listés n'avaient aucune adresse apprise (rien de branché, ou appareil éteint).

| Port | Ce qui est derrière |
|---|---|
| 01 | **Deco M4R Salon** + ses clients Wi-Fi (HomePod Cuisine, P1 meter, iPad Cyril, aspirateur laveur Dreame Aqua Roller Ultra, Meross caméra Cuisine, BSH, station météo, Salon (2)…) |
| 04 | Apple TV 4K (Salon) |
| 06 | Gigaset C5310-IP |
| 07 | Mezzanine, bureau de Céline : **Deco M4R Étage 1** + clients (iPhone Elias, iPhone Tristan, caméra IndoorCam, Meross MSS210-1e56) |
| 08 | Mezzanine, côté armoire Expedit : TL-WR802N (ancien Wi-Fi 2,4 GHz du Neato ; **inutile** depuis la disparition de Neato, à débrancher) |
| 11 | Mezzanine, bureau de Céline : **CPL TP-Link** (adaptateur de base, réservation `.35`). L'autre bout (TL-WPA7617) est dans l'**abri de jardin** ; derrière lui, `.212` = robot tondeuse **Dreame A1 Pro**, réservé en `.28` (MAC `10:06:48:a2:7c:05`, SSH Dropbear 2019) |
| 12 | TischNAS3 |
| 17 | **NIPoGi** (adaptateur USB LAN `vmbr1`) : Proxmox, pfSense LAN, Home Assistant, tous les LXC |
| 18 | TischNAS2 |
| 19 | **Deco M4R Grenier** + Mac mini (Ethernet et Wi-Fi), clim Smart AC, `.208`, `.245` |
| 23 | Niko Home Control 2 |
| 24 | eufy HomeBase 2 |

La Nintendo Switch (Ethernet, prise murale) n'apparaissait pas : éteinte au moment du relevé.

## Prises murales connues

| Pièce | Prises | Utilisation |
|---|---|---|
| Mezzanine, bureau de Céline | 2 | Deco Étage 1 (port 07), CPL (port 11) |
| Mezzanine, côté armoire Expedit | 2 | TL-WR802N (port 08), l'autre probablement libre |
| Chambre d'Elias | 2 | libres |
| Chambre de Tristan | 2 | libres |

Les prises libres des chambres permettront de câbler une borne UniFi ou un appareil fixe sans passer par le CPL.
