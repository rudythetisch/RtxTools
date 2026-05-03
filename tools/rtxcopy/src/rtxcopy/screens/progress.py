from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar
from textual.worker import Worker, get_current_worker

from rtxcopy.transfer import TransferJob, transfer


class ProgressScreen(Screen):
    """Show transfer progress."""

    BINDINGS = [
        Binding("q", "app.quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Transferring...", id="status")
        yield ProgressBar(total=100, show_eta=True, id="progress")
        yield Button("Done", variant="success", id="btn_done", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._do_transfer, thread=True)

    def _do_transfer(self) -> None:
        worker = get_current_worker()
        job = TransferJob(
            sources=self.app.selected_sources,  # type: ignore[attr-defined]
            destination=self.app.selected_destination,  # type: ignore[attr-defined]
            remote_path=self.app.remote_path,  # type: ignore[attr-defined]
        )

        def _cb(sent: int, total: int) -> None:
            if total > 0:
                pct = int(sent / total * 100)
                self.app.call_from_thread(self._update_progress, pct, sent, total)

        try:
            transfer(job, progress_callback=_cb)
            self.app.call_from_thread(self._on_success)
        except Exception as e:
            self.app.call_from_thread(self._on_error, str(e))

    def _update_progress(self, pct: int, sent: int, total: int) -> None:
        bar = self.query_one("#progress", ProgressBar)
        bar.update(progress=pct)
        label = self.query_one("#status", Label)
        label.update(f"Transferring... {sent // 1024}KB / {total // 1024}KB")

    def _on_success(self) -> None:
        self.query_one("#status", Label).update("[green]Transfer complete![/]")
        self.query_one("#progress", ProgressBar).update(progress=100)
        self.query_one("#btn_done", Button).disabled = False

    def _on_error(self, message: str) -> None:
        self.query_one("#status", Label).update(f"[red]Error: {message}[/]")
        self.query_one("#btn_done", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_done":
            self.app.pop_screen()
            self.app.pop_screen()
            self.app.pop_screen()
