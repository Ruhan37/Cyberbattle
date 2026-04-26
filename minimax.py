import random

from game import apply_attack, apply_defense, clone, evaluate, get_attack_moves, get_defense_moves, is_game_over

def minimax(board, depth, maximizing):
    winner = is_game_over(board)
    if depth == 0 or winner:
        return evaluate(board), None

    if maximizing:
        max_eval = float('-inf')
        best_moves = []

        for move in get_attack_moves(board):
            new_board = clone(board)
            apply_attack(new_board, move)
            eval_score, _ = minimax(new_board, depth - 1, False)

            if eval_score > max_eval:
                max_eval = eval_score
                best_moves = [move]
            elif eval_score == max_eval:
                best_moves.append(move)

        return max_eval, random.choice(best_moves) if best_moves else None

    else:
        min_eval = float('inf')
        best_moves = []

        for move in get_defense_moves(board):
            new_board = clone(board)
            apply_defense(new_board, move)
            eval_score, _ = minimax(new_board, depth - 1, True)

            if eval_score < min_eval:
                min_eval = eval_score
                best_moves = [move]
            elif eval_score == min_eval:
                best_moves.append(move)

        return min_eval, random.choice(best_moves) if best_moves else None