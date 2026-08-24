import math

import pygame

from src.config import MAX_SPEED, SCREEN_HEIGHT, SCREEN_WIDTH


class HUD:
    def __init__(self):
        pygame.font.init()
        # Cached fonts (never recreated per frame)
        self.label_font = pygame.font.SysFont("Trebuchet MS", 14, bold=True)
        self.value_font = pygame.font.SysFont("Consolas", 20, bold=True)
        self.large_font = pygame.font.SysFont("Consolas", 36, bold=True)
        self.key_font = pygame.font.SysFont("Trebuchet MS", 16, bold=True)
        self.warn_font = pygame.font.SysFont("Trebuchet MS", 22, bold=True)

        # colors
        self.primary_col = (0, 255, 204)  # Neon cyan
        self.accent_col = (255, 0, 85)  # Neon pink/red
        self.panel_bg = (10, 15, 20, 220)

    def draw(self, screen, car, game=None):
        self.draw_top_bar(screen, car)
        self.draw_health_bar(screen, car)
        self.draw_lap_times(screen, car)
        self.draw_speedometer(screen, car)
        self.draw_controller_overlay(screen, game)
        self.draw_offroad_warning(screen, car)

    def _draw_panel(
        self, surface, rect, border_radius=8, border_color=(60, 70, 90, 255)
    ):
        pygame.draw.rect(surface, self.panel_bg, rect, border_radius=border_radius)
        pygame.draw.rect(
            surface, border_color, rect, width=2, border_radius=border_radius
        )

    def draw_top_bar(self, screen, car):
        panel_w, panel_h = 520, 60
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = 15

        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        self._draw_panel(surf, (0, 0, panel_w, panel_h), 12, (50, 150, 255, 100))
        screen.blit(surf, (panel_x, panel_y))

        # Score
        score_lbl = self.label_font.render("TOTAL SCORE", True, (150, 160, 180))
        screen.blit(score_lbl, (panel_x + 20, panel_y + 10))
        score_val = self.value_font.render(
            f"{int(car.total_reward):06d}", True, self.primary_col
        )
        screen.blit(score_val, (panel_x + 20, panel_y + 28))

        # Reward
        rew_lbl = self.label_font.render("REWARD", True, (150, 160, 180))
        screen.blit(rew_lbl, (panel_x + 160, panel_y + 10))
        r_col = (100, 255, 100) if car.reward >= 0 else self.accent_col
        rew_val = self.value_font.render(f"{car.reward:+.1f}", True, r_col)
        screen.blit(rew_val, (panel_x + 160, panel_y + 28))

        # Distance
        dist_lbl = self.label_font.render("DISTANCE", True, (150, 160, 180))
        screen.blit(dist_lbl, (panel_x + 290, panel_y + 10))
        dist_val = self.value_font.render(
            f"{int(car.abs_z / 200):04d} m", True, (255, 200, 50)
        )
        screen.blit(dist_val, (panel_x + 290, panel_y + 28))

        # Laps
        lap_lbl = self.label_font.render("LAPS", True, (150, 160, 180))
        screen.blit(lap_lbl, (panel_x + 420, panel_y + 10))
        lap_val = self.value_font.render(
            f"{car.laps_completed}", True, self.primary_col
        )
        screen.blit(lap_val, (panel_x + 420, panel_y + 28))

    def draw_health_bar(self, screen, car):
        """Draw a health bar below the top bar."""
        bar_w = 200
        bar_h = 12
        bar_x = 20
        bar_y = 18

        surf = pygame.Surface((bar_w + 80, bar_h + 20), pygame.SRCALPHA)
        self._draw_panel(surf, (0, 0, bar_w + 80, bar_h + 20), 8, (60, 70, 90, 200))
        screen.blit(surf, (bar_x - 5, bar_y - 5))

        # Label
        hp_lbl = self.label_font.render("HP", True, (150, 160, 180))
        screen.blit(hp_lbl, (bar_x, bar_y))

        # Bar background
        bx = bar_x + 25
        pygame.draw.rect(
            screen, (40, 20, 20), (bx, bar_y + 1, bar_w, bar_h), border_radius=4
        )

        # Bar fill
        hp_ratio = car.health / max(car.max_health, 1)
        fill_w = int(hp_ratio * bar_w)
        if hp_ratio > 0.5:
            fill_col = (80, 220, 100)
        elif hp_ratio > 0.25:
            fill_col = (255, 200, 50)
        else:
            fill_col = (255, 50, 50)

        if fill_w > 0:
            pygame.draw.rect(
                screen, fill_col, (bx, bar_y + 1, fill_w, bar_h), border_radius=4
            )

        # HP text
        hp_text = self.label_font.render(
            f"{car.health}/{car.max_health}", True, (255, 255, 255)
        )
        screen.blit(hp_text, (bx + bar_w + 5, bar_y))

    def draw_lap_times(self, screen, car):
        panel_w, panel_h = 200, 110
        panel_x = SCREEN_WIDTH - panel_w - 20
        panel_y = 15

        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        self._draw_panel(surf, (0, 0, panel_w, panel_h), 12, (50, 150, 255, 100))
        screen.blit(surf, (panel_x, panel_y))

        current_time = (pygame.time.get_ticks() / 1000.0) - car.lap_start_time

        def format_time(t):
            if t == float("inf") or t == 0.0:
                return "--:--.--"
            m = int(t // 60)
            s = int(t % 60)
            ms = int((t * 100) % 100)
            return f"{m:02d}:{s:02d}.{ms:02d}"

        # Current Lap
        cur_lbl = self.label_font.render("CURRENT LAP", True, (150, 160, 180))
        screen.blit(cur_lbl, (panel_x + 15, panel_y + 10))
        cur_val = self.value_font.render(
            format_time(current_time), True, (255, 255, 255)
        )
        screen.blit(cur_val, (panel_x + 15, panel_y + 25))

        # Best Lap
        best_lbl = self.label_font.render("BEST LAP", True, (150, 160, 180))
        screen.blit(best_lbl, (panel_x + 15, panel_y + 45))
        best_val = self.value_font.render(
            format_time(car.best_lap_time), True, (255, 200, 50)
        )
        screen.blit(best_val, (panel_x + 15, panel_y + 60))

        # Last Lap
        last_lbl = self.label_font.render("LAST LAP", True, (150, 160, 180))
        screen.blit(last_lbl, (panel_x + 15, panel_y + 80))
        last_val = self.label_font.render(
            format_time(car.last_lap_time), True, (150, 160, 180)
        )
        screen.blit(last_val, (panel_x + 100, panel_y + 80))

    def draw_speedometer(self, screen, car):
        panel_w, panel_h = 240, 140
        panel_x = SCREEN_WIDTH - panel_w - 20
        panel_y = SCREEN_HEIGHT - panel_h - 20

        surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        self._draw_panel(surf, (0, 0, panel_w, panel_h), 16)
        screen.blit(surf, (panel_x, panel_y))

        # Speed Value
        km_h = abs(car.speed) / MAX_SPEED * 200.0
        speed_val = self.large_font.render(f"{km_h:03.0f}", True, (255, 255, 255))
        speed_lbl = self.label_font.render("KM/H", True, (120, 130, 150))

        screen.blit(speed_val, (panel_x + 25, panel_y + 20))
        screen.blit(speed_lbl, (panel_x + 25 + speed_val.get_width() + 5, panel_y + 35))

        # Speed bar
        bar_x, bar_y = panel_x + 25, panel_y + 70
        bar_w, bar_h = 190, 12
        pygame.draw.rect(
            screen, (30, 40, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4
        )

        fill_w = int((abs(car.speed) / MAX_SPEED) * bar_w)
        fill_w = min(max(fill_w, 0), bar_w)
        if fill_w > 0:
            for i in range(0, fill_w, 10):
                seg_w = min(8, fill_w - i)
                ratio = i / bar_w
                r = int(self.primary_col[0] * (1 - ratio) + self.accent_col[0] * ratio)
                g = int(self.primary_col[1] * (1 - ratio) + self.accent_col[1] * ratio)
                b = int(self.primary_col[2] * (1 - ratio) + self.accent_col[2] * ratio)
                pygame.draw.rect(
                    screen, (r, g, b), (bar_x + i, bar_y, seg_w, bar_h), border_radius=2
                )

        # Road Position Slider
        pos_lbl = self.label_font.render("LANE ALIGNMENT", True, (120, 130, 150))
        screen.blit(pos_lbl, (panel_x + 25, panel_y + 95))

        slider_y = panel_y + 115
        pygame.draw.line(
            screen, (60, 70, 90), (bar_x, slider_y), (bar_x + bar_w, slider_y), 3
        )
        # Center tick
        pygame.draw.line(
            screen,
            (150, 160, 180),
            (bar_x + bar_w // 2, slider_y - 4),
            (bar_x + bar_w // 2, slider_y + 4),
            2,
        )

        # Safe zone
        safe_x1 = bar_x + int(bar_w * 0.25)
        safe_x2 = bar_x + int(bar_w * 0.75)
        pygame.draw.line(
            screen, (50, 180, 100), (safe_x1, slider_y), (safe_x2, slider_y), 3
        )

        dot_x = bar_x + int(((car.player_x + 2) / 4.0) * bar_w)
        dot_x = max(bar_x, min(bar_x + bar_w, dot_x))
        d_col = self.primary_col if abs(car.player_x) <= 1.0 else self.accent_col
        pygame.draw.circle(screen, d_col, (dot_x, slider_y), 6)

    def draw_controller_overlay(self, screen, game=None):
        card_w, card_h = 150, 120
        card_x = 20
        card_y = SCREEN_HEIGHT - card_h - 20

        ctrl_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        self._draw_panel(ctrl_surf, (0, 0, card_w, card_h), 12)
        screen.blit(ctrl_surf, (card_x, card_y))

        key_size = 32
        gap = 6

        if game and getattr(game, "ai_active", False):
            w_active = game.ai_throttle > 0
            a_active = game.ai_steer < 0
            s_active = game.ai_brake > 0
            d_active = game.ai_steer > 0

            ai_lbl = self.label_font.render("AI DRIVING", True, self.primary_col)
            screen.blit(
                ai_lbl, (card_x + (card_w - ai_lbl.get_width()) // 2, card_y + 8)
            )
        else:
            keys = pygame.key.get_pressed()
            w_active = keys[pygame.K_w] or keys[pygame.K_UP]
            a_active = keys[pygame.K_a] or keys[pygame.K_LEFT]
            s_active = keys[pygame.K_s] or keys[pygame.K_DOWN]
            d_active = keys[pygame.K_d] or keys[pygame.K_RIGHT]

            hum_lbl = self.label_font.render("PLAYER", True, (150, 160, 180))
            screen.blit(
                hum_lbl, (card_x + (card_w - hum_lbl.get_width()) // 2, card_y + 8)
            )

        def render_keycap(letter, offset_x, offset_y, is_active):
            if is_active:
                bg_color = self.primary_col
                border_color = (255, 255, 255)
                text_color = (0, 0, 0)
            else:
                bg_color = (30, 40, 50, 200)
                border_color = (60, 70, 90)
                text_color = (150, 160, 180)

            ks = pygame.Surface((key_size, key_size), pygame.SRCALPHA)
            pygame.draw.rect(ks, bg_color, (0, 0, key_size, key_size), border_radius=6)
            pygame.draw.rect(
                ks, border_color, (0, 0, key_size, key_size), width=2, border_radius=6
            )

            txt = self.key_font.render(letter, True, text_color)
            txt_rect = txt.get_rect(center=(key_size // 2, key_size // 2))
            ks.blit(txt, txt_rect)

            screen.blit(ks, (card_x + offset_x, card_y + offset_y))

        start_x = (card_w - (key_size * 3 + gap * 2)) // 2
        start_y = 28

        render_keycap("W", start_x + key_size + gap, start_y, w_active)
        render_keycap("A", start_x, start_y + key_size + gap, a_active)
        render_keycap("S", start_x + key_size + gap, start_y + key_size + gap, s_active)
        render_keycap(
            "D", start_x + (key_size + gap) * 2, start_y + key_size + gap, d_active
        )

    def draw_offroad_warning(self, screen, car):
        if car.won:
            win_surf = pygame.Surface((SCREEN_WIDTH, 120), pygame.SRCALPHA)
            pygame.draw.rect(win_surf, (20, 200, 50, 180), (0, 0, SCREEN_WIDTH, 120))
            pygame.draw.line(win_surf, (255, 255, 255), (0, 0), (SCREEN_WIDTH, 0), 4)
            pygame.draw.line(
                win_surf, (255, 255, 255), (0, 116), (SCREEN_WIDTH, 116), 4
            )
            screen.blit(win_surf, (0, 300))

            msg = self.large_font.render(
                "RACE COMPLETE! ALL LAPS FINISHED!", True, (255, 255, 255)
            )
            msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, 360))
            screen.blit(msg, msg_rect)
            return

        if abs(car.player_x) > 1.0:
            warn_surf = pygame.Surface((SCREEN_WIDTH, 60), pygame.SRCALPHA)

            pulse = int(abs(math.sin(pygame.time.get_ticks() / 150.0)) * 100)
            pygame.draw.rect(
                warn_surf, (200, 20, 20, 100 + pulse), (0, 0, SCREEN_WIDTH, 60)
            )

            pygame.draw.line(warn_surf, self.accent_col, (0, 0), (SCREEN_WIDTH, 0), 2)
            pygame.draw.line(warn_surf, self.accent_col, (0, 58), (SCREEN_WIDTH, 58), 2)

            screen.blit(warn_surf, (0, 315))

            msg = self.warn_font.render("WARNING: OFF ROAD!", True, (255, 255, 255))
            msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, 345))
            screen.blit(msg, msg_rect)
