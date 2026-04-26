import argparse
import csv
import os
import random

from game import ATTACKER_MINIMAX_DEPTH, DEFAULT_MCTS_SIMULATIONS, apply_attack, apply_defense, create_board, is_game_over
from minimax import minimax
from mcts import mcts_decision


class MissingTkinterError(RuntimeError):
    pass


def format_board(board):
    legend = {0: "S", 1: "V", 2: "C"}
    rows = [" ".join(legend[cell] for cell in row) for row in board]
    return "\n".join(rows)


def play_game(simulations=DEFAULT_MCTS_SIMULATIONS, max_turns=100, on_turn_end=None):
    board = create_board()

    winner = is_game_over(board)
    if winner:
        return winner, 0, board

    for turn in range(1, max_turns + 1):
        _, attack_move = minimax(board, ATTACKER_MINIMAX_DEPTH, True)
        if attack_move is not None:
            apply_attack(board, attack_move)

        winner = is_game_over(board)
        if winner:
            if on_turn_end:
                on_turn_end(turn, board)
            return winner, turn, board

        defend_move = mcts_decision(board, simulations)
        if defend_move is not None:
            apply_defense(board, defend_move)

        if on_turn_end:
            on_turn_end(turn, board)

        winner = is_game_over(board)
        if winner:
            return winner, turn, board

    return "DRAW", max_turns, board


def run_text_mode(simulations=DEFAULT_MCTS_SIMULATIONS, max_turns=100):
    print("Running in text mode (S=Secure, V=Vulnerable, C=Compromised)\n")

    def print_turn(turn, board):
        print(f"Turn {turn}")
        print(format_board(board))
        print()

    winner, turns, board = play_game(
        simulations=simulations,
        max_turns=max_turns,
        on_turn_end=print_turn,
    )

    if winner == "DRAW":
        print(f"No winner after {max_turns} turns.")
    else:
        print(f"Winner: {winner}")
        print(format_board(board))

    return {
        "winner": winner,
        "turns": turns,
        "simulations": simulations,
        "attacker_depth": ATTACKER_MINIMAX_DEPTH,
        "max_turns": max_turns,
    }


def run_benchmark(game_count, simulations=DEFAULT_MCTS_SIMULATIONS, max_turns=100, seed=None):
    results = {"ATTACKER": 0, "DEFENDER": 0, "DRAW": 0}
    rows = []
    total_turns = 0

    for game_index in range(1, game_count + 1):
        game_seed = None
        if seed is not None:
            game_seed = seed + game_index - 1
            random.seed(game_seed)

        winner, turns, _ = play_game(simulations=simulations, max_turns=max_turns)

        results[winner] += 1
        total_turns += turns

        rows.append(
            {
                "game": game_index,
                "seed": "" if game_seed is None else game_seed,
                "winner": winner,
                "turns": turns,
                "simulations": simulations,
                "attacker_depth": ATTACKER_MINIMAX_DEPTH,
                "max_turns": max_turns,
            }
        )

    attacker_rate = (results["ATTACKER"] / game_count) * 100
    defender_rate = (results["DEFENDER"] / game_count) * 100
    draw_rate = (results["DRAW"] / game_count) * 100
    avg_turns = total_turns / game_count

    print(f"Benchmark games: {game_count}")
    print(f"Attacker win rate: {attacker_rate:.2f}%")
    print(f"Defender win rate: {defender_rate:.2f}%")
    print(f"Draw rate: {draw_rate:.2f}%")
    print(f"Average turns: {avg_turns:.2f}")

    return rows


def save_match_summaries_csv(csv_path, rows):
    directory = os.path.dirname(os.path.abspath(csv_path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    fieldnames = [
        "game",
        "seed",
        "winner",
        "turns",
        "simulations",
        "attacker_depth",
        "max_turns",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved match summaries to: {csv_path}")


def run_gui():
    try:
        import tkinter as tk
    except ModuleNotFoundError as exc:
        if exc.name in {"_tkinter", "tkinter"}:
            raise MissingTkinterError(
                "Tkinter is not available for this Python interpreter. "
                "Install it with `brew install python-tk@3.14` or run with --no-gui."
            ) from exc
        raise

    from ui import GameUI

    root = tk.Tk()
    root.title("CyberBattle AI")
    GameUI(root)
    root.mainloop()


def parse_args():
    parser = argparse.ArgumentParser(description="Run CyberBattle AI")
    parser.add_argument("--no-gui", action="store_true", help="Run without tkinter GUI")
    parser.add_argument(
        "--simulations",
        type=int,
        default=DEFAULT_MCTS_SIMULATIONS,
        help="MCTS simulations per defender move in text mode",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=100,
        help="Maximum number of turns in text mode",
    )
    parser.add_argument(
        "--benchmark",
        type=int,
        default=0,
        help="Run N headless games and report win rates and average turns",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Base random seed for reproducible experiments",
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Save match summaries to CSV",
    )

    args = parser.parse_args()

    if args.simulations < 1:
        parser.error("--simulations must be at least 1")
    if args.max_turns < 1:
        parser.error("--max-turns must be at least 1")
    if args.benchmark < 0:
        parser.error("--benchmark must be 0 or higher")

    return args


def main():
    args = parse_args()

    if args.benchmark > 0:
        rows = run_benchmark(
            game_count=args.benchmark,
            simulations=args.simulations,
            max_turns=args.max_turns,
            seed=args.seed,
        )
        if args.csv:
            save_match_summaries_csv(args.csv, rows)
        return

    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    if args.no_gui:
        summary = run_text_mode(simulations=args.simulations, max_turns=args.max_turns)
        if args.csv:
            save_match_summaries_csv(
                args.csv,
                [
                    {
                        "game": 1,
                        "seed": "" if args.seed is None else args.seed,
                        "winner": summary["winner"],
                        "turns": summary["turns"],
                        "simulations": summary["simulations"],
                        "attacker_depth": summary["attacker_depth"],
                        "max_turns": summary["max_turns"],
                    }
                ],
            )
        return

    try:
        run_gui()
    except MissingTkinterError as exc:
        print(exc)
        print("Falling back to text mode.\n")
        summary = run_text_mode(simulations=args.simulations, max_turns=args.max_turns)
        if args.csv:
            save_match_summaries_csv(
                args.csv,
                [
                    {
                        "game": 1,
                        "seed": "" if args.seed is None else args.seed,
                        "winner": summary["winner"],
                        "turns": summary["turns"],
                        "simulations": summary["simulations"],
                        "attacker_depth": summary["attacker_depth"],
                        "max_turns": summary["max_turns"],
                    }
                ],
            )


if __name__ == "__main__":
    main()
