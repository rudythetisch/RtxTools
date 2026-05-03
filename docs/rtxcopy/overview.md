# rtxcopy — Architecture

TUI tool (Python + Textual) to copy files from any machine to NAS or Proxmox LXC/VM over SSH.

## Module map

```
src/rtxcopy/
├── __main__.py       click CLI entry point (rtxcopy, rtxcopy manage, rtxcopy keygen)
├── app.py            Textual App — owns screen stack + global state
├── config.py         load/save ~/.config/rtxtools/rtxcopy/config.toml (atomic write)
├── destinations.py   NASDestination / ProxmoxLXCDestination / ProxmoxQEMUDestination
├── ssh_keys.py       Ed25519 key generation, import, remote deployment
├── transfer.py       paramiko SFTP upload (NAS) + Proxmox temp-upload + pct push
├── proxmox.py        pct push / qm guest exec wrappers
└── screens/
    ├── file_picker.py         DirectoryTree multi-select
    ├── destination_picker.py  ListView of configured destinations
    ├── remote_path.py         Input for remote path
    ├── progress.py            Worker thread + ProgressBar
    └── dest_manager.py        CRUD DataTable + SSH key management modals
```

## TUI flow

```
FilePicker → DestinationPicker → RemotePath → Progress → (back to FilePicker)
```

`rtxcopy manage` jumps directly to `DestManagerScreen`.

## Key design decisions

- **paramiko over rsync**: progress callbacks are clean byte-level API vs fragile rsync stdout parsing
- **Ed25519 keys via `cryptography` lib**: no subprocess `ssh-keygen`, easier testing
- **Proxmox strategy**: SSH to node → SFTP upload to `/tmp/` → `pct push` into container. No REST API needed.
- **Config**: TOML array-of-tables, `type` discriminator field, no secrets stored (only key paths)
- **`call_from_thread`**: must use `self.app.call_from_thread()` — not available on Screen in Textual 8.x
- **SSH key deploy**: single compound command via stdin to avoid `MaxSessions 1` on Synology
- **SFTP unavailable**: graceful fallback to manual path input with Synology-specific guidance
- **Favorites**: stored per destination in `config.toml` under `[favorites]`, managed with `f`/`F` in remote browser
- **Proxmox browser**: uses `pct exec <vmid> -- ls -1p` (LXC) or `qm guest exec <vmid> -- ls -1p` + JSON parse (QEMU) — lists files inside the container/VM, not on the node
- **HAOS config path**: `/mnt/data/supervisor/homeassistant/` (not `/config` or `/root`)
- **`_build_tree` threading**: `_load_children` runs in a worker — never block the main asyncio thread with SSH calls
