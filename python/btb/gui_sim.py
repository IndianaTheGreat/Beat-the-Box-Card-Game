"""
==============================================
SIMULATOR AND STRATEGY OPTIMIZER WINDOWS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/gui_sim.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Replaces the GUIs in BTBSimulator.py and BTBOptimizer.py.
- Runs on a worker thread with a Stop button and live progress; the
  window never freezes.
- Input validation: positive counts, step > 0, ordered ranges, limits.
- Optional seed, shown in the results so a run can be repeated.
- Fixed a crash: Python's garbage collector could free Tk objects on the
  worker thread and abort the process.

DESCRIPTION:
-----------
Windows for btb.sim. The worker thread never touches Tk; it reports
progress through a queue that the window polls.

DEPENDENCIES:
------------
- btb.engine, btb.sim
- Standard library: tkinter, threading, queue, gc, time, typing

KEY FUNCTIONS:
-------------
- BackgroundTask(root, work, on_progress, on_done, on_error) -> runs
  work(progress, should_stop) on a thread, reports on the Tk thread
- SimulatorGUI -> one batch, results and Advanced Statistics
- OptimizerGUI -> parameter sweep, top results and Advanced Statistics
- describe_batch / describe_sweep (+ _details) -> results text

ERROR HANDLING:
--------------
Invalid input shows an error dialog and nothing starts. An exception in
the worker is reported in a dialog and the Run button comes back. Closing
a window mid-run stops its worker.

NOTES:
-----
- While any worker runs, automatic cyclic garbage collection is paused
  and the window collects on the Tk thread instead (_GcPause). Without
  this, Tcl aborts with "async handler deleted by the wrong thread".
- Polling is scheduled on the app root, so it survives a closed window.
- Runs over 2,000,000 games ask for confirmation first.
"""

from __future__ import annotations

import gc
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

from .engine import MAX_JOKERS, max_inclusive_calls, new_seed
from .sim import (
    BatchResult, SweepResult, counter_mean, float_range, mean, run_batch,
    run_sweep, sweep_grid,
)

POLL_MS = 50
GC_EVERY_S = 1.0
LARGE_RUN_GAMES = 2_000_000


class _GcPause:
    """Reference-counted pause of automatic garbage collection (Tk thread only)."""

    active = 0
    was_enabled = False

    @classmethod
    def acquire(cls) -> None:
        if cls.active == 0:
            cls.was_enabled = gc.isenabled()
            gc.disable()
        cls.active += 1

    @classmethod
    def release(cls) -> None:
        cls.active -= 1
        if cls.active == 0:
            gc.collect()
            if cls.was_enabled:
                gc.enable()


class BackgroundTask:
    """Run ``work(progress, should_stop)`` on a thread; report back on Tk's thread."""

    def __init__(self, root: tk.Misc, work: Callable, on_progress: Callable[[int, int], None],
                 on_done: Callable[[object], None], on_error: Callable[[BaseException], None]):
        self.root = root
        # Poll through the application's root window: callbacks scheduled on
        # this window would be cancelled if it were closed mid-run.
        self._scheduler = root._root()
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._stop = threading.Event()
        self._on_progress, self._on_done, self._on_error = on_progress, on_done, on_error
        self._last_gc = time.monotonic()
        self._finished = False

        # The worker holds no reference to any Tk object (not even `self`),
        # so it can never be the thread that frees one.
        results, stop = self._queue, self._stop

        def run():
            try:
                outcome = work(lambda d, t: results.put(("progress", d, t)), stop.is_set)
                results.put(("done", outcome))
            except BaseException as exc:  # reported on the GUI thread
                results.put(("error", exc))

        _GcPause.acquire()
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self._scheduler.after(POLL_MS, self._poll)

    def stop(self):
        self._stop.set()

    @property
    def running(self) -> bool:
        return not self._finished

    def _finish(self):
        if not self._finished:
            self.thread.join(timeout=5)
            self._finished = True
            _GcPause.release()

    def _window_alive(self) -> bool:
        try:
            return bool(self.root.winfo_exists())
        except tk.TclError:
            return False

    def _poll(self):
        alive = self._window_alive()
        if not alive:
            self._stop.set()  # window closed: wind the worker down
        latest = None
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] == "progress":
                    latest = item
                    continue
                self._finish()
                if alive:
                    if latest:
                        self._on_progress(latest[1], latest[2])
                    (self._on_done if item[0] == "done" else self._on_error)(item[1])
                return
        except queue.Empty:
            pass
        if alive and latest:
            self._on_progress(latest[1], latest[2])
        if time.monotonic() - self._last_gc >= GC_EVERY_S:
            gc.collect()
            self._last_gc = time.monotonic()
        try:
            self._scheduler.after(POLL_MS, self._poll)
        except tk.TclError:  # the whole app is gone
            self._finish()


class _RunnerWindow:
    """Shared plumbing: progress bar, Run/Stop buttons, a results box."""

    TITLE = ""

    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title(self.TITLE)
        self.task: Optional[BackgroundTask] = None
        self.main = ttk.Frame(self.root, padding=10)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main.columnconfigure(0, weight=1)
        self.build_inputs()

        progress = ttk.LabelFrame(self.main, text="Progress", padding=5)
        progress.grid(row=1, column=0, sticky="ew", pady=8)
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(progress, variable=self.progress_var, maximum=100).pack(
            fill="x", padx=5, pady=4)
        self.progress_label = ttk.Label(progress, text="Ready")
        self.progress_label.pack()

        buttons = ttk.Frame(self.main)
        buttons.grid(row=2, column=0, pady=5)
        self.run_button = ttk.Button(buttons, text=self.RUN_LABEL, command=self.start)
        self.run_button.pack(side="left", padx=4)
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop,
                                      state="disabled")
        self.stop_button.pack(side="left", padx=4)
        self.stats_button = ttk.Button(buttons, text="Advanced Statistics",
                                       command=self.show_advanced_stats)
        self.stats_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear Results", command=self.clear).pack(side="left", padx=4)

        self.results_text = tk.Text(self.main, height=18, width=72, font=("Consolas", 10))
        self.results_text.grid(row=3, column=0, sticky="nsew", pady=5)
        self.main.rowconfigure(3, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    RUN_LABEL = "Run"

    # subclass hooks
    def build_inputs(self): ...
    def make_work(self) -> Optional[Callable]: ...
    def show_results(self, result): ...
    def show_advanced_stats(self): ...

    def error(self, message: str):
        messagebox.showerror("Invalid input", message, parent=self.root)

    def start(self):
        if self.task and self.task.running:
            return
        work = self.make_work()
        if work is None:
            return
        self.clear()
        self.run_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.progress_label.config(text="Starting...")
        self.task = BackgroundTask(self.root, work, self.on_progress,
                                   self.on_done, self.on_error)

    def stop(self):
        if self.task:
            self.task.stop()
            self.progress_label.config(text="Stopping...")

    def close(self):
        self.stop()
        self.root.destroy()

    def clear(self):
        self.results_text.delete("1.0", "end")
        self.progress_var.set(0)
        self.progress_label.config(text="Ready")

    def on_progress(self, done: int, total: int):
        pct = 100.0 * done / total if total else 100.0
        self.progress_var.set(pct)
        self.progress_label.config(text=f"{pct:.1f}% complete ({done:,} of {total:,} games)")

    def _finish(self):
        self.run_button.state(["!disabled"])
        self.stop_button.state(["disabled"])

    def on_done(self, result):
        self._finish()
        if getattr(result, "stopped", False):
            self.progress_label.config(text=f"Stopped. {self.progress_label.cget('text')}")
        else:
            self.progress_var.set(100)
            self.progress_label.config(text="100% complete")
        self.show_results(result)

    def on_error(self, exc: BaseException):
        self._finish()
        self.progress_label.config(text="Failed")
        messagebox.showerror("Error", f"The run failed: {exc}", parent=self.root)

    def write(self, body: str):
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", body)
        self.results_text.see("1.0")

    def text_window(self, title: str, body: str):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("620x720")
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        widget = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                         font=("Consolas", 10))
        widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=widget.yview)
        widget.insert("1.0", body)
        widget.config(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))
        return win


def _parse_seed(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return new_seed()
    seed = int(value)
    if seed < 0:
        raise ValueError
    return seed


def describe_batch(result: BatchResult, seed: Optional[int]) -> str:
    lines = [
        f"Games played:        {result.games:,}" + ("  (stopped early)" if result.stopped else ""),
        f"Wins:                {result.wins:,} ({result.win_rate:.1f}%)",
        f"Losses:              {result.losses:,} ({100 - result.win_rate if result.games else 0:.1f}%)",
        f"Avg plays per game:  {mean(result.plays):.1f}",
        f"Avg inclusive used:  {mean(result.inclusive_used):.1f} of {result.inclusive_calls}",
        f"Avg recoveries:      {mean(result.recoveries):.2f}",
        f"Avg jokers drawn:    {mean(result.jokers_drawn):.2f}",
        f"Seed:                {seed}",
    ]
    return "\n".join(lines)


def describe_batch_details(result: BatchResult, seed: Optional[int]) -> str:
    def distribution(counter, unit: str, of: int) -> str:
        if not counter:
            return "  (none)"
        return "\n".join(f"  {k:>2} {unit}: {v:,} ({100 * v / of:.1f}%)"
                         for k, v in sorted(counter.items()))

    usage = (100 * mean(result.inclusive_used) / result.inclusive_calls
             if result.inclusive_calls else 0.0)
    return "\n".join([
        "=== Settings ===",
        f"Jokers: {result.jokers}   Inclusive calls: {result.inclusive_calls}   "
        f"Threshold: {result.threshold}%   Seed: {seed}",
        "",
        "=== Overall ===",
        f"Games: {result.games:,}   Win rate: {result.win_rate:.2f}%",
        "",
        "=== Plays ===",
        f"Average: {mean(result.plays):.1f}   Max: {max(result.plays, default=0)}   "
        f"Min: {min(result.plays, default=0)}",
        "",
        "=== Inclusive calls ===",
        f"Average used: {mean(result.inclusive_used):.2f}   "
        f"Max used: {max(result.inclusive_used, default=0)}   Usage rate: {usage:.1f}%",
        f"Average recoveries: {mean(result.recoveries):.2f}",
        "",
        "=== Jokers ===",
        f"Average drawn: {mean(result.jokers_drawn):.2f}   "
        f"Max drawn: {max(result.jokers_drawn, default=0)}",
        "",
        "=== Wins: boxes left ===",
        f"Average: {counter_mean(result.boxes_left_in_wins):.2f}",
        distribution(result.boxes_left_in_wins, "boxes", result.wins),
        "",
        "=== Losses: cards left in the pile ===",
        f"Average: {counter_mean(result.cards_left_in_losses):.2f}",
        distribution(result.cards_left_in_losses, "cards", result.losses),
    ])


class SimulatorGUI(_RunnerWindow):
    """📊 Simulator: play many games with the threshold strategy."""

    TITLE = "Beat the Box: Simulator"
    RUN_LABEL = "Run Simulations"

    def build_inputs(self):
        self.result: Optional[BatchResult] = None
        self.seed: Optional[int] = None
        form = ttk.LabelFrame(self.main, text="Settings", padding=8)
        form.grid(row=0, column=0, sticky="ew")
        self.sims_var = tk.StringVar(value="1000")
        self.jokers_var = tk.StringVar(value="0")
        self.calls_var = tk.StringVar(value="5")
        self.threshold_var = tk.StringVar(value="5")
        self.seed_var = tk.StringVar(value="")
        rows = [("Number of games:", ttk.Entry(form, textvariable=self.sims_var, width=12)),
                ("Jokers:", ttk.Combobox(form, textvariable=self.jokers_var, width=10,
                                         state="readonly", values=list(range(MAX_JOKERS + 1)))),
                ("Inclusive calls:", ttk.Combobox(form, textvariable=self.calls_var, width=10)),
                ("Inclusive threshold (% points):",
                 ttk.Entry(form, textvariable=self.threshold_var, width=12)),
                ("Seed (blank = random):", ttk.Entry(form, textvariable=self.seed_var, width=12))]
        for r, (label, widget) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            widget.grid(row=r, column=1, sticky="w", pady=2, padx=6)
        self.calls_combo = rows[2][1]
        self.jokers_var.trace_add("write", self._update_calls)
        self._update_calls()

    def _update_calls(self, *_):
        self.calls_combo["values"] = list(range(max_inclusive_calls(int(self.jokers_var.get())) + 1))

    def make_work(self):
        try:
            games = int(self.sims_var.get())
            jokers = int(self.jokers_var.get())
            calls = int(self.calls_var.get())
            threshold = float(self.threshold_var.get())
            seed = _parse_seed(self.seed_var.get())
        except ValueError:
            self.error("Please enter valid numbers (the seed must be a whole number ≥ 0).")
            return None
        if games <= 0:
            self.error("The number of games must be positive.")
            return None
        limit = max_inclusive_calls(jokers)
        if not 0 <= calls <= limit:
            self.error(f"Inclusive calls must be 0-{limit} with {jokers} joker(s).")
            return None
        if not 0 <= threshold <= 100:
            self.error("The threshold must be between 0 and 100.")
            return None
        self.seed = seed
        return lambda progress, stop: run_batch(games, jokers, calls, threshold, seed,
                                                progress, stop)

    def show_results(self, result: BatchResult):
        self.result = result
        self.write(describe_batch(result, self.seed))

    def show_advanced_stats(self):
        if not self.result or not self.result.games:
            messagebox.showinfo("No data", "Run some simulations first.", parent=self.root)
            return
        self.text_window("Advanced Statistics", describe_batch_details(self.result, self.seed))


def describe_sweep(sweep: SweepResult, seed: Optional[int]) -> str:
    if not sweep.results:
        return "No configuration finished. Nothing to report."
    lines = []
    if sweep.stopped:
        lines.append(f"Stopped early: {len(sweep.results)} of {sweep.planned} "
                     "configurations finished.\n")
    best = sweep.best
    lines.append(f"Seed: {seed} (every configuration plays the same deals)\n")
    if best.win_rate == 0:
        lines.append("Every configuration won 0% of its games. "
                     "Try more games per test or more inclusive calls.\n")
    lines.append("=== Top 10 configurations ===")
    for r in sweep.ranked()[:10]:
        lines.append(f"{r.win_rate:6.2f}%  jokers {r.jokers}  inclusive {r.inclusive_calls:>2}"
                     f"  threshold {r.threshold:g}%")
    for param, title in (("jokers", "Jokers"), ("moves", "Inclusive calls"),
                         ("threshold", "Threshold")):
        lines.append(f"\n=== Top 5 for each {title.lower()} value ===")
        for value, results in sweep.top_by(param, 5).items():
            lines.append(f"{title}: {value:g}" if isinstance(value, float)
                         else f"{title}: {value}")
            for r in results:
                lines.append(f"   {r.win_rate:6.2f}%  jokers {r.jokers}  inclusive "
                             f"{r.inclusive_calls:>2}  threshold {r.threshold:g}%")
    return "\n".join(lines)


def describe_sweep_details(sweep: SweepResult, seed: Optional[int]) -> str:
    best = sweep.best
    lines = ["=== Best overall ===",
             f"Jokers: {best.jokers}   Inclusive calls: {best.inclusive_calls}   "
             f"Threshold: {best.threshold:g}%   Win rate: {best.win_rate:.2f}%",
             f"Games per test: {best.games:,}   Seed: {seed}"]
    for param, title in (("jokers", "joker count"), ("moves", "inclusive calls"),
                         ("threshold", "threshold")):
        lines.append(f"\n=== Best for each {title} ===")
        for value, r in sweep.best_by(param).items():
            lines.append(f"{value!s:>6}: {r.win_rate:6.2f}%  (jokers {r.jokers}, "
                         f"inclusive {r.inclusive_calls}, threshold {r.threshold:g}%)")
    return "\n".join(lines)


class OptimizerGUI(_RunnerWindow):
    """🔬 Strategy Optimizer: sweep jokers, inclusive calls and thresholds."""

    TITLE = "Beat the Box: Strategy Optimizer"
    RUN_LABEL = "Run Optimization"

    def build_inputs(self):
        self.sweep: Optional[SweepResult] = None
        self.seed: Optional[int] = None
        form = ttk.LabelFrame(self.main, text="Optimization Parameters", padding=8)
        form.grid(row=0, column=0, sticky="ew")
        self.vars = {name: tk.StringVar(value=value) for name, value in (
            ("games", "1000"), ("jokers_min", "0"), ("jokers_max", "2"),
            ("moves_min", "0"), ("moves_max", "10"), ("threshold_min", "0"),
            ("threshold_max", "10"), ("step", "2.5"), ("seed", ""))}

        def pair(row, label, lo, hi):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            box = ttk.Frame(form)
            box.grid(row=row, column=1, sticky="w", padx=6)
            ttk.Entry(box, textvariable=self.vars[lo], width=6).pack(side="left")
            ttk.Label(box, text=" to ").pack(side="left")
            ttk.Entry(box, textvariable=self.vars[hi], width=6).pack(side="left")

        ttk.Label(form, text="Games per test:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.vars["games"], width=10).grid(
            row=0, column=1, sticky="w", padx=6)
        pair(1, "Jokers (0-2):", "jokers_min", "jokers_max")
        pair(2, "Inclusive calls:", "moves_min", "moves_max")
        pair(3, "Threshold (% points):", "threshold_min", "threshold_max")
        ttk.Label(form, text="Threshold step:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.vars["step"], width=10).grid(
            row=4, column=1, sticky="w", padx=6)
        ttk.Label(form, text="Seed (blank = random):").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.vars["seed"], width=10).grid(
            row=5, column=1, sticky="w", padx=6)

    def validate(self):
        """Return (games, grid, seed) or None after showing an error."""
        v = {k: var.get().strip() for k, var in self.vars.items()}
        try:
            games = int(v["games"])
            jmin, jmax = int(v["jokers_min"]), int(v["jokers_max"])
            mmin, mmax = int(v["moves_min"]), int(v["moves_max"])
            tmin, tmax = float(v["threshold_min"]), float(v["threshold_max"])
            step = float(v["step"])
            seed = _parse_seed(v["seed"])
        except ValueError:
            self.error("Please enter valid numbers (the seed must be a whole number ≥ 0).")
            return None
        problems = []
        if games <= 0:
            problems.append("Games per test must be positive.")
        if not 0 <= jmin <= jmax <= MAX_JOKERS:
            problems.append(f"Jokers must satisfy 0 ≤ min ≤ max ≤ {MAX_JOKERS}.")
        if not 0 <= mmin <= mmax:
            problems.append("Inclusive calls must satisfy 0 ≤ min ≤ max.")
        elif mmin > max_inclusive_calls(min(jmax, MAX_JOKERS)):
            problems.append(f"Inclusive calls min is above the limit "
                            f"({max_inclusive_calls(min(jmax, MAX_JOKERS))}).")
        if not 0 <= tmin <= tmax <= 100:
            problems.append("Threshold must satisfy 0 ≤ min ≤ max ≤ 100.")
        if step <= 0:
            problems.append("Threshold step must be greater than 0.")
        if problems:
            self.error("\n".join(problems))
            return None
        grid = sweep_grid((jmin, jmax), (mmin, mmax), float_range(tmin, tmax, step))
        if not grid:
            self.error("Those ranges contain no legal configurations.")
            return None
        return games, grid, seed

    def make_work(self):
        checked = self.validate()
        if checked is None:
            return None
        games, grid, seed = checked
        total = games * len(grid)
        if total > LARGE_RUN_GAMES and not messagebox.askyesno(
                "Large run", f"This will play {total:,} games over {len(grid)} "
                "configurations and may take a while. You can stop it at any time. "
                "Continue?", parent=self.root):
            return None
        self.seed = seed
        return lambda progress, stop: run_sweep(games, grid, seed, progress, stop)

    def show_results(self, sweep: SweepResult):
        self.sweep = sweep
        self.write(describe_sweep(sweep, self.seed))

    def show_advanced_stats(self):
        if not self.sweep or not self.sweep.results:
            messagebox.showinfo("No data", "Run an optimization first.", parent=self.root)
            return
        self.text_window("Advanced Statistics", describe_sweep_details(self.sweep, self.seed))