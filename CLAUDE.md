# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo structure

```
RtxTools/
├── docs/                      Markdown documentation (sync to Obsidian)
│   ├── rtxcopy/               rtxcopy docs
│   └── network/               Network docs (per-device Internet cut-off, Servarr)
├── scripts/                   Standalone scripts (no build system)
│   ├── home-assistant/        HA YAML snippets (per-device Internet cut-off via pfSense API)
│   ├── guides/                Setup guides (NUT UPS, SSH keys)
│   ├── nipogi-shutdown.sh     Shutdown script for NIPoGi server
│   └── synology-shutdown.sh   Shutdown script for Synology NAS
├── shared/rtxlib/             Future shared lib (empty for now)
└── tools/
    ├── rtxcopy/               File-copy TUI tool (Python + Textual)
    └── homelab-dashboard/     Dashboard homelab — statut, inventaire, actions rapides (React + Express)
```

Each tool under `tools/` has its own dependencies:
- `rtxcopy/` — Python package, use `uv`
- `homelab-dashboard/` — Node.js/React app, use `npm install && npm run dev` (port 8160 Express + 5173 Vite)

Scripts under `scripts/` are standalone YAML/shell files — no build step required.

## rtxcopy — dev commands

```bash
cd tools/rtxcopy
uv sync             # install deps into .venv
uv run rtxcopy      # launch TUI
uv run rtxcopy manage  # destination manager
uv run pytest       # run tests
uv tool install .   # install globally as `rtxcopy`
```

Requires Python ≥ 3.11 and `uv` (`brew install uv`).

## rtxcopy — architecture

- `src/rtxcopy/config.py` — loads/saves `~/.config/rtxtools/rtxcopy/config.toml` (atomic write)
- `src/rtxcopy/destinations.py` — dataclasses: `NASDestination`, `ProxmoxLXCDestination`, `ProxmoxQEMUDestination`
- `src/rtxcopy/ssh_keys.py` — Ed25519 key generation + deployment via paramiko (no subprocess ssh-keygen)
- `src/rtxcopy/transfer.py` — paramiko SFTP for NAS; for Proxmox: SFTP to node `/tmp/` then `pct push`
- `src/rtxcopy/proxmox.py` — `pct push` / `qm guest exec` wrappers
- `src/rtxcopy/app.py` — Textual App root; screen flow: FilePicker → DestinationPicker → RemotePath → Progress
- `src/rtxcopy/screens/dest_manager.py` — destination CRUD + SSH key management modals

## Infrastructure (home network)

- TischNAS2: `192.168.10.5`
- TischNAS3: `192.168.10.3`
- Proxmox node: `192.168.10.2`

## Workflow git

Le repo est utilisé avec Claude Code CLI depuis deux machines (Mac et Mac mini) qui poussent toutes deux sur `main`.

- `git pull --rebase` en début de session et avant chaque push (historique linéaire, pas de merge commits)
- `git push` régulier, après chaque commit ou lot de commits terminé; ne pas laisser de commits non poussés
- En cas de conflit au rebase: résoudre sans force-push et prévenir l'utilisateur

## Documentation

`docs/` contains Markdown files intended for Obsidian sync. Use standard Markdown (no frontmatter required). Wikilinks (`[[file]]`) are fine for cross-references within `docs/`.
