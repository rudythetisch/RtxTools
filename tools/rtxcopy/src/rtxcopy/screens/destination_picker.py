from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView

from rtxcopy.destinations import NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination


_TYPE_BADGE = {
    "nas": "[bold cyan]NAS[/]",
    "proxmox_lxc": "[bold yellow]LXC[/]",
    "proxmox_qemu": "[bold magenta]VM[/]",
}


class DestinationPickerScreen(Screen):
    """Pick a configured remote destination."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        destinations = self.app.config.destinations  # type: ignore[attr-defined]
        if not destinations:
            yield Label("[red]No destinations configured. Run `rtxcopy manage` to add one.[/]")
        else:
            items = []
            for dest in destinations:
                badge = _TYPE_BADGE.get(dest.type, dest.type)
                host = getattr(dest, "host", None) or getattr(dest, "node_host", "")
                items.append(ListItem(Label(f"{badge}  {dest.name}  [dim]{host}[/]")))
            yield ListView(*items)
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        dest = self.app.config.destinations[idx]  # type: ignore[attr-defined]
        self.app.selected_destination = dest  # type: ignore[attr-defined]
        from rtxcopy.screens.remote_path import RemotePathScreen
        self.app.push_screen(RemotePathScreen())
