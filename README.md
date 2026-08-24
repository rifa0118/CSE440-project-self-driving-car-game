# Self-Driving Car Racing Game 🏎️🤖

Welcome to the **Self-Driving Car Racing Game**! This is a complete Python-based racing game built with Pygame that features a smart, self-driving Artificial Intelligence (AI) car. 

## 📖 About the Project

This project explores how a computer can learn to drive a car on its own in a simulated world. Instead of writing strict rules for how to drive, the AI learns through a process called **Deep Reinforcement Learning** (specifically, Dueling DQN). 

Just like a human learning to ride a bike, the AI starts by making random moves. When it stays on the track and drives fast, it gets a "reward". When it crashes into traffic, barriers, or drives off the road, it gets a "penalty". By playing the game over and over, the AI's "brain" slowly figures out the best way to steer, accelerate, and brake to get the highest score.

With this project, you can:
- **Play the game yourself** to understand the physics and controls.
- **Train the AI** from scratch and watch it slowly get better at driving.
- **Watch a fully trained AI** confidently dodge obstacles and race at high speeds.
- **Compete against the AI** in an exciting 3-lap race to see who is faster!

## 🎮 Features

- **Manual Driving:** Drive the car yourself using the W/A/S/D or Arrow Keys.
- **AI Training Mode:** Start the training process and watch the AI learn by trial and error. You can pause the training at any time, and the AI's "memory" will automatically save so you can continue later.
- **Watch AI Drive:** Load a fully trained AI model and watch it navigate the endless track and traffic automatically.
- **AI Race Mode:** Pit your trained AI against 3 other computer-controlled cars in a thrilling 3-lap race!
- **Car Customization:** Change your car's color and adjust its speed, acceleration, and handling.
- **Live HUD Display:** A screen overlay shows your current speed, health bar, lap times, and the AI's learning progress.

## 🧠 How the AI Works (Simply Explained)

- **The Eyes:** Every fraction of a second, the AI looks at 18 different things around it. This includes its current speed, how the road curves ahead, its health, and the distance to the nearest obstacles.
- **The Brain:** It uses a smart neural network to decide the best move. It figures out how safe the current situation is and chooses the best action to take right now.
- **The Memory:** It remembers past drives in a "Replay Buffer". It looks back at its biggest mistakes so it can learn not to repeat them.
- **The Actions:** Based on what it sees, the AI decides whether to steer left, steer right, go straight, or hit the brakes.

## ⚙️ Setup & Installation

To play the game, you will need Python 3.8 or a newer version installed on your computer.

1. **Install the required packages:**
   Open your terminal or command prompt in the game folder and run:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 How to Play

### 1. Launch the Game Menu
To open the main menu, run this command:
```bash
python main.py
```

From the menu, you can easily click to start playing, customize your car, train the AI, or watch the AI race.

### 2. Direct Commands (For Advanced Users)
You can also run specific parts of the game directly from your terminal:
```bash
# Train the AI from scratch
python train.py

# Watch a trained AI drive
python evaluate.py

# Start a 3-lap race against bots
python race.py
```

## 💡 Training Tips

- **Patience is Key:** The first 100 tries will look completely random because the AI is exploring its options. Real learning starts after that!
- **Save and Continue:** You don't have to train it all in one sitting. Closing the game window saves the AI's progress. When you run `train.py` again, it picks up right where it left off.
- **Watch the Score:** You want to see the "moving average reward" slowly go up over time. This means the AI is getting smarter.

## 📁 Project Files Structure

```
├── main.py              # The main game menu
├── train.py             # Script to train the AI
├── evaluate.py          # Script to watch the AI drive
├── race.py              # Script to start the 3-lap race
├── ai/
│   ├── dqn.py           # The AI's Neural Network Brain
│   └── replay_buffer.py # The AI's Memory system
├── src/
│   ├── game.py          # The core game engine and rules
│   ├── env.py           # Connects the game to the AI
│   ├── car.py           # Car physics (movement and crashes)
│   ├── track.py         # Builds the road and places obstacles
│   ├── hud.py           # Draws the speed and health on screen
│   ├── objects.py       # Code for traffic cars, barriers, and trees
│   ├── config.py        # Game settings (speeds, laps, etc.)
│   └── profile.py       # Saves your car customization
├── assets/              # Images for cars, roads, and objects
├── models/              # Where your trained AI brains are saved
└── requirements.txt     # List of Python packages needed
```
