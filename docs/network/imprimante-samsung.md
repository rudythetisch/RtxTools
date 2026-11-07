# Imprimante Samsung SCX-3400 Series

| Élément | Valeur |
|---|---|
| Nom mDNS | `Samsung SCX-3400 Series (SEC001599E3E853)` |
| IP | `192.168.10.249` |
| MAC | `00:15:99:e3:e8:53` (déduite du nom mDNS, OUI Samsung, à confirmer) |
| Ports ouverts | 631 (IPP), 9100 (RAW) |
| Utilisée par | MacBook Pro (file CUPS via un proxy local `127.0.0.1:6310`) et iPhone |

## À faire

- **Réservation DHCP fixe dans pfSense** : pas encore créée, l'IP `.249` est dans la plage dynamique (`.200–.250`) et peut changer. Créer la réservation (Services → DHCP Server → LAN → Static Mappings), puis l'ajouter au tableau de [[network/migration-opnsense]].
- Relever le port du switch (ou confirmer que l'imprimante est en Wi-Fi) pour compléter [[network/switch]].
