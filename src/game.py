import random

import pygame

from src.car import Car
from src.config import (
    DEPTH_SCALE,
    FPS,
    HORIZON_Y,
    LANE_COL,
    NSTRIPS,
    ROAD_SCALE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SEG_LEN,
    SKY_BOT,
    SKY_TOP,
)
from src.hud import HUD
from src.objects import Barricade, TrafficCar, Tree
from src.track import Track

_BOTTOM_Z = DEPTH_SCALE / (SCREEN_HEIGHT - HORIZON_Y)
_BOTTOM_SCALE = 100.0 / _BOTTOM_Z


class Game:
    def __init__(self, mode="train"):
        self.mode = mode
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Self-Driving Car Racing — RL Agent")
        self.clock = pygame.time.Clock()
        self.running = True
        self.training_info = ""

        self.track = Track()
        self.hud = HUD()
        self.reset()

        self._sky = self._build_sky()
        self._bg = self._load_bg()

        # Cache training info font (don't recreate every frame)
        self._info_font = pygame.font.SysFont("Consolas", 24, bold=True)

    def reset(self):
        if self.mode == "race":
            self.cars = [
                Car(mode="race"),
                Car(is_bot=True, bot_level=1, mode="race"),
                Car(is_bot=True, bot_level=2, mode="race"),
                Car(is_bot=True, bot_level=3, mode="race"),
            ]
            self.cars[0].player_x = 0.55
            self.cars[1].player_x = -0.55
            self.cars[2].player_x = 0.0
            self.cars[2].player_z = 200
            self.cars[3].player_x = -0.55
            self.cars[3].player_z = 200
            self.traffic = []  # No random traffic in race mode
        else:
            self.cars = [Car(mode=self.mode)]
            tl = self.track.total_length
            # Spawn traffic cars at well-separated positions
            num_traffic = 5
            spacing = int((tl - 2000) / num_traffic)
            safe_z_positions = [1500 + i * spacing for i in range(num_traffic)]
            self.traffic = [
                TrafficCar(
                    z=z_pos,
                    offset_x=random.uniform(-0.8, 0.8),
                    speed=random.uniform(30, 100),
                )
                for z_pos in safe_z_positions
            ]
        self.camera_car = self.cars[0]

    def _build_sky(self):
        s = pygame.Surface((SCREEN_WIDTH, HORIZON_Y))
        for y in range(HORIZON_Y):
            t = y / max(HORIZON_Y - 1, 1)
            r = max(0, min(255, int(SKY_TOP[0] + t * (SKY_BOT[0] - SKY_TOP[0]))))
            g = max(0, min(255, int(SKY_TOP[1] + t * (SKY_BOT[1] - SKY_TOP[1]))))
            b = max(0, min(255, int(SKY_TOP[2] + t * (SKY_BOT[2] - SKY_TOP[2]))))
            pygame.draw.line(s, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        return s

    def _load_bg(self):
        try:
            raw = pygame.image.load("assets/background.png")
            return pygame.transform.scale(raw, (SCREEN_WIDTH, HORIZON_Y))
        except Exception:  # noqa: BLE001
            return None

    def run(self):
        """Main loop for manual play mode."""
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.step(dt, draw=True)

    def step(self, dt, draw=True, action=None):
        """Advance the game by one tick.

        This is the single entry point for ALL modes (manual, train, race, eval).
        """
        self._events()
        self._update(dt, action)
        if draw:
            self._draw()

    # ─── Input handling ───────────────────────────────────────────────────────

    def _events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (
                e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
            ):
                self.running = False

    # ─── Physics + collisions (ALL modes) ─────────────────────────────────────

    def _update(self, dt, action=None):
        self.debug_rects = []

        # ── Parse input ───────────────────────────────────────────────────────
        throttle, brake, steer_val = 0.0, 0.0, 0.0
        if action is not None:
            self.ai_active = True
            if action == 0:
                steer_val = -1.0
                throttle = 1.0
                brake = 0.0
            elif action == 1:
                steer_val = 1.0
                throttle = 1.0
                brake = 0.0
            elif action == 2:
                steer_val = 0.0
                throttle = 1.0
                brake = 0.0
            elif action == 3:
                steer_val = 0.0
                throttle = 0.0
                brake = 1.0
            self.ai_throttle = throttle
            self.ai_brake = brake
            self.ai_steer = steer_val
        else:
            self.ai_active = False
            keys = pygame.key.get_pressed()
            throttle = 1.0 if (keys[pygame.K_UP] or keys[pygame.K_w]) else 0.0
            brake = 1.0 if (keys[pygame.K_DOWN] or keys[pygame.K_s]) else 0.0
            steer_val = 0.0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                steer_val = -1.0
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                steer_val = 1.0

        # ── Update car physics ────────────────────────────────────────────────
        for idx, car in enumerate(self.cars):
            seg = self.track.get_seg(car.player_z)
            if idx == 0:
                car.update(dt, seg.curve, throttle, brake, steer_val)
            else:
                # Bots get AI-controlled inputs (set in _update_bots)
                car.update(
                    dt,
                    seg.curve,
                    getattr(car, "bot_throttle", 0.8),
                    getattr(car, "bot_brake", 0.0),
                    getattr(car, "bot_steer", 0.0),
                )

            car.update_reward(dt, self.track.total_length)
            car.player_z %= self.track.total_length

            if abs(car.nudge_vel) > 0.001:
                car.player_x += car.nudge_vel * dt
                car.nudge_vel *= max(1.0 - 8.0 * dt, 0.0)

            car.hit_flash = max(0.0, car.hit_flash - dt)

        # ── Update traffic cars (ALL modes, not just race) ────────────────────
        total_len = self.track.total_length
        for tc in self.traffic:
            tc.update(dt, self.camera_car.player_z, total_len)

        # Prevent traffic from forming impossible walls
        for i in range(len(self.traffic)):
            for j in range(i + 1, len(self.traffic)):
                tc1 = self.traffic[i]
                tc2 = self.traffic[j]
                z_diff = tc1.z - tc2.z
                if z_diff < -total_len / 2:
                    z_diff += total_len
                elif z_diff > total_len / 2:
                    z_diff -= total_len
                if abs(z_diff) < 1000:
                    if z_diff > 0:
                        tc1.speed = min(120.0, tc1.speed + 70.0 * dt)
                        tc2.speed = max(20.0, tc2.speed - 70.0 * dt)
                    else:
                        tc2.speed = min(120.0, tc2.speed + 70.0 * dt)
                        tc1.speed = max(20.0, tc1.speed - 70.0 * dt)

        # ── Collision detection (ALL modes) ───────────────────────────────────
        self._check_all_collisions(dt)

        # ── Bot AI + car-vs-car (race mode only) ──────────────────────────────
        if self.mode == "race":
            self._update_bots(dt)
            self._check_car_collisions(dt)

    def _check_all_collisions(self, dt):
        """Check collisions between each car and traffic/scenery.

        This runs in ALL modes (train, race, manual, eval) so the AI
        actually learns to avoid obstacles during training.
        """
        total_len = self.track.total_length
        num_segs = len(self.track.segments)

        for car in self.cars:
            player_z = car.player_z
            player_x = car.player_x
            player_seg_idx = int(player_z / SEG_LEN)

            # ── Traffic car collisions ────────────────────────────────────────
            for tc in self.traffic:
                rel_z = tc.z - player_z
                if rel_z < -total_len / 2:
                    rel_z += total_len
                elif rel_z > total_len / 2:
                    rel_z -= total_len

                # Reward for passing traffic car (camera car only)
                if car == self.camera_car and -100.0 < rel_z < 0.0:
                    tc_id = id(tc)
                    if tc_id not in car.passed_cars and car.last_hit_id != tc_id:
                        car.passed_cars.add(tc_id)
                        car.add_pass_reward()

                if rel_z <= 5.0 or rel_z > 2000.0:
                    continue

                # 3D collision check
                z_overlap = rel_z < 180.0
                x_dist = abs(tc.offset_x - player_x)
                x_overlap = x_dist < 0.55

                if x_overlap and z_overlap:
                    if id(tc) == car.last_hit_id and car.hit_flash > 0.1:
                        continue
                    push_dir = 1.0 if player_x > tc.offset_x else -1.0
                    tc.apply_nudge(-push_dir * 1.5)
                    car.nudge_vel = push_dir * 0.5
                    car.speed *= 0.70
                    car.hit_flash = 0.25
                    car.last_hit_id = id(tc)
                    car.add_collision_penalty(damage=1)

            # ── Scenery collisions (barricades, trees) ────────────────────────
            for offset in range(-2, 8):
                seg_idx = (player_seg_idx + offset) % num_segs
                seg = self.track.segments[seg_idx]
                seg_z = seg.index * SEG_LEN
                rel_z = seg_z - player_z
                if rel_z < -total_len / 2:
                    rel_z += total_len
                elif rel_z > total_len / 2:
                    rel_z -= total_len
                if rel_z <= 5.0 or rel_z > 2000.0:
                    continue

                for obj in seg.objects:
                    if not isinstance(obj, (Barricade, Tree)):
                        continue

                    if isinstance(obj, Barricade):
                        z_overlap = rel_z < 100.0
                        x_overlap = abs(obj.offset_x - player_x) < 0.5
                    else:  # Tree
                        z_overlap = rel_z < 100.0
                        x_overlap = abs(obj.offset_x - player_x) < 0.2

                    if x_overlap and z_overlap:
                        collision_id = f"scenery_{seg.index}_{id(obj)}"
                        if collision_id == car.last_hit_id and car.hit_flash > 0.1:
                            continue

                        bounce_dir = 1.0 if player_x > obj.offset_x else -1.0
                        if isinstance(obj, Barricade):
                            car.nudge_vel = bounce_dir * 0.5
                            car.speed *= 0.5
                            car.hit_flash = 0.20
                        else:
                            car.nudge_vel = bounce_dir * 0.8
                            car.speed *= 0.2
                            car.hit_flash = 0.30
                        car.last_hit_id = collision_id
                        car.add_collision_penalty(damage=1)

    def _update_bots(self, dt):
        """Bot AI logic — race mode only."""
        for idx in range(1, len(self.cars)):
            car = self.cars[idx]

            car.bot_throttle = 1.0
            car.bot_brake = 0.0
            car.bot_steer = 0.0

            # Look ahead to see track curve
            seg = self.track.get_seg(car.player_z + 300)
            target_x = 0.0

            if seg.curve > 2.0:
                car.bot_throttle = 0.6
                target_x = -0.5
            elif seg.curve < -2.0:
                car.bot_throttle = 0.6
                target_x = 0.5

            # Steer towards target
            if car.player_x < target_x - 0.1:
                car.bot_steer = 1.0
            elif car.player_x > target_x + 0.1:
                car.bot_steer = -1.0

            # Random variations based on bot level
            if random.random() < 0.02:
                car.bot_steer += random.uniform(-0.2, 0.2)

            car.bot_steer = max(-1.0, min(1.0, car.bot_steer))

    def _check_car_collisions(self, dt):
        """Car-vs-car collisions — race mode only."""
        total_len = self.track.total_length
        for i in range(len(self.cars)):
            for j in range(i + 1, len(self.cars)):
                c1 = self.cars[i]
                c2 = self.cars[j]

                rel_z = c2.player_z - c1.player_z
                if rel_z < -total_len / 2:
                    rel_z += total_len
                elif rel_z > total_len / 2:
                    rel_z -= total_len

                z_overlap = abs(rel_z) < 200.0
                x_overlap = abs(c1.player_x - c2.player_x) < 0.65

                if z_overlap and x_overlap:
                    # Hit-flash cooldown to prevent per-frame damage spam
                    pair_id = f"car_{id(c1)}_{id(c2)}"
                    if pair_id == c1.last_hit_id and c1.hit_flash > 0.1:
                        continue

                    push_dir = 1.0 if c1.player_x > c2.player_x else -1.0
                    c1.nudge_vel = push_dir * 1.0
                    c2.nudge_vel = -push_dir * 1.0

                    c1.speed *= 0.85
                    c2.speed *= 0.85

                    c1.hit_flash = 0.25
                    c2.hit_flash = 0.25
                    c1.last_hit_id = pair_id
                    c2.last_hit_id = pair_id

                    c1.add_collision_penalty(damage=1)
                    c2.add_collision_penalty(damage=1)

    # ─── Rendering ────────────────────────────────────────────────────────────

    def _draw(self):
        # draw background
        if self._bg:
            cur_seg = self.track.get_seg(self.camera_car.player_z)
            bx = int(-cur_seg.world_x * 0.04) % SCREEN_WIDTH
            for dx in (-SCREEN_WIDTH, 0, SCREEN_WIDTH):
                self.screen.blit(self._bg, (bx + dx, 0))
        else:
            self.screen.blit(self._sky, (0, 0))

        player_z = self.camera_car.player_z
        player_x = self.camera_car.player_x
        player_seg = self.track.get_seg(player_z)
        total_len = self.track.total_length
        road_h = SCREEN_HEIGHT - HORIZON_Y

        # setup screen lines for pseudo-3D
        lines = []
        for i in range(NSTRIPS + 1):
            y = HORIZON_Y + road_h * i // NSTRIPS
            if i == 0:
                lines.append((y, SCREEN_WIDTH // 2, 0, 0.0))
                continue
            z = DEPTH_SCALE / (y - HORIZON_Y)
            world_z = (player_z + z) % total_len
            seg = self.track.get_seg(world_z)
            road_cx_world = seg.world_x - player_seg.world_x - player_x * 800.0
            cx = SCREEN_WIDTH // 2 + int(road_cx_world * ROAD_SCALE / z / 800.0)
            rw = int(ROAD_SCALE / z)
            scale = 100.0 / z
            lines.append((y, cx, rw, scale))

        sprites = []
        # render road segments from back to front
        for i in range(NSTRIPS):
            y_top, cx_top, rw_top, _ = lines[i]
            y_bot, cx_bot, rw_bot, _ = lines[i + 1]

            if y_bot <= HORIZON_Y:
                continue

            z_near = DEPTH_SCALE / (y_bot - HORIZON_Y)
            world_z = (player_z + z_near) % total_len
            seg = self.track.get_seg(world_z)

            # grass
            gc = seg.colors["sand"]
            pygame.draw.polygon(
                self.screen,
                gc,
                [
                    (0, y_top),
                    (cx_top - rw_top, y_top),
                    (cx_bot - rw_bot, y_bot),
                    (0, y_bot),
                ],
            )
            pygame.draw.polygon(
                self.screen,
                gc,
                [
                    (SCREEN_WIDTH, y_top),
                    (cx_top + rw_top, y_top),
                    (cx_bot + rw_bot, y_bot),
                    (SCREEN_WIDTH, y_bot),
                ],
            )

            # rumble strips
            rc = seg.colors["rumble"]
            rrb = max(int(rw_bot * 0.11), 1)
            rrt = max(int(rw_top * 0.11), 1)
            pygame.draw.polygon(
                self.screen,
                rc,
                [
                    (cx_top - rw_top - rrt, y_top),
                    (cx_top - rw_top, y_top),
                    (cx_bot - rw_bot, y_bot),
                    (cx_bot - rw_bot - rrb, y_bot),
                ],
            )
            pygame.draw.polygon(
                self.screen,
                rc,
                [
                    (cx_top + rw_top, y_top),
                    (cx_top + rw_top + rrt, y_top),
                    (cx_bot + rw_bot + rrb, y_bot),
                    (cx_bot + rw_bot, y_bot),
                ],
            )

            # lane markers
            if seg.colors["lane"]:
                for _, sign in (("l", -1), ("r", 1)):
                    cx_r_top = cx_top + sign * (rw_top + rrt // 2)
                    cx_r_bot = cx_bot + sign * (rw_bot + rrb // 2)
                    lw_t = max(int(rrt * 0.22), 1)
                    lw_b = max(int(rrb * 0.22), 1)
                    pygame.draw.polygon(
                        self.screen,
                        (255, 255, 255),
                        [
                            (cx_r_top - lw_t, y_top),
                            (cx_r_top + lw_t, y_top),
                            (cx_r_bot + lw_b, y_bot),
                            (cx_r_bot - lw_b, y_bot),
                        ],
                    )

            # road surface
            rd = seg.colors["road"]
            pygame.draw.polygon(
                self.screen,
                rd,
                [
                    (cx_top - rw_top, y_top),
                    (cx_top + rw_top, y_top),
                    (cx_bot + rw_bot, y_bot),
                    (cx_bot - rw_bot, y_bot),
                ],
            )

            # horizontal grid lines for depth
            if seg.index % 8 == 0:
                lw_y = max(int(rw_bot * 0.022), 1)
                pygame.draw.line(
                    self.screen,
                    (115, 120, 125),
                    (cx_bot - rw_bot, y_bot),
                    (cx_bot + rw_bot, y_bot),
                    width=lw_y,
                )

            # center dashes
            if seg.colors["lane"]:
                for frac in (-0.335, 0.335):
                    lxb = int(rw_bot * frac)
                    lwb = max(int(rw_bot * 0.025), 1)
                    lxt = int(rw_top * frac)
                    lwt = max(int(rw_top * 0.025), 1)
                    pygame.draw.polygon(
                        self.screen,
                        LANE_COL,
                        [
                            (cx_top + lxt - lwt, y_top),
                            (cx_top + lxt + lwt, y_top),
                            (cx_bot + lxb + lwb, y_bot),
                            (cx_bot + lxb - lwb, y_bot),
                        ],
                    )

        # collect scenery objects
        player_seg_idx = int(player_z / SEG_LEN)
        num_segs = len(self.track.segments)
        for offset in range(-2, 35):
            seg_idx = (player_seg_idx + offset) % num_segs
            seg = self.track.segments[seg_idx]
            seg_z = seg.index * SEG_LEN
            rel_z = seg_z - player_z
            if rel_z < -total_len / 2:
                rel_z += total_len
            elif rel_z > total_len / 2:
                rel_z -= total_len

            if rel_z <= 5.0 or rel_z > 2000.0:
                continue

            for obj in seg.objects:
                ox = (
                    seg.world_x - player_seg.world_x - player_x * 800.0
                ) + obj.offset_x * 800.0
                sc = 100.0 / rel_z
                sx = SCREEN_WIDTH // 2 + int(ox * ROAD_SCALE * sc / 800.0 / 100.0)
                sy = HORIZON_Y + int(DEPTH_SCALE / rel_z)
                sprites.append((rel_z, obj, sx, sy, sc))

        # collect traffic cars
        for tc in self.traffic:
            rel_z = tc.z - player_z
            if rel_z < -total_len / 2:
                rel_z += total_len
            elif rel_z > total_len / 2:
                rel_z -= total_len
            if rel_z <= 0 or rel_z > NSTRIPS * 200:
                continue
            tc_seg = self.track.get_seg(tc.z % total_len)
            ox = (
                tc_seg.world_x - player_seg.world_x - player_x * 800.0
            ) + tc.offset_x * 800.0
            tc_sc = 100.0 / rel_z
            tsx = SCREEN_WIDTH // 2 + int(ox * ROAD_SCALE * tc_sc / 800.0 / 100.0)
            tsy = HORIZON_Y + int(DEPTH_SCALE / rel_z)
            sprites.append((rel_z, tc, tsx, tsy, tc_sc))

        # collect other cars (race mode)
        for car in self.cars:
            if car == self.camera_car:
                continue
            rel_z = car.player_z - player_z
            if rel_z < -total_len / 2:
                rel_z += total_len
            elif rel_z > total_len / 2:
                rel_z -= total_len
            if rel_z <= 0 or rel_z > NSTRIPS * 200:
                continue

            c_seg = self.track.get_seg(car.player_z % total_len)
            ox = (
                c_seg.world_x - player_seg.world_x - player_x * 800.0
            ) + car.player_x * 800.0
            c_sc = 100.0 / rel_z
            tsx = SCREEN_WIDTH // 2 + int(ox * ROAD_SCALE * c_sc / 800.0 / 100.0)
            tsy = HORIZON_Y + int(DEPTH_SCALE / rel_z)
            sprites.append((rel_z, car, tsx, tsy, c_sc))

        # sort by depth and draw
        sprites.sort(key=lambda e: e[0], reverse=True)
        for z, obj, sx, sy, scale in sprites:
            if HORIZON_Y - 20 < sy < SCREEN_HEIGHT + 300:
                obj.draw(self.screen, sx, sy, scale)

        # draw our car
        self.camera_car.draw(self.screen)

        # crash red flash
        if self.camera_car.hit_flash > 0:
            alpha = int(min(self.camera_car.hit_flash / 0.25, 1.0) * 110)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 30, 30, alpha))
            self.screen.blit(overlay, (0, 0))

        # Draw debug boxes
        for rx, ry, rw, rh, color in self.debug_rects:
            pygame.draw.rect(
                self.screen, color, (int(rx), int(ry), int(rw), int(rh)), 2
            )

        # render hud
        self.hud.draw(self.screen, self.camera_car, self)

        # Training / race info overlay (uses cached font)
        if self.training_info:
            info_surf = self._info_font.render(self.training_info, True, (0, 255, 204))
            bg_surf = pygame.Surface(
                (info_surf.get_width() + 20, info_surf.get_height() + 10),
                pygame.SRCALPHA,
            )
            bg_surf.fill((0, 0, 0, 180))
            self.screen.blit(bg_surf, (10, 80))
            self.screen.blit(info_surf, (20, 85))

        pygame.display.flip()
