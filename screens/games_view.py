"""
ONYRA - Pantalla 3: Lista de Juegos y Ficha Técnica (Pygame / 60 FPS)
Panel izquierdo con lista limpia, buscador reactivo y scroll con inercia suave.
Panel derecho con carátula en alta definición (carga en segundo plano, fundido suave),
metadatos estructurados violeta/blanco y sinopsis envuelta.
Diálogo modal de partida guardada integrado.
"""

import datetime
import os
import queue
import threading
from typing import Dict, List, Any, Optional
import pygame
from PIL import Image, ImageDraw

import data
import launcher
import theme

_cover_cache: Dict[str, pygame.Surface] = {}
_cover_queue: queue.Queue = queue.Queue()
_loader_thread: Optional[threading.Thread] = None


def _cover_worker():
    while True:
        try:
            game_id, cover_path, target_w, target_h = _cover_queue.get()
            if game_id in _cover_cache:
                _cover_queue.task_done()
                continue

            if cover_path and os.path.exists(cover_path):
                try:
                    img = Image.open(cover_path).convert("RGBA")
                    orig_w, orig_h = img.size
                    ratio = orig_w / float(orig_h)

                    fit_h = target_h
                    fit_w = int(fit_h * ratio)
                    if fit_w > target_w:
                        fit_w = target_w
                        fit_h = int(fit_w / ratio)

                    img = img.resize((fit_w, fit_h), Image.Resampling.LANCZOS)

                    # Esquinas redondeadas
                    mask = Image.new("L", (fit_w, fit_h), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle([(0, 0), (fit_w, fit_h)], radius=12, fill=255)
                    img.putalpha(mask)

                    surf = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
                    _cover_cache[game_id] = surf
                except Exception:
                    pass
            _cover_queue.task_done()
        except Exception:
            pass


def ensure_loader_started():
    global _loader_thread
    if _loader_thread is None:
        _loader_thread = threading.Thread(target=_cover_worker, daemon=True)
        _loader_thread.start()


class GamesView:
    def __init__(self, sys_id: str, screen_w: int, screen_h: int):
        self.sys_id = sys_id
        self.screen_w = screen_w
        self.screen_h = screen_h

        ensure_loader_started()

        self.catalog = data.get_catalog()
        self.all_games: List[Dict[str, Any]] = self.catalog.get(sys_id, [])
        self.filtered_games: List[Dict[str, Any]] = list(self.all_games)
        self.selected_idx = 0
        self.should_exit_for_game = False

        # Info del sistema
        self.sys_info = next((s for s in data.SYSTEMS_INFO if s["id"] == sys_id), None)
        self.sys_title = self.sys_info["name"].upper() if self.sys_info else sys_id.upper()

        # Restaurar último juego
        state = data.load_state()
        last_game_id = state.get("last_game_id")
        for idx, g in enumerate(self.all_games):
            if g.get("id") == last_game_id:
                self.selected_idx = idx
                break

        # Layout Paneles
        self.pad_x = 40
        self.panel_y = 70
        self.panel_h = screen_h - self.panel_y - 50

        self.left_w = int((screen_w - self.pad_x * 2 - 24) * 0.40)
        self.right_w = screen_w - self.pad_x * 2 - 24 - self.left_w

        self.left_rect = pygame.Rect(self.pad_x, self.panel_y, self.left_w, self.panel_h)
        self.right_rect = pygame.Rect(self.left_rect.right + 24, self.panel_y, self.right_w, self.panel_h)

        # Buscador
        self.search_query = ""
        self.search_active = False

        # Scroll suave con inercia
        self.item_h = 48
        self.scroll_pos = 0.0
        self.target_scroll_pos = 0.0

        # Crossfade de carátula
        self.prev_game_id = ""
        self.cur_cover_alpha = 255.0

        # Modal de partida guardada
        self.modal_active = False
        self.modal_save_file = ""
        self.modal_opt = 0 # 0: Reanudar, 1: Empezar de nuevo

        self.should_back_to_systems = False
        self._request_cover_current()

    def _request_cover_current(self):
        if not self.filtered_games:
            return
        g = self.filtered_games[self.selected_idx]
        gid = g.get("id", "")
        if gid and gid not in _cover_cache:
            cover_path = data.get_game_cover_path(g)
            max_w = min(360, int(self.right_w * 0.60))
            max_h = min(360, int(self.panel_h * 0.48))
            _cover_queue.put((gid, cover_path, max_w, max_h))

    def update(self, dt: float) -> None:
        # 1. Scroll suave con inercia
        vis_count = max(1, (self.panel_h - 120) // self.item_h)
        target_top = max(0, self.selected_idx - vis_count // 2) * self.item_h
        self.target_scroll_pos = float(target_top)

        # Lerp de scroll
        self.scroll_pos += (self.target_scroll_pos - self.scroll_pos) * min(1.0, 16.0 * dt)

        # 2. Fade suave de carátula
        if self.cur_cover_alpha < 255.0:
            self.cur_cover_alpha = min(255.0, self.cur_cover_alpha + 650.0 * dt)

    def handle_input(self, action: str, char: str = "") -> None:
        if self.modal_active:
            if action == "UP" or action == "LEFT":
                self.modal_opt = 0
            elif action == "DOWN" or action == "RIGHT":
                self.modal_opt = 1
            elif action == "BACK":
                self.modal_active = False
            elif action == "ENTER":
                self._execute_launch(restart_clean=(self.modal_opt == 1))
            return

        if action == "UP":
            if self.selected_idx > 0:
                self.selected_idx -= 1
                self._on_selection_changed()

        elif action == "DOWN":
            if self.selected_idx < len(self.filtered_games) - 1:
                self.selected_idx += 1
                self._on_selection_changed()

        elif action == "LEFT":
            self.selected_idx = max(0, self.selected_idx - 6)
            self._on_selection_changed()

        elif action == "RIGHT":
            self.selected_idx = min(len(self.filtered_games) - 1, self.selected_idx + 6)
            self._on_selection_changed()

        elif action == "CHAR":
            self.search_query += char
            self._apply_filter()

        elif action == "BACKSPACE":
            if self.search_query:
                self.search_query = self.search_query[:-1]
                self._apply_filter()

        elif action == "BACK":
            if self.search_query:
                self.search_query = ""
                self._apply_filter()
            else:
                self.should_back_to_systems = True

        elif action == "ENTER":
            if self.filtered_games:
                cur_game = self.filtered_games[self.selected_idx]
                save_file = data.get_game_autosave(cur_game)
                if save_file:
                    self.modal_active = True
                    self.modal_save_file = save_file
                    self.modal_opt = 0
                else:
                    self._execute_launch(restart_clean=False)

    def _on_selection_changed(self):
        if self.filtered_games:
            cur_game = self.filtered_games[self.selected_idx]
            data.save_state(self.sys_id, cur_game.get("id", ""))
            self.cur_cover_alpha = 100.0 # Reiniciar fade para suavidad
            self._request_cover_current()

    def _apply_filter(self):
        q = self.search_query.strip().lower()
        if not q:
            self.filtered_games = list(self.all_games)
        else:
            self.filtered_games = [
                g for g in self.all_games
                if q in g["clean_title"].lower() or q in g.get("genre", "").lower()
            ]
        self.selected_idx = 0
        self._on_selection_changed()

    def _execute_launch(self, restart_clean: bool = False):
        if not self.filtered_games:
            return
        self.modal_active = False
        cur_game = self.filtered_games[self.selected_idx]
        data.save_state(self.sys_id, cur_game.get("id", ""))
        launcher.prepare_launch(cur_game, restart_clean=restart_clean)
        self.should_exit_for_game = True

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(theme.COLOR_BG)

        # 1. Cabecera pequeña
        head_surf = theme.render_text("O  N  Y  R  A", font_name="sans_bold", size=20, color=theme.COLOR_MINT)
        screen.blit(head_surf, (self.screen_w // 2 - head_surf.get_width() // 2, 24))

        # 2. Panel Izquierdo (~40%)
        theme.draw_rounded_panel(screen, self.left_rect, bg_color=theme.COLOR_PANEL, border_color=theme.COLOR_BORDER_INACTIVE, radius=12)

        # Título del sistema en el panel izquierdo
        title_surf = theme.render_text(f"◆  {self.sys_title}  ◆", font_name="sans_bold", size=18, color=theme.COLOR_MINT)
        screen.blit(title_surf, (self.left_rect.centerx - title_surf.get_width() // 2, self.left_rect.y + 18))

        # Barra de búsqueda
        search_box = pygame.Rect(self.left_rect.x + 18, self.left_rect.y + 54, self.left_rect.width - 36, 36)
        pygame.draw.rect(screen, theme.COLOR_BG, search_box, border_radius=8)
        pygame.draw.rect(screen, theme.COLOR_BORDER_INACTIVE, search_box, width=1, border_radius=8)

        search_txt = f"🔍 {self.search_query}" if self.search_query else "🔍 Buscar juego (empieza a escribir)..."
        search_col = theme.COLOR_TEXT if self.search_query else theme.COLOR_TEXT_DIM
        st_surf = theme.render_text(search_txt, font_name="regular", size=14, color=search_col)
        screen.blit(st_surf, (search_box.x + 12, search_box.y + 9))

        # Lista de juegos con clipping y scroll suave
        list_y = search_box.bottom + 14
        list_h = self.left_rect.bottom - list_y - 16
        list_rect = pygame.Rect(self.left_rect.x + 10, list_y, self.left_rect.width - 20, list_h)

        prev_clip = screen.get_clip()
        screen.set_clip(list_rect)

        for idx, g in enumerate(self.filtered_games):
            item_y = list_y + idx * self.item_h - int(self.scroll_pos)
            if item_y + self.item_h < list_y or item_y > list_rect.bottom:
                continue

            item_rect = pygame.Rect(list_rect.x + 6, item_y, list_rect.width - 12, self.item_h - 4)
            is_sel = (idx == self.selected_idx)

            if is_sel:
                # Elemento seleccionado
                pygame.draw.rect(screen, (20, 26, 36), item_rect, border_radius=8)
                pygame.draw.rect(screen, theme.COLOR_MINT, item_rect, width=1, border_radius=8)
                item_txt = f"▶  {g['clean_title']}"
                t_surf = theme.render_text(item_txt, font_name="sans_bold", size=15, color=theme.COLOR_MINT)
            else:
                item_txt = f"   {g['clean_title']}"
                t_surf = theme.render_text(item_txt, font_name="regular", size=15, color=theme.COLOR_TEXT_DIM)

            screen.blit(t_surf, (item_rect.x + 12, item_rect.y + (item_rect.height - t_surf.get_height()) // 2))

        screen.set_clip(prev_clip)

        # 3. Panel Derecho (~60%): Ficha técnica y Carátula
        theme.draw_rounded_panel(screen, self.right_rect, bg_color=theme.COLOR_PANEL, border_color=theme.COLOR_BORDER_INACTIVE, radius=12)

        if self.filtered_games:
            cur_game = self.filtered_games[self.selected_idx]

            # Área de Carátula arriba
            cover_max_h = min(360, int(self.panel_h * 0.46))
            cover_area = pygame.Rect(self.right_rect.x + 24, self.right_rect.y + 20, self.right_w - 48, cover_max_h)

            gid = cur_game.get("id", "")
            if gid in _cover_cache:
                c_surf = _cover_cache[gid]
                c_copy = c_surf.copy()
                c_copy.set_alpha(int(self.cur_cover_alpha))
                cx = cover_area.centerx - c_copy.get_width() // 2
                cy = cover_area.centery - c_copy.get_height() // 2
                screen.blit(c_copy, (cx, cy))
            else:
                # Placeholder elegante ONYRA
                ph_rect = pygame.Rect(cover_area.centerx - 120, cover_area.centery - 100, 240, 200)
                pygame.draw.rect(screen, (18, 22, 30), ph_rect, border_radius=12)
                pygame.draw.rect(screen, theme.COLOR_BORDER_INACTIVE, ph_rect, width=1, border_radius=12)
                ph_txt = theme.render_text("O N Y R A", font_name="sans_bold", size=18, color=theme.COLOR_MINT)
                ph_sub = theme.render_text("RETRO ARCHIVE", font_name="regular", size=12, color=theme.COLOR_TEXT_DIM)
                screen.blit(ph_txt, (ph_rect.centerx - ph_txt.get_width() // 2, ph_rect.centery - 20))
                screen.blit(ph_sub, (ph_rect.centerx - ph_sub.get_width() // 2, ph_rect.centery + 10))

            # Ficha Técnica debajo de la carátula
            info_y = cover_area.bottom + 16

            # Título principal
            title_surf = theme.render_text(cur_game["clean_title"].upper(), font_name="sans_bold", size=24, color=theme.COLOR_TEXT)
            screen.blit(title_surf, (self.right_rect.x + 36, info_y))
            info_y += 34

            # Metadatos estructurados en 2 columnas
            def draw_meta_pair(label: str, val: str, x: int, y: int):
                lbl_s = theme.render_text(label, font_name="sans_bold", size=13, color=theme.COLOR_VIOLET)
                val_s = theme.render_text(val, font_name="regular", size=13, color=theme.COLOR_TEXT)
                screen.blit(lbl_s, (x, y))
                screen.blit(val_s, (x + lbl_s.get_width() + 8, y))

            col1_x = self.right_rect.x + 36
            col2_x = self.right_rect.x + int(self.right_w * 0.50)

            draw_meta_pair("AÑO:", cur_game.get("year", "N/A"), col1_x, info_y)
            draw_meta_pair("GÉNERO:", cur_game.get("genre", "N/A"), col2_x, info_y)
            info_y += 24

            draw_meta_pair("DESARROLLADOR:", cur_game.get("dev", "N/A"), col1_x, info_y)
            draw_meta_pair("JUGADORES:", cur_game.get("players", "1-2"), col2_x, info_y)
            info_y += 30

            # Línea divisoria
            div_line = pygame.Rect(self.right_rect.x + 36, info_y, self.right_w - 72, 1)
            pygame.draw.rect(screen, theme.COLOR_BORDER_INACTIVE, div_line)
            info_y += 14

            # Sinopsis / Descripción envuelta
            desc_text = cur_game.get("desc", "")
            words = desc_text.split()
            max_text_w = self.right_w - 72

            font_desc = theme.get_font("regular", 14)
            line = ""
            for w in words:
                test_line = (line + " " + w).strip()
                if font_desc.size(test_line)[0] < max_text_w:
                    line = test_line
                else:
                    if line:
                        ls = font_desc.render(line, True, theme.COLOR_TEXT_DIM)
                        screen.blit(ls, (self.right_rect.x + 36, info_y))
                        info_y += 21
                    line = w
            if line:
                ls = font_desc.render(line, True, theme.COLOR_TEXT_DIM)
                screen.blit(ls, (self.right_rect.x + 36, info_y))
                info_y += 26

            # Mandos y atajos
            controls_txt = cur_game.get("controls", "")
            if controls_txt and info_y < self.right_rect.bottom - 45:
                ctrl_lbl = theme.render_text("MANDOS:", font_name="sans_bold", size=12, color=theme.COLOR_MINT)
                screen.blit(ctrl_lbl, (self.right_rect.x + 36, info_y))
                ctrl_val = font_desc.render(controls_txt[:90], True, theme.COLOR_TEXT_DIM)
                screen.blit(ctrl_val, (self.right_rect.x + 36 + ctrl_lbl.get_width() + 8, info_y))

        # 4. Pie de página
        footer_y = self.screen_h - 36
        help_s = theme.render_text(
            "[▲ / ▼] Elegir Juego   [ENTER / Botón A] JUGAR   [ESC / Q / Botón B] Volver a Sistemas",
            font_name="regular", size=13, color=theme.COLOR_TEXT_DIM
        )
        screen.blit(help_s, (self.screen_w // 2 - help_s.get_width() // 2, footer_y))

        # 5. Diálogo Modal de Partida Guardada
        if self.modal_active:
            # Overlay oscurecido
            overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            overlay.fill((8, 9, 13, 210))
            screen.blit(overlay, (0, 0))

            dialog_w = 640
            dialog_h = 320
            d_rect = pygame.Rect((self.screen_w - dialog_w) // 2, (self.screen_h - dialog_h) // 2, dialog_w, dialog_h)

            theme.draw_rounded_panel(screen, d_rect, bg_color=theme.COLOR_PANEL, border_color=theme.COLOR_VIOLET, radius=16, border_width=2)

            # Contenido del modal
            dt_title = theme.render_text("★  PARTIDA GUARDADA DETECTADA  ★", font_name="sans_bold", size=20, color=theme.COLOR_VIOLET)
            screen.blit(dt_title, (d_rect.centerx - dt_title.get_width() // 2, d_rect.y + 30))

            g_name = self.filtered_games[self.selected_idx]["clean_title"]
            g_surf = theme.render_text(f"[ {g_name} ]", font_name="sans_bold", size=18, color=theme.COLOR_MINT)
            screen.blit(g_surf, (d_rect.centerx - g_surf.get_width() // 2, d_rect.y + 68))

            mtime = os.path.getmtime(self.modal_save_file) if os.path.exists(self.modal_save_file) else 0
            time_str = datetime.datetime.fromtimestamp(mtime).strftime("%d/%m/%Y a las %H:%M") if mtime else "N/A"
            t_info = theme.render_text(f"Última instantánea: {time_str}", font_name="regular", size=14, color=theme.COLOR_TEXT_DIM)
            screen.blit(t_info, (d_rect.centerx - t_info.get_width() // 2, d_rect.y + 98))

            # Opción 1: Reanudar
            btn1_rect = pygame.Rect(d_rect.x + 50, d_rect.y + 145, d_rect.width - 100, 48)
            col_b1 = theme.COLOR_MINT if self.modal_opt == 0 else theme.COLOR_TEXT_DIM
            bg_b1 = (20, 26, 36) if self.modal_opt == 0 else (14, 17, 22)
            theme.draw_rounded_panel(screen, btn1_rect, bg_color=bg_b1, border_color=col_b1, radius=10, border_width=2 if self.modal_opt == 0 else 1)
            b1_txt = theme.render_text("▶  1. REANUDAR PARTIDA  (Continuar donde lo dejaste)", font_name="sans_bold", size=15, color=col_b1)
            screen.blit(b1_txt, (btn1_rect.centerx - b1_txt.get_width() // 2, btn1_rect.centery - b1_txt.get_height() // 2))

            # Opción 2: Empezar de nuevo
            btn2_rect = pygame.Rect(d_rect.x + 50, d_rect.y + 205, d_rect.width - 100, 48)
            col_b2 = (255, 90, 120) if self.modal_opt == 1 else theme.COLOR_TEXT_DIM
            bg_b2 = (20, 26, 36) if self.modal_opt == 1 else (14, 17, 22)
            theme.draw_rounded_panel(screen, btn2_rect, bg_color=bg_b2, border_color=col_b2, radius=10, border_width=2 if self.modal_opt == 1 else 1)
            b2_txt = theme.render_text("▶  2. EMPEZAR DE NUEVO  (Reiniciar desde el inicio)", font_name="sans_bold", size=15, color=col_b2)
            screen.blit(b2_txt, (btn2_rect.centerx - b2_txt.get_width() // 2, btn2_rect.centery - b2_txt.get_height() // 2))

            hint_txt = theme.render_text("[▲ / ▼] Elegir   [ENTER] Confirmar   [ESC / Q] Cancelar", font_name="regular", size=13, color=theme.COLOR_TEXT_DIM)
            screen.blit(hint_txt, (d_rect.centerx - hint_txt.get_width() // 2, d_rect.bottom - 36))
