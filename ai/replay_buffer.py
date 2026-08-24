"""Prioritized Experience Replay buffer.

Samples transitions proportional to their TD-error magnitude, so the
network learns more from surprising or important transitions (e.g.
collisions, near-misses) instead of boring straight-driving samples.

Uses a Sum-Tree data structure for O(log N) sampling and updates.
"""

import random

import numpy as np


class SumTree:
    """Binary tree where each leaf holds a priority and parent nodes hold
    the sum of their children. Enables O(log N) proportional sampling."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        self.data = [None] * capacity
        self.write_idx = 0
        self.size = 0

    def _propagate(self, idx, change):
        parent = (idx - 1) // 2
        while True:
            self.tree[parent] += change
            if parent == 0:
                break
            parent = (parent - 1) // 2

    def _retrieve(self, idx, s):
        while True:
            left = 2 * idx + 1
            if left >= len(self.tree):
                return idx
            if s <= self.tree[left]:
                idx = left
            else:
                s -= self.tree[left]
                idx = left + 1

    def total(self):
        return self.tree[0]

    def add(self, priority, data):
        idx = self.write_idx + self.capacity - 1
        self.data[self.write_idx] = data
        self.update(idx, priority)
        self.write_idx = (self.write_idx + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def update(self, idx, priority):
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        self._propagate(idx, change)

    def get(self, s):
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return idx, self.tree[idx], self.data[data_idx]


class PrioritizedReplayBuffer:
    """Prioritized Experience Replay using a Sum-Tree.

    Args:
        capacity: maximum number of transitions to store
        alpha: prioritization exponent (0 = uniform, 1 = full prioritization)
        beta_start: initial importance-sampling correction
        beta_frames: number of frames to anneal beta to 1.0
    """

    def __init__(self, capacity=100000, alpha=0.6, beta_start=0.4, beta_frames=200000):
        self.tree = SumTree(capacity)
        self.capacity = capacity
        self.alpha = alpha
        self.beta_start = beta_start
        self.beta_frames = beta_frames
        self.frame = 0
        self.max_priority = 1.0
        self._eps = 1e-6  # small constant to ensure no zero priorities

    def push(self, state, action, reward, next_state, done):
        """Store a transition with maximum priority (will be corrected on first sample)."""
        data = (state, action, reward, next_state, done)
        priority = self.max_priority**self.alpha
        self.tree.add(priority, data)

    def sample(self, batch_size):
        """Sample a batch proportional to priorities.

        Returns:
            states, actions, rewards, next_states, dones, indices, weights
        """
        self.frame += 1
        beta = min(
            1.0,
            self.beta_start + (1.0 - self.beta_start) * self.frame / self.beta_frames,
        )

        indices = []
        priorities = []
        batch = []

        segment = self.tree.total() / batch_size

        for i in range(batch_size):
            low = segment * i
            high = segment * (i + 1)
            s = random.uniform(low, high)
            idx, priority, data = self.tree.get(s)

            if data is None:
                # Edge case: tree slot not yet filled; retry with random
                s = random.uniform(0, self.tree.total())
                idx, priority, data = self.tree.get(s)
                if data is None:
                    continue

            indices.append(idx)
            priorities.append(priority)
            batch.append(data)

        if len(batch) < batch_size:
            # Fallback: pad with random samples from available data
            while len(batch) < batch_size:
                s = random.uniform(0, self.tree.total())
                idx, priority, data = self.tree.get(s)
                if data is not None:
                    indices.append(idx)
                    priorities.append(priority)
                    batch.append(data)

        # Importance sampling weights
        priorities = np.array(priorities, dtype=np.float64)
        probs = priorities / (self.tree.total() + self._eps)
        weights = (self.tree.size * probs + self._eps) ** (-beta)
        weights /= weights.max()  # normalize

        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
            indices,
            np.array(weights, dtype=np.float32),
        )

    def update_priorities(self, indices, td_errors):
        """Update priorities based on new TD-errors after a learning step."""
        for idx, td_error in zip(indices, td_errors):
            priority = (abs(td_error) + self._eps) ** self.alpha
            self.max_priority = max(self.max_priority, priority)
            self.tree.update(idx, priority)

    def __len__(self):
        return self.tree.size
