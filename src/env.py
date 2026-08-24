import numpy as np

from src.config import MAX_SPEED, WIN_LAPS
from src.game import Game
from src.objects import Barricade


class CarEnv:
    """Reinforcement Learning environment wrapping the racing game.

    State space (18 dimensions):
        [0]  speed_norm        — current speed / MAX_SPEED
        [1]  speed_delta       — acceleration since last step (clamped)
        [2]  player_x          — lateral road position [-1.1, 1.1]
        [3]  lean_norm         — car lean / 13.0 (steering visual)
        [4]  curve_near        — road curvature +200 units ahead
        [5]  curve_mid         — road curvature +400 units ahead
        [6]  curve_far         — road curvature +600 units ahead
        [7]  curve_vfar        — road curvature +1000 units ahead
        [8]  health_norm       — current health / max_health
        [9-11]  obstacle 1     — (dx, dist_norm, speed_norm)
        [12-14] obstacle 2     — (dx, dist_norm, speed_norm)
        [15-17] obstacle 3     — (dx, dist_norm, speed_norm)

    Action space (4 discrete actions):
        0 = steer left  + throttle
        1 = steer right + throttle
        2 = straight    + throttle
        3 = brake       + straight
    """

    def __init__(self, mode="train"):
        self.mode = mode
        self.game = Game(mode=mode)
        self.action_space = 4
        self.state_space = 18
        self.max_steps = 12000
        self.current_step = 0
        self.off_road_steps = 0
        self.low_speed_steps = 0

    def reset(self):
        """Reset environment for a new episode."""
        self.game.reset()
        self.current_step = 0
        self.low_speed_steps = 0
        self.off_road_steps = 0
        # Initial step to populate state properly
        self.game.step(1 / 30.0, draw=False, action=2)
        return self.get_state()

    def step(self, action, draw=False):
        """Take one action and return (next_state, reward, done, info)."""
        dt = 1 / 30.0
        reward_sum = 0
        done = False

        # Single frame per decision
        self.game.step(dt, draw=draw, action=action)
        self.current_step += 1

        # Per-step reward from physics engine
        reward_sum += self.game.camera_car.reward

        # Small steering penalty to discourage constant left-right zig-zag
        if action == 0 or action == 1:
            reward_sum -= 0.05 * (dt * 60.0)

        # ── Termination conditions ────────────────────────────────────────────

        # Death: health depleted
        if self.game.camera_car.health <= 0:
            reward_sum -= 150.0  # Death penalty
            done = True
            return self.get_state(), reward_sum, done, {"reason": "death"}

        # Win: completed enough laps
        if self.game.camera_car.laps_completed >= WIN_LAPS:
            self.game.camera_car.won = True
            reward_sum += 500.0
            done = True
            return self.get_state(), reward_sum, done, {"reason": "win"}

        # Max steps safety net
        if self.current_step >= self.max_steps:
            done = True
            return self.get_state(), reward_sum, done, {"reason": "max_steps"}

        # Stuck detection: truly stopped for 4 seconds
        if self.current_step > 60 and self.game.camera_car.speed < 5.0:
            self.low_speed_steps += 1
            if self.low_speed_steps > 120:
                done = True
                reward_sum -= 200.0
                return self.get_state(), reward_sum, done, {"reason": "stuck"}
        else:
            self.low_speed_steps = 0

        # Off-road timeout: 1.5 seconds off-road
        if abs(self.game.camera_car.player_x) > 1.0:
            self.off_road_steps += 1
            if self.off_road_steps > 45:
                done = True
                reward_sum -= 150.0
                return self.get_state(), reward_sum, done, {"reason": "off_road"}
        else:
            self.off_road_steps = 0

        state = self.get_state()
        return state, reward_sum, done, {}

    def get_state(self):
        """Build the 18-dimensional state vector."""
        car = self.game.camera_car
        track = self.game.track

        # ── Core features ─────────────────────────────────────────────────────
        speed_norm = car.speed / MAX_SPEED
        speed_delta = np.clip((car.speed - car.prev_speed) / MAX_SPEED, -0.5, 0.5)
        px_norm = np.clip(car.player_x, -1.1, 1.1)
        lean_norm = car.lean / 13.0
        health_norm = car.health / max(car.max_health, 1)

        # ── Lookahead curvature (4 distances) ─────────────────────────────────
        z = car.player_z
        c_near = track.get_seg(z + 200).curve / 3.0
        c_mid = track.get_seg(z + 400).curve / 3.0
        c_far = track.get_seg(z + 600).curve / 3.0
        c_vfar = track.get_seg(z + 1000).curve / 3.0

        # ── Obstacle detection ────────────────────────────────────────────────
        obstacles = []

        # Traffic cars
        for tc in self.game.traffic:
            rel_z = tc.z - z
            if rel_z < -track.total_length / 2:
                rel_z += track.total_length
            elif rel_z > track.total_length / 2:
                rel_z -= track.total_length
            if 0 < rel_z < 2000:
                obstacles.append(
                    {
                        "rel_z": rel_z,
                        "dx": tc.offset_x - car.player_x,
                        "speed": tc.speed / 120.0,
                    }
                )

        # Race opponents
        if self.game.mode == "race":
            for oc in self.game.cars:
                if oc == car:
                    continue
                rel_z = oc.player_z - z
                if rel_z < -track.total_length / 2:
                    rel_z += track.total_length
                elif rel_z > track.total_length / 2:
                    rel_z -= track.total_length
                if 0 < rel_z < 2000:
                    obstacles.append(
                        {
                            "rel_z": rel_z,
                            "dx": oc.player_x - car.player_x,
                            "speed": oc.speed / 120.0,
                        }
                    )

        # Barricades (static objects on road)
        player_seg_idx = int(z / track.seg_len)
        num_segs = len(track.segments)
        for offset in range(15):
            seg_idx = (player_seg_idx + offset) % num_segs
            seg = track.segments[seg_idx]
            rel_z = (seg.index * track.seg_len) - z
            if rel_z < -track.total_length / 2:
                rel_z += track.total_length
            elif rel_z > track.total_length / 2:
                rel_z -= track.total_length
            if 0 < rel_z < 2000:
                for obj in seg.objects:
                    if isinstance(obj, Barricade):
                        obstacles.append(
                            {
                                "rel_z": rel_z,
                                "dx": obj.offset_x - car.player_x,
                                "speed": 0.0,
                            }
                        )

        # Sort by closeness
        obstacles.sort(key=lambda x: x["rel_z"])

        # Pack 3 closest obstacles into state vector
        obs_features = []
        for i in range(3):
            if i < len(obstacles):
                obs = obstacles[i]
                dist_norm = obs["rel_z"] / 2000.0
                dx_clamped = np.clip(obs["dx"], -1.0, 1.0)
                obs_features.extend([dx_clamped, dist_norm, obs["speed"]])
            else:
                obs_features.extend([0.0, 1.0, 1.0])

        state = [
            speed_norm,
            speed_delta,
            px_norm,
            lean_norm,
            c_near,
            c_mid,
            c_far,
            c_vfar,
            health_norm,
        ] + obs_features

        return np.array(state, dtype=np.float32)
