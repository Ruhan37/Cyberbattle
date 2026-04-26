import random
from game import (
    MAX_MCTS_ROLLOUT_STEPS,
    apply_attack,
    apply_defense,
    clone,
    evaluate,
    get_attack_moves,
    get_defense_moves,
    is_game_over,
)

def random_playout(board, max_steps=MAX_MCTS_ROLLOUT_STEPS):
    temp = clone(board)

    for _ in range(max_steps):
        winner = is_game_over(temp)
        if winner:
            return winner

        attack_moves = get_attack_moves(temp)
        if attack_moves:
            apply_attack(temp, random.choice(attack_moves))

        winner = is_game_over(temp)
        if winner:
            return winner

        defense_moves = get_defense_moves(temp)
        if defense_moves:
            apply_defense(temp, random.choice(defense_moves))

    return "ATTACKER" if evaluate(temp) > 0 else "DEFENDER"

def mcts_decision(board, simulations=50):
    defender_moves = get_defense_moves(board)
    if not defender_moves:
        return None

    best_move = defender_moves[0]
    best_score = float('-inf')

    for move in defender_moves:
        score_sum = 0.0

        for _ in range(max(1, simulations)):
            temp = clone(board)
            apply_defense(temp, move)

            result = random_playout(temp)

            if result == "DEFENDER":
                score_sum += 1.0
            else:
                score_sum -= 1.0

        score = score_sum / max(1, simulations)
        score += random.uniform(-0.03, 0.03)

        if score > best_score:
            best_score = score
            best_move = move

    return best_move