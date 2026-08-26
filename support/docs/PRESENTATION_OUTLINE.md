# Presentation Outline

This outline is designed for approximately 10–12 minutes plus questions.

## Slide 1 — Title

**Self-Driving Car Racing Game Using Deep Q-Network Reinforcement Learning**

- CSE440 – Introduction to Artificial Intelligence
- team member names and IDs
- Python, Pygame, PyTorch

**Speaker note:** Our project is a 2D racing environment where the car is not programmed with a fixed route. It learns an action policy from rewards.

## Slide 2 — Project Idea and Scope

- one AI-controlled car;
- simple 2D physics;
- five distance sensors;
- four discrete actions;
- validated trained Easy, Medium, and Hard policies;
- normal laptop, no GPU required.

**Speaker note:** We intentionally kept the simulator simple so the reinforcement-learning process is visible and explainable.

## Slide 3 — Overall Architecture

Use `docs/images/architecture.png`.

```text
state → DQN → action → physics → reward → replay/update → repeat
```

**Speaker note:** The agent repeatedly observes, acts, receives a reward, stores the transition, and updates the network.

## Slide 4 — Game and Track Design

- Pygame interface;
- white-road/black-wall mask;
- nine collision probes around the car;
- 720-point ordered centerline;
- twelve checkpoints;
- easy, medium, hard.

**Speaker note:** The display image and collision mask are separate. This makes collision and sensor calculations clear and reliable.

## Slide 5 — State and Sensors

```text
[left, front_left, front, front_right, right, speed]
```

- five rays;
- maximum range;
- normalized to `[0,1]`;
- six neural-network inputs.

Use `docs/images/gameplay.png` and point to the rays.

## Slide 6 — Actions and Reward Function

Actions:

- turn left;
- turn right;
- go straight;
- brake.

Rewards:

| Situation | Reward |
|---|---:|
| Forward | +1 |
| Checkpoint | +20 |
| Lap | +100 |
| Collision | -100 |
| Backward | -10 |
| Still | -2 |

**Speaker note:** Reward design is more important than making the network unnecessarily large.

## Slide 7 — DQN Architecture

```text
6 inputs → 64 ReLU → 64 ReLU → 4 Q-values
```

- policy network;
- target network;
- Huber loss;
- Adam optimizer;
- discount factor 0.99.

**Speaker note:** Each output estimates the future return of one action in the current state.

## Slide 8 — Experience Replay and Epsilon-Greedy

- store `(s, a, r, s', done)`;
- train on random mini-batches;
- epsilon begins at 1.00;
- epsilon falls to 0.05;
- evaluation uses epsilon 0.

**Speaker note:** Replay reduces correlation. Epsilon separates exploration during learning from exploitation during evaluation.

## Slide 9 — Training Interface and Engineering

- live start/pause/continue;
- adjustable training speed;
- save/load checkpoints;
- headless faster training;
- CSV, JSON, and graphs;
- 20 automated tests.

## Slide 10 — Training Results

Use `results/pretrained_easy_300_episodes/reward_per_episode.png`.

- 300 episodes;
- 110 exploratory lap completions;
- final-50 mean reward 614.7;
- best exploratory reward 653.

**Speaker note:** Training remains noisy because random exploration is still active.

## Slide 11 — Evaluation Results

- 20 greedy episodes;
- 20 completed laps;
- 0 collisions;
- mean reward 631;
- mean lap length 295 steps.

Use the live Watch Trained AI mode here.

**Speaker note:** Evaluation turns random exploration off, so it measures the learned policy itself.

## Slide 12 — Limitations and Future Work

Limitations:

- fixed evaluation start for each packaged checkpoint;
- Medium/Hard checkpoints use curriculum continuation;
- simple physics;
- no real-world perception.

Future work:

- random starts;
- random-start and from-scratch Medium/Hard benchmarks;
- PPO comparison;
- obstacles and multiple cars;
- camera-image input.

## Slide 13 — Conclusion

- complete agent–environment loop;
- compact DQN learned reproducible policies for all three packaged tracks from their standard starts;
- runs on CPU;
- model and raw data are saved and testable.

**Closing line:** The project demonstrates how reinforcement learning converts local sensor measurements and reward feedback into a working driving policy.
