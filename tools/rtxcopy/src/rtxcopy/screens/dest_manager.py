from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, Select
)
from textual.containers import Vertical, Horizontal

from rtxcopy.config import save_config
from rtxcopy.destinations import NASDestination, ProxmoxLXCDestination, destination_to_dict


class DestManagerScreen(Screen):
    """CRUD screen for managing destinations."""

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("d", "delete", "Delete"),
        Binding("k", "manage_key", "SSH Key"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Destinations[/]  [dim]a=add  d=delete  k=SSH key[/]")
        yield DataTable(id="dest_table")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#dest_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Type", "Host", "Key")
        for dest in self.app.config.destinations:  # type: ignore[attr-defined]
            host = getattr(dest, "host", None) or getattr(dest, "node_host", "")
            key_ok = "✓" if dest.key_path.exists() else "✗"
            table.add_row(dest.name, dest.type, host, key_ok)

    def action_add(self) -> None:
        self.app.push_screen(AddDestScreen(), self._on_dest_added)

    def _on_dest_added(self, dest) -> None:
        if dest:
            self.app.config.destinations.append(dest)  # type: ignore[attr-defined]
            save_config(self.app.config)  # type: ignore[attr-defined]
            self._refresh_table()

    def action_delete(self) -> None:
        table = self.query_one("#dest_table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self.app.config.destinations):  # type: ignore[attr-defined]
            self.app.config.destinations.pop(row)  # type: ignore[attr-defined]
            save_config(self.app.config)  # type: ignore[attr-defined]
            self._refresh_table()

    def action_manage_key(self) -> None:
        table = self.query_one("#dest_table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self.app.config.destinations):  # type: ignore[attr-defined]
            dest = self.app.config.destinations[row]  # type: ignore[attr-defined]
            self.app.push_screen(KeyManagerScreen(dest), lambda _: self._refresh_table())


class AddDestScreen(ModalScreen):
    """Modal form to add a new destination."""

    BINDINGS = [Binding("escape", "dismiss_none", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("[bold]Add Destination[/]")
            yield Select(
                [("NAS (SSH/SFTP)", "nas"), ("Proxmox LXC", "proxmox_lxc")],
                prompt="Type",
                id="dest_type",
            )
            yield Input(placeholder="Name (e.g. TischNAS2)", id="name")
            yield Input(placeholder="Host / IP", id="host")
            yield Input(placeholder="Port (default 22)", id="port", value="22")
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Default remote path", id="remote_path", value="/")
            yield Input(placeholder="VM ID (Proxmox only)", id="vmid")
            with Horizontal():
                yield Button("Add", variant="primary", id="btn_add")
                yield Button("Cancel", id="btn_cancel")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
            return
        dest_type = self.query_one("#dest_type", Select).value
        name = self.query_one("#name", Input).value.strip()
        host = self.query_one("#host", Input).value.strip()
        port = int(self.query_one("#port", Input).value or "22")
        username = self.query_one("#username", Input).value.strip()
        remote_path = self.query_one("#remote_path", Input).value.strip() or "/"
        vmid_str = self.query_one("#vmid", Input).value.strip()

        if not name or not host or not username:
            return

        from rtxcopy.ssh_keys import key_path_for_dest
        key_path = str(key_path_for_dest(name))

        if dest_type == "nas":
            dest = NASDestination(
                type="nas", name=name, host=host, port=port,
                username=username, ssh_key_path=key_path,
                default_remote_path=remote_path,
            )
        else:
            vmid = int(vmid_str) if vmid_str else 0
            dest = ProxmoxLXCDestination(
                type="proxmox_lxc", name=name, node_host=host, node_port=port,
                node_username=username, ssh_key_path=key_path, vmid=vmid,
                default_remote_path=remote_path,
            )
        self.dismiss(dest)


class KeyManagerScreen(ModalScreen):
    """Manage SSH key for a destination."""

    def __init__(self, dest) -> None:
        super().__init__()
        self.dest = dest

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"[bold]SSH Key — {self.dest.name}[/]")
            key_exists = self.dest.key_path.exists()
            status = "[green]Key exists[/]" if key_exists else "[red]No key[/]"
            yield Label(status, id="key_status")
            with Horizontal():
                yield Button("Generate new key", id="btn_gen", variant="primary")
                yield Button("Deploy to remote", id="btn_deploy")
                yield Button("Close", id="btn_close")
            yield Label("", id="msg")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close":
            self.dismiss(None)
        elif event.button.id == "btn_gen":
            from rtxcopy.ssh_keys import generate_keypair
            priv, pub = generate_keypair(self.dest.name)
            self.query_one("#key_status", Label).update("[green]Key exists[/]")
            self.query_one("#msg", Label).update(f"[green]Generated:[/] {priv}")
        elif event.button.id == "btn_deploy":
            self.app.push_screen(DeployKeyScreen(self.dest), lambda _: None)


class DeployKeyScreen(ModalScreen):
    """Prompt for password to deploy SSH key."""

    def __init__(self, dest) -> None:
        super().__init__()
        self.dest = dest

    def compose(self) -> ComposeResult:
        host = getattr(self.dest, "host", None) or getattr(self.dest, "node_host", "")
        username = getattr(self.dest, "username", None) or getattr(self.dest, "node_username", "")
        with Vertical(id="dialog"):
            yield Label(f"Deploy key to [bold]{host}[/] as [bold]{username}[/]")
            yield Input(placeholder="Password (one-time)", password=True, id="password")
            with Horizontal():
                yield Button("Deploy", variant="primary", id="btn_deploy")
                yield Button("Cancel", id="btn_cancel")
            yield Label("", id="msg")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
            return
        password = self.query_one("#password", Input).value
        host = getattr(self.dest, "host", None) or getattr(self.dest, "node_host", "")
        port = getattr(self.dest, "port", None) or getattr(self.dest, "node_port", 22)
        username = getattr(self.dest, "username", None) or getattr(self.dest, "node_username", "")
        try:
            from rtxcopy.ssh_keys import deploy_public_key
            deploy_public_key(host, port, username, password, self.dest.name)
            self.query_one("#msg", Label).update("[green]Key deployed successfully![/]")
        except Exception as e:
            self.query_one("#msg", Label).update(f"[red]Error: {e}[/]")
