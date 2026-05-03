from __future__ import annotations
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from rtxcopy.config import load_config, Config
from rtxcopy.destinations import Destination


class RtxCopyApp(App):
    """Main TUI application for rtxcopy."""

    TITLE = "rtxcopy"
    SUB_TITLE = "Copy files to NAS or Proxmox"
    CSS = """
    Screen { background: $surface; }
    """

    def __init__(self, start_screen: str = "main") -> None:
        super().__init__()
        self.start_screen = start_screen
        self.config: Config = load_config()
        self.selected_sources: list[Path] = []
        self.selected_destination: Destination | None = None
        self.remote_path: str = ""

    def on_mount(self) -> None:
        if self.start_screen == "manage":
            from rtxcopy.screens.dest_manager import DestManagerScreen
            self.push_screen(DestManagerScreen())
        else:
            from rtxcopy.screens.file_picker import FilePickerScreen
            self.push_screen(FilePickerScreen())
