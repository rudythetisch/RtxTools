# Changelog

## 2026-05-03

### rtxcopy — initial implementation

- `tools/rtxcopy/src/rtxcopy/destinations.py`: modèles de destinations (NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination)
  Reason: représentation typée des cibles de copie, discriminant TOML via champ `type`
  Source: `destination_from_dict`, `destination_to_dict`

- `tools/rtxcopy/src/rtxcopy/config.py`: chargement/sauvegarde TOML atomique, gestion des favoris par destination
  Reason: config persistante dans `~/.config/rtxtools/rtxcopy/config.toml`, écriture via fichier `.tmp` + rename
  Source: `load_config`, `save_config`, `Config.add_favorite`, `Config.remove_favorite`

- `tools/rtxcopy/src/rtxcopy/ssh_keys.py`: génération Ed25519, import, déploiement via stdin (compatible Synology MaxSessions=1)
  Reason: clés dédiées par destination, déploiement one-shot sans stocker le mot de passe
  Source: `generate_keypair`, `deploy_public_key`

- `tools/rtxcopy/src/rtxcopy/transfer.py`: moteur SFTP paramiko avec callback de progression byte-level
  Reason: progression en temps réel sans parser stdout rsync
  Source: `transfer`, `_transfer_nas`, `_sftp_upload`

- `tools/rtxcopy/src/rtxcopy/proxmox.py`: wrappers `pct push` / `qm guest exec`
  Reason: copie vers LXC/QEMU via SSH nœud Proxmox, pas d'API REST
  Source: `push_to_lxc`, `push_to_qemu`

- `tools/rtxcopy/src/rtxcopy/screens/file_picker.py`: TUI file picker avec tailles, multi-select, navigation P/U
  Reason: `priority=True` sur Space/C pour capturer avant DirectoryTree; U = parent, P = focus champ chemin
  Source: `SizedDirectoryTree.render_label`, `action_toggle_select`, `action_go_up`

- `tools/rtxcopy/src/rtxcopy/screens/remote_path.py`: browser SFTP lazy avec favoris (f/F)
  Reason: navigation distante sans taper le chemin; fallback texte si SFTP indisponible (Synology)
  Source: `_connect_and_load_root`, `action_toggle_favorite`, `FavoritesModal`

- `tools/rtxcopy/src/rtxcopy/screens/progress.py`: barre de progression async via Worker thread
  Reason: transfert non-bloquant avec mise à jour UI via `self.app.call_from_thread`
  Source: `_do_transfer`, `_update_progress`

- `tools/rtxcopy/src/rtxcopy/screens/dest_manager.py`: CRUD destinations + gestion clés SSH en TUI
  Reason: ajout/suppression/déploiement de clés sans quitter l'app
  Source: `DestManagerScreen`, `KeyManagerScreen`, `DeployKeyScreen`

## 2026-05-03 (session 2)

### rtxcopy — édition destinations, browser Proxmox, fix HAOS

- `screens/dest_manager.py`: refactorisé `AddDestScreen` → `DestFormScreen` avec pré-remplissage pour l'édition, touche `e`, support `proxmox_qemu` dans le Select, colonne `VM/LXC ID` dans la table, validation inline
  Reason: impossible de modifier l'IP ou l'ID d'une destination existante
  Source: `DestFormScreen`, `action_edit`, `_on_dest_edited`

- `screens/remote_path.py`: browser Proxmox utilise maintenant `pct exec` (LXC) ou `qm guest exec` + JSON parsing (QEMU) pour lister les dossiers **dans la VM**, pas sur le nœud
  Reason: le browser SFTP montrait le filesystem du nœud Proxmox au lieu de celui de la VM/LXC
  Source: `_load_children_proxmox`, `_load_children_sftp`, `_is_proxmox`

- `screens/remote_path.py`: `_load_children` déplacé dans un worker thread dans `_build_tree`
  Reason: appel SSH bloquant sur le thread principal causait des timeouts silencieux
  Source: `_build_tree`

- Config HASS: `default_remote_path` mis à jour → `/mnt/data/supervisor/homeassistant`
  Reason: sur HAOS, `configuration.yaml` est à `/mnt/data/supervisor/homeassistant/`, pas à `/`
