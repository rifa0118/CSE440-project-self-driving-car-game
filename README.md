# CSE440 Self-Driving Car Racing Game

A complete 2D racing game in which a car learns to drive using **Deep Q-Network (DQN) reinforcement learning**. The project uses Python, Pygame, PyTorch, NumPy, Pillow, and Matplotlib and is designed to train on a normal CPU-only laptop.

![The trained DQN driving with five live distance sensors](support/docs/images/gameplay.png)

## What is included

- A polished Pygame menu and live game interface.
- Keyboard-controlled manual racing.
- Three image-based track difficulties: easy, medium, and hard.
- Five ray sensors plus speed as the six-value AI state.
- Four discrete actions: turn left, turn right, go straight, and brake.
- A `6 → 64 → 64 → 4` PyTorch DQN.
- Experience replay, epsilon-greedy exploration, target network updates, gradient clipping, and optional Double DQN targets.
- Live start, pause, continue, speed, and save controls during training.
- Model save/load through `.pth` checkpoints.
- Headless CLI training and evaluation.
- Reward, lap-time, and collision graphs.
- Validated trained checkpoints for Easy, Medium, and Hard.
- Automated tests and GitHub Actions CI.

## Verified included result

The package includes validated `*_best.pth` checkpoints for Easy, Medium, and Hard. Easy was trained directly; Medium and Hard were produced by curriculum continuation from the previous difficulty, then each checkpoint was evaluated greedily from its standard start position.

| Measurement | Result |
|---|---:|
| Training episodes | 300 |
| Exploratory training episodes completing a lap | 110 / 300 (36.7%) |
| Average reward over the final 50 training episodes | 614.7 |
| Greedy evaluation episodes | 20 |
| Greedy evaluation success | 20 / 20 (100%) |
| Greedy evaluation collisions | 0 |
| Mean greedy lap length | 295 simulation steps (4.92 s at 60 FPS) |

The complete raw metrics and graphs can be found inside the `data/results/` folder. Checkpoints are available in `data/models/`.

## Fastest Setup

1. Install **64-bit Python 3.10 or newer** and ensure it's added to your PATH.
2. If you are on Windows, you can double-click `support/setup_windows.bat` to install dependencies, and `support/run_game.bat` to launch the game.
3. On macOS or Linux, follow the command-line usage below.

## Command-line usage

```bash
# Install and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
python -m pip install -r requirements.txt

# Open the full Pygame app GUI
python main.py gui

# Train without rendering (faster)
python main.py train --track easy --episodes 500

# Evaluate a model over 20 greedy episodes
python main.py evaluate --track easy --model data/models/easy_best.pth --episodes 20

# Print the state/action/reward configuration
python main.py describe
```

## GUI modes and controls

### Main menu

- **Manual Drive** — control the car with the keyboard.
- **Train AI (DQN)** — watch reinforcement learning happen live.
- **Watch Trained AI** — run a saved model with exploration disabled.
- **Evaluate Trained AI** — run 20 headless test episodes and save JSON results.
- **Settings** — choose the track, car colour, and training episode count.

### Manual driving

| Key | Action |
|---|---|
| Up | Accelerate |
| Down | Brake |
| Left / Right | Steer |
| `R` | Reset after a collision |
| `G` | Show/hide sensors |
| `Esc` | Return to the main menu |

### Live training

| Key | Action |
|---|---|
| Space | Pause or continue |
| `+` / `-` | Increase or decrease simulation steps per rendered frame |
| `S` | Save the current checkpoint |
| `G` | Show/hide sensors |
| `Esc` | Save and return to the main menu |

## Reinforcement-learning design

![Agent–environment loop](support/docs/images/architecture.png)

### State
```text
[left, front_left, front, front_right, right, speed]
```
All six values are normalized to `[0, 1]`. The five sensor rays stop when they encounter a black pixel in the track mask or reach maximum range.

### Actions

| Index | Action | Control applied |
|---:|---|---|
| 0 | Turn left | throttle + left steering |
| 1 | Turn right | throttle + right steering |
| 2 | Go straight | throttle |
| 3 | Brake | braking, no steering |

### Reward function

| Situation | Reward |
|---|---:|
| Driving forward | `+1` |
| Passing a checkpoint | `+20` |
| Completing a lap | `+100` |
| Collision | `-100` |
| Driving backwards | `-10` |
| Standing still | `-2` |

### Network

```text
Input: 6 values
Hidden layer: 64 ReLU units
Hidden layer: 64 ReLU units
Output: 4 action Q-values
```

The policy network learns from random batches in replay memory. A separate target network stabilizes the Bellman target. Epsilon decreases linearly from `1.00` to `0.05`, changing the agent from mostly exploratory behavior to mostly learned behavior.

## Project Structure

This repository is strictly organized to comply with our university guidelines.

```text
CSE440-project-self-driving-car-game/
├── data/                     # Subfolder for all datasets and assets
│   ├── assets/               # Track images, collision masks, and JSON metadata
│   ├── models/               # Included and newly trained checkpoints (*.pth)
│   └── results/              # Evaluation CSV, JSON, and graphs
├── others/                   # Subfolder for all submission documents and media
│   └── CSE440 Presentation.pptx # Final presentation (Update PPTX, PDFs, Video demo go here)
├── support/                  # Subfolder for all supportive code modules and scripts
│   ├── ai/                   # DQN agent, replay memory, and PyTorch network
│   ├── docs/                 # Documentation source and architecture images
│   ├── game/                 # Pygame UI, kinematics, sensors, and environment logic
│   ├── scripts/              # Helper scripts for generating assets and building docs
│   ├── tests/                # Automated tests suite
│   ├── tools/                # Assorted tooling
│   ├── utils/                # Helper utilities
│   ├── verification/         # Verification tests and scripts
│   ├── config.py             # Central simulation and hyperparameter settings
│   └── ...                   # .bat / .sh runner scripts, requirements-dev.txt, etc.
├── main.py                   # The main code file used to run the project
├── README.md                 # Project explanation (You are here)
└── requirements.txt          # Tools and libraries the project needs to run
```

## Training outputs

Every run gets a timestamped directory under `data/results/` containing:
- `run_config.json` — exact environment and training settings;
- `metrics.csv` — one row per episode;
- `summary.json` — aggregate and full episode data;
- `reward_per_episode.png`, `lap_time_per_episode.png`, `collision_count_per_episode.png`.

Models are written to:
- `data/models/<track>_best.pth` — highest completed/reward score seen in the run;
- `data/models/<track>_latest.pth` — resumable checkpoint.

## Honest scope and limitations

- Validated pretrained checkpoints are included for **Easy, Medium, and Hard**. Each packaged best checkpoint completed 20/20 deterministic greedy evaluation episodes from its standard start position with zero collisions. These results do not prove random-start generalization.
- The physics are deliberately simple and educational, not a realistic vehicle simulator.
- DQN results can vary with seed and hyperparameters. Raw logs are kept so results can be inspected rather than merely claimed.
- This project demonstrates reinforcement learning; it is not software for controlling a real vehicle.

## Video Demo link of the Project

https://drive.google.com/file/d/1UnZuLWp-DlSeWpC30vlNtAYJ7OgpmhO_/view?usp=sharing


