import math

import pygame

from src.config import (
    ACCEL,
    BRAKE,
    CENTRIFUGAL,
    MANUAL_HEALTH,
    MAX_SPEED,
    OFFROAD_SLOW,
    RACE_HEALTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    STEER_SPD,
    TRAIN_HEALTH,
)
from src.profile import PlayerProfile

CAR_W = 200
CAR_H = 125
CAR_X = SCREEN_WIDTH // 2
CAR_Y = SCREEN_HEIGHT - 80


class Car:
    def __init__(self, is_bot=False, bot_level=0, mode="train"):
        self.is_bot = is_bot
        self.mode = mode
        self.profile = PlayerProfile()

        self.max_speed = MAX_SPEED
        self.accel = ACCEL
        self.brake = BRAKE
        self.steer_spd = STEER_SPD

        if not is_bot:
            self.max_speed *= self.profile.top_speed_mod
            self.accel *= self.profile.accel_mod
            self.steer_spd *= self.profile.handling_mod
        else:
            self.max_speed *= 0.8 + 0.05 * bot_level
            self.accel *= 0.8
            self.profile.color = (100, 100, 100)  # Gray for bots

        self.speed = 0.0
        self.player_x = 0.0  # road offset: 0=centre, ±1=edges
        self.player_z = 0.0  # distance along track
        self.abs_z = 0.0  # absolute distance, not modulo'd
        self.lean = 0.0  # visual tilt degrees
        self.prev_speed = 0.0  # for computing acceleration delta

        # Collision state
        self.nudge_vel = 0.0
        self.hit_flash = 0.0
        self.last_hit_id = None

        # Health system: mode-dependent
        if mode == "train":
            self.max_health = TRAIN_HEALTH
        elif mode == "race":
            self.max_health = RACE_HEALTH
        else:
            self.max_health = MANUAL_HEALTH
        self.health = self.max_health

        self.passed_cars = set()
        self.won = False

        # Reward System
        self.reward = 0.0
        self.total_reward = 0.0
        self.max_lap = 0
        self.max_checkpoint = -1
        self.CHECKPOINTS_PER_LAP = (
            8  # More granular checkpoints for better reward shaping
        )

        # Lap Timing
        self.lap_start_time = pygame.time.get_ticks() / 1000.0
        self.last_lap_time = 0.0
        self.best_lap_time = float("inf")
        self.laps_completed = 0

        self._img = None
        self._load()

    def _load(self):
        try:
            raw = pygame.image.load("assets/car.png").convert_alpha()

            # Apply color tint
            color_surface = pygame.Surface(raw.get_size(), pygame.SRCALPHA)
            color_surface.fill((*self.profile.color, 255))
            raw.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            self._img = pygame.transform.scale(raw, (CAR_W, CAR_H))
        except Exception:  # noqa: BLE001
            self._img = None

    def update(self, dt, curve, throttle=0.0, brake=0.0, steer_val=0.0):
        self.prev_speed = self.speed
        speed_ratio = abs(self.speed) / self.max_speed
        drag = 24.0 + 0.00015 * (self.speed**2)

        if throttle > 0.1:
            # Scale engine force with accel
            engine_force = (
                (61.5 * (self.accel / ACCEL)) * (1.3 - 0.3 * speed_ratio) * throttle
            )
            self.speed = min(self.speed + (engine_force - drag) * dt, self.max_speed)
        elif brake > 0.1:
            self.speed = max(self.speed - (120.0 * brake + drag) * dt, 0.0)
        else:
            # coasting
            if self.speed > 0:
                self.speed = max(self.speed - drag * dt, 0.0)

        # Hard cap to ensure reverse is completely mathematically impossible
        self.speed = max(self.speed, 0.0)

        steer = 0.0
        if self.speed != 0:
            steer_sensitivity = 0.3 + 0.7 * math.sin(
                min(speed_ratio, 1.0) * math.pi / 2.0
            )
            direction = 1.0 if self.speed > 0 else -1.0
            rate = self.steer_spd * steer_sensitivity * direction * dt

            if steer_val < -0.1:
                steer = rate * steer_val
                self.lean = max(self.lean - 2.2, -13)
            elif steer_val > 0.1:
                steer = rate * steer_val
                self.lean = min(self.lean + 2.2, 13)
        if steer == 0:
            self.lean *= 0.82  # snap back

        self.player_x += steer

        # push outward on curves
        self.player_x -= curve * CENTRIFUGAL * self.speed * dt

        # off-road slowdown
        if abs(self.player_x) > 1.0:
            self.speed *= OFFROAD_SLOW
            if self.speed > 120.0:
                self.speed = max(self.speed - 300.0 * dt, 120.0)
        # Prevent car from going far off-road
        self.player_x = max(-1.1, min(1.1, self.player_x))

        # Advance along track
        delta_z = self.speed * dt
        self.player_z += delta_z
        self.abs_z += delta_z

    def draw(self, surface: pygame.Surface, sx=None, sy=None, scale=1.0):
        if not self._img:
            self._fallback(surface)
            return

        lean_scaled = int(self.lean)
        img = pygame.transform.rotate(self._img, lean_scaled)

        if sx is not None and sy is not None:
            # Draw shadow
            sw, sh = int(CAR_W * scale * 0.9), int(CAR_H * scale * 0.15)
            shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 100), (0, 0, sw, sh))
            surface.blit(shadow, (sx - sw // 2, sy - sh // 2))

            # Draw as a projected remote car sprite
            w, h = int(CAR_W * scale), int(CAR_H * scale)
            img = pygame.transform.scale(img, (w, h))
            rect = img.get_rect(midbottom=(sx, sy))
            surface.blit(img, rect)
        else:
            # Draw shadow
            sw, sh = int(CAR_W * 0.9), int(CAR_H * 0.15)
            shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 120), (0, 0, sw, sh))
            surface.blit(shadow, (CAR_X - sw // 2, CAR_Y + CAR_H // 2 - sh // 2))

            # Draw as the main camera car
            rect = img.get_rect(center=(CAR_X, CAR_Y))
            surface.blit(img, rect)

    def _fallback(self, screen):
        surf = pygame.Surface((CAR_W, CAR_H), pygame.SRCALPHA)

        # Body
        pygame.draw.rect(
            surf,
            (200, 30, 30),
            (0, CAR_H // 3, CAR_W, CAR_H * 2 // 3),
            border_radius=10,
        )
        # Cabin
        cab_m = int(CAR_W * 0.12)
        pygame.draw.rect(
            surf,
            (150, 20, 20),
            (cab_m, 0, CAR_W - cab_m * 2, CAR_H * 2 // 3),
            border_radius=12,
        )
        gw = int(CAR_W * 0.56)
        gh = int(CAR_H * 0.30)
        gx = (CAR_W - gw) // 2
        pygame.draw.rect(
            surf, (100, 160, 200), (gx, int(CAR_H * 0.06), gw, gh), border_radius=5
        )
        pygame.draw.rect(
            surf, (180, 210, 240), (gx + gw // 5, int(CAR_H * 0.09), gw // 5, gh // 2)
        )

        # Highlight stripe
        pygame.draw.rect(
            surf,
            (230, 50, 50),
            (0, CAR_H // 3, CAR_W, int(CAR_H * 0.07)),
            border_radius=5,
        )

        # Tail-lights
        tl_w, tl_h = int(CAR_W * 0.18), int(CAR_H * 0.10)
        tl_y = int(CAR_H * 0.75)
        pygame.draw.rect(
            surf, (220, 10, 10), (int(CAR_W * 0.04), tl_y, tl_w, tl_h), border_radius=2
        )
        pygame.draw.rect(
            surf,
            (220, 10, 10),
            (CAR_W - int(CAR_W * 0.04) - tl_w, tl_y, tl_w, tl_h),
            border_radius=2,
        )
        # Bright cores
        pygame.draw.rect(
            surf,
            (255, 120, 120),
            (int(CAR_W * 0.06), tl_y + tl_h // 4, tl_w // 2, tl_h // 2),
        )
        pygame.draw.rect(
            surf,
            (255, 120, 120),
            (
                CAR_W - int(CAR_W * 0.06) - tl_w // 2,
                tl_y + tl_h // 4,
                tl_w // 2,
                tl_h // 2,
            ),
        )

        # Bumper
        pygame.draw.rect(
            surf,
            (50, 50, 55),
            (0, CAR_H - int(CAR_H * 0.09), CAR_W, int(CAR_H * 0.09)),
            border_radius=6,
        )

        # Licence plate
        pl_w, pl_h = int(CAR_W * 0.30), int(CAR_H * 0.08)
        pygame.draw.rect(
            surf,
            (240, 240, 180),
            ((CAR_W - pl_w) // 2, CAR_H - int(CAR_H * 0.09) - pl_h - 1, pl_w, pl_h),
        )

        # Outline
        pygame.draw.rect(
            surf,
            (20, 20, 25),
            (0, CAR_H // 3, CAR_W, CAR_H * 2 // 3),
            width=2,
            border_radius=10,
        )
        pygame.draw.rect(
            surf,
            (15, 15, 20),
            (cab_m, 0, CAR_W - cab_m * 2, CAR_H * 2 // 3),
            width=2,
            border_radius=12,
        )

        rot = pygame.transform.rotate(surf, -self.lean)
        rect = rot.get_rect(center=(CAR_X, CAR_Y))
        screen.blit(rot, rect)

    def update_reward(self, dt, track_length):
        """Compute per-step reward. Called once per game step."""
        self.reward = 0.0
        step_reward = 0.0

        # ── Speed reward ──────────────────────────────────────────────────────
        # Reward proportional to speed — strong signal to keep moving
        if self.speed > 5.0:
            step_reward += (self.speed / self.max_speed) * 2.0 * (dt * 60.0)
        else:
            step_reward -= 2.0 * (dt * 60.0)

        # ── Lane discipline ───────────────────────────────────────────────────
        if abs(self.player_x) <= 1.0:
            step_reward += (1.0 - abs(self.player_x)) * 1.0 * (dt * 60.0)

        # Penalise going off-road
        if abs(self.player_x) > 1.0:
            step_reward -= 8.0 * (dt * 60.0)

        # ── Survival bonus ────────────────────────────────────────────────────
        # Small per-step bonus for staying alive (encourages longevity)
        step_reward += 0.1 * (dt * 60.0)

        # ── Checkpoint and lap rewards ────────────────────────────────────────
        if track_length > 0:
            lap_float = self.abs_z / track_length
            current_lap = int(lap_float)

            fractional_lap = lap_float % 1.0
            current_checkpoint = int(fractional_lap * self.CHECKPOINTS_PER_LAP)

            if current_lap > self.max_lap:
                # Lap completion
                current_time = pygame.time.get_ticks() / 1000.0
                lap_time = current_time - self.lap_start_time
                self.last_lap_time = lap_time
                self.laps_completed += 1
                if lap_time < self.best_lap_time and lap_time > 1.0:
                    self.best_lap_time = lap_time
                self.lap_start_time = current_time

                # Give reward proportional to how fast the lap was
                time_bonus = max(0, 60.0 - lap_time)
                step_reward += 50.0 + time_bonus  # Increased lap reward

                self.max_lap = current_lap
                self.max_checkpoint = -1
            elif (
                current_lap == self.max_lap and current_checkpoint > self.max_checkpoint
            ):
                step_reward += 8.0  # Checkpoint bonus
                self.max_checkpoint = current_checkpoint

        self.reward = step_reward
        self.total_reward += step_reward

    def add_collision_penalty(self, damage=1):
        """Apply collision damage and reward penalty.

        Args:
            damage: amount of health to subtract
        """
        self.health = max(0, self.health - damage)

        # Collision penalty scaled so it hurts but doesn't destroy gradient learning
        self.reward -= 100.0
        self.total_reward -= 100.0

    def add_pass_reward(self):
        """Reward for cleanly passing a traffic car."""
        self.reward += 15.0
        self.total_reward += 15.0
