# User Guide

## 1. Requirements

- Windows 10/11, macOS, or Linux;
- 64-bit Python 3.10 or newer;
- approximately 2 GB of free space for Python, PyTorch, and the environment;
- no dedicated GPU required.

## 2. Windows installation

1. Install Python and select **Add Python to PATH**.
2. Extract or clone the project.
3. Double-click `setup_windows.bat`.
4. Wait for the virtual environment and dependencies to install.
5. Double-click `run_game.bat`.

## 3. Manual installation

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py generate-assets
python main.py gui
```

## 4. Main menu

### Manual Drive

Use this mode to verify that the track, car physics, steering, collision, and sensors work before discussing AI.

| Key | Function |
|---|---|
| Up | Accelerate |
| Down | Brake |
| Left / Right | Steer |
| `R` | Reset |
| `G` | Toggle sensor rays |
| `Esc` | Main menu |

### Train AI (DQN)

The agent starts with high exploration. Early movement may look random. Epsilon decreases as environment steps increase.

| Key | Function |
|---|---|
| Space | Pause/continue |
| `+` | More simulation steps per frame |
| `-` | Fewer simulation steps per frame |
| `S` | Save immediately |
| `G` | Toggle sensor rays |
| `Esc` | Save and return |

For the fastest training, use the headless CLI instead of rendering.

### Watch Trained AI

This loads `models/<track>_best.pth`, or the latest model if no best model exists. Exploration is disabled (`ε = 0`). The repository includes validated best checkpoints for Easy, Medium, and Hard. You can still retrain or continue training any track.

### Evaluate Trained AI

This runs 20 greedy episodes and displays:

- success rate;
- mean reward;
- mean lap time;
- collision count.

A JSON result is saved under `results/`.

### Settings

Use Left/Right or Enter to change:

- track difficulty;
- car color;
- training episode count.

## 5. Headless training

```bash
python main.py train --track easy --episodes 500
```

Useful options:

```text
--track easy|medium|hard
--episodes N
--seed N
--device cpu|auto|cuda
--resume models/easy_latest.pth
--run-dir results/my_run
--quiet
--no-plots
```

Resume example:

```bash
python main.py train --track easy --episodes 200 --resume models/easy_latest.pth
```

The `--episodes` value is the number of additional episodes executed in that command.

## 6. Evaluation

```bash
python main.py evaluate \
  --track easy \
  --model models/easy_best.pth \
  --episodes 20 \
  --output results/my_evaluation.json
```

## 7. Reading results

Open the run folder under `results/`.

- `metrics.csv` can be opened in Excel or Google Sheets.
- `summary.json` includes aggregate and per-episode data.
- `reward_per_episode.png` shows learning progress.
- `lap_time_per_episode.png` shows completed-lap performance.
- `collision_count_per_episode.png` shows failures versus successful laps.

## 8. Common problems

### “Pygame is not installed”

Activate the virtual environment and reinstall:

```bash
python -m pip install -r requirements.txt
```

### A model file is missing or was deleted

The release includes best checkpoints for all three tracks. If one is missing, restore the package or retrain that track:

```bash
python main.py train --track medium --episodes 500
```

### PyTorch installation is slow

PyTorch is the largest dependency. Let the installation finish. The project itself does not download any model or track asset.

### The GUI opens and closes immediately

Run it from a terminal to see the error:

```bat
.venv\Scripts\python.exe main.py gui
```

### Training appears random

Check epsilon. High epsilon intentionally causes random exploration. Use Watch Trained AI or `evaluate` to inspect the learned greedy policy.

### Windows cannot find Python

Reinstall Python with **Add Python to PATH**, or use the `py` launcher.

### Regenerate damaged track assets

```bash
python main.py generate-assets --force
```

## 9. Recommended classroom demonstration

1. Show Manual Drive and intentionally collide.
2. Toggle the five sensors.
3. Show the reward table in the report.
4. Start live training and explain epsilon.
5. Increase training speed.
6. Return to the menu and Watch Trained AI on Easy.
7. Run Evaluate Trained AI and show the 20-episode result.
8. Open the three saved graphs.
