# Technical Design

## 1. Design goals

The implementation is organized around five goals:

1. preserve the exact educational state/action/reward design;
2. keep headless training independent of Pygame;
3. make all assets reproducible without downloads;
4. keep checkpoints, metrics, and tests auditable;
5. provide a polished GUI without mixing rendering into core learning logic.

## 2. Module responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Central simulation, reward, training, path, action, and color settings |
| `game/track.py` | Track generation/loading, road masks, centerline, checkpoints |
| `game/car.py` | Kinematics and body collision points |
| `game/sensors.py` | Five ray casts and normalized distance readings |
| `game/environment.py` | Reset/step API, state, action mapping, reward, termination |
| `game/renderer.py` | Pygame drawing and user-interface presentation |
| `game/app.py` | Menu, settings, manual, training, watch, evaluation state machine |
| `ai/network.py` | `6 → 64 → 64 → 4` neural network |
| `ai/replay_buffer.py` | Preallocated circular replay memory |
| `ai/agent.py` | Epsilon policy, optimization, target sync, checkpointing |
| `ai/trainer.py` | Blocking headless training and evaluation |
| `ai/live_trainer.py` | Bounded non-blocking training for Pygame frames |
| `utils/metrics.py` | CSV, JSON, summaries, and graphs |
| `main.py` | CLI command routing |

## 3. Headless-first separation

The environment uses only NumPy and Pillow. It does not initialize a display and does not import Pygame. Therefore:

- CPU training can run on servers or CI;
- tests do not require an SDL display;
- rendering speed cannot change simulation behavior;
- the same environment is used by manual, live training, CLI training, and evaluation.

Pygame is imported lazily by `game/renderer.py` only when the GUI starts.

## 4. Track representation

Each difficulty has three files:

```text
assets/tracks/easy.png
assets/tracks/easy_mask.png
assets/tracks/easy.json
```

The display image contains grass, road, shoulders, lane marks, and a start line. The mask is grayscale:

```text
white (>= 128) = road
black (< 128)  = collision/wall
```

The JSON contains 720 ordered centerline points. Track generation is deterministic, so deleting and regenerating the assets produces the same geometry.

## 5. Collision detection

The car is a rotated rectangle. Nine probes are checked:

- four corners;
- front and rear midpoints;
- left and right side midpoints;
- center.

All probes must be on white road pixels. This is more reliable than testing only the center pixel.

## 6. Progress tracking

A naive global nearest-point search can jump from one part of a closed track to another during a collision. The environment instead searches a local centerline window around the previous index. The signed wrapped index change becomes forward or backward progress.

A second plausibility clamp limits a single-step centerline change. Checkpoint targets are absolute ordered progress values, so an agent cannot repeatedly oscillate across one checkpoint for unlimited reward.

## 7. Sensor algorithm

For each relative ray angle:

1. create sample distances from `sensor_step` to `sensor_max_distance`;
2. calculate all sample coordinates along the ray;
3. round coordinates to mask pixels;
4. identify the first out-of-bounds or non-road sample;
5. return that distance or the maximum range.

The result contains five distances and five endpoints. Endpoints are reused by the renderer.

## 8. Environment contract

The environment follows a Gym-like API without adding a Gym dependency:

```python
state = env.reset(seed=440)
next_state, reward, terminated, truncated, info = env.step(action)
```

`terminated` represents a collision or target lap completion. `truncated` represents a time or stuck limit. Both are stored as terminal transitions in replay.

`info` includes:

- action and action name;
- speed and step;
- collision/checkpoint/lap flags;
- progress index and fraction;
- reward breakdown;
- termination reason;
- raw sensor distances and endpoints.

## 9. DQN optimization

The replay buffer is preallocated as NumPy arrays to avoid per-transition object overhead. A sampled batch is moved to the selected PyTorch device.

For each optimization:

1. calculate policy Q-values for stored actions;
2. calculate a no-gradient target using the target network;
3. use Double DQN action selection by default;
4. apply Smooth L1 (Huber) loss;
5. zero gradients;
6. backpropagate;
7. clip gradient norm;
8. update with Adam;
9. periodically synchronize the target network.

Small CPU matrix operations use one PyTorch thread by default, which avoids excessive thread-management overhead on this network size.

## 10. Checkpoint format

A checkpoint contains:

```text
format_version
state_size
action_size
training_config
policy_state_dict
target_state_dict
optimizer_state_dict
global_step
optimisation_steps
last_loss
metadata
```

Writes use a temporary file followed by atomic replacement. Loading validates format and architecture before applying weights.

## 11. GUI state machine

The application modes are:

```text
menu → settings
menu → manual
menu → training
menu → watch
menu → evaluation/message
```

The live trainer executes a configurable number of simulation steps per Pygame frame. This allows faster training while the event loop remains responsive. Leaving training triggers a checkpoint save.

## 12. Metrics

Each episode records:

```text
episode, reward, steps, laps, lap_time_steps, collisions,
completed, epsilon, mean_loss, termination_reason
```

Metrics are written after every episode, reducing data loss if training stops. Graphs are separate files rather than a combined subplot, matching the three required presentation measurements.

## 13. Reproducibility

- deterministic procedural track generation;
- stored run configuration;
- stored seed;
- raw episode data;
- versioned checkpoint structure;
- included evaluation JSON;
- automated test covering the included model.

GPU operations may introduce additional nondeterminism if the device is changed from CPU.

## 14. Extension points

- Add new tracks by implementing a centerline in `_make_centerline`.
- Add actions by changing `ACTION_CONTROLS`, the network output size, and UI labels.
- Add state values by updating sensor/state construction and network input size.
- Replace DQN through the `select_action` and `observe` interface.
- Add random starts through `RacingEnv.reset(start_index=...)`.
