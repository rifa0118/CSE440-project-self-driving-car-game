# Live Demo Script

## 1. Preparation

Before presenting:

```bat
setup_windows.bat
```

Confirm:

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe main.py evaluate --track easy --model models\easy_best.pth --episodes 3
```

Keep these files ready:

- `docs/PROJECT_REPORT.md`;
- `results/pretrained_easy_300_episodes/reward_per_episode.png`;
- `results/easy_pretrained_evaluation_20.json`.

## 2. Three-to-five-minute demonstration

### Step 1 — Open the application

Run `run_game.bat`.

Say: “The same environment supports manual control, live training, model playback, and evaluation.”

### Step 2 — Manual Drive

- select Manual Drive;
- accelerate and steer;
- press `G` to show sensor rays;
- intentionally leave the road.

Say: “Collision is based on the white-road/black-wall image mask, not a hard-coded boundary.”

### Step 3 — Live training

- return to the menu;
- select Train AI;
- point to episode, reward, epsilon, and loss;
- use `+` to increase simulation speed;
- pause and continue with Space;
- save with `S`.

Say: “At high epsilon, random actions are expected. Transitions go into replay memory, and the network learns from random batches.”

### Step 4 — Trained model

- return to the menu;
- ensure Easy is selected;
- choose Watch Trained AI.

Say: “This mode sets epsilon to zero. The car chooses only the largest predicted Q-value.”

### Step 5 — Evaluation

- return to the menu;
- select Evaluate Trained AI;
- show success rate, mean reward, mean lap time, and collisions.

Say: “We separate exploratory training behavior from greedy evaluation behavior.”

### Step 6 — Graph

Open `reward_per_episode.png`.

Say: “The raw CSV and JSON are included, so the graph and reported numbers can be checked.”

## 3. Backup if the GUI cannot open

Run:

```bat
.venv\Scripts\python.exe main.py evaluate --track easy --model models\easy_best.pth --episodes 20
```

Then show `docs/images/gameplay.png` and the saved graphs. This still demonstrates that the model, environment, and evaluation code run.
