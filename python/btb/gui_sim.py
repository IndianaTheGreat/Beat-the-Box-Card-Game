"""
==============================================
SIMULATOR AND STRATEGY OPTIMIZER PAGES
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/gui_sim.py
Status: ACTIVE
Version: 1.3
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.3 CHANGES (2026-10-20):
- Advanced tabs are charts instead of plain text. Simulator: four tiles
  and a bar chart for every distribution (boxes left in wins, cards left
  in losses, plays per game, inclusive calls used, recoveries, jokers
  drawn), each with its average. Optimizer: the result tiles, win rate
  against the threshold and against inclusive calls (a line per joker
  count, with 95% ranges), the best win rate per joker count, and a table
  of the best configuration for each value. The charts go two to a row
  when there is room and scroll when there are more than fit.
- "Show as text" switches to the full report as text; "Copy text" copies
  it, whichever view is showing.

VERSION 1.2 CHANGES (2026-10-20):
- Pages, not pop-ups: each tool builds inside the frame it is given (a
  page of the one-window app). Advanced Statistics is a tab beside the
  results; input errors, notices and failed runs show on the page; a very
  large run asks for a second press of Run instead of a dialog; "Use Best
  in Simulator" switches to the Simulator page. The menu bar is gone
  (theme in Settings, help in the sidebar). Only the system Save dialog
  for exports still opens a window.
- Resizable: the results, chart and tables follow the window size. The
  settings column is narrower and scrolls if the window is too short; the
  Export and Use Best buttons sit under it, so the results get the full
  height. Tables get a sideways scrollbar when the window is too narrow
  for every column, and the Simulator's tiles go two by two.
- The CPU cores choice is re-read whenever the page is shown, so a change
  made in Settings (or on the other page) is never undone by a stale copy.
- Clear also forgets a pending "press Run again" warning, and Use Best
  won't overwrite a Simulator run that is still going.

VERSION 1.1 CHANGES (2026-10-20):
- New look: settings and controls on the left, results on the right, in
  the chosen theme. Results show as tiles, a chart and tables instead of
  a block of text (the text versions live on in Advanced Statistics).
- Win rates show their 95% margin of error. The Optimizer table marks the
  configurations that are statistically tied with the best, and can be
  sorted by clicking a column heading.
- CPU cores setting (Auto by default, remembered). Auto scans free CPU
  and memory at the start of each run; helpers run at low priority.
- Optimizer: "Confirm top 10" re-runs the best ten on 5x more fresh
  games; "Use Best in Simulator" opens a Simulator with those settings.
- Export CSV / Export JSON buttons in both windows.
- Progress shows games per second; the finish line shows the time taken
  and the number of processes used.
- Advanced Statistics lists every distribution in full.
- Defaults: threshold 10 (Simulator), threshold 0-30 in steps of 5 and
  1,000 games per test (Optimizer). The Simulator also asks before a
  very large run, and the Optimizer refuses sweeps over 5,000 settings.

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
Pages for btb.sim. The worker thread never touches Tk; it reports
progress through a queue that the page polls. Big runs are spread over
helper processes by btb.sim; this file only chooses how many. Given a
window of its own instead of a page, each tool also works on its own (the
tests use that).

DEPENDENCIES:
------------
- btb.engine, btb.sim, btb.strategy, btb.system, btb.export, btb.theme,
  btb.settings, btb.widgets
- Standard library: tkinter, threading, queue, gc, time, dataclasses,
  pathlib, typing

KEY FUNCTIONS:
-------------
- BackgroundTask(root, work, on_progress, on_done, on_error) -> runs
  work(progress, should_stop) on a thread, reports on the Tk thread
- SimulatorGUI(parent, app) -> one batch: tiles, chart, details, exports
- OptimizerGUI(parent, app) -> parameter sweep: ranked table, confirm,
  exports, Use Best in Simulator
- describe_batch / describe_sweep (+ _details) -> the Advanced report as text
- build_advanced / show_advanced_charts / reset_advanced_charts -> the
  Advanced charts (each page); layout_advanced, copy_advanced, arrange_charts

ERROR HANDLING:
--------------
Invalid input shows a red message on the page and nothing starts. An
exception in the worker is reported the same way and the Run button comes
back. Closing a window mid-run stops its worker. A failed export shows
the reason.

NOTES:
-----
- While any worker runs, automatic cyclic garbage collection is paused
  and the window collects on the Tk thread instead (_GcPause). Without
  this, Tcl aborts with "async handler deleted by the wrong thread".
- Polling is scheduled on the app root, so it survives a closed window.
- The work functions capture only plain values (numbers, strings), never
  a widget, so the worker thread can't end up freeing a Tk object.
"""

from __future__ import annotations

import gc
import queue
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable, Dict, List, Optional, Tuple

from . import export as exporter
from . import settings as app_settings
from . import theme as themes
from .engine import BOX_SIZE, MAX_JOKERS, max_inclusive_calls, new_seed
from .sim import (
    MAX_CONFIGS, BatchResult, SweepResult, best_curves, counter_max, counter_mean,
    counter_min, distribution, float_range, run_batch, run_sweep, sweep_games, sweep_grid,
)
from .strategy import DEFAULT_THRESHOLD
from .system import cpu_count, resolve_workers
from .theme import Theme, font
from .widgets import (
    BarChart, LineChart, ScrollFrame, StatTile, flow_row, readable_on, scrolled_tree,
    wrap_to,
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


@dataclass
class RunOutcome:
    """What a finished run hands back to the window."""
    result: object
    workers: int
    seconds: float


def _cores_label(setting) -> str:
    return "Auto" if setting in (None, "auto") else str(setting)


def _cores_setting(label: str):
    label = label.strip()
    if not label or label.lower().startswith("auto"):
        return "auto"
    try:
        return max(1, int(label))
    except ValueError:
        return "auto"


def _parse_seed(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return new_seed()
    seed = int(value)
    if seed < 0:
        raise ValueError
    return seed


def _plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 'es' if word.endswith('s') else 's'}"


class _RunnerWindow:
    """Shared plumbing: header, settings column (Run/Stop, progress, an
    inline message line, Export buttons), and a results area with tabs."""

    WRAP = 270          # text width in the settings column

    TITLE = ""
    HEADING = ""
    SUBTITLE = ""
    TOOL = ""
    RUN_LABEL = "Run"

    def __init__(self, parent: tk.Misc, app=None):
        self.app = app
        self.root = parent.winfo_toplevel()
        self.standalone = parent is self.root
        if self.standalone:
            self.root.title(self.TITLE)
        self.theme: Theme = themes.use(self.root)
        self.task: Optional[BackgroundTask] = None
        self.outcome: Optional[RunOutcome] = None
        self._started = 0.0
        self._pending_large: Optional[tuple] = None
        self._text_widgets: List[tk.Misc] = []
        self.cores_var = tk.StringVar(value=_cores_label(app_settings.get("cpu_workers")))
        self.message_var = tk.StringVar(value="")

        self.frame = ttk.Frame(parent, padding=14)
        self.frame.grid(row=0, column=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.main = self.frame
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(header, text=self.HEADING, style="Heading.TLabel").pack(anchor="w")
        ttk.Label(header, text=self.SUBTITLE, style="Muted.TLabel").pack(anchor="w")

        # The settings column scrolls if the window is too short for it.
        self.left_scroll = ScrollFrame(self.frame)
        self.left_scroll.grid(row=1, column=0, sticky="ns", padx=(0, 16))
        left = self.left_scroll.body
        form = ttk.LabelFrame(left, text="Settings", padding=10)
        form.pack(fill="x")
        self.build_inputs(form)

        speed = ttk.LabelFrame(left, text="Speed", padding=10)
        speed.pack(fill="x", pady=(10, 0))
        ttk.Label(speed, text="CPU cores:").grid(row=0, column=0, sticky="w")
        cores = ttk.Combobox(speed, textvariable=self.cores_var, width=8, state="readonly",
                             values=["Auto"] + [str(n) for n in range(1, cpu_count() + 1)])
        cores.grid(row=0, column=1, sticky="w", padx=(8, 0))
        cores.bind("<<ComboboxSelected>>", self._save_cores)
        ttk.Label(speed, text="Auto checks what is free at the start of each run and "
                  "always leaves a core for you.", style="Muted.TLabel",
                  wraplength=self.WRAP).grid(row=1, column=0, columnspan=2, sticky="w",
                                             pady=(4, 0))

        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))
        self.run_button = ttk.Button(buttons, text=self.RUN_LABEL, style="Accent.TButton",
                                     command=self.start)
        self.run_button.pack(side="left")
        # width=-6: at least 6 characters wide (ttk's default minimum is 11)
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled",
                                      width=-6)
        self.stop_button.pack(side="left", padx=6)
        ttk.Button(buttons, text="Clear", command=self.clear, width=-6).pack(side="left")

        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(left, variable=self.progress_var, maximum=100).pack(
            fill="x", pady=(12, 4))
        self.progress_label = ttk.Label(left, text="Ready", style="Muted.TLabel",
                                        wraplength=self.WRAP)
        self.progress_label.pack(anchor="w")
        # Errors and notices show here, on the page (no pop-ups), just under
        # the progress line (packed only while there is a message).
        self.message_label = ttk.Label(left, textvariable=self.message_var,
                                       style="Error.TLabel", wraplength=self.WRAP)

        # Export (and Use Best) live under the settings, so the results get
        # the whole height of the page.
        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(14, 0))
        self.build_actions(actions)
        exports = ttk.Frame(actions)
        exports.pack(anchor="w")
        self.export_buttons = [
            ttk.Button(exports, text="Export CSV...", command=lambda: self.export("csv")),
            ttk.Button(exports, text="Export JSON...", command=lambda: self.export("json"))]
        self.export_buttons[0].pack(side="left")
        self.export_buttons[1].pack(side="left", padx=(6, 0))

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.grid(row=1, column=1, sticky="nsew")
        self.build_results(self.notebook)
        # Advanced: charts (scrolling when long), or the full report as text
        # to read or copy.
        self.advanced_tab = ttk.Frame(self.notebook, padding=8)
        bar = ttk.Frame(self.advanced_tab)
        bar.pack(fill="x", pady=(0, 6))
        self.advanced_as_text = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Show as text", variable=self.advanced_as_text,
                        command=self.layout_advanced).pack(side="left")
        self.copy_note = ttk.Label(bar, text="", style="Muted.TLabel")
        self.copy_note.pack(side="right", padx=(8, 0))
        ttk.Button(bar, text="Copy text", command=self.copy_advanced).pack(side="right")
        self.advanced_charts = ScrollFrame(self.advanced_tab)
        self.build_advanced(self.advanced_charts.body)
        self.advanced_text_frame = holder = ttk.Frame(self.advanced_tab)
        scroll = ttk.Scrollbar(holder)
        scroll.pack(side="right", fill="y")
        self.advanced_text = tk.Text(holder, wrap="word", font=font("mono", 10), padx=12,
                                     pady=10, yscrollcommand=scroll.set, height=10)
        self.advanced_text.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.advanced_text.yview)
        themes.style_text_widget(self.advanced_text, self.theme)
        self._text_widgets.append(self.advanced_text)
        self.notebook.add(self.advanced_tab, text="Advanced")
        self.set_advanced("Run something first: the full statistics appear here.")
        self.layout_advanced()

        left.update_idletasks()
        self.left_scroll.set_width(left.winfo_reqwidth())
        if self.standalone:
            self.root.protocol("WM_DELETE_WINDOW", self.close)
        themes.subscribe(self.frame, self.on_theme)

    # ----- subclass hooks ------------------------------------------------- #
    def build_inputs(self, form: ttk.Frame): ...
    def build_results(self, notebook: ttk.Notebook): ...
    def build_advanced(self, body: ttk.Frame): ...
    def show_advanced_charts(self): ...
    def reset_advanced_charts(self): ...
    def build_actions(self, frame: ttk.Frame): ...
    def make_work(self) -> Optional[Callable]: ...
    def show_results(self, result): ...
    def reset_results(self): ...
    def advanced_report(self) -> Optional[str]: ...
    def export_target(self): ...
    def export_name(self) -> str: ...

    # ----- theme, settings, messages -------------------------------------- #

    def on_theme(self, theme: Theme):
        self.theme = theme
        if self.standalone:
            themes.paint_window(self.root, theme)
        themes.repaint(self._text_widgets, [], theme)

    def on_show(self):
        """Called by the app each time this page is shown: pick up the CPU
        cores choice in case it was changed in Settings or on the other page."""
        if not (self.task and self.task.running):
            self.cores_var.set(_cores_label(app_settings.get("cpu_workers")))

    def _save_cores(self, _event=None):
        app_settings.update(cpu_workers=_cores_setting(self.cores_var.get()))

    def error(self, message: str):
        """Show a problem on the page, in red, under the progress line."""
        self.message_label.configure(style="Error.TLabel")
        self.message_var.set(message)
        self.message_label.pack(anchor="w", fill="x", pady=(8, 0), after=self.progress_label)
        self.left_scroll.update_layout()

    def notice(self, message: str):
        self.message_label.configure(style="Notice.TLabel")
        self.message_var.set(message)
        self.message_label.pack(anchor="w", fill="x", pady=(8, 0), after=self.progress_label)
        self.left_scroll.update_layout()

    def clear_message(self):
        self.message_var.set("")
        self.message_label.pack_forget()
        self.left_scroll.update_layout()

    def confirm_large(self, total: int, signature: tuple) -> bool:
        """Big runs need a second press of Run (instead of a pop-up question)."""
        if total <= LARGE_RUN_GAMES or self._pending_large == signature:
            self._pending_large = None
            return True
        self._pending_large = signature
        self.notice(f"This will play {total:,} games and may take a while. Press "
                    f"{self.RUN_LABEL} again to start; Stop works at any time.")
        return False

    def set_advanced(self, body: str):
        self.advanced_text.config(state="normal")
        self.advanced_text.delete("1.0", "end")
        self.advanced_text.insert("1.0", body)
        self.advanced_text.config(state="disabled")

    def layout_advanced(self):
        """Charts, or (Show as text) the full report as text."""
        if self.advanced_as_text.get():
            self.advanced_charts.pack_forget()
            self.advanced_text_frame.pack(fill="both", expand=True)
        else:
            self.advanced_text_frame.pack_forget()
            self.advanced_charts.pack(fill="both", expand=True)
            self.advanced_charts.update_layout()

    def copy_advanced(self):
        """Copy the full Advanced report as text (whichever view is showing)."""
        body = self.advanced_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(body)
        self.copy_note.configure(text="Copied")

    def arrange_charts(self, frame: ttk.Frame, charts: List[tk.Misc], wide: int = 720,
                       columns_wide: int = 2, columns_narrow: int = 1, gap: int = 10):
        """Charts (or tiles) columns_wide to a row when the frame is at least
        `wide` pixels wide, else columns_narrow."""
        state = {"columns": 0}

        def arrange(_event=None):
            width = frame.winfo_width()
            columns = columns_wide if width >= wide or width <= 1 else columns_narrow
            if columns == state["columns"]:
                return
            state["columns"] = columns
            for col in range(columns_wide):
                frame.columnconfigure(col, weight=0, uniform="")
            for i, chart in enumerate(charts):
                row, col = divmod(i, columns)
                chart.grid(row=row, column=col, sticky="ew",
                           padx=(0 if col == 0 else gap, 0), pady=(0, gap))
            for col in range(columns):
                frame.columnconfigure(col, weight=1, uniform="charts")
            self.advanced_charts.update_layout()
        frame.bind("<Configure>", arrange, add="+")
        arrange()

    def show_advanced_stats(self):
        """Open the Advanced tab (it fills in after every run)."""
        if self.advanced_report() is None:
            self.notice("Run something first: Advanced shows the full statistics.")
            return
        self.notebook.select(self.advanced_tab)

    # ----- running -------------------------------------------------------- #

    def start(self):
        if self.task and self.task.running:
            return
        work = self.make_work()
        if work is None:
            return
        self.clear()
        self.run_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.progress_label.config(text="Checking free CPU and memory...")
        self._started = time.perf_counter()
        setting = _cores_setting(self.cores_var.get())

        def job(progress, should_stop, work=work, setting=setting):
            # Runs on the worker thread: plain values only, no widgets.
            workers = resolve_workers(setting)
            started = time.perf_counter()
            result = work(progress, should_stop, workers)
            return RunOutcome(result, workers, time.perf_counter() - started)

        self.task = BackgroundTask(self.frame, job, self.on_progress,
                                   self.on_done, self.on_error)

    def stop(self):
        if self.task:
            self.task.stop()
            self.progress_label.config(text="Stopping...")

    def close(self):
        self.stop()
        self.root.destroy()

    def clear(self):
        self._pending_large = None          # a "press Run again" warning is forgotten too
        self.progress_var.set(0)
        self.progress_label.config(text="Ready")
        self.clear_message()
        self.reset_results()
        self.reset_advanced_charts()
        self.copy_note.configure(text="")
        self.set_advanced("Run something first: the full statistics appear here.")

    def on_progress(self, done: int, total: int):
        pct = 100.0 * done / total if total else 100.0
        elapsed = max(1e-6, time.perf_counter() - self._started)
        self.progress_var.set(pct)
        self.progress_label.config(
            text=f"{pct:.1f}% complete ({done:,} of {total:,} games, "
                 f"{done / elapsed:,.0f} games/s)")

    def _finish(self):
        self.run_button.state(["!disabled"])
        self.stop_button.state(["disabled"])

    def on_done(self, outcome: RunOutcome):
        self._finish()
        self.outcome = outcome
        result = outcome.result
        games = self.games_played(result)
        rate = games / outcome.seconds if outcome.seconds > 0 else 0
        summary = (f"{games:,} games in {outcome.seconds:.1f} s ({rate:,.0f} games/s, "
                   f"{_plural(outcome.workers, 'process')})")
        if getattr(result, "stopped", False):
            self.progress_label.config(text=f"Stopped. {summary}")
        else:
            self.progress_var.set(100)
            self.progress_label.config(text=f"100% complete. {summary}")
        self.show_results(result)
        report = self.advanced_report()
        if report:
            self.set_advanced(report)
            self.show_advanced_charts()
        self.advanced_charts.update_layout()

    def games_played(self, result) -> int:
        return getattr(result, "games", 0)

    def on_error(self, exc: BaseException):
        self._finish()
        self.progress_label.config(text="Failed")
        self.error(f"The run failed: {exc}")

    # ----- output --------------------------------------------------------- #

    def export(self, kind: str):
        target = self.export_target()
        if target is None:
            self.notice("Nothing to export yet: run something first.")
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title=f"Export {kind.upper()}", defaultextension=f".{kind}",
            initialfile=f"{self.export_name()}.{kind}",
            filetypes=[(kind.upper(), f"*.{kind}"), ("All files", "*.*")])
        if not path:
            return
        try:
            saved = exporter.export(target, path)
        except (OSError, ValueError) as exc:
            self.error(f"Export failed: {exc}")
            return
        self.clear_message()
        self.progress_label.config(text=f"Saved {Path(saved).name}")

    def make_tree(self, parent: tk.Misc, columns: Dict[str, Tuple[str, int, str]],
                  height: int, pady=0) -> ttk.Treeview:
        """A table with scrollbars (sideways only when the window is too narrow).
        columns: id -> (heading, width, anchor)."""
        holder, tree = scrolled_tree(parent, columns, height)
        holder.pack(fill="both", expand=True, pady=pady)
        return tree


def _margin_text(r: BatchResult) -> str:
    low, high = r.margin
    return f"{r.win_rate:.2f}% (95% range {low:.2f}% to {high:.2f}%)"


def describe_batch(result: BatchResult, seed: Optional[int]) -> str:
    lines = [
        f"Games played:        {result.games:,}" + ("  (stopped early)" if result.stopped else ""),
        f"Wins:                {result.wins:,} ({result.win_rate:.1f}% "
        f"± {result.margin_points:.1f})",
        f"Losses:              {result.losses:,} ({100 - result.win_rate if result.games else 0:.1f}%)",
        f"Avg plays per game:  {counter_mean(result.plays):.1f}",
        f"Avg inclusive used:  {counter_mean(result.inclusive_used):.1f} of {result.inclusive_calls}",
        f"Avg recoveries:      {counter_mean(result.recoveries):.2f}",
        f"Avg jokers drawn:    {counter_mean(result.jokers_drawn):.2f}",
        f"Seed:                {seed}",
    ]
    return "\n".join(lines)


def describe_batch_details(result: BatchResult, seed: Optional[int]) -> str:
    def distribution(counter, unit: str, of: int) -> str:
        if not counter:
            return "  (none)"
        return "\n".join(f"  {k:>2} {unit}: {v:,} ({100 * v / of:.1f}%)"
                         for k, v in sorted(counter.items()))

    usage = (100 * counter_mean(result.inclusive_used) / result.inclusive_calls
             if result.inclusive_calls else 0.0)
    return "\n".join([
        "=== Settings ===",
        f"Jokers: {result.jokers}   Inclusive calls: {result.inclusive_calls}   "
        f"Threshold: {result.threshold:g}   Seed: {seed}",
        "",
        "=== Overall ===",
        f"Games: {result.games:,}   Win rate: {_margin_text(result)}",
        "The 95% range is where the true win rate almost certainly lies;",
        "more games make it narrower.",
        "",
        "=== Plays ===",
        f"Average: {counter_mean(result.plays):.1f}   Max: {counter_max(result.plays)}   "
        f"Min: {counter_min(result.plays)}",
        "",
        "=== Inclusive calls ===",
        f"Average used: {counter_mean(result.inclusive_used):.2f}   "
        f"Max used: {counter_max(result.inclusive_used)}   Usage rate: {usage:.1f}%",
        f"Average recoveries: {counter_mean(result.recoveries):.2f}",
        "",
        "=== Jokers ===",
        f"Average drawn: {counter_mean(result.jokers_drawn):.2f}   "
        f"Max drawn: {counter_max(result.jokers_drawn)}",
        "",
        "=== Wins: boxes left ===",
        f"Average: {counter_mean(result.boxes_left_in_wins):.2f}",
        distribution(result.boxes_left_in_wins, "boxes", result.wins),
        "",
        "=== Losses: cards left in the pile ===",
        f"Average: {counter_mean(result.cards_left_in_losses):.2f}",
        distribution(result.cards_left_in_losses, "cards", result.losses),
        "",
        "=== Plays per game ===",
        distribution(result.plays, "plays", result.games),
        "",
        "=== Inclusive calls used per game ===",
        distribution(result.inclusive_used, "calls", result.games),
        "",
        "=== Recoveries per game ===",
        distribution(result.recoveries, "recoveries", result.games),
        "",
        "=== Jokers drawn per game ===",
        distribution(result.jokers_drawn, "jokers", result.games),
    ])


def _config_text(r: BatchResult) -> str:
    return (f"jokers {r.jokers}  inclusive {r.inclusive_calls:>2}  "
            f"threshold {r.threshold:g}")


def describe_sweep(sweep: SweepResult, seed: Optional[int]) -> str:
    if not sweep.results:
        return "No configuration finished. Nothing to report."
    lines = []
    if sweep.stopped:
        lines.append(f"Stopped early: {len(sweep.results)} of {sweep.planned} "
                     "configurations finished.\n")
    lines.append(f"Seed: {seed} (every configuration plays the same deals)\n")
    if sweep.ranked()[0].win_rate == 0:
        lines.append("Every configuration won 0% of its games. "
                     "Try more games per test or more inclusive calls.\n")
    tied = sweep.tied()
    lines.append("=== Top 10 configurations (* = tied with the best) ===")
    for r in sweep.ranked()[:10]:
        mark = "*" if r.key in tied else " "
        lines.append(f"{mark} {r.win_rate:6.2f}% ±{r.margin_points:4.2f}  {_config_text(r)}")
    if sweep.confirmed:
        tied_c = sweep.tied_confirmed()
        lines.append(f"\n=== Confirmed on fresh deals "
                     f"({sweep.ranked_confirmed()[0].games:,} games each) ===")
        for r in sweep.ranked_confirmed():
            mark = "*" if r.key in tied_c else " "
            lines.append(f"{mark} {r.win_rate:6.2f}% ±{r.margin_points:4.2f}  {_config_text(r)}")
    for param, title in (("jokers", "Jokers"), ("moves", "Inclusive calls"),
                         ("threshold", "Threshold")):
        lines.append(f"\n=== Top 5 for each {title.lower()} value ===")
        for value, results in sweep.top_by(param, 5).items():
            lines.append(f"{title}: {value:g}" if isinstance(value, float)
                         else f"{title}: {value}")
            for r in results:
                lines.append(f"   {r.win_rate:6.2f}%  {_config_text(r)}")
    return "\n".join(lines)


def describe_sweep_details(sweep: SweepResult, seed: Optional[int]) -> str:
    best = sweep.best
    lines = ["=== Best overall ===",
             f"Jokers: {best.jokers}   Inclusive calls: {best.inclusive_calls}   "
             f"Threshold: {best.threshold:g}   Win rate: {_margin_text(best)}",
             f"Games: {best.games:,}   First seed: {best.seed}"
             + ("   (confirmed on fresh deals)" if sweep.confirmed else ""),
             f"Sweep seed: {seed}"]
    tied = sweep.tied()
    lines.append(f"\n{len(tied)} configuration(s) are statistically tied with the top "
                 "of the sweep: their 95% ranges overlap, so the data can't tell them "
                 "apart. More games per test (or Confirm top 10) narrows this down.")
    for param, title in (("jokers", "joker count"), ("moves", "inclusive calls"),
                         ("threshold", "threshold")):
        lines.append(f"\n=== Best for each {title} ===")
        for value, r in sweep.best_by(param).items():
            lines.append(f"{value!s:>6}: {r.win_rate:6.2f}%  ({_config_text(r)})")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Simulator
# --------------------------------------------------------------------------- #

class SimulatorGUI(_RunnerWindow):
    """📊 Simulator: play many games with the threshold strategy."""

    TITLE = "Beat the Box: Simulator"
    HEADING = "Simulator"
    SUBTITLE = "Let the built-in strategy play thousands of games with one setting."
    TOOL = "simulator"
    RUN_LABEL = "Run Simulations"

    def build_inputs(self, form):
        self.result: Optional[BatchResult] = None
        self.seed: Optional[int] = None
        self.sims_var = tk.StringVar(value="10000")
        self.jokers_var = tk.StringVar(value="0")
        self.calls_var = tk.StringVar(value="5")
        self.threshold_var = tk.StringVar(value=f"{DEFAULT_THRESHOLD:g}")
        self.seed_var = tk.StringVar(value="")
        self.calls_combo = ttk.Combobox(form, textvariable=self.calls_var, width=10)
        rows = [("Number of games:", ttk.Entry(form, textvariable=self.sims_var, width=12)),
                ("Jokers:", ttk.Combobox(form, textvariable=self.jokers_var, width=10,
                                         state="readonly", values=list(range(MAX_JOKERS + 1)))),
                ("Inclusive calls:", self.calls_combo),
                ("Threshold (% points):",
                 ttk.Entry(form, textvariable=self.threshold_var, width=12)),
                ("Seed (blank = random):", ttk.Entry(form, textvariable=self.seed_var, width=12))]
        for r, (label, widget) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=3)
            widget.grid(row=r, column=1, sticky="w", pady=3, padx=(8, 0))
        ttk.Label(form, text="Threshold: only spend an inclusive call when it adds at least "
                  "this many points of win chance.", style="Muted.TLabel",
                  wraplength=self.WRAP).grid(row=len(rows), column=0, columnspan=2,
                                             sticky="w", pady=(6, 0))
        self.jokers_var.trace_add("write", self._update_calls)
        self._update_calls()

    def _update_calls(self, *_):
        self.calls_combo["values"] = list(range(max_inclusive_calls(int(self.jokers_var.get())) + 1))

    def build_results(self, notebook):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text="Overview")
        self.win_var = tk.StringVar(value="-")
        self.games_var = tk.StringVar(value="-")
        self.boxes_var = tk.StringVar(value="-")
        self.plays_var = tk.StringVar(value="-")
        self.tiles_frame = tiles = ttk.Frame(frame)
        tiles.pack(fill="x")
        self.tiles = [StatTile(tiles, caption, var) for caption, var in (
            ("Win rate (± 95% range)", self.win_var), ("Games played", self.games_var),
            ("Avg boxes left in wins", self.boxes_var), ("Avg plays per game", self.plays_var))]
        self._tile_columns = 0
        tiles.bind("<Configure>", self._arrange_tiles)
        self._arrange_tiles()
        self.chart = BarChart(frame, self.theme, width=520, height=170,
                              title="Boxes left in winning games (% of wins)")
        self.chart.pack(fill="both", expand=True, pady=(10, 0))
        self.details_tree = self.make_tree(
            frame, {"stat": ("Statistic", 210, "w"), "value": ("Value", 220, "w")},
            height=8, pady=(10, 0))

    def _arrange_tiles(self, _event=None):
        """Four tiles in a row when there is room, otherwise two by two."""
        width = self.tiles_frame.winfo_width()
        columns = 2 if 1 < width < 600 else 4
        if columns == self._tile_columns:
            return
        self._tile_columns = columns
        for col in range(4):
            self.tiles_frame.columnconfigure(col, weight=0, uniform="")
        for i, tile in enumerate(self.tiles):
            row, col = divmod(i, columns)
            tile.grid(row=row, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0),
                      pady=(0 if row == 0 else 6, 0))
        for col in range(columns):
            self.tiles_frame.columnconfigure(col, weight=1, uniform="tiles")

    def reset_results(self):
        self.result = None
        for var in (self.win_var, self.games_var, self.boxes_var, self.plays_var):
            var.set("-")
        self.chart.draw([])
        self.details_tree.delete(*self.details_tree.get_children())

    def on_theme(self, theme):
        super().on_theme(theme)
        self.chart.set_theme(theme)
        for chart in self.adv_charts:
            chart.set_theme(theme)

    # (counter, chart title, what the % is of, first value or None, last value or None)
    ADVANCED_CHARTS = (
        ("boxes_left_in_wins", "Boxes left in winning games", "wins", 1, BOX_SIZE),
        ("cards_left_in_losses", "Cards left in the pile in lost games", "losses", 0, None),
        ("plays", "Plays per game", "games", None, None),
        ("inclusive_used", "Inclusive calls used per game", "games", 0, "calls"),
        ("recoveries", "Recoveries per game", "games", 0, None),
        ("jokers_drawn", "Jokers drawn per game", "games", 0, "jokers"),
    )

    def build_advanced(self, body):
        self.adv_vars = [tk.StringVar(value="-") for _ in range(4)]
        tiles = ttk.Frame(body)
        tiles.pack(fill="x", pady=(0, 4))
        self.arrange_charts(tiles, [StatTile(tiles, caption, var) for caption, var in zip(
            ("Win rate (± 95% range)", "Games played", "Wins / losses", "Seed"),
            self.adv_vars)], wide=600, columns_wide=4, columns_narrow=2, gap=6)
        grid = ttk.Frame(body)
        grid.pack(fill="x")
        self.adv_charts = []
        for _attr, title, _of, _low, _high in self.ADVANCED_CHARTS:
            chart = BarChart(grid, self.theme, width=360, height=210, title=title)
            self.adv_charts.append(chart)
        self.arrange_charts(grid, [chart.canvas for chart in self.adv_charts])

    def reset_advanced_charts(self):
        for var in self.adv_vars:
            var.set("-")
        for chart, (_attr, title, *_rest) in zip(self.adv_charts, self.ADVANCED_CHARTS):
            chart.draw([], title=title)

    def show_advanced_charts(self):
        r = self.result
        if r is None:
            return
        self.adv_vars[0].set(f"{r.win_rate:.1f}% ±{r.margin_points:.1f}")
        self.adv_vars[1].set(f"{r.games:,}")
        self.adv_vars[2].set(f"{r.wins:,} / {r.losses:,}")
        self.adv_vars[3].set(str(self.seed))
        limits = {"calls": r.inclusive_calls, "jokers": r.jokers}
        for chart, (attr, title, of, low, high) in zip(self.adv_charts, self.ADVANCED_CHARTS):
            counter = getattr(r, attr)
            high = limits.get(high, high)
            if high is not None:
                high = max(high, counter_max(counter))
            items = distribution(counter, low, high)
            chart.empty_message = f"No {of} in this run"
            if not items:
                chart.draw([], title=title)
                continue
            mean = counter_mean(counter)
            chart.draw([(str(value), share) for value, share in items],
                       value_format=lambda v: f"{v:.0f}%" if v >= 1 else f"{v:.1f}%",
                       average=(mean - items[0][0], f"avg {mean:.2f}"),
                       title=f"{title} (% of {of})")

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
        if not self.confirm_large(games, (games, jokers, calls, threshold)):
            return None
        self.seed = seed
        return lambda progress, stop, workers: run_batch(
            games, jokers, calls, threshold, seed, progress, stop, workers)

    def show_results(self, result: BatchResult):
        self.result = result
        self.win_var.set(f"{result.win_rate:.1f}% ±{result.margin_points:.1f}")
        self.games_var.set(f"{result.games:,}")
        self.boxes_var.set(f"{counter_mean(result.boxes_left_in_wins):.2f}")
        self.plays_var.set(f"{counter_mean(result.plays):.1f}")
        wins = result.wins or 1
        self.chart.draw([(str(n), 100 * result.boxes_left_in_wins.get(n, 0) / wins)
                         for n in range(1, BOX_SIZE + 1)])
        low, high = result.margin
        rows = [
            ("Wins", f"{result.wins:,} ({result.win_rate:.2f}%)"),
            ("Losses", f"{result.losses:,}"),
            ("95% range for the win rate", f"{low:.2f}% to {high:.2f}%"),
            ("Inclusive calls used (avg)",
             f"{counter_mean(result.inclusive_used):.2f} of {result.inclusive_calls}"),
            ("Recoveries per game (avg)", f"{counter_mean(result.recoveries):.2f}"),
            ("Jokers drawn per game (avg)", f"{counter_mean(result.jokers_drawn):.2f}"),
            ("Cards left in losses (avg)", f"{counter_mean(result.cards_left_in_losses):.1f}"),
            ("Plays per game (min / max)",
             f"{counter_min(result.plays)} / {counter_max(result.plays)}"),
            ("Settings", f"jokers {result.jokers}, inclusive {result.inclusive_calls}, "
                         f"threshold {result.threshold:g}"),
            ("Seed", str(self.seed)),
        ]
        if result.stopped:
            rows.insert(0, ("Note", "Stopped early: these are partial results"))
        self.details_tree.delete(*self.details_tree.get_children())
        for stat, value in rows:
            self.details_tree.insert("", "end", values=(stat, value))

    def advanced_report(self) -> Optional[str]:
        if not self.result or not self.result.games:
            return None
        return (describe_batch(self.result, self.seed) + "\n\n"
                + describe_batch_details(self.result, self.seed))

    def export_target(self):
        return self.result if self.result and self.result.games else None

    def export_name(self) -> str:
        r = self.result
        return (f"btb-simulator-j{r.jokers}-c{r.inclusive_calls}-t{r.threshold:g}-"
                f"seed{self.seed}")


# --------------------------------------------------------------------------- #
# Strategy Optimizer
# --------------------------------------------------------------------------- #

class OptimizerGUI(_RunnerWindow):
    """🔬 Strategy Optimizer: sweep jokers, inclusive calls and thresholds."""

    TITLE = "Beat the Box: Strategy Optimizer"
    HEADING = "Strategy Optimizer"
    SUBTITLE = "Try every combination of settings on the same deals and rank them."
    TOOL = "optimizer"
    RUN_LABEL = "Run Optimization"

    TABLE_COLUMNS = {
        "rank": ("#", 28, "center"), "win": ("Win %", 60, "e"), "margin": ("±", 40, "e"),
        "jokers": ("Jokers", 58, "center"), "calls": ("Calls", 48, "center"),
        "threshold": ("Threshold", 88, "center"), "boxes": ("Boxes left", 90, "e"),
        "games": ("Games", 62, "e"), "note": ("", 126, "w"),
    }

    def build_inputs(self, form):
        self.sweep: Optional[SweepResult] = None
        self.seed: Optional[int] = None
        self.vars = {name: tk.StringVar(value=value) for name, value in (
            ("games", "1000"), ("jokers_min", "0"), ("jokers_max", "2"),
            ("moves_min", "0"), ("moves_max", "10"), ("threshold_min", "0"),
            ("threshold_max", "30"), ("step", "5"), ("seed", ""))}
        self.confirm_var = tk.BooleanVar(value=True)

        def pair(row, label, lo, hi):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
            box = ttk.Frame(form)
            box.grid(row=row, column=1, sticky="w", padx=(8, 0))
            ttk.Entry(box, textvariable=self.vars[lo], width=6).pack(side="left")
            ttk.Label(box, text=" to ").pack(side="left")
            ttk.Entry(box, textvariable=self.vars[hi], width=6).pack(side="left")

        ttk.Label(form, text="Games per test:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.vars["games"], width=10).grid(
            row=0, column=1, sticky="w", padx=(8, 0))
        pair(1, "Jokers (0-2):", "jokers_min", "jokers_max")
        pair(2, "Inclusive calls:", "moves_min", "moves_max")
        pair(3, "Threshold (% points):", "threshold_min", "threshold_max")
        ttk.Label(form, text="Threshold step:").grid(row=4, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.vars["step"], width=10).grid(
            row=4, column=1, sticky="w", padx=(8, 0))
        ttk.Label(form, text="Seed (blank = random):").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.vars["seed"], width=10).grid(
            row=5, column=1, sticky="w", padx=(8, 0))
        ttk.Checkbutton(form, text="Confirm top 10", variable=self.confirm_var).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(form, text="Re-runs the ten best with 5x more games on fresh deals.",
                  style="Muted.TLabel", wraplength=self.WRAP).grid(
            row=7, column=0, columnspan=2, sticky="w")

    def build_results(self, notebook):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text="Results")
        self.best_var = tk.StringVar(value="-")
        self.best_settings_var = tk.StringVar(value="-")
        self.configs_var = tk.StringVar(value="-")
        self.total_var = tk.StringVar(value="-")
        tiles = ttk.Frame(frame)
        tiles.pack(fill="x")
        for i, (caption, var) in enumerate((("Best win rate (± 95%)", self.best_var),
                                            ("Best settings", self.best_settings_var),
                                            ("Configurations tested", self.configs_var),
                                            ("Games played", self.total_var))):
            row, col = divmod(i, 2)
            StatTile(tiles, caption, var).grid(row=row, column=col, sticky="ew",
                                               padx=(0 if col == 0 else 6, 0),
                                               pady=(0 if row == 0 else 6, 0))
            tiles.columnconfigure(col, weight=1, uniform="tiles")

        view = ttk.Frame(frame)
        view.pack(fill="x", pady=(10, 0))
        self.table_view = tk.StringVar(value="sweep")
        self.view_buttons = []
        for value, label in (("sweep", "All configurations"), ("confirm", "Confirmed top 10")):
            btn = ttk.Radiobutton(view, text=label, value=value, variable=self.table_view,
                                  command=self.fill_table)
            self.view_buttons.append(btn)
        flow_row(view, self.view_buttons, gap=12)
        note = ttk.Label(frame, text="Highlighted rows are statistically tied with the best. "
                         "Click a heading to sort.", style="Muted.TLabel")
        note.pack(anchor="w", fill="x", pady=(2, 4))
        wrap_to(note)
        self.table = self.make_tree(frame, self.TABLE_COLUMNS, height=14)
        self._sort = ("rank", False)
        for col in self.TABLE_COLUMNS:
            self.table.heading(col, command=lambda c=col: self.sort_table(c))
        self._tag_colors()

    def build_actions(self, frame):
        self.use_best_button = ttk.Button(frame, text="Use Best in Simulator",
                                          command=self.use_best)
        self.use_best_button.pack(anchor="w", pady=(0, 6))

    def _tag_colors(self):
        self.table.tag_configure("tied", background=self.theme.recover,
                                 foreground=readable_on(self.theme.recover))

    def on_theme(self, theme):
        super().on_theme(theme)
        self._tag_colors()
        for chart in self.adv_charts:
            chart.set_theme(theme)

    BEST_COLUMNS = {
        "setting": ("Setting", 110, "w"), "value": ("Value", 60, "center"),
        "win": ("Best win %", 84, "e"), "margin": ("±", 46, "e"),
        "jokers": ("Jokers", 58, "center"), "calls": ("Calls", 50, "center"),
        "threshold": ("Threshold", 80, "center"),
    }

    def build_advanced(self, body):
        tiles = ttk.Frame(body)
        tiles.pack(fill="x", pady=(0, 10))
        for i, (caption, var) in enumerate((("Best win rate (± 95%)", self.best_var),
                                            ("Best settings", self.best_settings_var),
                                            ("Configurations tested", self.configs_var),
                                            ("Games played", self.total_var))):
            row, col = divmod(i, 2)
            StatTile(tiles, caption, var).grid(row=row, column=col, sticky="ew",
                                               padx=(0 if col == 0 else 6, 0),
                                               pady=(0 if row == 0 else 6, 0))
            tiles.columnconfigure(col, weight=1, uniform="tiles")
        grid = ttk.Frame(body)
        grid.pack(fill="x")
        self.threshold_chart = LineChart(grid, self.theme, width=360, height=240,
                                         title="Win rate by threshold")
        self.calls_chart = LineChart(grid, self.theme, width=360, height=240,
                                     title="Win rate by inclusive calls")
        self.jokers_chart = BarChart(grid, self.theme, width=360, height=240,
                                     title="Best win rate by joker count")
        self.adv_charts = [self.threshold_chart, self.calls_chart, self.jokers_chart]
        for chart in self.adv_charts:
            chart.empty_message = "Run an optimization to see this"
        self.jokers_chart.axis_format = lambda v: f"{v:g}%"
        note = ttk.Label(body, text="Each point is the best configuration for that value "
                         "(over the settings not on the chart), with its 95% range. Lines "
                         "that overlap can't be told apart.", style="Muted.TLabel")
        note.pack(anchor="w", fill="x", pady=(0, 8))
        wrap_to(note)
        self.arrange_charts(grid, [chart.canvas for chart in self.adv_charts])
        ttk.Label(body, text="Best configuration for each value",
                  style="Heading.TLabel").pack(anchor="w", pady=(6, 4))
        holder, self.best_table = scrolled_tree(body, self.BEST_COLUMNS, height=4)
        holder.pack(fill="x")

    def reset_advanced_charts(self):
        self.threshold_chart.draw_series([], {})
        self.calls_chart.draw_series([], {})
        self.jokers_chart.draw([])
        self.best_table.delete(*self.best_table.get_children())
        self.best_table.configure(height=4)

    def show_advanced_charts(self):
        sweep = self.sweep
        if not sweep or not sweep.results:
            return
        results = sweep.ranked()

        def jokers_name(j):
            return f"{j} joker" + ("" if j == 1 else "s")

        for chart, x, fmt in ((self.threshold_chart, "threshold", lambda v: f"{v:g}"),
                              (self.calls_chart, "moves", str)):
            curves = best_curves(results, x)
            xs = sorted({getattr(r, "threshold" if x == "threshold" else "inclusive_calls")
                         for r in results})
            series = {}
            for jokers, line in curves.items():
                at = {(r.threshold if x == "threshold" else r.inclusive_calls): r for r in line}
                series[jokers_name(jokers)] = [
                    (at[v].win_rate, *at[v].margin) if v in at else None for v in xs]
            subtitle = "best over inclusive calls" if x == "threshold" else "best over thresholds"
            title = ("Win rate by threshold" if x == "threshold"
                     else "Win rate by inclusive calls")
            chart.axis_format = lambda v: f"{v:g}%"
            chart.draw_series([fmt(v) for v in xs], series, title=f"{title} ({subtitle})")
        best_jokers = sweep.best_by("jokers")
        self.jokers_chart.draw(
            [(jokers_name(j), r.win_rate) for j, r in best_jokers.items()],
            value_format=lambda v: f"{v:.1f}%",
            errors=[r.margin for r in best_jokers.values()],
            title="Best win rate by joker count")
        table = self.best_table
        table.delete(*table.get_children())
        for param, name in (("jokers", "Jokers"), ("moves", "Inclusive calls"),
                            ("threshold", "Threshold")):
            for value, r in sweep.best_by(param).items():
                table.insert("", "end", values=(
                    name, f"{value:g}" if isinstance(value, float) else value,
                    f"{r.win_rate:.2f}", f"{r.margin_points:.2f}", r.jokers,
                    r.inclusive_calls, f"{r.threshold:g}"))
        table.configure(height=min(30, max(4, len(table.get_children()))))

    def reset_results(self):
        self.sweep = None
        for var in (self.best_var, self.best_settings_var, self.configs_var, self.total_var):
            var.set("-")
        self.table.delete(*self.table.get_children())

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
        thresholds = float_range(tmin, tmax, step)
        configs = len(range(jmin, jmax + 1)) * (mmax - mmin + 1) * len(thresholds)
        if configs > MAX_CONFIGS * 4:  # rough check before building a huge list
            self.error(f"That sweep has over {MAX_CONFIGS:,} configurations. "
                       "Narrow the ranges or use a bigger threshold step.")
            return None
        grid = sweep_grid((jmin, jmax), (mmin, mmax), thresholds)
        if not grid:
            self.error("Those ranges contain no legal configurations.")
            return None
        if len(grid) > MAX_CONFIGS:
            self.error(f"That sweep has {len(grid):,} configurations; the limit is "
                       f"{MAX_CONFIGS:,}. Narrow the ranges or use a bigger threshold step.")
            return None
        return games, grid, seed

    def make_work(self):
        checked = self.validate()
        if checked is None:
            return None
        games, grid, seed = checked
        confirm = bool(self.confirm_var.get())
        total = sweep_games(games, len(grid), confirm)
        if not self.confirm_large(total, (games, tuple(grid), confirm)):
            return None
        self.seed = seed
        return lambda progress, stop, workers: run_sweep(
            games, grid, seed, progress, stop, workers, confirm)

    def games_played(self, sweep: SweepResult) -> int:
        return (sum(r.games for r in sweep.results.values())
                + sum(r.games for r in sweep.confirmed.values()))

    def show_results(self, sweep: SweepResult):
        self.sweep = sweep
        best = sweep.best
        if best is None:
            self.best_var.set("-")
            self.configs_var.set("0 finished")
            return
        self.best_var.set(f"{best.win_rate:.1f}% ±{best.margin_points:.1f}")
        self.best_settings_var.set(f"{best.jokers} jk · {best.inclusive_calls} calls · "
                                   f"{best.threshold:g} pts")
        tied = len(sweep.tied())
        self.configs_var.set(f"{len(sweep.results):,} ({tied} tied)")
        self.total_var.set(f"{self.games_played(sweep):,}")
        self.view_buttons[1].state(["!disabled"] if sweep.confirmed else ["disabled"])
        self.table_view.set("confirm" if sweep.confirmed else "sweep")
        self._sort = ("rank", False)
        self.fill_table()

    def _rows(self) -> List[tuple]:
        sweep = self.sweep
        if sweep is None:
            return []
        confirmed = self.table_view.get() == "confirm" and sweep.confirmed
        ranked = sweep.ranked_confirmed() if confirmed else sweep.ranked()
        tied = sweep.tied_confirmed() if confirmed else sweep.tied()
        rows = []
        for rank, r in enumerate(ranked, start=1):
            note = "tied for best" if r.key in tied else ""
            if rank == 1:
                note = "best" + (" (confirmed)" if confirmed else "")
            rows.append((rank, round(r.win_rate, 2), round(r.margin_points, 2), r.jokers,
                         r.inclusive_calls, r.threshold,
                         round(counter_mean(r.boxes_left_in_wins), 2), r.games, note,
                         r.key in tied))
        return rows

    def fill_table(self):
        self.table.delete(*self.table.get_children())
        rows = self._rows()
        col, reverse = self._sort
        index = list(self.TABLE_COLUMNS).index(col)
        rows.sort(key=lambda row: (row[index] if not isinstance(row[index], str)
                                   else row[index].lower()), reverse=reverse)
        for row in rows:
            values = list(row[:-1])
            values[1] = f"{values[1]:.2f}"
            values[2] = f"{values[2]:.2f}"
            values[5] = f"{values[5]:g}"
            values[6] = f"{values[6]:.2f}"
            values[7] = f"{values[7]:,}"
            self.table.insert("", "end", values=values, tags=("tied",) if row[-1] else ())

    def sort_table(self, column: str):
        current, reverse = self._sort
        self._sort = (column, not reverse if column == current else column in (
            "win", "boxes", "games"))
        self.fill_table()

    def use_best(self) -> Optional["SimulatorGUI"]:
        """Fill the Simulator page with the winning settings (and show it)."""
        if not self.sweep or self.sweep.best is None:
            self.notice("Run an optimization first.")
            return None
        best = self.sweep.best
        running = self.app.page("simulator") if self.app is not None else None
        if running is not None and running.task and running.task.running:
            self.notice("The Simulator is still running. Stop it or let it finish, "
                        "then press Use Best again.")
            return None
        if self.app is not None:
            sim = self.app.show_page("simulator")
        else:  # on its own (tests): a Simulator in a new window
            sim = SimulatorGUI(tk.Toplevel(self.root))
        sim.jokers_var.set(str(best.jokers))
        sim.calls_var.set(str(best.inclusive_calls))
        sim.threshold_var.set(f"{best.threshold:g}")
        sim.seed_var.set(str(self.sweep.seed))
        sim.sims_var.set("10000")
        sim.notice("Settings copied from the Optimizer's best. Press Run Simulations.")
        return sim

    def advanced_report(self) -> Optional[str]:
        if not self.sweep or not self.sweep.results:
            return None
        return (describe_sweep_details(self.sweep, self.seed) + "\n\n"
                + describe_sweep(self.sweep, self.seed))

    def export_target(self):
        return self.sweep if self.sweep and self.sweep.results else None

    def export_name(self) -> str:
        return f"btb-optimizer-seed{self.seed}"