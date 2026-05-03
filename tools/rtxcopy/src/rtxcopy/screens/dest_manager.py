from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Select
from textual.containers import Vertical, Horizontal

from rtxcopy.config import save_config
from rtxcopy.destinations import (
    Destination, NASDestination, ProxmoxLXCDestination, ProxmoxQEMUDestination,
)


class DestManagerScreen(Screen):
    """CRUD screen for managing destinations."""

    BINDINGS = [
        Binding("a", "add", "Ajouter"),
        Binding("e", "edit", "Éditer"),
        Binding("d", "delete", "Supprimer"),
        Binding("k", "manage_key", "SSH Key"),
        Binding("escape", "app.pop_screen", "Retour"),
        Binding("q", "app.quit", "Quitter"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Destinations[/]  [dim]a=ajouter  e=éditer  d=supprimer  k=SSH key[/]")
        yield DataTable(id="dest_table")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#dest_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Nom", "Type", "Host / IP", "VM/LXC ID", "Clé SSH")
        for dest in self.app.config.destinations:  # type: ignore[attr-defined]
            host = getattr(dest, "host", None) or getattr(dest, "node_host", "")
            vmid = str(getattr(dest, "vmid", "—"))
            key_ok = "[green]✓[/]" if dest.key_path.exists() else "[red]✗[/]"
            table.add_row(dest.name, dest.type, host, vmid, key_ok)

    def _selected_dest(self) -> Destination | None:
        table = self.query_one("#dest_table", DataTable)
        row = table.cursor_row
        dests = self.app.config.destinations  # type: ignore[attr-defined]
        return dests[row] if 0 <= row < len(dests) else None

    def action_add(self) -> None:
        self.app.push_screen(DestFormScreen(), self._on_dest_added)

    def _on_dest_added(self, dest: Destination | None) -> None:
        if dest:
            self.app.config.destinations.append(dest)  # type: ignore[attr-defined]
            save_config(self.app.config)  # type: ignore[attr-defined]
            self._refresh_table()

    def action_edit(self) -> None:
        dest = self._selected_dest()
        if dest:
            table = self.query_one("#dest_table", DataTable)
            row = table.cursor_row
            self.app.push_screen(DestFormScreen(existing=dest), lambda d: self._on_dest_edited(row, d))

    def _on_dest_edited(self, row: int, dest: Destination | None) -> None:
        if dest:
            self.app.config.destinations[row] = dest  # type: ignore[attr-defined]
            save_config(self.app.config)  # type: ignore[attr-defined]
            self._refresh_table()

    def action_delete(self) -> None:
        dest = self._selected_dest()
        if dest:
            table = self.query_one("#dest_table", DataTable)
            self.app.config.destinations.pop(table.cursor_row)  # type: ignore[attr-defined]
            save_config(self.app.config)  # type: ignore[attr-defined]
            self._refresh_table()

    def action_manage_key(self) -> None:
        dest = self._selected_dest()
        if dest:
            self.app.push_screen(KeyManagerScreen(dest), lambda _: self._refresh_table())


class DestFormScreen(ModalScreen):
    """Add or edit a destination — pre-filled when editing."""

    BINDINGS = [Binding("escape", "dismiss_none", "Annuler")]

    def __init__(self, existing: Destination | None = None) -> None:
        super().__init__()
        self.existing = existing

    def compose(self) -> ComposeResult:
        ex = self.existing
        is_proxmox = ex is not None and ex.type in ("proxmox_lxc", "proxmox_qemu")

        title = "[bold]Modifier la destination[/]" if ex else "[bold]Nouvelle destination[/]"

        with Vertical(id="dialog"):
            yield Label(title)
            yield Select(
                [
                    ("NAS (SSH/SFTP)", "nas"),
                    ("Proxmox LXC", "proxmox_lxc"),
                    ("Proxmox QEMU/VM", "proxmox_qemu"),
                ],
                prompt="Type",
                id="dest_type",
                value=ex.type if ex else Select.BLANK,
            )
            yield Input(
                placeholder="Nom (ex. TischNAS2)",
                id="name",
                value=ex.name if ex else "",
            )
            yield Input(
                placeholder="Host / IP",
                id="host",
                value=(getattr(ex, "host", None) or getattr(ex, "node_host", "")) if ex else "",
            )
            yield Input(
                placeholder="Port SSH (défaut 22)",
                id="port",
                value=str((getattr(ex, "port", None) or getattr(ex, "node_port", 22)) if ex else 22),
            )
            yield Input(
                placeholder="Nom d'utilisateur",
                id="username",
                value=(getattr(ex, "username", None) or getattr(ex, "node_username", "")) if ex else "",
            )
            yield Input(
                placeholder="Chemin distant par défaut",
                id="remote_path",
                value=ex.default_remote_path if ex else "/",
            )
            yield Input(
                placeholder="ID LXC ou VM (Proxmox uniquement)",
                id="vmid",
                value=str(ex.vmid) if ex and hasattr(ex, "vmid") else "",
            )
            with Horizontal():
                label = "Enregistrer" if ex else "Ajouter"
                yield Button(label, variant="primary", id="btn_save")
                yield Button("Annuler", id="btn_cancel")
            yield Label("", id="error_msg")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cancel":
            self.dismiss(None)
            return

        dest_type = self.query_one("#dest_type", Select).value
        name = self.query_one("#name", Input).value.strip()
        host = self.query_one("#host", Input).value.strip()
        port_str = self.query_one("#port", Input).value.strip()
        username = self.query_one("#username", Input).value.strip()
        remote_path = self.query_one("#remote_path", Input).value.strip() or "/"
        vmid_str = self.query_one("#vmid", Input).value.strip()

        if not name or not host or not username:
            self.query_one("#error_msg", Label).update("[red]Nom, host et username sont requis.[/]")
            return

        port = int(port_str) if port_str.isdigit() else 22

        from rtxcopy.ssh_keys import key_path_for_dest
        # Keep existing key path when editing; assign new one when adding
        if self.existing and self.existing.name == name:
            key_path = str(self.existing.ssh_key_path)
        else:
            key_path = str(key_path_for_dest(name))

        if dest_type == "nas":
            dest: Destination = NASDestination(
                type="nas", name=name, host=host, port=port,
                username=username, ssh_key_path=key_path,
                default_remote_path=remote_path,
            )
        elif dest_type in ("proxmox_lxc", "proxmox_qemu"):
            if not vmid_str.isdigit():
                self.query_one("#error_msg", Label).update("[red]VM/LXC ID doit être un entier.[/]")
                return
            vmid = int(vmid_str)
            cls = ProxmoxLXCDestination if dest_type == "proxmox_lxc" else ProxmoxQEMUDestination
            dest = cls(
                type=dest_type, name=name, node_host=host, node_port=port,
                node_username=username, ssh_key_path=key_path,
                vmid=vmid, default_remote_path=remote_path,
            )
        else:
            self.query_one("#error_msg", Label).update("[red]Sélectionne un type.[/]")
            return

        self.dismiss(dest)


class KeyManagerScreen(ModalScreen):
    """Manage SSH key for a destination."""

    def __init__(self, dest: Destination) -> None:
        super().__init__()
        self.dest = dest

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"[bold]Clé SSH — {self.dest.name}[/]")
            key_exists = self.dest.key_path.exists()
            status = "[green]Clé présente[/]" if key_exists else "[red]Aucune clé[/]"
            yield Label(status, id="key_status")
            with Horizontal():
                yield Button("Générer nouvelle clé", id="btn_gen", variant="primary")
                yield Button("Déployer sur le remote", id="btn_deploy")
                yield Button("Fermer", id="btn_close")
            yield Label("", id="msg")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_close":
            self.dismiss(None)
        elif event.button.id == "btn_gen":
            from rtxcopy.ssh_keys import generate_keypair
            priv, _ = generate_keypair(self.dest.name)
            self.query_one("#key_status", Label).update("[green]Clé présente[/]")
            self.query_one("#msg", Label).update(f"[green]Générée :[/] {priv}")
        elif event.button.id == "btn_deploy":
            self.app.push_screen(DeployKeyScreen(self.dest), lambda _: None)


class DeployKeyScreen(ModalScreen):
    """Prompt for password to deploy SSH key."""

    def __init__(self, dest: Destination) -> None:
        super().__init__()
        self.dest = dest

    def compose(self) -> ComposeResult:
        host = getattr(self.dest, "host", None) or getattr(self.dest, "node_host", "")
        username = getattr(self.dest, "username", None) or getattr(self.dest, "node_username", "")
        with Vertical(id="dialog"):
            yield Label(f"Déployer la clé sur [bold]{host}[/] en tant que [bold]{username}[/]")
            yield Input(placeholder="Mot de passe (usage unique)", password=True, id="password")
            with Horizontal():
                yield Button("Déployer", variant="primary", id="btn_deploy")
                yield Button("Annuler", id="btn_cancel")
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
            self.query_one("#msg", Label).update("[green]Clé déployée avec succès ![/]")
        except Exception as e:
            self.query_one("#msg", Label).update(f"[red]Erreur : {e}[/]")
