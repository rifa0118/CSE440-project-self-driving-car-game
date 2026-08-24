"""
Main menu for the Self-Driving Car Racing Game.

All game modes are launched via direct Python imports — no subprocess calls.
"""

import os
import sys

import pygame

from src.profile import PlayerProfile


def draw_text(surface, text, font, color, x, y):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(x, y))
    surface.blit(text_surface, text_rect)
    return text_rect


def customization_menu(screen, clock):
    profile = PlayerProfile()
    title_font = pygame.font.SysFont("Consolas", 48, bold=True)
    label_font = pygame.font.SysFont("Consolas", 24, bold=True)
    small_font = pygame.font.SysFont("Consolas", 18)

    def draw_car_preview(surface, color, x, y):
        w, h = 100, 60
        pygame.draw.rect(
            surface, color, (x - w // 2, y - h // 2, w, h), border_radius=10
        )
        pygame.draw.rect(
            surface,
            (40, 40, 40),
            (x - w // 2 + 10, y - h // 2 + 5, w - 20, h - 10),
            border_radius=8,
        )
        pygame.draw.rect(
            surface,
            (200, 200, 200),
            (x - w // 2 + 20, y - h // 2 + 10, w - 40, h - 20),
            border_radius=5,
        )

    colors = [
        ((255, 0, 0), "Red"),
        ((0, 255, 0), "Green"),
        ((0, 100, 255), "Blue"),
        ((255, 255, 0), "Yellow"),
        ((255, 0, 255), "Magenta"),
        ((0, 255, 255), "Cyan"),
    ]
    color_idx = 0
    for i, (c, _) in enumerate(colors):
        if c == profile.color:
            color_idx = i

    # Track which stat is selected for adjustment
    selected_stat = 0  # 0=top_speed, 1=accel, 2=handling

    running = True
    while running:
        screen.fill((15, 20, 25))
        draw_text(screen, "CUSTOMIZE AI DRIVER", title_font, (0, 255, 204), 500, 80)

        draw_car_preview(screen, profile.color, 500, 180)

        # Draw Stats with selection indicator
        y_pos = 280
        stats = [
            ("Top Speed", profile.top_speed_mod),
            ("Acceleration", profile.accel_mod),
            ("Handling", profile.handling_mod),
        ]

        for i, (name, val) in enumerate(stats):
            col = (0, 255, 204) if i == selected_stat else (255, 255, 255)
            prefix = "▸ " if i == selected_stat else "  "
            draw_text(
                screen, f"{prefix}{name}: {val:.1f}x", label_font, col, 500, y_pos
            )

            # Draw stat bar
            bar_x = 350
            bar_w = 300
            bar_h = 8
            bar_y = y_pos + 20
            pygame.draw.rect(
                screen, (40, 50, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=4
            )
            fill = int((val - 0.8) / 0.4 * bar_w)  # 0.8 to 1.2 range
            fill = max(0, min(bar_w, fill))
            pygame.draw.rect(screen, col, (bar_x, bar_y, fill, bar_h), border_radius=4)

            y_pos += 60

        draw_text(
            screen,
            f"Color: {colors[color_idx][1]}",
            label_font,
            colors[color_idx][0],
            500,
            y_pos,
        )
        y_pos += 50

        # Instructions
        draw_text(
            screen,
            "Up/Down: Select Stat  |  Left/Right: Adjust Value",
            small_font,
            (150, 160, 180),
            500,
            y_pos,
        )
        draw_text(
            screen,
            "C: Change Color  |  Enter/Esc: Save & Return",
            small_font,
            (150, 160, 180),
            500,
            y_pos + 25,
        )

        # Back button
        mouse_pos = pygame.mouse.get_pos()
        btn_rect = pygame.Rect(400, 650, 200, 50)
        if btn_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (0, 255, 204), btn_rect, border_radius=10)
            draw_text(screen, "SAVE & BACK", label_font, (0, 0, 0), 500, 675)
        else:
            pygame.draw.rect(screen, (30, 40, 50), btn_rect, border_radius=10)
            pygame.draw.rect(screen, (0, 255, 204), btn_rect, width=2, border_radius=10)
            draw_text(screen, "SAVE & BACK", label_font, (255, 255, 255), 500, 675)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and btn_rect.collidepoint(mouse_pos):
                profile.save()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                    profile.save()
                    return
                elif event.key == pygame.K_UP:
                    selected_stat = (selected_stat - 1) % 3
                elif event.key == pygame.K_DOWN:
                    selected_stat = (selected_stat + 1) % 3
                elif event.key == pygame.K_LEFT:
                    if selected_stat == 0:
                        profile.top_speed_mod = max(
                            0.8, round(profile.top_speed_mod - 0.1, 1)
                        )
                    elif selected_stat == 1:
                        profile.accel_mod = max(0.8, round(profile.accel_mod - 0.1, 1))
                    elif selected_stat == 2:
                        profile.handling_mod = max(
                            0.8, round(profile.handling_mod - 0.1, 1)
                        )
                elif event.key == pygame.K_RIGHT:
                    if selected_stat == 0:
                        profile.top_speed_mod = min(
                            1.2, round(profile.top_speed_mod + 0.1, 1)
                        )
                    elif selected_stat == 1:
                        profile.accel_mod = min(1.2, round(profile.accel_mod + 0.1, 1))
                    elif selected_stat == 2:
                        profile.handling_mod = min(
                            1.2, round(profile.handling_mod + 0.1, 1)
                        )
                elif event.key == pygame.K_c:
                    color_idx = (color_idx + 1) % len(colors)
                    profile.color = colors[color_idx][0]

        pygame.display.flip()
        clock.tick(60)


def main_menu():
    pygame.init()
    screen = pygame.display.set_mode((1000, 850))
    pygame.display.set_caption("Self-Driving Car Racing — RL Agent")
    clock = pygame.time.Clock()

    # Fonts
    title_font = pygame.font.SysFont("Impact", 72, bold=False)
    if not title_font:
        title_font = pygame.font.SysFont("Consolas", 64, bold=True)
    subtitle_font = pygame.font.SysFont("Arial", 22, bold=True)
    button_font = pygame.font.SysFont("Arial", 26, bold=True)
    info_font = pygame.font.SysFont("Arial", 16, bold=True)

    # Colors
    bg_color = (15, 20, 25)
    btn_color = (30, 40, 50)
    btn_hover_color = (0, 255, 204)
    text_color = (255, 255, 255)
    accent = (0, 255, 204)

    # Check if model exists
    def model_exists():
        return os.path.exists("models/model.pth") or os.path.exists(
            "models/latest_model.pth"
        )

    timer = 0
    while True:
        timer += 1
        screen.fill(bg_color)

        # --- Draw Animated Synthwave Background ---
        # 1. Sky Gradient (top half)
        for i in range(400):
            # From dark purple to pinkish-orange
            r = min(255, int(15 + (200 - 15) * (i / 400)))
            g = min(255, int(20 + (50 - 20) * (i / 400)))
            b = min(255, int(40 + (100 - 40) * (i / 400)))
            pygame.draw.line(screen, (r, g, b), (0, i), (1000, i))
            
        # 2. Retro Sun
        pygame.draw.circle(screen, (255, 200, 50), (500, 320), 120)
        # Stripes in the sun
        for i in range(15):
            sy = 320 + i * 8
            thickness = int(i * 0.8) + 1
            pygame.draw.rect(screen, bg_color, (300, sy, 400, thickness))

        # 3. Ground Gradient (bottom half)
        for i in range(400, 850):
            pygame.draw.line(screen, (10, 10, 20), (0, i), (1000, i))

        # 4. Moving Perspective Grid
        grid_color = (0, 200, 255)
        speed = 3
        offset = (timer * speed) % 30
        
        # Horizontal lines
        for i in range(25):
            y = 400 + offset + (i ** 2.2) * 0.5
            if y < 850:
                thickness = max(1, int(i / 5))
                pygame.draw.line(screen, grid_color, (0, int(y)), (1000, int(y)), thickness)
                
        # Vertical lines
        for i in range(-20, 21):
            x_bottom = 500 + i * 150
            x_top = 500 + i * 10
            pygame.draw.line(screen, grid_color, (x_top, 400), (x_bottom, 850), 1)

        # --- Overlay Content ---
        # Draw Title with Shadow
        draw_text(screen, "SELF-DRIVING CAR", title_font, (0, 0, 0), 505, 105)
        draw_text(screen, "SELF-DRIVING CAR", title_font, (255, 255, 255), 500, 100)
        draw_text(screen, "RACING GAME", title_font, (0, 0, 0), 505, 175)
        draw_text(screen, "RACING GAME", title_font, accent, 500, 170)
        
        # Subtitle
        draw_text(
            screen,
            "Reinforcement Learning AI  •  Dueling DQN",
            subtitle_font,
            (0, 0, 0),
            502,
            232,
        )
        draw_text(
            screen,
            "Reinforcement Learning AI  •  Dueling DQN",
            subtitle_font,
            (200, 210, 220),
            500,
            230,
        )

        # Model status indicator
        if model_exists():
            draw_text(
                screen,
                "✓ Trained Model Available",
                info_font,
                (0, 0, 0),
                501,
                266,
            )
            draw_text(
                screen,
                "✓ Trained Model Available",
                info_font,
                (100, 255, 100),
                500,
                265,
            )
        else:
            draw_text(
                screen,
                "✗ No Trained Model — Train First",
                info_font,
                (0, 0, 0),
                501,
                266,
            )
            draw_text(
                screen,
                "✗ No Trained Model — Train First",
                info_font,
                (255, 100, 100),
                500,
                265,
            )

        mouse_pos = pygame.mouse.get_pos()

        # Button configurations
        buttons = [
            ("Play Manually", 330, True),
            ("Customize AI Driver", 400, True),
            ("Train RL Agent", 470, True),
            ("Watch AI Drive", 540, model_exists()),
            ("AI Race (3 Laps)", 610, model_exists()),
            ("Reset Trained Model", 680, model_exists()),
            ("Quit Game", 750, True),
        ]

        button_rects = []
        for text, y, enabled in buttons:
            btn_rect = pygame.Rect(300, y - 25, 400, 50)

            if not enabled:
                # Disabled style
                pygame.draw.rect(screen, (20, 25, 30), btn_rect, border_radius=12)
                pygame.draw.rect(
                    screen, (40, 50, 60), btn_rect, width=2, border_radius=12
                )
                draw_text(screen, text, button_font, (80, 90, 100), 500, y)
            elif btn_rect.collidepoint(mouse_pos):
                # Hover style (scaled up slightly)
                hover_rect = btn_rect.inflate(16, 8)
                pygame.draw.rect(screen, (255, 255, 255), hover_rect, border_radius=15)
                draw_text(screen, text, button_font, (0, 0, 0), 500, y)
            else:
                # Normal style
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=12)
                pygame.draw.rect(
                    screen, accent, btn_rect, width=2, border_radius=12
                )
                draw_text(screen, text, button_font, text_color, 500, y)

            button_rects.append((btn_rect, text, enabled))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, text, enabled in button_rects:
                    if rect.collidepoint(mouse_pos) and enabled:
                        if text == "Quit Game":
                            pygame.quit()
                            sys.exit()

                        if text == "Reset Trained Model":
                            import glob

                            model_files = (
                                glob.glob("models/*.pth")
                                + glob.glob("models/*.txt")
                                + glob.glob("models/*.csv")
                            )
                            if model_files:
                                for f in model_files:
                                    os.remove(f)
                                msg = f"Deleted {len(model_files)} file(s)!"
                                msg_color = (255, 50, 50)
                            else:
                                msg = "No trained model found."
                                msg_color = (200, 200, 100)
                            draw_text(screen, msg, button_font, msg_color, 500, 830)
                            pygame.display.flip()
                            pygame.time.delay(1500)
                            break

                        # Visual feedback
                        draw_text(screen, "Launching...", button_font, accent, 500, 830)
                        pygame.display.flip()

                        try:
                            if text == "Play Manually":
                                from src.game import Game

                                game = Game(mode="manual")
                                game.run()
                                # Re-init pygame after game quits
                                pygame.init()
                                screen = pygame.display.set_mode((1000, 850))
                                pygame.display.set_caption(
                                    "Self-Driving Car Racing — RL Agent"
                                )

                            elif text == "Customize AI Driver":
                                customization_menu(screen, clock)

                            elif text == "Train RL Agent":
                                from train import train

                                train()
                                # Re-init pygame
                                pygame.init()
                                screen = pygame.display.set_mode((1000, 850))
                                pygame.display.set_caption(
                                    "Self-Driving Car Racing — RL Agent"
                                )

                            elif text == "Watch AI Drive":
                                from evaluate import evaluate

                                evaluate()
                                pygame.init()
                                screen = pygame.display.set_mode((1000, 850))
                                pygame.display.set_caption(
                                    "Self-Driving Car Racing — RL Agent"
                                )

                            elif text == "AI Race (3 Laps)":
                                from race import race

                                race()
                                pygame.init()
                                screen = pygame.display.set_mode((1000, 850))
                                pygame.display.set_caption(
                                    "Self-Driving Car Racing — RL Agent"
                                )

                        except Exception as e:  # noqa: BLE001
                            print(f"Error launching: {e}")
                            import traceback

                            traceback.print_exc()
                            # Re-init pygame in case of crash
                            try:
                                pygame.init()
                                screen = pygame.display.set_mode((1000, 850))
                                pygame.display.set_caption(
                                    "Self-Driving Car Racing — RL Agent"
                                )
                            except Exception:  # noqa: BLE001, S110
                                pass

                        break

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main_menu()
