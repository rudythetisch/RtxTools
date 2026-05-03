# rtxcopy — Installation

## Prerequisites

- macOS (or Linux)
- [`uv`](https://docs.astral.sh/uv/): `brew install uv`
- Python 3.11+ (uv manages this automatically)

## Install

```bash
cd tools/rtxcopy
uv sync
uv tool install .
```

After install, `rtxcopy` is available globally.

## Development mode

```bash
cd tools/rtxcopy
uv sync
uv run rtxcopy          # launch TUI
uv run rtxcopy manage   # destination manager
uv run pytest           # run tests
```

## Config location

`~/.config/rtxtools/rtxcopy/config.toml` — created automatically on first run.

SSH keys: `~/.config/rtxtools/rtxcopy/keys/<dest_name>/id_ed25519`
