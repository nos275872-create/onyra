"""
ONYRA - Pantalla 3: Lista de Juegos y Ficha Técnica
Panel izquierdo (~40%): buscador dinámico y lista limpia de juegos con nombres sin tags.
Panel derecho (~60%): carátula fotográfica a medios bloques truecolor, metadatos estructurados y sinopsis.
"""

from typing import List, Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, ListView, ListItem, Static
from rich.text import Text
from rich.style import Style

import data
import launcher
import renderer
from screens.dialogs import SaveStateDialog


class GameListItem(ListItem):
    """Elemento individual de la lista de juegos."""
    def __init__(self, game: Dict[str, Any]):
        super().__init__()
        self.game = game

    def render(self) -> Text:
        txt = Text()
        # Si está seleccionado Textual le aplica estilo de seleccionado
        txt.append(f"  {self.game['clean_title']}")
        return txt


class GamesScreen(Screen):
    BINDINGS = [
        ("escape", "back_to_systems", "Volver a Sistemas"),
        ("q", "back_to_systems", "Volver a Sistemas"),
        ("enter", "launch_current_game", "Jugar"),
        ("slash", "focus_search", "Buscar"),
    ]

    def __init__(self, sys_id: str):
        super().__init__(id="games-screen")
        self.sys_id = sys_id
        self.catalog = data.get_catalog()
        self.all_games: List[Dict[str, Any]] = self.catalog.get(sys_id, [])
        self.filtered_games: List[Dict[str, Any]] = list(self.all_games)
        self.selected_game: Optional[Dict[str, Any]] = None

        # Determinar info del sistema
        self.sys_info = next((s for s in data.SYSTEMS_INFO if s["id"] == sys_id), None)

        # Restaurar último juego seleccionado si existe
        state = data.load_state()
        last_game_id = state.get("last_game_id")
        self.initial_idx = 0
        for idx, g in enumerate(self.all_games):
            if g.get("id") == last_game_id:
                self.initial_idx = idx
                break

    def compose(self) -> ComposeResult:
        # Cabecera
        with Horizontal(classes="header-bar"):
            header_txt = Text("O  N  Y  R  A", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            yield Static(header_txt, classes="header-title")

        # Contenedor 2 paneles
        with Horizontal(id="games-container"):
            # Panel Izquierdo (~40%)
            with Vertical(id="games-list-panel"):
                sys_title = self.sys_info["name"].upper() if self.sys_info else self.sys_id.upper()
                yield Static(f"◆ {sys_title} ◆", id="games-list-title")
                with Vertical(id="games-search-box"):
                    yield Input(placeholder="🔍 Buscar juego...", id="games-search-input")
                yield ListView(id="games-list-view")

            # Panel Derecho (~60%)
            with Vertical(id="game-details-panel"):
                yield Static(id="game-cover-container")
                with VerticalScroll(id="game-info-container"):
                    yield Static(id="game-title")
                    yield Static(id="game-metadata")
                    yield Static("SINOPSIS E HISTORIA", id="game-desc-header")
                    yield Static(id="game-desc")
                    yield Static(id="game-controls-box")

        # Pie
        with Horizontal(classes="footer-bar"):
            help_text = Text()
            help_text.append("[▲ / ▼ / Mando]", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            help_text.append(" Elegir Juego   ", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append("[ENTER / Botón A]", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
            help_text.append(" Iniciar Partida   ", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append("[ESC / Q / Botón B]", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            help_text.append(" Volver a Sistemas", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
            yield Static(help_text, classes="footer-help")

    def on_mount(self) -> None:
        self.populate_games_list()
        list_view = self.query_one("#games-list-view", ListView)
        list_view.focus()

    def populate_games_list(self) -> None:
        list_view = self.query_one("#games-list-view", ListView)
        list_view.clear()

        for g in self.filtered_games:
            list_view.append(GameListItem(g))

        if self.filtered_games:
            idx = min(self.initial_idx, len(self.filtered_games) - 1)
            list_view.index = idx
            self.selected_game = self.filtered_games[idx]
            self.update_game_details(self.selected_game)
        else:
            self.selected_game = None
            self.clear_game_details()

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        if not query:
            self.filtered_games = list(self.all_games)
        else:
            self.filtered_games = [
                g for g in self.all_games
                if query in g["clean_title"].lower() or query in g.get("genre", "").lower()
            ]
        self.initial_idx = 0
        self.populate_games_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Al pulsar Enter en la lista."""
        self.action_launch_current_game()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Al desplazarse por la lista."""
        if event.item and isinstance(event.item, GameListItem):
            self.selected_game = event.item.game
            self.update_game_details(self.selected_game)
            data.save_state(self.sys_id, self.selected_game.get("id", ""))

    def update_game_details(self, game: Dict[str, Any]) -> None:
        # 1. Carátula fotográfica o placeholder
        cover_widget = self.query_one("#game-cover-container", Static)
        cover_path = data.get_game_cover_path(game)
        rendered_cover = renderer.render_cover_image(
            cover_path,
            max_cols=36,
            max_lines=15,
            bg=renderer.COLOR_PANEL,
            game_title=game["clean_title"]
        )
        cover_widget.update(rendered_cover)

        # 2. Título principal
        title_widget = self.query_one("#game-title", Static)
        title_txt = Text(f"★  {game['clean_title']}  ★", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT), bold=True))
        title_widget.update(title_txt)

        # 3. Metadatos estructurados
        meta_widget = self.query_one("#game-metadata", Static)
        meta_txt = Text()

        def add_meta_row(label: str, value: str):
            meta_txt.append(f"{label:<16}", style=Style(color=renderer.hex_rgb(renderer.COLOR_VIOLET), bold=True))
            meta_txt.append(f"{value}\n", style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT)))

        add_meta_row("AÑO:", game.get("year", "N/A"))
        add_meta_row("DESARROLLADOR:", game.get("dev", "N/A"))
        add_meta_row("GÉNERO:", game.get("genre", "N/A"))
        add_meta_row("JUGADORES:", game.get("players", "1 Jugador"))
        add_meta_row("SISTEMA:", game.get("system", "Retro"))
        meta_widget.update(meta_txt)

        # 4. Descripción enriquecida
        desc_widget = self.query_one("#game-desc", Static)
        desc_txt = Text(game.get("desc", "Sin descripción disponible."), style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
        desc_widget.update(desc_txt)

        # 5. Mandos y controles
        controls_widget = self.query_one("#game-controls-box", Static)
        ctrl_txt = Text()
        ctrl_txt.append("MANDOS Y ATAJOS:\n", style=Style(color=renderer.hex_rgb(renderer.COLOR_MINT), bold=True))
        ctrl_txt.append(game.get("controls", "Mando: Cruceta / Sticks + Botones A/B/X/Y"), style=Style(color=renderer.hex_rgb(renderer.COLOR_TEXT_DIM)))
        controls_widget.update(ctrl_txt)

    def clear_game_details(self) -> None:
        self.query_one("#game-cover-container", Static).update("")
        self.query_one("#game-title", Static).update("No se encontraron juegos")
        self.query_one("#game-metadata", Static).update("")
        self.query_one("#game-desc", Static).update("")
        self.query_one("#game-controls-box", Static).update("")

    def action_launch_current_game(self) -> None:
        if not self.selected_game:
            return

        save_file = data.get_game_autosave(self.selected_game)
        if save_file:
            # Hay partida guardada: mostrar diálogo interactivo
            def dialog_callback(restart_clean: Optional[bool]):
                if restart_clean is not None:
                    launcher.launch_game(self.app, self.selected_game, restart_clean=restart_clean)

            self.app.push_screen(SaveStateDialog(self.selected_game, save_file), dialog_callback)
        else:
            # No hay save previo: arrancar directamente
            launcher.launch_game(self.app, self.selected_game, restart_clean=False)

    def action_back_to_systems(self) -> None:
        search_input = self.query_one("#games-search-input", Input)
        if search_input.has_focus:
            # Si el foco está en la barra de búsqueda, pasar a la lista
            self.query_one("#games-list-view", ListView).focus()
            return
        self.app.switch_to_systems()

    def action_focus_search(self) -> None:
        self.query_one("#games-search-input", Input).focus()
