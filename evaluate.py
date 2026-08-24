"""
Watch the trained AI drive the car.

Loads the best trained model and runs it in pure greedy mode (no randomness).
Uses the same CarEnv and physics as training for perfect consistency.
"""

import os
import time

import pygame
import torch

from ai.dqn import DQN
from src.env import CarEnv


def evaluate():
    env = CarEnv(mode="manual")  # manual mode for generous health

    state_dim = env.state_space
    action_dim = env.action_space
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
    clock = env.game.clock

    episode = 0

    while env.game.running:
        episode += 1
        state = env.reset()
        total_reward = 0.0
        collisions = 0
        prev_health = env.game.camera_car.health
        done = False

        print(f"Watch Episode {episode} — starting…")

        while not done and env.game.running:
            # Quit events are handled by game._events() inside env.step()

            # Pure greedy inference (no randomness)
            with torch.no_grad():
                q = policy_net(torch.FloatTensor(state).unsqueeze(0))
                action = q.max(1)[1].item()

            env.game.training_info = (
                f"WATCH AI PLAY  |  Episode {episode}  |  "
                f"Score: {int(total_reward)}  |  Collisions: {collisions}  |  "
                f"HP: {env.game.camera_car.health}/{env.game.camera_car.max_health}"
            )
            next_state, reward, done, info = env.step(action, draw=True)

            clock.tick(60)

            total_reward += reward

            # Track collisions via health change
            curr_health = env.game.camera_car.health
            if curr_health < prev_health:
                collisions += prev_health - curr_health
                prev_health = curr_health

            state = next_state

        reason = info.get("reason", "unknown") if isinstance(info, dict) else ""
        print(
            f"Watch Episode {episode} finished — Score: {int(total_reward)}, "
            f"Collisions: {collisions}, Reason: {reason}"
        )

        if env.game.running and done:
            time.sleep(0.6)


if __name__ == "__main__":
    evaluate()
