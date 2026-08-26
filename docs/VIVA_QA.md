# Viva Questions and Answers

## 1. What is reinforcement learning?

Reinforcement learning is a learning process in which an agent interacts with an environment, receives rewards, and improves a policy that aims to maximize expected cumulative reward.

## 2. What are the agent and environment here?

The DQN is the agent. The car, track, physics, sensors, collision system, checkpoints, and reward calculation form the environment.

## 3. What is the state?

The state is a six-value normalized vector containing five wall-distance readings and speed:

```text
[left, front_left, front, front_right, right, speed]
```

## 4. Why use five sensors?

Five rays provide information about both side boundaries and the road ahead while keeping the input small enough for a simple fully connected network.

## 5. What are the actions?

Turn left, turn right, go straight, and brake. They are discrete, which makes DQN suitable.

## 6. Why is DQN appropriate?

DQN estimates a Q-value for each discrete action. Our action space contains only four choices, and the state is a small numeric vector.

## 7. What does a Q-value mean?

`Q(s,a)` estimates the expected discounted future reward if the agent takes action `a` in state `s` and then follows its policy.

## 8. What is the Bellman equation used for?

It defines a target that combines the immediate reward with the discounted estimate of the best future value.

## 9. Why are there two networks?

The policy network is updated every training step. The target network changes less frequently, so the learning target is more stable.

## 10. What is experience replay?

The system stores transitions and trains on random samples. This reduces correlation between consecutive experiences and reuses earlier data.

## 11. What is epsilon-greedy?

With probability epsilon, the agent chooses a random action. Otherwise it chooses the largest-Q action. This balances exploration and exploitation.

## 12. Why does epsilon decrease?

The agent needs broad exploration at the beginning. Later, it should increasingly use what it has learned.

## 13. Why can training success be lower than evaluation success?

Training intentionally includes random actions. Evaluation sets epsilon to zero, so it measures the learned greedy policy without exploratory mistakes.

## 14. What is the neural-network architecture?

Six inputs, two hidden layers of 64 ReLU neurons, and four output Q-values.

## 15. What loss function is used?

Smooth L1, also called Huber loss. It is less sensitive to large errors than mean squared error.

## 16. What optimizer is used?

Adam with a learning rate of 0.001.

## 17. What is the discount factor?

Gamma is 0.99. It gives high importance to future rewards while still discounting them slightly.

## 18. How is collision detected?

Nine points around the rotated car body are checked against a mask. White is road; black is wall/non-road.

## 19. How is forward or backward movement detected?

The car is mapped to an ordered centerline index. A positive wrapped index change is forward; a negative change is backward.

## 20. Why use local centerline search?

A global nearest point could jump to another nearby section after a crash. Local search keeps progress physically continuous and prevents false rewards.

## 21. Why are checkpoints needed?

They provide intermediate goals and prevent the lap reward from being too delayed. Ordered checkpoints also discourage shortcuts.

## 22. What happens when the car stands still?

It receives `-2`. If it remains below the speed threshold for too long, the episode is truncated as stuck.

## 23. What ends an episode?

Collision, target lap completion, stuck limit, or maximum step limit.

## 24. What is saved in `model.pth`?

Policy and target weights, optimizer state, architecture, training configuration, step counts, loss, and metadata.

## 25. Does it require a GPU?

No. The state and network are small, and the included model was trained on CPU.

## 26. Did the agent learn, or is it scripted?

The model is a PyTorch DQN trained from replayed transitions. A centerline controller exists only inside one environment test to verify lap mechanics; it is not used to generate the included model or to drive in Watch Trained AI.

## 27. What evidence shows the model works?

The packaged best checkpoints for Easy, Medium, and Hard each completed 20 of 20 deterministic greedy evaluation episodes from their standard start positions with zero collisions. Raw JSON and training metrics are included; automated tests also verify the Easy model completes a lap.

## 28. What are the main limitations?

Evaluation starts from one standard pose per track, Medium/Hard use curriculum continuation, physics are simple, and the state does not represent real camera perception.

## 29. How would you improve generalization?

Train with randomized start positions, speeds, headings, track variations, and possibly a curriculum across difficulties.

## 30. Why not use PPO?

PPO is a good alternative, especially for continuous actions, but DQN is simpler and academically appropriate for the required four-action discrete problem.
