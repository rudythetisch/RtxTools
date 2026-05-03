# rtxcopy — Usage

## Copy files

```bash
rtxcopy
```

1. Navigate the local file tree with arrow keys
2. Press `Space` to select files/folders (multiple allowed)
3. Press `Enter` to confirm selection
4. Choose a destination from the list
5. Enter or confirm the remote path
6. Watch the transfer progress bar

## Manage destinations

```bash
rtxcopy manage
```

| Key | Action |
|-----|--------|
| `a` | Add destination |
| `d` | Delete selected |
| `k` | Manage SSH key (generate / deploy) |
| `Esc` | Back |

## Generate a key without TUI

```bash
rtxcopy keygen TischNAS2
```

## Dry run (no actual transfer)

```bash
rtxcopy --dry-run   # (coming soon)
```
