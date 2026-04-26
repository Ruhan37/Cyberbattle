# CyberBattle AI Simulator - Full Game Logic

## 1. Project Overview
CyberBattle is a turn-based cyber defense simulation on a 5x5 grid.

- Each grid cell is a network node.
- The Attacker and Defender are both AI agents.
- The Attacker uses Minimax.
- The Defender uses Monte Carlo style simulation (MCTS-like playout scoring).

The purpose is to model a cyber conflict where:

- the attacker tries to compromise enough nodes,
- the defender tries to eliminate all vulnerable nodes.

---

## 2. Node States (What Each Node Means)
Each node is represented by an integer in the board matrix:

- 0 = Secure
- 1 = Vulnerable
- 2 = Compromised

Text mode uses:

- S for Secure
- V for Vulnerable
- C for Compromised

---

## 3. How a Node Becomes Vulnerable
Nodes are initialized in `create_board()` in `game.py`.

Initial random distribution:

- 45% chance of Secure (0)
- 55% chance of Vulnerable (1)
- 0% Compromised at start

So vulnerability mostly comes from initial conditions, not from defender actions.

Important: Defender does not create new vulnerable nodes. Defender only moves risk downward (2->1->0).

---

## 4. How Attacker Attacks a Node
Attacker action is implemented in `apply_attack(board, move)`:

- If chosen node is Vulnerable (1), it becomes Compromised (2).
- Otherwise the attack does nothing.

Transition:

- 1 -> 2

Attacker legal moves from `get_attack_moves(board)`:

- Prefer all nodes currently Vulnerable (1).
- Fallback to all positions only if no vulnerable node exists.

---

## 5. How Defender Defends a Node
Defender action is implemented in `apply_defense(board, move)`:

- If node is Compromised (2), defender isolates/remediates it back to Vulnerable (1).
- Else if node is Vulnerable (1), defender hardens it to Secure (0).
- Else if node is already Secure (0), defense does nothing.

Transitions:

- 2 -> 1
- 1 -> 0

Defender legal moves from `get_defense_moves(board)`:

- Any node that is 1 or 2.
- Fallback to all positions only if none are 1 or 2.

---

## 6. Win Conditions (When Game Ends)
`is_game_over(board)` checks two terminal conditions:

1. Attacker wins if compromised count reaches threshold.
2. Defender wins if vulnerable count becomes zero.

Current threshold in `game.py`:

- `ATTACKER_WIN_THRESHOLD = max(5, (GRID_SIZE * GRID_SIZE) // 3)`
- With GRID_SIZE = 5, threshold is 8 compromised nodes.

Why this matters:

- Higher threshold makes defender much more likely to win.
- Lower threshold gives attacker a realistic winning path.

---

## 7. Turn Order and Game Loop
A full turn in `play_game(...)` in `main.py`:

1. Attacker chooses move using Minimax and applies attack.
2. Check winner immediately.
3. Defender chooses move using MCTS decision and applies defense.
4. Check winner again.
5. Continue until winner or max turns.

If no winner by max turns, result is DRAW.

---

## 8. Attacker AI Logic (Minimax)
Attacker uses `minimax(board, depth, maximizing)` in `minimax.py`.

- Search depth is controlled by `ATTACKER_MINIMAX_DEPTH` (currently 2).
- Terminal/depth-0 nodes are scored by `evaluate(board)`.
- On attacker step: maximize evaluation.
- On defender step: minimize evaluation.

Evaluation function in `game.py`:

- score = (compromised * 10) + (vulnerable * 5) - (secure * 8)

Interpretation:

- More compromised nodes strongly helps attacker.
- More secure nodes strongly hurts attacker.

---

## 9. Defender AI Logic (MCTS-Style)
Defender uses `mcts_decision(board, simulations)` in `mcts.py`.

For each possible defender move:

1. Apply that move on a cloned board.
2. Run several random playouts (`random_playout`) from that state.
3. Playout result scoring:
   - Defender win = +1
   - Attacker win = -1
4. Average score across simulations.
5. Pick move with highest average score.

Small random tie noise is added to avoid deterministic ties.

Playout depth limit:

- `MAX_MCTS_ROLLOUT_STEPS = 12`

---

## 10. Node Lifecycle Example
A common lifecycle for one node:

- Start Vulnerable (1)
- Attacker hits it -> Compromised (2)
- Defender remediates -> Vulnerable (1)
- Defender hardens later -> Secure (0)

This two-step defender recovery is why defense can stabilize the board over time.

---

## 11. UI Logic (Presentation-Friendly Features)
`ui.py` adds demo controls and observability:

- Pause / Resume
- Step one phase at a time
- Restart game
- Live counters for Secure, Vulnerable, Compromised
- Event log by turn (attack/defense actions with row and column)
- Speed slider
- Winner popup with Play Again

This is useful for presenting logic clearly in class.

---

## 12. CLI Modes for Experiments
Main entry: `main.py`

### GUI mode
Run:

python3 main.py

### Text mode
Run:

python3 main.py --no-gui

### Reproducible runs with seed
Run:

python3 main.py --no-gui --seed 10

### Benchmark mode
Run many games and print win rates and average turns:

python3 main.py --benchmark 120 --simulations 20 --seed 10

### Save results to CSV
Run:

python3 main.py --benchmark 120 --simulations 20 --seed 10 --csv results.csv

CSV columns:

- game
- seed
- winner
- turns
- simulations
- attacker_depth
- max_turns

---

## 13. One-Minute Presentation Script (Ready to Say)
"This project simulates cyber conflict on a 5x5 network. Each node is Secure, Vulnerable, or Compromised.
The attacker can only convert Vulnerable to Compromised, while the defender can convert Compromised to Vulnerable and Vulnerable to Secure.
So attack moves risk upward by one level, defense moves risk downward by one level.
Attacker decisions are made with Minimax, and defender decisions are made by simulation-based MCTS scoring.
The game ends when compromised nodes reach the attacker threshold, or when vulnerable nodes become zero for a defender win.
For experiments, I can run benchmark mode with fixed seeds and export CSV for reproducible report results."

---

## 14. File Map
- `game.py`: game state, transitions, win rules, evaluation
- `minimax.py`: attacker decision making
- `mcts.py`: defender decision making
- `ui.py`: GUI, controls, logs, stats
- `main.py`: run modes, benchmarking, seed control, CSV export
