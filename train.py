"""
Train a Dueling DQN agent to drive the self-driving car.

Features:
  - Dueling DQN with Double DQN target computation
  - Prioritized Experience Replay (PER)
  - Episode-based epsilon decay
  - Periodic greedy evaluation with best-model checkpointing
  - CSV logging for training analytics
  - Graceful save on window close
"""

import atexit
import csv
import os
import random

import matplotlib
import numpy as np
import pygame
import torch
from torch import nn, optim

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ai.dqn import DQN
from ai.replay_buffer import PrioritizedReplayBuffer
from src.env import CarEnv


def train():
    env = CarEnv(mode="train")

    state_dim = env.state_space  # 18
    action_dim = env.action_space  # 4

    device = torch.device("cpu")

    policy_net = DQN(state_dim, action_dim).to(device)
    target_net = DQN(state_dim, action_dim).to(device)

    # ── Resume from checkpoint ────────────────────────────────────────────────
    resume_path = "models/latest_model.pth"
    epsilon_path = "models/latest_epsilon.txt"
    epsilon = 1.0  # default, will be overwritten if checkpoint exists

    if os.path.exists(resume_path):
        print(f"Resuming from checkpoint: {resume_path}")
        try:
            ckpt = torch.load(resume_path, map_location=device, weights_only=True)
            policy_net.load_state_dict(ckpt)
            if os.path.exists(epsilon_path):
                with open(epsilon_path) as f:
                    epsilon = float(f.read().strip())
                print(f"Resuming epsilon from {epsilon:.4f}")
        except Exception as e:  # noqa: BLE001
            print(f"Warning: Could not load checkpoint ({e}). Starting fresh.")
            epsilon = 1.0

    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()

    optimizer = optim.Adam(policy_net.parameters(), lr=3e-4)
    # StepLR is stepped once per episode (not per optimization step) — intentional
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=600, gamma=0.5)
    memory = PrioritizedReplayBuffer(
        capacity=100000, alpha=0.6, beta_start=0.4, beta_frames=300000
    )

    # ── Hyperparameters ───────────────────────────────────────────────────────
    batch_size = 128
    gamma = 0.99
    tau = 0.005  # soft target-network update coefficient
    epsilon_end = 0.05
    epsilon_decay = 0.995  # multiplied once per episode
    num_episodes = 1500

    episode_rewards = []
    collision_counts = []
    episode_steps = []
    best_eval_reward = -float("inf")

    # ── CSV logging ───────────────────────────────────────────────────────────
    os.makedirs("models", exist_ok=True)
    log_path = "models/training_log.csv"
    log_exists = os.path.exists(log_path)
    log_file = open(log_path, "a", newline="")  # noqa: SIM115
    atexit.register(log_file.close)  # Ensure file is closed even on unhandled exceptions
    log_writer = csv.writer(log_file)
    if not log_exists:
        log_writer.writerow(
            ["episode", "reward", "epsilon", "collisions", "steps", "laps", "best_eval"]
        )

    print("=" * 60)
    print("TRAINING STARTED — Dueling DQN + Prioritized Replay")
    print(f"  State dim: {state_dim}  |  Action dim: {action_dim}")
    print(f"  Epsilon: {epsilon:.3f}  |  Episodes: {num_episodes}")
    print("=" * 60)

    for episode in range(num_episodes):
        moving_avg = np.mean(episode_rewards[-20:]) if episode_rewards else 0.0

        state = env.reset()
        total_reward = 0.0
        done = False
        collisions = 0
        step_count = 0
        prev_health = env.game.camera_car.health

        # ── Periodic greedy evaluation (every 30 episodes) ────────────────────
        if episode > 0 and episode % 30 == 0:
            eval_reward = _run_eval(
                env, policy_net, device, episode, epsilon, moving_avg
            )
            if eval_reward > best_eval_reward:
                best_eval_reward = eval_reward
                print(f"  --> New best eval score: {eval_reward:.1f}  Saving model…")
                torch.save(policy_net.state_dict(), "models/model.pth")
            state = env.reset()

            if not env.game.running:
                _save_and_exit(
                    policy_net,
                    epsilon,
                    best_eval_reward,
                    episode_rewards,
                    collision_counts,
                    log_file,
                )
                return

        # ── Training episode ──────────────────────────────────────────────────
        while not done:
            if not env.game.running:
                _save_and_exit(
                    policy_net,
                    epsilon,
                    best_eval_reward,
                    episode_rewards,
                    collision_counts,
                    log_file,
                )
                return

            step_count += 1

            # ε-greedy action selection
            if random.random() < epsilon:
                action = random.randrange(action_dim)
            else:
                with torch.no_grad():
                    st = torch.FloatTensor(state).unsqueeze(0).to(device)
                    action = policy_net(st).max(1)[1].item()

            env.game.training_info = (
                f"Ep: {episode + 1}/{num_episodes}  |  ε={epsilon:.3f}  |  "
                f"Score: {total_reward:.1f}  |  20-avg: {moving_avg:.1f}  |  "
                f"HP: {env.game.camera_car.health}/{env.game.camera_car.max_health}"
            )
            next_state, reward, done, _info = env.step(action, draw=True)
            env.game.clock.tick(0)  # uncapped: maximise training throughput
            pygame.event.pump()

            # Track collisions
            curr_health = env.game.camera_car.health
            if curr_health < prev_health:
                collisions += prev_health - curr_health
                prev_health = curr_health

            # Store transition in prioritized buffer
            memory.push(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward

            # ── Learn from experience replay ──────────────────────────────────
            if len(memory) >= batch_size:
                _learn(
                    policy_net,
                    target_net,
                    optimizer,
                    memory,
                    batch_size,
                    gamma,
                    tau,
                    device,
                )

        # ── End of episode bookkeeping ────────────────────────────────────────
        episode_rewards.append(total_reward)
        collision_counts.append(collisions)
        episode_steps.append(step_count)

        # Decay epsilon ONCE per episode
        epsilon = max(epsilon_end, epsilon * epsilon_decay)

        # Step LR scheduler
        if len(memory) >= batch_size:
            scheduler.step()

        # Save on high-scoring training episodes
        if total_reward > 3000 and total_reward > best_eval_reward:
            best_eval_reward = total_reward
            torch.save(policy_net.state_dict(), "models/model.pth")
            print(f"  --> Training ep {episode + 1} scored {total_reward:.0f}! Saved.")

        # CSV log
        laps = env.game.camera_car.laps_completed
        log_writer.writerow(
            [
                episode + 1,
                f"{total_reward:.1f}",
                f"{epsilon:.4f}",
                collisions,
                step_count,
                laps,
                f"{best_eval_reward:.1f}",
            ]
        )
        log_file.flush()

        print(
            f"Episode {episode + 1:4d} | "
            f"Reward: {total_reward:8.1f} | "
            f"ε: {epsilon:.3f} | "
            f"Collisions: {collisions} | "
            f"Steps: {step_count} | "
            f"Laps: {laps}"
        )

    # ── Training complete ─────────────────────────────────────────────────────
    print("\nTraining finished.")
    _save_and_exit(
        policy_net,
        epsilon,
        best_eval_reward,
        episode_rewards,
        collision_counts,
        log_file,
    )


def _run_eval(env, policy_net, device, episode, epsilon, moving_avg):
    """Run a single greedy evaluation episode."""
    eval_state = env.reset()
    eval_done = False
    eval_reward = 0.0

    while not eval_done:
        if not env.game.running:
            return eval_reward

        env.game.training_info = (
            f"*** EVAL (Ep {episode}) ***  "
            f"Score: {eval_reward:.1f}  |  ε={epsilon:.3f}  |  "
            f"20-ep avg: {moving_avg:.1f}"
        )
        with torch.no_grad():
            st = torch.FloatTensor(eval_state).unsqueeze(0).to(device)
            eval_action = policy_net(st).max(1)[1].item()

        eval_state, rwd, eval_done, _ = env.step(eval_action, draw=True)
        eval_reward += rwd
        env.game.clock.tick(60)

    return eval_reward


def _learn(policy_net, target_net, optimizer, memory, batch_size, gamma, tau, device):
    """One step of Double DQN learning with PER."""
    (states_b, actions_b, rewards_b, next_states_b, dones_b, indices, weights) = (
        memory.sample(batch_size)
    )

    states_t = torch.FloatTensor(states_b).to(device)
    actions_t = torch.LongTensor(actions_b).unsqueeze(1).to(device)
    rewards_t = torch.FloatTensor(rewards_b).unsqueeze(1).to(device)
    next_states_t = torch.FloatTensor(next_states_b).to(device)
    dones_t = torch.FloatTensor(dones_b).unsqueeze(1).to(device)
    weights_t = torch.FloatTensor(weights).unsqueeze(1).to(device)

    # Current Q-values for chosen actions
    q_values = policy_net(states_t).gather(1, actions_t)

    # Double DQN: policy_net picks action, target_net evaluates it
    with torch.no_grad():
        next_actions = policy_net(next_states_t).max(1)[1].unsqueeze(1)
        next_q_values = target_net(next_states_t).gather(1, next_actions)
        expected_q = rewards_t + gamma * next_q_values * (1.0 - dones_t)

    # Weighted Huber loss for PER
    td_errors = (q_values - expected_q).detach().cpu().numpy().flatten()
    loss = (weights_t * nn.SmoothL1Loss(reduction="none")(q_values, expected_q)).mean()

    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(policy_net.parameters(), 1.0)
    optimizer.step()

    # Update priorities in replay buffer
    memory.update_priorities(indices, td_errors)

    # Soft target-network update
    for t_p, l_p in zip(target_net.parameters(), policy_net.parameters()):
        t_p.data.copy_(tau * l_p.data + (1.0 - tau) * t_p.data)


def _save_and_exit(
    policy_net, epsilon, best_eval_reward, episode_rewards, collision_counts, log_file
):
    """Save model, epsilon, and training plots."""
    os.makedirs("models", exist_ok=True)
    torch.save(policy_net.state_dict(), "models/latest_model.pth")
    with open("models/latest_epsilon.txt", "w") as f:
        f.write(str(epsilon))

    if not os.path.exists("models/model.pth"):
        torch.save(policy_net.state_dict(), "models/model.pth")

    log_file.close()

    # ── Plot results ──────────────────────────────────────────────────────────
    if len(episode_rewards) > 5:
        _fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        axes[0].plot(episode_rewards, alpha=0.4, label="raw")
        window = 20
        if len(episode_rewards) >= window:
            smoothed = np.convolve(
                episode_rewards, np.ones(window) / window, mode="valid"
            )
            axes[0].plot(
                range(window - 1, len(episode_rewards)),
                smoothed,
                color="orange",
                linewidth=2,
                label=f"{window}-ep avg",
            )
        axes[0].set_title("Reward per Episode")
        axes[0].set_xlabel("Episode")
        axes[0].set_ylabel("Reward")
        axes[0].legend()

        axes[1].plot(collision_counts)
        axes[1].set_title("Collisions per Episode")
        axes[1].set_xlabel("Episode")
        axes[1].set_ylabel("Collisions")

        plt.tight_layout()
        plt.savefig("training_results.png")
        print("Saved training_results.png")

    print(f"Best eval reward: {best_eval_reward:.1f}")
    print("Model saved to models/")


if __name__ == "__main__":
    train()
