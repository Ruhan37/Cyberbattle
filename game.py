import random

GRID_SIZE = 5
# A lower threshold keeps both sides competitive instead of creating near-certain defender wins.
ATTACKER_WIN_THRESHOLD = max(5, (GRID_SIZE * GRID_SIZE) // 3)
ATTACKER_MINIMAX_DEPTH = 2
DEFAULT_MCTS_SIMULATIONS = 20
MAX_MCTS_ROLLOUT_STEPS = 12

def create_board():
    return [[random.choices([0, 1], weights=[0.45, 0.55], k=1)[0] for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

def get_all_positions(board):
    size = len(board)
    positions = []
    for i in range(size):
        for j in range(size):
            positions.append((i, j))
    return positions

def get_attack_moves(board):
    moves = []
    size = len(board)

    for i in range(size):
        for j in range(size):
            if board[i][j] == 1:
                moves.append((i, j))

    return moves if moves else get_all_positions(board)

def get_defense_moves(board):
    moves = []
    size = len(board)

    for i in range(size):
        for j in range(size):
            if board[i][j] in (1, 2):
                moves.append((i, j))

    return moves if moves else get_all_positions(board)

def count_states(board):
    secure = vulnerable = compromised = 0
    for row in board:
        for cell in row:
            if cell == 0: secure += 1
            elif cell == 1: vulnerable += 1
            elif cell == 2: compromised += 1
    return secure, vulnerable, compromised

def is_game_over(board):
    secure, vulnerable, compromised = count_states(board)

    if compromised >= ATTACKER_WIN_THRESHOLD:
        return "ATTACKER"
    if vulnerable == 0:
        return "DEFENDER"
    return None

def apply_attack(board, move):
    i, j = move
    if board[i][j] == 1:
        board[i][j] = 2
        return True
    return False

def apply_defense(board, move):
    i, j = move
    if board[i][j] == 2:
        board[i][j] = 1
        return True
    elif board[i][j] == 1:
        board[i][j] = 0
        return True
    return False

def evaluate(board):
    secure, vulnerable, compromised = count_states(board)
    return (compromised * 10) + (vulnerable * 5) - (secure * 8)

def clone(board):
    return [row[:] for row in board]