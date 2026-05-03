from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import paramiko
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, LoadingIndicator, Tree
from textual.widgets._tree import TreeNode
from textual.containers import Horizontal, Vertical


class FavoritesModal(ModalScreen):
    """Quick picker for favorite remote paths."""

    BINDINGS = [Binding("escape", "dismiss_none", "Fermer")]

    def __init__(self, dest_name: str, favorites: list[str]) -> None:
        super().__init__()
        self.dest_name = dest_name
        self.favorites = favorites

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"[bold]Favoris — {self.dest_name}[/]")
            if self.favorites:
                yield ListView(*[ListItem(Label(f"⭐ {p}")) for p in self.favorites], id="fav_list")
            else:
                yield Label("[dim]Aucun favori. Appuie sur F dans le browser pour en ajouter.[/]")
            yield Button("Fermer", id="btn_close")

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        self.dismiss(self.favorites[idx])


class RemotePathScreen(Screen):
    """Browse the remote filesystem and pick a destination folder."""

    BINDINGS = [
        Binding("enter", "select_node", "Ouvrir", priority=True),
        Binding("c", "confirm", "Copier ici", priority=True),
        Binding("f", "toggle_favorite", "⭐ Favori", priority=True),
        Binding("F", "open_favorites", "Voir favoris", priority=True),
        Binding("escape", "app.pop_screen", "Retour"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._sftp: paramiko.SFTPClient | None = None
        self._ssh: paramiko.SSHClient | None = None
        self._current_path: str = "/"
        self._is_proxmox: bool = False
        self._vmid: int = 0
        self._vm_type: str = ""  # "lxc" or "qemu"

    def compose(self) -> ComposeResult:
        dest = self.app.selected_destination  # type: ignore[attr-defined]
        default = getattr(dest, "default_remote_path", "/")
        yield Header()
        with Horizontal(id="top_bar"):
            yield Label(f"[bold]{dest.name}[/]", id="dest_label")
            yield Label("", id="fav_indicator")
        yield Label("", id="current_path")
        yield Input(value=default, placeholder="Chemin distant…", id="path_input")
        yield LoadingIndicator(id="loader")
        yield Tree("Connexion…", id="remote_tree")
        yield Button("Copier ici →", variant="primary", id="btn_copy", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#remote_tree", Tree).display = False
        self.run_worker(self._connect_and_load_root, thread=True)

    # ── Connection ────────────────────────────────────────────────────────────

    def _connect_and_load_root(self) -> None:
        from rtxcopy.destinations import ProxmoxLXCDestination, ProxmoxQEMUDestination
        dest = self.app.selected_destination  # type: ignore[attr-defined]

        self._is_proxmox = isinstance(dest, (ProxmoxLXCDestination, ProxmoxQEMUDestination))
        if self._is_proxmox:
            self._vmid = dest.vmid
            self._vm_type = "lxc" if isinstance(dest, ProxmoxLXCDestination) else "qemu"

        host = getattr(dest, "host", None) or getattr(dest, "node_host")
        port = getattr(dest, "port", None) or getattr(dest, "node_port", 22)
        username = getattr(dest, "username", None) or getattr(dest, "node_username")

        try:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh.connect(host, port=port, username=username,
                              key_filename=str(dest.key_path), timeout=10)

            if not self._is_proxmox:
                try:
                    self._sftp = self._ssh.open_sftp()
                except Exception:
                    self.app.call_from_thread(self._show_sftp_unavailable)
                    return

            start = getattr(dest, "default_remote_path", "/")
            self.app.call_from_thread(self._build_tree, start)
        except Exception as e:
            self.app.call_from_thread(self._show_error, str(e))

    def _build_tree(self, start_path: str) -> None:
        """Called on main thread — only sets up the root node, children load in a worker."""
        self._current_path = start_path
        tree = self.query_one("#remote_tree", Tree)
        tree.clear()
        tree.root.set_label(start_path)
        tree.root.data = start_path
        self.query_one("#loader", LoadingIndicator).display = False
        tree.display = True
        tree.focus()
        self._update_path_label(start_path)
        self.query_one("#btn_copy", Button).disabled = False
        # Load root children in a worker to avoid blocking the main thread
        self.run_worker(
            lambda: self.app.call_from_thread(self._load_children, tree.root, start_path),
            thread=True,
        )

    def _load_children(self, node: TreeNode, path: str) -> None:
        if self._is_proxmox:
            self._load_children_proxmox(node, path)
        else:
            self._load_children_sftp(node, path)

    def _load_children_sftp(self, node: TreeNode, path: str) -> None:
        if self._sftp is None:
            return
        try:
            entries = self._sftp.listdir_attr(path)
        except OSError:
            return
        entries.sort(key=lambda e: (not self._is_dir_sftp(e), e.filename.lower()))
        for entry in entries:
            if entry.filename.startswith("."):
                continue
            full = str(PurePosixPath(path) / entry.filename)
            is_dir = self._is_dir_sftp(entry)
            label = f"📁 {entry.filename}" if is_dir else f"📄 {entry.filename}"
            node.add(label, data=full, allow_expand=is_dir)

    def _load_children_proxmox(self, node: TreeNode, path: str) -> None:
        """List entries inside the LXC/VM using pct exec or qm guest exec."""
        if self._ssh is None:
            return
        import json, shlex
        safe_path = shlex.quote(path)
        try:
            if self._vm_type == "lxc":
                cmd = f"pct exec {self._vmid} -- ls -1p {safe_path} 2>/dev/null"
                _, stdout, _ = self._ssh.exec_command(cmd)
                lines = stdout.read().decode().splitlines()
            else:
                cmd = f"qm guest exec {self._vmid} -- ls -1p {safe_path}"
                _, stdout, _ = self._ssh.exec_command(cmd)
                raw = stdout.read().decode().strip()
                data = json.loads(raw)
                lines = data.get("out-data", "").splitlines()
        except Exception:
            return

        dirs, files = [], []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("."):
                continue
            if line.endswith("/"):
                dirs.append(line.rstrip("/"))
            else:
                files.append(line)

        for name in sorted(dirs, key=str.lower):
            full = str(PurePosixPath(path) / name)
            node.add(f"📁 {name}", data=full, allow_expand=True)
        for name in sorted(files, key=str.lower):
            full = str(PurePosixPath(path) / name)
            node.add(f"📄 {name}", data=full, allow_expand=False)

    @staticmethod
    def _is_dir_sftp(entry: Any) -> bool:
        import stat
        return entry.st_mode is not None and stat.S_ISDIR(entry.st_mode)

    def _show_error(self, message: str) -> None:
        self.query_one("#loader", LoadingIndicator).display = False
        self.query_one("#current_path", Label).update(f"[red]Erreur de connexion : {message}[/]")
        self.query_one("#btn_copy", Button).disabled = False

    def _show_sftp_unavailable(self) -> None:
        self.query_one("#loader", LoadingIndicator).display = False
        self.query_one("#current_path", Label).update(
            "[yellow]SFTP non disponible sur ce NAS.[/]\n"
            "[dim]Sur Synology : Panneau de configuration → Services de fichiers → FTP → Activer le service SFTP[/]\n"
            "Tu peux quand même taper le chemin manuellement ci-dessus."
        )
        self.query_one("#btn_copy", Button).disabled = False
        self.query_one("#path_input", Input).focus()

    # ── Tree interaction ──────────────────────────────────────────────────────

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        node = event.node
        if node.data and not node.children:
            self.run_worker(
                lambda n=node, p=node.data: self.app.call_from_thread(self._load_children, n, p),
                thread=True,
            )

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data:
            self._current_path = event.node.data
            self._update_path_label(event.node.data)

    def _update_path_label(self, path: str) -> None:
        self.query_one("#current_path", Label).update(f"[cyan]{path}[/]")
        self.query_one("#path_input", Input).value = path
        self._refresh_fav_indicator(path)

    def _refresh_fav_indicator(self, path: str) -> None:
        dest = self.app.selected_destination  # type: ignore[attr-defined]
        config = self.app.config  # type: ignore[attr-defined]
        if config.is_favorite(dest.name, path):
            self.query_one("#fav_indicator", Label).update("[yellow]⭐ Favori  [dim](F pour retirer)[/]")
        else:
            self.query_one("#fav_indicator", Label).update("[dim](f pour ajouter aux favoris  F pour voir les favoris)[/]")

    def action_select_node(self) -> None:
        tree = self.query_one("#remote_tree", Tree)
        node = tree.cursor_node
        if node and node.data:
            self._current_path = node.data
            self._update_path_label(node.data)
            if node.allow_expand:
                node.toggle()

    # ── Favorites ─────────────────────────────────────────────────────────────

    def action_toggle_favorite(self) -> None:
        path = self._current_path
        dest = self.app.selected_destination  # type: ignore[attr-defined]
        config = self.app.config  # type: ignore[attr-defined]
        if config.is_favorite(dest.name, path):
            config.remove_favorite(dest.name, path)
        else:
            config.add_favorite(dest.name, path)
        from rtxcopy.config import save_config
        save_config(config)
        self._refresh_fav_indicator(path)

    def action_open_favorites(self) -> None:
        dest = self.app.selected_destination  # type: ignore[attr-defined]
        config = self.app.config  # type: ignore[attr-defined]
        favs = config.get_favorites(dest.name)
        self.app.push_screen(FavoritesModal(dest.name, favs), self._on_favorite_selected)

    def _on_favorite_selected(self, path: str | None) -> None:
        if path:
            self._current_path = path
            self._update_path_label(path)
            # Navigate the tree to this path if SFTP is available
            if self._sftp:
                self.run_worker(
                    lambda p=path: self.app.call_from_thread(self._navigate_to, p),
                    thread=True,
                )

    def _navigate_to(self, path: str) -> None:
        """Rebuild the tree rooted at the given path."""
        self._build_tree(path)

    # ── Confirm ───────────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._current_path = event.value.strip()
        self._update_path_label(self._current_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_copy":
            self.action_confirm()

    def action_confirm(self) -> None:
        path = self.query_one("#path_input", Input).value.strip() or self._current_path
        if not path:
            return
        self.app.remote_path = path  # type: ignore[attr-defined]
        self._close_sftp()
        from rtxcopy.screens.progress import ProgressScreen
        self.app.push_screen(ProgressScreen())

    def _close_sftp(self) -> None:
        for obj in (self._sftp, self._ssh):
            if obj:
                try:
                    obj.close()
                except Exception:
                    pass

    def on_unmount(self) -> None:
        self._close_sftp()
