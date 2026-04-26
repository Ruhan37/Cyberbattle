import os
import threading
import tkinter as tk

from game import (
    ATTACKER_MINIMAX_DEPTH,
    DEFAULT_MCTS_SIMULATIONS,
    apply_attack,
    apply_defense,
    count_states,
    clone,
    create_board,
    is_game_over,
)
from minimax import minimax
from mcts import mcts_decision


class GameUI:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg="#0b1020")

        self.board = create_board()
        self.previous_board = clone(self.board)
        self.grid_size = len(self.board)

        self.running = True
        self.worker_busy = False
        self.paused = False
        self.pause_requested = False
        self.pending_step = False
        self.turn_number = 1
        self.next_phase = "attacker"
        self.game_token = 0
        self.winner_popup = None

        self.base_think_delay_ms = 450
        self.base_turn_delay_ms = 350
        self.base_flash_delay_ms = 120
        self.think_delay_ms = self.base_think_delay_ms
        self.turn_delay_ms = self.base_turn_delay_ms
        self.flash_delay_ms = self.base_flash_delay_ms

        self.simulations = tk.IntVar(value=DEFAULT_MCTS_SIMULATIONS)
        self.speed_multiplier = tk.DoubleVar(value=1.0)
        self.sim_value_text = tk.StringVar()
        self.speed_text = tk.StringVar()
        self.secure_text = tk.StringVar()
        self.vulnerable_text = tk.StringVar()
        self.compromised_text = tk.StringVar()
        self.status_text = tk.StringVar()

        self.icons = self._load_icons()
        icon_size = self.icons[0].width()
        self.flash_icon = self._create_flash_icon(icon_size)

        self._build_layout()
        self._on_simulation_change()
        self._on_speed_change()
        self.update_ui(animated=False)
        self._clear_log()
        self._append_log("New match started.")
        self._update_controls()

        self._set_status("Turn 1: Attacker (Minimax) is thinking...")
        self.root.after(700, self._schedule_next_phase)

    def _build_layout(self):
        title = tk.Label(
            self.root,
            text="CyberBattle AI Simulator",
            font=("Helvetica", 18, "bold"),
            fg="#e2e8f0",
            bg="#0b1020",
        )
        title.pack(pady=(10, 4))

        subtitle = tk.Label(
            self.root,
            text="Secure nodes vs cyber attacks in a 5x5 AI battlefield",
            font=("Helvetica", 10),
            fg="#94a3b8",
            bg="#0b1020",
        )
        subtitle.pack(pady=(0, 10))

        controls_frame = tk.Frame(self.root, bg="#0b1020")
        controls_frame.pack(pady=(0, 10))

        controls_label = tk.Label(
            controls_frame,
            text="Defender MCTS simulations:",
            font=("Helvetica", 10, "bold"),
            fg="#cbd5e1",
            bg="#0b1020",
        )
        controls_label.grid(row=0, column=0, padx=(0, 8))

        self.simulation_menu = tk.OptionMenu(controls_frame, self.simulations, 10, 20, 50)
        self.simulation_menu.configure(width=6, bg="#1e293b", fg="#e2e8f0", highlightthickness=0)
        self.simulation_menu.grid(row=0, column=1)

        sim_value_label = tk.Label(
            controls_frame,
            textvariable=self.sim_value_text,
            font=("Helvetica", 10),
            fg="#67e8f9",
            bg="#0b1020",
        )
        sim_value_label.grid(row=0, column=2, padx=(12, 0))

        speed_label = tk.Label(
            controls_frame,
            text="Playback speed:",
            font=("Helvetica", 10, "bold"),
            fg="#cbd5e1",
            bg="#0b1020",
        )
        speed_label.grid(row=1, column=0, padx=(0, 8), pady=(8, 0), sticky="w")

        speed_slider = tk.Scale(
            controls_frame,
            from_=0.5,
            to=3.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.speed_multiplier,
            command=lambda _value: self._on_speed_change(),
            showvalue=False,
            length=180,
            highlightthickness=0,
            bg="#0b1020",
            fg="#e2e8f0",
            troughcolor="#1e293b",
            activebackground="#22d3ee",
        )
        speed_slider.grid(row=1, column=1, pady=(8, 0), sticky="w")

        speed_value_label = tk.Label(
            controls_frame,
            textvariable=self.speed_text,
            font=("Helvetica", 10),
            fg="#67e8f9",
            bg="#0b1020",
        )
        speed_value_label.grid(row=1, column=2, padx=(12, 0), pady=(8, 0), sticky="w")

        button_frame = tk.Frame(controls_frame, bg="#0b1020")
        button_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky="w")

        control_button_style = {
            "width": 10,
            "font": ("Helvetica", 10, "bold"),
            "fg": "#0f172a",
            "activeforeground": "#0f172a",
            "disabledforeground": "#475569",
            "relief": "raised",
            "bd": 1,
            "highlightthickness": 0,
        }

        self.pause_button = tk.Button(
            button_frame,
            text="Pause",
            command=self.toggle_pause,
            bg="#38bdf8",
            activebackground="#0ea5e9",
            **control_button_style,
        )
        self.pause_button.pack(side="left", padx=(0, 8))

        self.step_button = tk.Button(
            button_frame,
            text="Step",
            command=self.step_turn,
            bg="#2dd4bf",
            activebackground="#14b8a6",
            **control_button_style,
        )
        self.step_button.pack(side="left", padx=(0, 8))

        self.restart_button = tk.Button(
            button_frame,
            text="Restart",
            command=self.restart_game,
            bg="#4ade80",
            activebackground="#22c55e",
            **control_button_style,
        )
        self.restart_button.pack(side="left")

        self.simulations.trace_add("write", self._on_simulation_change)

        self.board_frame = tk.Frame(self.root, bg="#0f172a", bd=2, relief="groove")
        self.board_frame.pack(padx=12, pady=6)

        self.labels = []
        for i in range(self.grid_size):
            row_labels = []
            for j in range(self.grid_size):
                label = tk.Label(
                    self.board_frame,
                    image=self.icons[self.board[i][j]],
                    bg="#0f172a",
                    bd=1,
                    relief="solid",
                )
                label.grid(row=i, column=j, padx=3, pady=3)
                row_labels.append(label)
            self.labels.append(row_labels)

        stats_frame = tk.Frame(self.root, bg="#0b1020")
        stats_frame.pack(fill="x", padx=12, pady=(6, 4))

        stats_title = tk.Label(
            stats_frame,
            text="Live Node Stats",
            font=("Helvetica", 10, "bold"),
            fg="#cbd5e1",
            bg="#0b1020",
        )
        stats_title.grid(row=0, column=0, padx=(0, 12), sticky="w")

        secure_label = tk.Label(
            stats_frame,
            textvariable=self.secure_text,
            font=("Helvetica", 10),
            fg="#93c5fd",
            bg="#0b1020",
        )
        secure_label.grid(row=0, column=1, padx=(0, 12), sticky="w")

        vulnerable_label = tk.Label(
            stats_frame,
            textvariable=self.vulnerable_text,
            font=("Helvetica", 10),
            fg="#fde047",
            bg="#0b1020",
        )
        vulnerable_label.grid(row=0, column=2, padx=(0, 12), sticky="w")

        compromised_label = tk.Label(
            stats_frame,
            textvariable=self.compromised_text,
            font=("Helvetica", 10),
            fg="#f87171",
            bg="#0b1020",
        )
        compromised_label.grid(row=0, column=3, sticky="w")

        log_frame = tk.Frame(self.root, bg="#0b1020")
        log_frame.pack(fill="both", expand=True, padx=12, pady=(2, 8))

        log_title = tk.Label(
            log_frame,
            text="Turn Event Log",
            font=("Helvetica", 10, "bold"),
            fg="#cbd5e1",
            bg="#0b1020",
        )
        log_title.pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg="#111827",
            fg="#d1d5db",
            insertbackground="#d1d5db",
            relief="solid",
            bd=1,
            wrap="word",
            state="disabled",
            font=("Courier", 10),
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        status_frame = tk.Frame(self.root, bg="#0b1020")
        status_frame.pack(fill="x", padx=12, pady=(8, 12))

        status_label = tk.Label(
            status_frame,
            textvariable=self.status_text,
            anchor="w",
            justify="left",
            font=("Helvetica", 11, "bold"),
            fg="#f8fafc",
            bg="#0b1020",
            wraplength=640,
        )
        status_label.pack(fill="x")

    def _on_simulation_change(self, *_):
        self.sim_value_text.set(f"Current MCTS simulations: {self.simulations.get()}")

    def _on_speed_change(self):
        factor = max(0.5, float(self.speed_multiplier.get()))
        self.think_delay_ms = max(80, int(self.base_think_delay_ms / factor))
        self.turn_delay_ms = max(80, int(self.base_turn_delay_ms / factor))
        self.flash_delay_ms = max(30, int(self.base_flash_delay_ms / factor))
        self.speed_text.set(f"x{factor:.1f}")

    def _set_status(self, text):
        self.status_text.set(text)

    def _append_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 300:
            self.log_text.delete("1.0", f"{line_count - 300}.0")

        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _state_letter(self, state):
        return {0: "S", 1: "V", 2: "C"}.get(state, "?")

    def _update_stats(self):
        secure, vulnerable, compromised = count_states(self.board)
        self.secure_text.set(f"Secure: {secure}")
        self.vulnerable_text.set(f"Vulnerable: {vulnerable}")
        self.compromised_text.set(f"Compromised: {compromised}")

    def _update_controls(self):
        self.pause_button.configure(text="Resume" if self.paused else "Pause")

        if not self.running:
            self.simulation_menu.configure(state="disabled")
            self.pause_button.configure(state="disabled")
            self.step_button.configure(state="disabled")
            self.restart_button.configure(state="normal")
            return

        self.simulation_menu.configure(state="normal")
        self.pause_button.configure(state="normal")
        self.restart_button.configure(state="normal")

        if self.paused and not self.worker_busy:
            self.step_button.configure(state="normal")
        else:
            self.step_button.configure(state="disabled")

    def toggle_pause(self):
        if not self.running:
            return

        if self.paused:
            self.paused = False
            self.pause_requested = False
            self._append_log(f"Resumed before Turn {self.turn_number}.")
            self._set_status(f"Resumed at Turn {self.turn_number}.")
            self._update_controls()
            if not self.worker_busy:
                self.root.after(60, self._schedule_next_phase)
            return

        if self.worker_busy:
            self.pause_requested = True
            self._set_status("Pause requested. The game will pause after this turn.")
            self._append_log("Pause requested.")
        else:
            self.paused = True
            self._set_status(f"Paused before Turn {self.turn_number}.")
            self._append_log(f"Paused before Turn {self.turn_number}.")

        self._update_controls()

    def step_turn(self):
        if not self.running:
            return

        if not self.paused:
            self._set_status("Pause the game before stepping.")
            return

        if self.worker_busy:
            self._set_status("Please wait. A move is still being computed.")
            return

        self.pending_step = True
        self.paused = False
        self.pause_requested = False

        self._append_log(f"Stepping from {self.next_phase} phase.")
        self._set_status(f"Stepping from {self.next_phase} phase...")
        self._update_controls()
        self.root.after(60, self._schedule_next_phase)

    def restart_game(self):
        self.game_token += 1
        self.board = create_board()
        self.previous_board = clone(self.board)
        self.grid_size = len(self.board)

        self.running = True
        self.worker_busy = False
        self.paused = False
        self.pause_requested = False
        self.pending_step = False
        self.turn_number = 1
        self.next_phase = "attacker"

        if self.winner_popup and self.winner_popup.winfo_exists():
            self.winner_popup.destroy()
        self.winner_popup = None

        self._clear_log()
        self._append_log("New match started.")

        self.update_ui(animated=False)
        self._set_status("Turn 1: Attacker (Minimax) is thinking...")
        self._update_controls()
        self.root.after(200, self._schedule_next_phase)

    def _schedule_next_phase(self):
        if not self.running or self.paused:
            return

        winner = is_game_over(self.board)
        if winner:
            self._finish_game(winner)
            return

        if self.next_phase == "attacker":
            self._set_status(f"Turn {self.turn_number}: Attacker (Minimax) is thinking...")
            self.root.after(self.think_delay_ms, self._run_attacker_async)
        else:
            self._set_status(f"Turn {self.turn_number}: Defender (MCTS) is responding...")
            self.root.after(self.think_delay_ms, self._run_defender_async)

    def _run_attacker_async(self):
        if not self.running or self.worker_busy or self.paused or self.next_phase != "attacker":
            return

        self.worker_busy = True
        self._update_controls()
        board_snapshot = clone(self.board)
        token = self.game_token
        threading.Thread(target=self._attacker_worker, args=(board_snapshot, token), daemon=True).start()

    def _attacker_worker(self, board_snapshot, token):
        _, move = minimax(board_snapshot, ATTACKER_MINIMAX_DEPTH, True)
        self.root.after(0, lambda chosen_move=move, game_token=token: self._apply_attacker_move(chosen_move, game_token))

    def _apply_attacker_move(self, move, token):
        if token != self.game_token:
            return

        self.worker_busy = False
        self._update_controls()

        if not self.running:
            return

        if move is not None:
            i, j = move
            before = self.board[i][j]
            changed = apply_attack(self.board, move)
            after = self.board[i][j]

            if changed:
                self._append_log(
                    f"Turn {self.turn_number}: Attacker compromised node at row {i + 1}, col {j + 1} "
                    f"({self._state_letter(before)}->{self._state_letter(after)})."
                )
            else:
                self._append_log(
                    f"Turn {self.turn_number}: Attacker attempted row {i + 1}, col {j + 1} with no change."
                )
        else:
            self._append_log(f"Turn {self.turn_number}: Attacker had no legal move.")

        self.update_ui(animated=True)

        winner = is_game_over(self.board)
        if winner:
            self._finish_game(winner)
            return

        self.next_phase = "defender"
        self.root.after(self.turn_delay_ms, self._schedule_next_phase)

    def _run_defender_async(self):
        if not self.running or self.worker_busy or self.paused or self.next_phase != "defender":
            return

        self.worker_busy = True
        self._update_controls()
        board_snapshot = clone(self.board)
        simulations = self.simulations.get()
        token = self.game_token
        threading.Thread(target=self._defender_worker, args=(board_snapshot, simulations, token), daemon=True).start()

    def _defender_worker(self, board_snapshot, simulations, token):
        move = mcts_decision(board_snapshot, simulations)
        self.root.after(0, lambda chosen_move=move, game_token=token: self._apply_defender_move(chosen_move, game_token))

    def _apply_defender_move(self, move, token):
        if token != self.game_token:
            return

        self.worker_busy = False
        self._update_controls()

        if not self.running:
            return

        if move is not None:
            i, j = move
            before = self.board[i][j]
            changed = apply_defense(self.board, move)
            after = self.board[i][j]

            if changed:
                action = "isolated" if before == 2 else "secured"
                self._append_log(
                    f"Turn {self.turn_number}: Defender {action} node at row {i + 1}, col {j + 1} "
                    f"({self._state_letter(before)}->{self._state_letter(after)})."
                )
            else:
                self._append_log(
                    f"Turn {self.turn_number}: Defender attempted row {i + 1}, col {j + 1} with no change."
                )
        else:
            self._append_log(f"Turn {self.turn_number}: Defender had no legal move.")

        self.update_ui(animated=True)

        winner = is_game_over(self.board)
        if winner:
            self._finish_game(winner)
            return

        self.turn_number += 1
        self.next_phase = "attacker"

        if self.pending_step:
            self.pending_step = False
            self.paused = True
            self._set_status(f"Paused before Turn {self.turn_number}.")
            self._append_log(f"Step complete. Paused before Turn {self.turn_number}.")
            self._update_controls()
            return

        if self.pause_requested:
            self.pause_requested = False
            self.paused = True
            self._set_status(f"Paused before Turn {self.turn_number}.")
            self._append_log(f"Paused before Turn {self.turn_number}.")
            self._update_controls()
            return

        self._set_status(f"Turn {self.turn_number}: Attacker (Minimax) is thinking...")
        self.root.after(self.turn_delay_ms, self._schedule_next_phase)

    def _finish_game(self, winner):
        self.running = False
        self.paused = True
        self.pause_requested = False
        self.pending_step = False
        self._set_status(f"Game Over: Winner = {winner}")
        self._append_log(f"Game Over: {winner} wins.")
        self._update_controls()

        self._show_winner_popup(winner)
        print("Winner:", winner)

    def _show_winner_popup(self, winner):
        if self.winner_popup and self.winner_popup.winfo_exists():
            self.winner_popup.destroy()

        popup = tk.Toplevel(self.root)
        popup.title("Match Result")
        popup.configure(bg="#0b1020")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        title = tk.Label(
            popup,
            text="Simulation Complete",
            font=("Helvetica", 14, "bold"),
            fg="#e2e8f0",
            bg="#0b1020",
        )
        title.pack(padx=24, pady=(18, 10))

        winner_text = tk.Label(
            popup,
            text=f"Winner: {winner}",
            font=("Helvetica", 12),
            fg="#67e8f9",
            bg="#0b1020",
        )
        winner_text.pack(padx=24, pady=(0, 14))

        button_frame = tk.Frame(popup, bg="#0b1020")
        button_frame.pack(pady=(0, 18))

        play_again_button = tk.Button(
            button_frame,
            text="Play Again",
            width=12,
            command=lambda: self._handle_play_again(popup),
            font=("Helvetica", 10, "bold"),
            bg="#4ade80",
            fg="#0f172a",
            activebackground="#22c55e",
            activeforeground="#0f172a",
            disabledforeground="#475569",
            highlightthickness=0,
        )
        play_again_button.pack(side="left", padx=(0, 10))

        close_button = tk.Button(
            button_frame,
            text="Close",
            width=12,
            command=popup.destroy,
            font=("Helvetica", 10, "bold"),
            bg="#a5f3fc",
            fg="#0f172a",
            activebackground="#67e8f9",
            activeforeground="#0f172a",
            disabledforeground="#475569",
            highlightthickness=0,
        )
        close_button.pack(side="left")

        self.winner_popup = popup

    def _handle_play_again(self, popup):
        popup.destroy()
        self.winner_popup = None
        self.restart_game()

    def update_ui(self, animated=False):
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                state = self.board[i][j]
                target_icon = self.icons[state]
                label = self.labels[i][j]
                changed = self.previous_board[i][j] != state

                if animated and changed:
                    label.config(image=self.flash_icon)
                    self.root.after(
                        self.flash_delay_ms,
                        lambda target_label=label, icon=target_icon: target_label.config(image=icon),
                    )
                else:
                    label.config(image=target_icon)

        self.previous_board = clone(self.board)
        self._update_stats()

    def _load_icons(self):
        icons = {}
        asset_map = {
            0: "shield.png",
            1: "warning.png",
            2: "hacker.png",
        }
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")

        for state, filename in asset_map.items():
            path = os.path.join(assets_dir, filename)
            if os.path.exists(path):
                try:
                    icons[state] = tk.PhotoImage(file=path)
                except tk.TclError:
                    pass

        fallback_icons = self._create_fallback_icons()
        for state in (0, 1, 2):
            if state not in icons:
                icons[state] = fallback_icons[state]

        return icons

    def _create_fallback_icons(self):
        size = 56

        secure = self._new_icon(size, "#0f172a")
        self._draw_secure_icon(secure, size)

        vulnerable = self._new_icon(size, "#0f172a")
        self._draw_warning_icon(vulnerable, size)

        compromised = self._new_icon(size, "#0f172a")
        self._draw_compromised_icon(compromised, size)

        return {
            0: secure,
            1: vulnerable,
            2: compromised,
        }

    def _new_icon(self, size, bg):
        icon = tk.PhotoImage(width=size, height=size)
        icon.put(bg, to=(0, 0, size, size))
        return icon

    def _create_flash_icon(self, size):
        icon = self._new_icon(size, "#182543")
        icon.put("#7dd3fc", to=(2, 2, size - 2, size - 2))
        icon.put("#182543", to=(5, 5, size - 5, size - 5))
        return icon

    def _draw_secure_icon(self, icon, size):
        for y in range(9, 41):
            if y < 21:
                inset = 16 - (y - 9) // 2
            else:
                inset = 10 + (y - 21) // 3
            icon.put("#1d4ed8", to=(inset, y, size - inset, y + 1))

        for y in range(11, 38):
            if y < 20:
                inset = 18 - (y - 11) // 2
            else:
                inset = 13 + (y - 20) // 3
            icon.put("#38bdf8", to=(inset, y, size - inset, y + 1))

        for step in range(6):
            icon.put("#e0f2fe", to=(20 + step, 29 + step, 23 + step, 31 + step))
        for step in range(11):
            icon.put("#e0f2fe", to=(26 + step, 35 - step, 29 + step, 37 - step))

    def _draw_warning_icon(self, icon, size):
        center = size // 2

        for y in range(10, 45):
            half = (y - 10) // 2
            x1 = center - half
            x2 = center + half
            icon.put("#f59e0b", to=(x1, y, x2 + 1, y + 1))

        for y in range(13, 43):
            half = max(0, (y - 13) // 2 - 2)
            x1 = center - half
            x2 = center + half
            icon.put("#facc15", to=(x1, y, x2 + 1, y + 1))

        icon.put("#1f2937", to=(center - 2, 21, center + 2, 34))
        icon.put("#1f2937", to=(center - 2, 37, center + 2, 40))

    def _draw_compromised_icon(self, icon, size):
        for y in range(9, 43):
            if y < 15 or y > 37:
                inset = 14
            elif y < 21 or y > 31:
                inset = 10
            else:
                inset = 8
            icon.put("#991b1b", to=(inset, y, size - inset, y + 1))

        for y in range(12, 40):
            if y < 18 or y > 34:
                inset = 16
            elif y < 22 or y > 30:
                inset = 12
            else:
                inset = 10
            icon.put("#ef4444", to=(inset, y, size - inset, y + 1))

        icon.put("#0b1020", to=(18, 21, 38, 34))
        icon.put("#22d3ee", to=(20, 24, 26, 27))
        icon.put("#22d3ee", to=(30, 24, 36, 27))
        icon.put("#fecaca", to=(22, 31, 34, 32))