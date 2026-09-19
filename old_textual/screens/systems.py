"""
ONYRA - Pantalla 2: Selector de Sistemas
Muestra dos filas de logos oficiales monocromos centradas, con recuadro redondeado neón,
indicador de sistema y conteo de juegos.
"""

from typing import List, Dict, Any
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Middle, Vertical
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text
from rich.style import Style

import data
import renderer


class SystemCard(Vertical):
    """Tarjeta individual que contiene el logo del sistema y su etiqueta."""
    def __init__(self, sys_info: Dict[str, Any], is_selected: bool = False):
        super().__init__(classes="system-card" + (" selected" if is_selected else ""))
        self.sys_info = sys_info
        self.is_selected = is_selected

    def compose(self) -> ComposeResult:
        yield Static(id=f"logo-{self.sys_info['id']}", classes="system-logo-widget")
        yield Static(self.sys_info["name"].upper(), classes="system-name-label")

    def on_mount(self) -> None:
        self.update_appearance(self.is_selected)

    def update_appearance(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

        logo_widget = self.query_one(f"#logo-{self.sys_info['id']}", Static)
        rendered_logo = renderer.render_system_logo(
            self.sys_info["id"],
            selected=selected,
            target_lines=4,
            max_cols=22,
            bg=renderer.COLOR_PANEL,
        )
        logo_widget.update(rendered_logo)


class SystemsScreen(Screen):
    BINDINGS = [
        ("left", "cursor_left", "Anterior"),
        ("right", "cursor_right", "Siguiente"),
        ("up", "cursor_up", "Fila Arriba"),
        ("down", "cursor_down", "Fila Abajo"),
        ("enter", "select_system", "Entrar"),
        ("escape", "exit_app", "Salir"),
        ("q", "exit_app", "Salir"),
    ]

    def __init__(self):
        super().__init__(id="systems-screen")
        self.systems = data.get_active_systems()
        # Organizar en 2 filas
        self.rows: List[List[Dict[str, Any]]] = [[], []]
        for s in self.systems:
            r = min(1, s.get("row", 0))
            self.rows[r].append(s)

        # Si una fila quedó vacía, balancear
        if not self.rows[1] and len(self.rows[0]) > 2:
            mid = (len(self.rows[0]) + 1) // 2
            self.rows[1] = self.rows[0][mid:]
            self.rows[0] = self.rows[0][:mid]

        # Cargar último sistema seleccionado
        state = data.load_state()
        last_sys = state.get("last_system_id")
        self.cur_row = 0
        self.cur_col = 0

        for r_idx, row in enumerate(self.rows):
            for c_idx, s in enumerate(row):
                if s["id"] == last_sys:
                    self.cur_row = r_idx
                    self.cur_col = c_idx
                    break

    def compose(self) -> ComposeResult:
        # Cabecera pequeña
        with Horizontal(classes="header-bar"):
            header_txt = Text("O  N  Y  R  A", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            yield Static(header_txt, classes="header-title")

        # Contenedor central con 2 filas
        with Middle(id="systems-container"):
            with Center():
                with Vertical(id="systems-grid"):
                    for r_idx, row in enumerate(self.rows):
                        with Horizontal(classes="system-row", id=f"row-{r_idx}"):
                            for c_idx, s in enumerate(row):
                                is_sel = (r_idx == self.cur_row and c_idx == self.cur_col)
                                yield SystemCard(s, is_selected=is_sel)

                    with Vertical(id="system-details-box"):
                        yield Static("", id="system-info-title")
                        yield Static("", id="system-info-count")

        # Pie con atajos de ayuda
        with Horizontal(classes="footer-bar"):
            help_text = Text()
            help_text.append("[◀ / ▶ / ▲ / ▼ / Mando]", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            help_text.append(" Navegar   ", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append("[ENTER / Botón A]", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            help_text.append(" Elegir Sistema   ", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append("[ESC / Q / Botón B]", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append(" Salir", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            yield Static(help_text, classes="footer-help")

    def on_mount(self) -> None:
        self.update_selection_ui()

    def get_current_system(self) -> Dict[str, Any]:
        return self.rows[self.cur_row][self.cur_col]

    def update_selection_ui(self) -> None:
        # Actualizar aspecto de cada tarjeta
        for r_idx, row in enumerate(self.rows):
            for c_idx, s in enumerate(row):
                try:
                    card = self.query_one(f"#row-{r_idx} SystemCard:nth-of-type({c_idx + 1})", SystemCard)
                    is_sel = (r_idx == self.cur_row and c_idx == self.cur_col)
                    card.update_appearance(is_sel)
                except Exception:
                    pass

        cur = self.get_current_system()
        # Actualizar info bajo el recuadro
        title_widget = self.query_one("#system-info-title", Static)
        count_widget = self.query_one("#system-info-count", Static)

        title_text = Text(f"{cur['name'].upper()}", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT), bold=True))
        title_widget.update(title_text)

        count_text = Text(f"◆ {cur['games_count']} JUEGOS DISPONIBLES ◆", style=Style(color=renderer.hex_rgb(renderer.COLOR_VIOLET)))
        count_widget.update(count_text)

        data.save_state(cur["id"], data.load_state().get("last_game_id", ""))

    def action_cursor_left(self) -> None:
        if self.cur_col > 0:
            self.cur_col -= 1
        else:
            self.cur_col = len(self.rows[self.cur_row]) - 1
        self.update_selection_ui()

    def action_cursor_right(self) -> None:
        if self.cur_col < len(self.rows[self.cur_row]) - 1:
            self.cur_col += 1
        else:
            self.cur_col = 0
        self.update_selection_ui()

    def action_cursor_up(self) -> None:
        if self.cur_row > 0:
            self.cur_row -= 1
            self.cur_col = min(self.cur_col, len(self.rows[self.cur_row]) - 1)
            self.update_selection_ui()

    def action_cursor_down(self) -> None:
        if self.cur_row < len(self.rows) - 1:
            self.cur_row += 1
            self.cur_col = min(self.cur_col, len(self.rows[self.cur_row]) - 1)
            self.update_selection_ui()

    def action_select_system(self) -> None:
        cur_sys = self.get_current_system()
        self.app.switch_to_games(cur_sys["id"])

    def action_exit_app(self) -> None:
        self.app.exit()
