"""
ONYRA - Pantalla 1: Boot Splash Screen
Fade-in del logo tipográfico ONYRA (2 a 3 segundos), subtítulo RETRO GAMES
y barra de carga degradada de violeta oscuro a menta. Saltable con cualquier tecla o mando.
"""

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import Screen
from textual.widgets import Static
from rich.text import Text
from rich.style import Style

import renderer

TOTAL_FRAMES = 24       # ~2.4 segundos a 100ms por frame
FADE_FRAMES = 12        # Los primeros 12 frames son el fade-in del logo


class BootScreen(Screen):
    BINDINGS = [
        ("escape", "skip_boot", "Saltar"),
        ("enter", "skip_boot", "Continuar"),
        ("space", "skip_boot", "Continuar"),
        ("q", "skip_boot", "Continuar"),
    ]

    def __init__(self):
        super().__init__(id="boot-screen")
        self.frame = 0
        self.timer = None

    def compose(self) -> ComposeResult:
        with Middle(id="boot-screen"):
            with Center():
                with Vertical(id="boot-container"):
                    yield Static(id="boot-logo")
                    yield Static(id="boot-divider")
                    yield Static(id="boot-subtitle")
                    with Center(id="boot-progress-container"):
                        yield Static(id="boot-progress-bar")

    def on_mount(self) -> None:
        self.render_frame()
        self.timer = self.set_interval(0.1, self.tick)

    def tick(self) -> None:
        self.frame += 1
        if self.frame > TOTAL_FRAMES:
            self.action_skip_boot()
            return
        self.render_frame()

    def render_frame(self) -> None:
        # 1. Fade-in del logo
        alpha = min(1.0, self.frame / float(FADE_FRAMES))
        logo_widget = self.query_one("#boot-logo", Static)
        logo_widget.update(renderer.render_onyra_logo(alpha=alpha))

        # 2. Línea divisoria y subtítulo
        div_widget = self.query_one("#boot-divider", Static)
        sub_widget = self.query_one("#boot-subtitle", Static)

        if self.frame >= FADE_FRAMES // 2:
            div_alpha = min(1.0, (self.frame - FADE_FRAMES // 2) / (FADE_FRAMES / 2))
            div_c = renderer.lerp_rgb(renderer.COLOR_BG, renderer.COLOR_BORDER_INACTIVE, div_alpha)
            div_text = Text("─" * 48, style=Style(color=renderer.hex_rgb(div_c)))
            div_widget.update(div_text)

            sub_c = renderer.lerp_rgb(renderer.COLOR_BG, renderer.COLOR_TEXT_DIM, div_alpha)
            sub_text = Text("R E T R O   G A M E S", style=Style(color=renderer.hex_rgb(sub_c), bold=True))
            sub_widget.update(sub_text)
        else:
            div_widget.update("")
            sub_widget.update("")

        # 3. Barra de progreso fina (de violeta oscuro #4B3A99 a menta #3DFFC0)
        bar_widget = self.query_one("#boot-progress-bar", Static)
        bar_width = 48
        progress = max(0.0, min(1.0, self.frame / float(TOTAL_FRAMES)))
        filled_chars = int(round(progress * bar_width))

        bar_text = Text()
        for i in range(bar_width):
            if i < filled_chars:
                t = i / float(bar_width - 1)
                c = renderer.lerp_rgb(renderer.COLOR_SHADOW, renderer.COLOR_MINT, t)
                bar_text.append("━", style=Style(color=renderer.hex_rgb(c)))
            else:
                bar_text.append("━", style=Style(color=renderer.hex_rgb(renderer.COLOR_BORDER_INACTIVE)))
        bar_widget.update(bar_text)

    def on_key(self, event) -> None:
        """Cualquier tecla salta el boot inmediatamente."""
        event.stop()
        event.prevent_default()
        self.action_skip_boot()

    def action_skip_boot(self) -> None:
        if self.timer:
            self.timer.stop()
        self.app.switch_to_systems()
