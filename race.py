"""
Race Mode: Trained AI car vs bot opponents on a 3-lap race.

Uses CarEnv properly in race mode — no conflicting Game instances.
"""

import os
import time

import pygame
import torch

from ai.dqn import DQN
from src.config import WIN_LAPS
from src.env import CarEnv


def race():
    state_dim = 18  # must match env.state_space
    action_dim = 4
    device = torch.device("cpu")
    policy_net = DQN(state_dim, action_dim).to(device)

    # Load best available model
    loaded = False
    for path in ["models/model.pth", "models/latest_model.pth"]:
        if os.path.exists(path):
            try:
                policy_net.load_state_dict(torch.load(path, map_location=device, weights_only=True))
                print(f"Loaded model: {path}")
                loaded = True
                break
            except Exception as e:  # noqa: BLE001
                print(f"Warning: Could not load {path}: {e}")
    if not loaded:
        print("Error: No trained model found. Please run Train RL Agent first.")
        return

    policy_net.eval()

    # Create environment in race mode — this properly sets up the Game
    # with bot opponents, no conflicting second Game instance
    env = CarEnv(mode="race")
    clock = env.game.clock

    race_num = 0
    while env.game.running:
        race_num += 1
        state = env.reset()
        done = False
        info = {}  # Initialize to prevent UnboundLocalError if loop exits early

        print(f"Race {race_num} — starting…")
        race_start = time.time()

        # Quit events are handled by game._events() inside env.step()
        while not done and env.game.running:

            with torch.no_grad():
                q = policy_net(torch.FloatTensor(state).unsqueeze(0))
                action = q.max(1)[1].item()

            car = env.game.camera_car
            laps = car.laps_completed
            best_lap = car.best_lap_time

            # Build race HUD info
            best_str = f"{best_lap:.1f}s" if best_lap < float("inf") else "--"
            env.game.training_info = (
                f"RACE MODE  |  Lap {laps}/{WIN_LAPS}  |  "
                f"Best Lap: {best_str}  |  "
                f"HP: {car.health}/{car.max_health}  |  "
                f"Speed: {int(car.speed)}"
            )

            # Check race completion
            if laps >= WIN_LAPS:
                elapsed = time.time() - race_start
                env.game.training_info = (
                    f"RACE FINISHED!  |  {WIN_LAPS} Laps in {elapsed:.1f}s  |  "
                    f"Best Lap: {best_str}"
                )
                env.game.step(1 / 30.0, draw=True, action=action)
                pygame.display.flip()
                print(
                    f"Race {race_num} finished! Time: {elapsed:.1f}s, Best lap: {best_str}"
                )
                time.sleep(3.0)
                break

            next_state, _reward, done, info = env.step(action, draw=True)
            clock.tick(60)
            state = next_state

        if done and env.game.running:
            reason = info.get("reason", "") if isinstance(info, dict) else ""
            print(f"Race {race_num} ended: {reason}")
            time.sleep(1.0)


if __name__ == "__main__":
    race()
