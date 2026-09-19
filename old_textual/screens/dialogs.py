"""
ONYRA - Diálogo Modal: Partida Guardada Detectada
Permite al usuario elegir entre reanudar la partida guardada (.mca) o empezar una partida limpia desde cero.
"""

import datetime
import os
from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from rich.text import Text
from rich.style import Style
import renderer


class SaveStateDialog(ModalScreen[bool]):
    """
    Diálogo modal para gestionar partida guardada.
    Devuelve:
      - False: Reanudar partida (no borrar save)
      - True: Empezar de nuevo (borrar save previo)
      - None: Cancelar / Cerrar
    """
    BINDINGS = [
        ("escape", "cancel", "Cancelar"),
        ("q", "cancel", "Cancelar"),
        ("1", "resume", "Reanudar"),
        ("2", "restart", "Reiniciar"),
    ]

    def __init__(self, game: dict, save_file: str):
        super().__init__(id="dialog-screen")
        self.game = game
        self.save_file = save_file

    def compose(self) -> ComposeResult:
        mtime = os.path.getmtime(self.save_file)
        date_str = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y a las %H:%M")

        with Middle():
            with Center():
                with Vertical(id="dialog-container"):
                    yield Static("★  PARTIDA GUARDADA DETECTADA  ★", id="dialog-title")
                    yield Static(f"[ {self.game.get('clean_title', self.game.get('title'))} ]", id="dialog-game-name")
                    yield Static(f"Última instantánea: {date_str}", id="dialog-timestamp")

                    yield Button("▶  1. REANUDAR PARTIDA (Continuar donde lo dejaste)", id="btn-resume", classes="dialog-button")
                    yield Button("▶  2. EMPEZAR DE NUEVO (Reiniciar desde el inicio)", id="btn-restart", classes="dialog-button dialog-button-danger")

    def on_mount(self) -> None:
        self.query_one("#btn-resume", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-resume":
            self.dismiss(False)
        elif event.button.id == "btn-restart":
            self.dismiss(True)

    def action_resume(self) -> None:
        self.dismiss(False)

    def action_restart(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(None)
