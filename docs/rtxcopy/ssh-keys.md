# rtxcopy — SSH Key Management

Each destination has its own dedicated Ed25519 key pair stored in:

```
~/.config/rtxtools/rtxcopy/keys/<dest_name>/
├── id_ed25519      (chmod 600)
└── id_ed25519.pub  (chmod 644)
```

## Generate a new key

In the TUI: `rtxcopy manage` → select destination → `k` → "Generate new key"

CLI: `rtxcopy keygen <dest_name>`

## Deploy key to remote

In the TUI: `rtxcopy manage` → select destination → `k` → "Deploy to remote"

You'll be prompted for the remote password **once**. The public key is appended to `~/.ssh/authorized_keys` on the remote. The password is never stored.

## Proxmox note

The key is deployed to the **Proxmox node** only. Access to LXC containers uses `pct push` (runs as root on the node) — no separate key inside the container is needed.

## Import an existing key

Place your private key anywhere, then in `dest_manager.py` choose "Import existing key" and navigate to it. The key is copied into the managed keys directory.
