from __future__ import annotations
from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Header, Input, Label
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TreeNode


def _fmt_size(size: int) -> str:
    for unit, threshold in (("Go", 1 << 30), ("Mo", 1 << 20), ("Ko", 1 << 10)):
        if size >= threshold:
            return f"{size / threshold:.1f} {unit}"
    return f"{size} o"


class SizedDirectoryTree(DirectoryTree):
    """DirectoryTree that appends file size to each file label."""

    def render_label(self, node: TreeNode[DirEntry], base_style: Style, style: Style) -> Text:
        text = super().render_label(node, base_style, style)
        if node.data and node.data.path:
            p = Path(node.data.path)
            if p.is_file():
                try:
                    size_str = _fmt_size(p.stat().st_size)
                    text.append(f"  {size_str}", style="dim")
                except OSError:
                    pass
        return text


class FilePickerScreen(Screen):
    """Pick one or more local files or folders to copy."""

    BINDINGS = [
        Binding("space", "toggle_select", "Sélectionner", priority=True),
        Binding("c", "confirm", "Copier", priority=True),
        Binding("p", "focus_path", "Changer chemin", priority=True),
        Binding("u", "go_up", "Dossier parent", priority=True),
        Binding("escape", "app.quit", "Quitter"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._selected: set[Path] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        start = Path(self.app.config.default_local_start_path).expanduser()  # type: ignore[attr-defined]
        yield Input(value=str(start), placeholder="Chemin de départ… (Entrée pour naviguer)", id="path_input")
        yield Label("", id="hint")
        yield SizedDirectoryTree(str(start), id="tree")
        yield Footer()

    def on_mount(self) -> None:
        self._update_hint()
        self.query_one("#tree", SizedDirectoryTree).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        p = Path(event.value).expanduser()
        if p.exists():
            self._navigate_to(p)
        else:
            self.query_one("#path_input", Input).styles.border = ("solid", "red")

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#path_input", Input).styles.border = None

    def _navigate_to(self, p: Path) -> None:
        tree = self.query_one("#tree", SizedDirectoryTree)
        tree.path = p
        self.query_one("#path_input", Input).value = str(p)
        tree.focus()

    def action_focus_path(self) -> None:
        inp = self.query_one("#path_input", Input)
        inp.focus()
        inp.cursor_position = len(inp.value)

    def action_go_up(self) -> None:
        tree = self.query_one("#tree", SizedDirectoryTree)
        current = Path(str(tree.path))
        parent = current.parent
        if parent != current:
            self._navigate_to(parent)

    def action_toggle_select(self) -> None:
        tree = self.query_one("#tree", SizedDirectoryTree)
        node = tree.cursor_node
        if node and node.data and node.data.path:
            p = Path(node.data.path)
            if p in self._selected:
                self._selected.discard(p)
                node.label = Text(p.name)
            else:
                self._selected.add(p)
                label = Text("✓ ", style="bold green")
                label.append(p.name)
                node.label = label
        self._update_hint()

    def _update_hint(self) -> None:
        count = len(self._selected)
        if count == 0:
            self.query_one("#hint", Label).update(
                "[dim]Space = sélectionner  C = copier  P = changer dossier  U = dossier parent[/]"
            )
        else:
            names = ", ".join(p.name for p in list(self._selected)[:3])
            suffix = f" (+{count - 3})" if count > 3 else ""
            self.query_one("#hint", Label).update(
                f"[green]{count} sélectionné(s):[/] {names}{suffix}  [dim]C = copier  U = parent[/]"
            )

    def action_confirm(self) -> None:
        if not self._selected:
            tree = self.query_one("#tree", SizedDirectoryTree)
            node = tree.cursor_node
            if node and node.data and node.data.path:
                self._selected.add(Path(node.data.path))

        if self._selected:
            self.app.selected_sources = list(self._selected)  # type: ignore[attr-defined]
            from rtxcopy.screens.destination_picker import DestinationPickerScreen
            self.app.push_screen(DestinationPickerScreen())
