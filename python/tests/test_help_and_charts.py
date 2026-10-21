"""
==============================================
HELP PAGES, CHARTS AND TEST SET-UP TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_help_and_charts.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.0 CHANGES (2026-10-20):
- New. The help-page markup (btb/markup.py) and how DocView draws it
  (headings, lists, tables, key and card chips, copying, every theme);
  the chart data (sim.distribution, sim.best_curves) and the charts in
  the Advanced tabs; the colour palettes for help pages and charts; the
  mouse wheel over a table with nothing to scroll; and the test set-up
  itself (one shared Tk root, left clean after every test).

DESCRIPTION:
-----------
The markup and chart-data tests run anywhere. The drawing tests need Tk
and a display and skip without one (on headless Linux, run under
xvfb-run).

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for the drawing tests

KEY FUNCTIONS:
-------------
- doc(tk_root, source) -> a DocView in its own window, drawn

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_help_and_charts.py
"""

import gc
from collections import Counter

import pytest

from btb import markup, text
from btb.sim import best_curves, distribution, run_batch, run_sweep, sweep_grid
from conftest import pump


# ------------------------------------------------------------- the markup -- #

SAMPLE = """# Title

A paragraph that runs
over two lines, with **bold**, a `key` and the A♥.

## Section

- a bullet
  that continues
  - a nested bullet
1. first
2. second

| Key | What |
|---|---|
| `W` | Higher |
| `S` | Lower |

> A note
> on two lines.

---

### Small"""


def test_markup_reads_every_kind_of_block():
    blocks = markup.parse(SAMPLE)
    assert [b.kind for b in blocks] == ["heading", "para", "heading", "item", "item", "item",
                                        "item", "table", "note", "rule", "heading"]
    assert [b.level for b in blocks if b.kind == "heading"] == [1, 2, 3]
    para = blocks[1]
    assert ("bold", "bold") in para.spans and ("key", "code") in para.spans
    assert ("A♥", "card") in para.spans
    assert "".join(t for t, _s in para.spans).startswith("A paragraph that runs over two")
    items = [b for b in blocks if b.kind == "item"]
    assert [(b.level, b.marker) for b in items] == [(0, "•"), (1, "•"), (0, "1."), (0, "2.")]
    assert "".join(t for t, _s in items[0].spans) == "a bullet that continues"
    table = blocks[7]
    assert len(table.header) == 1 and len(table.rows) == 2
    assert blocks[8].spans == [("A note on two lines.", "")]


def test_card_names_are_found_but_not_inside_plain_numbers():
    pieces = markup.spans("Play 10♠, then ♦ but not 10 or 7.")
    assert ("10♠", "card") in pieces and ("♦", "card") in pieces
    assert "".join(t for t, _s in pieces) == "Play 10♠, then ♦ but not 10 or 7."
    assert [t for t, s in pieces if s == "card"] == ["10♠", "♦"]


def test_markup_helpers_give_plain_text_rows_and_headings():
    assert "**" not in markup.plain_text(SAMPLE) and "`" not in markup.plain_text(SAMPLE)
    assert markup.table_rows(SAMPLE) == [["Key", "What"], ["W", "Higher"], ["S", "Lower"]]
    assert markup.headings(SAMPLE, 2) == ["Section"]


ALL_HELP = {"rules": text.RULES_SUMMARY, "strategy": text.STRATEGY_GUIDE,
            "guide": text.tool_guide(), "shortcuts": text.shortcut_help(),
            **{f"about-{k}": v for k, v in text.TOOL_HELP.items()}}


@pytest.mark.parametrize("name", sorted(ALL_HELP))
def test_every_help_text_is_clean_markup(name):
    source = ALL_HELP[name]
    plain = markup.plain_text(source)
    assert "**" not in plain and "`" not in plain, name        # nothing left unread
    for block in markup.parse(source):
        if block.kind == "table":                               # every row the same width
            widths = {len(row) for row in block.header + block.rows}
            assert len(widths) == 1 and block.header, name
    assert markup.parse(source)[0].kind == "heading", name     # each page has a title


def test_the_shortcuts_page_has_one_row_per_shortcut():
    rows = markup.table_rows(text.shortcut_help())
    assert rows[0] == ["Keys", "What it does"]
    assert [row[0] for row in rows[1:]] == [keys for keys, *_ in text.SHORTCUTS]


# -------------------------------------------------------------- chart data -- #

def test_distribution_fills_gaps_and_adds_up_to_100():
    tally = Counter({2: 3, 5: 1})
    shares = distribution(tally)
    assert [value for value, _share in shares] == [2, 3, 4, 5]
    assert shares[1][1] == 0.0 and sum(share for _v, share in shares) == pytest.approx(100)
    assert [value for value, _ in distribution(tally, 1, 9)] == list(range(1, 10))
    assert distribution(Counter()) == []


def test_best_curves_keep_the_best_result_at_each_value():
    sweep = run_sweep(30, sweep_grid((0, 1), (0, 3), [0.0, 10.0]), seed=1)
    results = list(sweep.results.values())
    curves = best_curves(results, "threshold")
    assert sorted(curves) == [0, 1]
    for jokers, line in curves.items():
        assert [r.threshold for r in line] == [0.0, 10.0]
        for r in line:
            rivals = [o for o in results if o.jokers == jokers and o.threshold == r.threshold]
            assert r.win_rate == max(o.win_rate for o in rivals)
    by_calls = best_curves(results, "moves")
    assert [r.inclusive_calls for r in by_calls[0]] == [0, 1, 2, 3]


# ---------------------------------------------------------------- palettes -- #

def test_help_pages_and_charts_are_readable_in_every_theme():
    pytest.importorskip("tkinter")
    from btb import theme as themes
    for t in themes.THEMES:
        p = themes.doc_palette(t)
        for fg, bg, minimum in (("text", "bg", 4.5), ("heading", "bg", 4.5),
                                ("marker", "bg", 3.0), ("code_text", "code_bg", 4.5),
                                ("red", "card_bg", 4.5), ("black", "card_bg", 4.5),
                                ("text", "head_bg", 4.5), ("text", "stripe_bg", 4.5),
                                ("select_text", "select_bg", 4.5)):
            ratio = themes.contrast(p[fg], p[bg])
            assert ratio >= minimum, f"{t.name}: {fg} on {bg} is {ratio:.2f}"
        colors = themes.chart_palette(t)
        assert len(colors) >= 3, t.name          # three joker counts, three colours
        for i, color in enumerate(colors):
            assert themes.contrast(color, t.panel) >= 3.0, t.name
            for other in colors[:i]:
                assert themes.color_distance(color, other) >= 150, t.name


# ----------------------------------------------------------------- DocView -- #

def doc(tk_root, source):
    import tkinter as tk
    from btb.widgets import DocView
    window = tk.Toplevel(tk_root)
    window.geometry("700x500")
    view = DocView(window, source)
    view.pack(fill="both", expand=True)
    pump(tk_root)
    return view


def test_a_help_page_is_drawn_as_a_document(tk_root):
    from btb.theme import font
    view = doc(tk_root, SAMPLE)
    t = view.text
    assert t.tag_cget("h1", "font") != t.tag_cget("h2", "font")
    assert str(t.tag_cget("h1", "font")).split()[-2:] == [str(font("ui", 20, "bold")[1]),
                                                          "bold"]
    assert t.tag_ranges("item1") and int(t.tag_cget("item1", "lmargin2")) > int(
        t.tag_cget("item0", "lmargin2"))                          # nested and hanging
    assert t.tag_cget("table1", "tabs")                            # aligned columns
    assert str(t.cget("wrap")) == "word" and str(t.cget("state")) == "disabled"
    chips = {chip.cget("text"): chip for chip in view.chips}
    assert set(chips) == {"key", "A♥", "W", "S"}
    from btb import theme as themes
    current = themes.current()
    assert chips["A♥"].cget("foreground") == current.red             # card colours
    assert chips["A♥"].cget("background") == current.card


def test_a_help_page_can_be_copied_whole_or_in_part(tk_root):
    view = doc(tk_root, SAMPLE)
    plain = view.plain()
    for words in ("Title", "a `key`".replace("`", ""), "A♥", "Higher", "A note on two lines."):
        assert words in plain                     # chips' text is there, hidden
    view.text.focus_force()
    pump(tk_root)
    view.text.event_generate("<Control-a>")                  # Ctrl+A selects the page
    first, last = view.text.tag_ranges("sel")
    assert str(first) == "1.0" and view.text.compare(last, ">=", "end-1c")
    view.copy()
    assert "Higher" in view.clipboard_get() and "A♥" in view.clipboard_get()
    view.text.tag_remove("sel", "1.0", "end")
    start = view.text.search("Lower", "1.0")
    view.text.tag_add("sel", start, f"{start}+5c")
    view.copy()
    assert view.clipboard_get() == "Lower"


def test_help_pages_repaint_in_every_theme_and_keep_their_place(tk_root):
    from btb import theme as themes
    view = doc(tk_root, text.tool_guide())
    view.text.yview_moveto(0.5)
    pump(tk_root)
    place = view.text.index("@0,0")                    # the line at the top
    for t in themes.THEMES:
        themes.set_theme(t.name, tk_root, save=False)
        assert view.text.cget("background") == t.panel
        assert view.text.tag_cget("h2", "foreground") == t.accent
        assert all(chip.cget("background") in (t.card, themes.doc_palette(t)["code_bg"])
                   for chip in view.chips)
    pump(tk_root)
    assert view.text.index("@0,0") == place


def test_the_count_table_fits_the_smallest_window(tk_root, no_dialogs):
    # 14 columns: at 960 x 620 the gaps (and if need be the text) shrink so
    # no row wraps onto a second line.
    import tkinter as tk
    import main
    app = main.MainApplication(tk.Toplevel(tk_root))
    app.root.geometry("960x620")
    page = app.show_page("strategy")
    pump(tk_root)
    tk_root.after(200)
    pump(tk_root)
    text = page.doc.text
    for word in ("Rank", "Basic", "Weighted", "Advanced"):
        line = text.search(word, "1.0").split(".")[0]
        assert not text.count(f"{line}.0", f"{line}.end", "displaylines"), word


def test_a_key_chip_fits_its_column_and_passes_the_wheel_on(tk_root):
    view = doc(tk_root, text.shortcut_help())
    chip = next(c for c in view.chips if c.cget("text") == "7 8 9 / 4 5 6 / 1 2 3")
    stops = [float(v) for v in view.text.tag_cget("table1", "tabs")[::2]]
    assert view.text.winfo_rootx() + stops[1] > chip.winfo_rootx() + chip.winfo_width()
    view.text.yview_moveto(0)
    pump(tk_root)
    before = view.text.yview()[0]
    view._wheel(type("Event", (), {"num": 5, "delta": -120})())
    assert view.text.yview()[0] > before
    assert chip.bind("<Button-5>") and chip.bind("<MouseWheel>")


def test_the_app_help_pages_use_the_document_view(tk_root, no_dialogs):
    import tkinter as tk
    import main
    from btb.widgets import DocView
    app = main.MainApplication(tk.Toplevel(tk_root))
    for key in ("rules", "strategy", "guide", "shortcuts"):
        page = app.show_page(key)
        assert isinstance(page.doc, DocView) and page.doc.plain().strip()
    assert "Keyboard Shortcuts" in app.page("shortcuts").doc.plain()


# ------------------------------------------------------------------ charts -- #

def test_nice_ticks_are_round_and_cover_the_range():
    pytest.importorskip("tkinter")
    from btb.widgets import nice_ticks
    assert nice_ticks(0, 37.5) == [0, 10, 20, 30, 40]
    assert nice_ticks(21.3, 27.9) == [20, 22, 24, 26, 28]
    ticks = nice_ticks(0, 0.4)
    assert ticks[0] == 0 and ticks[-1] >= 0.4


def chart_texts(chart):
    c = chart.canvas
    return [c.itemcget(i, "text") for i in c.find_all() if c.type(i) == "text"]


def test_bar_chart_thins_labels_and_marks_the_average(tk_root):
    import tkinter as tk
    from btb import theme as themes
    from btb.widgets import BarChart
    window = tk.Toplevel(tk_root)
    chart = BarChart(window, themes.current(), width=320, height=200, title="Plays")
    chart.pack()
    items = [(str(n), float(n % 7)) for n in range(20, 70)]
    chart.draw(items, average=(12.3, "avg 32.30"))
    pump(tk_root)
    labels = [t for t in chart_texts(chart) if t.isdigit() and 20 <= int(t) < 70]
    assert 2 <= len(labels) < len(items)                       # thinned, never crowded
    assert "avg 32.30" in chart_texts(chart)
    dashed = [i for i in chart.canvas.find_all()
              if chart.canvas.type(i) == "line" and chart.canvas.itemcget(i, "dash")]
    assert dashed                                              # the average line
    chart.draw([])
    assert chart.empty_message in chart_texts(chart)


def test_line_chart_draws_each_series_with_a_legend(tk_root):
    import tkinter as tk
    from btb import theme as themes
    from btb.widgets import LineChart
    window = tk.Toplevel(tk_root)
    chart = LineChart(window, themes.current(), width=420, height=240, title="Win rate")
    chart.pack()
    chart.draw_series(["0", "5", "10"], {
        "0 jokers": [(20, 18, 22), (24, 22, 26), None],
        "1 joker": [(30, 27, 33), (35, 32, 38), (31, 28, 34)]})
    pump(tk_root)
    texts = chart_texts(chart)
    assert "0 jokers" in texts and "1 joker" in texts and "10" in texts
    series_lines = [i for i in chart.canvas.find_all() if chart.canvas.type(i) == "line"
                    and float(chart.canvas.itemcget(i, "width")) == 2.0]
    assert len(series_lines) >= 2


def test_simulator_advanced_tab_charts_every_distribution(tk_root, no_dialogs):
    import tkinter as tk
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(tk.Toplevel(tk_root))
    gui.sims_var.set("400")
    gui.seed_var.set("3")
    gui.jokers_var.set("1")
    gui.cores_var.set("1")
    gui.start()
    pump(tk_root, until=lambda: gui.result is not None)
    assert len(gui.adv_charts) == 6
    for chart in gui.adv_charts:
        assert chart.items and chart.average is not None, chart.title
        assert chart.average[1].startswith("avg ")
    boxes = gui.adv_charts[0]
    assert [label for label, _ in boxes.items] == [str(n) for n in range(1, 10)]
    assert sum(v for _, v in boxes.items) == pytest.approx(100)
    assert gui.adv_vars[0].get() == gui.win_var.get()
    gui.advanced_as_text.set(True)                           # Show as text
    gui.layout_advanced()
    assert gui.advanced_text_frame.winfo_manager() and not gui.advanced_charts.winfo_manager()
    gui.copy_advanced()
    assert "Plays per game" in gui.root.clipboard_get()
    gui.clear()
    assert not gui.adv_charts[0].items and gui.adv_vars[0].get() == "-"


def test_optimizer_advanced_tab_charts_win_rate_against_each_setting(tk_root, no_dialogs):
    import tkinter as tk
    from btb.gui_sim import OptimizerGUI
    gui = OptimizerGUI(tk.Toplevel(tk_root))
    for name, value in (("games", "20"), ("jokers_max", "1"), ("moves_max", "2"),
                        ("threshold_max", "10"), ("step", "5"), ("seed", "1")):
        gui.vars[name].set(value)
    gui.confirm_var.set(False)
    gui.cores_var.set("1")
    gui.start()
    pump(tk_root, until=lambda: gui.sweep is not None)
    assert list(gui.threshold_chart.series) == ["0 jokers", "1 joker"]
    assert gui.threshold_chart.labels == ["0", "5", "10"]
    assert gui.calls_chart.labels == ["0", "1", "2"]
    assert all(len(points) == 3 for points in gui.threshold_chart.series.values())
    best = gui.sweep.best_by("jokers")
    assert [v for _, v in gui.jokers_chart.items] == [r.win_rate for r in best.values()]
    assert gui.jokers_chart.errors == [r.margin for r in best.values()]
    rows = [gui.best_table.item(i, "values") for i in gui.best_table.get_children()]
    assert len(rows) == 2 + 3 + 3                            # jokers, calls, thresholds
    assert rows[0][0] == "Jokers"


def test_the_wheel_scrolls_the_page_over_a_table_with_nothing_to_scroll(tk_root):
    import tkinter as tk
    from tkinter import ttk
    from btb.widgets import ScrollFrame, _can_scroll, _wheel, scrolled_tree
    window = tk.Toplevel(tk_root)
    window.geometry("300x200")
    panel = ScrollFrame(window)
    panel.pack(fill="both", expand=True)
    holder, tree = scrolled_tree(panel.body, {"a": ("A", 60, "w")}, height=5)
    holder.pack()
    ttk.Frame(panel.body, height=600).pack()                  # the panel must scroll
    for n in range(3):
        tree.insert("", "end", values=(n,))
    pump(tk_root)
    tk_root.after(100)
    pump(tk_root)
    assert panel.scrolling and not _can_scroll(tree)        # all rows show: the page scrolls
    assert _wheel(type("Event", (), {"widget": tree, "state": 0, "num": 5,
                                     "delta": -120})()) == "break"
    assert panel.canvas.yview()[0] > 0
    for n in range(20):
        tree.insert("", "end", values=(n,))
    pump(tk_root)
    assert _can_scroll(tree)                                 # now the table scrolls itself


def test_theme_listeners_of_closed_windows_are_dropped(tk_root):
    import tkinter as tk
    from btb import theme as themes
    window = tk.Toplevel(tk_root)
    themes.subscribe(window, lambda t: None)
    window.destroy()
    themes.subscribe(tk_root, lambda t: None)
    assert all(themes.alive(w) for w, _c in themes._listeners)


# --------------------------------------------------------- the test set-up -- #

def test_every_gui_test_shares_one_hidden_root(tk_root):
    import tkinter as tk
    import conftest
    assert tk_root is conftest.session_root()
    assert tk._default_root is tk_root and tk_root.state() == "withdrawn"


def test_clean_up_leaves_the_root_as_a_new_test_expects(tk_root, no_dialogs):
    import tkinter as tk
    import conftest
    from btb.gui_sim import SimulatorGUI, _GcPause
    from btb.gui_game import PlayerGUI
    PlayerGUI(tk.Toplevel(tk_root))
    sim = SimulatorGUI(tk.Toplevel(tk_root))
    sim.sims_var.set("200000")
    sim.cores_var.set("1")
    sim.start()                                              # a run still going...
    tk_root.after(60000, lambda: None)                       # ...and a timer still set
    conftest.clean_up(tk_root)
    assert tk_root.winfo_children() == []
    assert conftest._pending_after(tk_root) == []
    assert _GcPause.active == 0 and gc.isenabled() and not sim.task.running