# Projets futurs (homelab)

Changements prévus mais pas encore réalisés. Une fois un projet terminé, le passer dans « Réalisés » avec la date, et documenter le résultat dans la page du sujet concerné.

## Vue d'ensemble

| Priorité | Projet | Statut | Budget indicatif | Dépend de |
|---|---|---|---|---|
| 🔴 Haute | [Remplacer le disque en panne de TischNAS2](#remplacer-le-disque-en-panne-de-tischnas2) | À faire, RAID dégradé depuis 2026-07 | ~80–120 € (WD Red Plus 2 To ou plus) | — |
| 🟠 Moyenne | [OPNsense sur appliance dédiée](#opnsense-sur-appliance-dédiée) | Plan rédigé, matériel à commander | ~356 € | — |
| 🟠 Moyenne | [RAM TischNAS3](#ram-tischnas3) | Choix entre 2 options ECC | ~221–344 € | — |
| 🟢 Basse | [Wi-Fi UniFi + VLAN](#wi-fi-unifi--vlan) | Idée, à chiffrer | À chiffrer | OPNsense |
| 🟢 Basse | [NIPoGi : LAN sur la carte réseau intégrée](#nipogi--lan-sur-la-carte-réseau-intégrée) | Après OPNsense | 0 € | OPNsense |
| ⚪ Optionnel | [Tailscale](#tailscale) | Pour apprendre, aucune urgence | 0 € | — |

Ordre conseillé : **disque TischNAS2 → OPNsense → RAM TischNAS3 → NIPoGi → UniFi + VLAN**.

---

## Remplacer le disque en panne de TischNAS2

- **Problème** : le disque `sdd` (WD20EARX 2 To) est en panne depuis fin juillet 2026. Le RAID5 `md3` (`volume1`) tourne sur 2 disques sur 3 : `[UU_]`, encore le cas le 2026-10-13. **Une deuxième panne ferait perdre tout le volume.**
- **Impact** : `volume1` contient surtout la bibliothèque de téléchargements (~1,9 To, re-téléchargeable). Le backup des photos est sur `volume2`, qui est sain.
- **À faire** : acheter un disque NAS de **2 To ou plus** (WD Red Plus, Seagate IronWolf), remplacer `sdd`, puis lancer la réparation du pool dans DSM (Gestionnaire de stockage).
- **Ensuite** : surveiller `sdc`, du même lot et du même âge que `sdd`.

## OPNsense sur appliance dédiée

- **Pourquoi** : pfSense en VM sur le NIPoGi s'est figé deux fois pendant les sauvegardes Proxmox (LAN sur un adaptateur USB saturé). Et pfSense CE est moins suivi que la version payante.
- **Matériel** : Topton N150, boîtier « Big » sans ventilateur, 4× Intel i226-V 2,5 Gb, 8 Go DDR4 + NVMe 128 Go. **356,39 €** sur AliExpress (boutique officielle Topton).
- **Plan complet** : [[network/migration-opnsense]] (inventaire, bascule, retour arrière).
- **En attendant** : la sauvegarde Proxmox est passée à 3h00 avec un débit limité à 40 Mo/s (2026-10-11). Surveiller sa durée dans l'e-mail de rapport.

## RAM TischNAS3

- **Situation** : DS925+ (AMD Ryzen V1500B), **4 Go DDR4 ECC** sur 1 des 2 emplacements, 32 Go maximum. 2,5 Go utilisés, moins de 1 Go disponible : c'est la cause de la lenteur du 2026-09-20 (qBittorrent).
- **Officiel Synology** : hors de prix sur le marché actuel (relevé le 2026-10-13). En 8 Go, D4ES02-8G à 489 € et D4ES03-8G à 639 € sur Amazon. En 16 Go, plus de 1 500 € chez LDLC.
- **Options ECC non officielles** (Amazon.fr, 2026-10-13) :
  - **OWC 16 Go DDR4-2666 ECC SO-DIMM**, ~221 €, ajoutée à la barrette de 4 Go → **20 Go** ;
  - **kit NEMIX 2 × 16 Go DDR4-2666 ECC SO-DIMM**, ~344 € (~172 € les 16 Go), à la place de la barrette de 4 Go → **32 Go**, le maximum ;
  - **BytecRAM 8 Go DDR4-2666 ECC**, présentée comme compatible DS925+, ~239 € → 12 Go. Moins intéressante que l'OWC.
- **Choix à faire** : l'OWC pour 20 Go, ou le kit NEMIX pour 32 Go à meilleur prix au Go. Dans les deux cas, DSM affichera un avertissement « mémoire non Synology », sans effet sur le fonctionnement. Garder la barrette de 4 Go d'origine en cas de souci ou de demande au support.
- **Avant de commander** : vérifier que l'annonce mentionne bien **ECC Unbuffered SO-DIMM** (NEMIX vend aussi de la non-ECC), et le vendeur.
- **À éviter** : de la RAM **non-ECC** (comme la Crucial CT16G4SFRA32A) à côté de la barrette ECC. Le mélange désactive l'ECC, et le NAS peut même ne pas démarrer.

## Wi-Fi UniFi + VLAN

- **Objectif** : remplacer les 3 TP-Link Deco M4R (Grenier `.30`, Étage `.31`, Salon `.32`) par des bornes **UniFi** qui gèrent les **VLAN**. Chaque réseau Wi-Fi peut alors être isolé sur son propre sous-réseau.
- **Découpage envisagé** :

| VLAN | Réseau | Usage |
|---|---|---|
| 1 (non tagué) | `192.168.10.0/24` | Principal : PC, NAS, serveurs |
| 20 | `192.168.20.0/24` | Enfants : coupure Internet par réseau entier, horaires, « deny unknown clients » contre les adresses MAC rotatives |
| 30 | `192.168.30.0/24` | Invités : Internet seulement, pas d'accès au LAN |
| 40 | `192.168.40.0/24` | Objets connectés : caméras Eufy, TV, prises… isolés du reste |

- **Ce qu'il faut** :
  - **OPNsense d'abord** : il fera le routage et les règles entre VLAN.
  - **Switch** : le D-Link DGS-1100-24 gère le 802.1Q, aucun achat nécessaire.
  - **Bornes** : par exemple 3× **U7 Lite** (Wi-Fi 7) ou **U6+** (Wi-Fi 6), à chiffrer.
  - **Alimentation PoE** : les bornes UniFi doivent être alimentées par le câble réseau (PoE). Le DGS-1100-24 n'en fournit pas (voir [[network/switch]]). Il faudra donc des injecteurs PoE ou un petit switch PoE.
  - **Contrôleur** : l'application UniFi Network peut tourner gratuitement dans un LXC Proxmox. Pas besoin d'une passerelle UniFi, puisque c'est OPNsense qui route.
- **Bonus** : le blocage Internet des enfants (aujourd'hui IP par IP, voir [[network/internet-appareils]]) pourra viser tout le VLAN enfants d'un coup. Les adresses Wi-Fi « rotatives » d'iOS ne pourront plus y échapper.
- **À décider** : les modèles de bornes, le PoE, le CPL (base sur la mezzanine, TL-WPA7617 dans l'abri de jardin : garder, ou remplacer par une borne UniFi extérieure) (le TL-WR802N du Neato est à débrancher : Neato n'existe plus).

## NIPoGi : LAN sur la carte réseau intégrée

- Une fois pfSense sorti du NIPoGi, la carte intégrée `enp1s0` (Realtek, utilisée aujourd'hui pour le WAN) se libère. Il faut alors y passer `vmbr1` (LAN) et débrancher l'adaptateur USB `cdc_ncm`.
- **Attention** : l'IP de gestion de Proxmox (`.2`) est sur `vmbr1`. Garder un écran et un clavier branchés, ou un accès console, pendant l'opération.

## Tailscale

- Pour apprendre, en complément de WireGuard, qui reste l'accès principal. Avantages : pas de port ouvert, ajout d'un appareil en 30 secondes, accès par nom (MagicDNS), relier un 2e site.
- Pour démarrer : un petit LXC « subnet router » sur Proxmox, ou le plugin `os-tailscale` une fois sur OPNsense.
- Les services web restent publiés par Cloudflare. Pistes pour les sécuriser : bloquer `/admin` de Vaultwarden, n'autoriser que certains pays, limiter les tentatives de connexion. Les interfaces d'administration seraient à rendre accessibles uniquement par VPN.

---

## Réalisés

- 2026-10-11 : sauvegarde Proxmox déplacée à 3h00, débit limité à 40 Mo/s (suite au blocage de pfSense).
- 2026-10-12 : DNS de secours de Home Assistant désactivé, et notification en cas d'échec d'une coupure Internet.
