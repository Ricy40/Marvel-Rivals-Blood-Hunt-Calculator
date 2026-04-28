import json
import tkinter as tk
from tkinter import ttk, filedialog


# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#0d0d1a"
PANEL    = "#141428"
CARD     = "#1b1b38"
RED      = "#c41e3a"
RED_H    = "#e02040"   # activebackground tint
RED_HH   = "#ff2040"   # strong hover for Calculate buttons
GOLD     = "#d4a534"
GREEN    = "#27ae60"
TEXT     = "#e5e5f0"
DIM      = "#6e6e9a"
ENTRY_BG = "#0a0a18"
BORDER   = "#26265a"
BORDER_H = "#3a3a80"   # hover for toolbar buttons
T_ON     = "#c41e3a"
T_ON_H   = "#ff2040"   # hover: ON state (red toggle)
T_OFF    = "#232350"
T_OFF_H  = "#2d2d72"   # hover: OFF state
BLUE     = "#2a6ebb"
BLUE_H   = "#3d87e8"   # hover: blue mode toggle
WHITE    = "#ffffff"


# ── Tooltip ────────────────────────────────────────────────────────────────────
class Tooltip:
    # Shows a floating label near the widget. side='right' or 'below'.

    def __init__(self, widget, msg, side="right"):
        self.widget = widget
        self.msg    = msg
        self.side   = side
        self._tip   = None
        widget.bind("<Enter>", self._show, "+")
        widget.bind("<Leave>", self._hide, "+")

    def _show(self, _=None):
        if self._tip:
            return
        if self.side == "below":
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        else:
            x = self.widget.winfo_rootx() + self.widget.winfo_width() + 10
            y = self.widget.winfo_rooty()
        self._tip = tw = tk.Toplevel(self.widget)
        tw.overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        border = tk.Frame(tw, bg=GOLD, padx=1, pady=1)
        border.pack()
        inner = tk.Frame(border, bg=CARD, padx=12, pady=10)
        inner.pack()
        tk.Label(inner, text=self.msg, bg=CARD, fg=TEXT,
                 font=("Segoe UI", 9), wraplength=290, justify="left").pack()

    def _hide(self, _=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Hover helper ───────────────────────────────────────────────────────────────
def _add_hover(btn, hover_bg):
    # Bind a subtle background change on mouse-over to signal interactivity.
    normal_bg = btn.cget("bg")
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg))


# ── Toggle button ──────────────────────────────────────────────────────────────
class ToggleBtn(tk.Label):
    # Maps each normal bg to its hover tint so _refresh can pick the right one
    # regardless of current ON/OFF state.
    _HOVER = {
        T_ON:  T_ON_H,
        T_OFF: T_OFF_H,
        BLUE:  BLUE_H,
        RED:   T_ON_H,
    }

    def __init__(self, parent, var, text_on, text_off,
                 bg_on=T_ON, bg_off=T_OFF, **kw):
        super().__init__(parent, cursor="hand2",
                         font=("Segoe UI", 8, "bold"),
                         fg=WHITE, relief="flat", padx=10, pady=4, **kw)
        self.var      = var
        self.text_on  = text_on
        self.text_off = text_off
        self.bg_on    = bg_on
        self.bg_off   = bg_off
        self._hovered = False
        self._refresh()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        # Keep visual in sync when the var is changed externally (e.g. session load)
        var.trace_add("write", lambda *_: self._refresh())

    def _on_enter(self, _=None):
        self._hovered = True
        self._refresh()

    def _on_leave(self, _=None):
        self._hovered = False
        self._refresh()

    def _refresh(self):
        on   = self.var.get()
        base = self.bg_on if on else self.bg_off
        bg   = self._HOVER.get(base, base) if self._hovered else base
        self.configure(text=self.text_on if on else self.text_off, bg=bg)

    def _click(self, _=None):
        self.var.set(not self.var.get())
        self._refresh()


# ── Loadout ────────────────────────────────────────────────────────────────────
class Loadout:
    # One complete set of inputs + outputs, living in a notebook tab.

    FIELDS = [
        ("Base Damage",                              "BD"),
        ("Total Damage Bonus",                       "TDB"),
        ("Total Output Boost",                       "TOB"),
        ("Bonus Damage Against Close-Range Enemies", "BDACRE"),
        ("Bonus Damage Against Bosses",              "BDAB"),
        ("Damage Bonus Against Healthy Enemies",     "DBAHE"),
        ("Critical Hit Rate",                        "CHR"),
        ("Critical Damage",                          "CD"),
        ("Precision Hit Rate",                       "PHR"),
        ("Precision Damage",                         "PD"),
    ]
    BONUS = ("BDACRE", "BDAB", "DBAHE")
    FIELD_DEFAULTS = {
        "BD": "1",  "TDB": "0",   "TOB": "0",
        "BDACRE": "0", "BDAB": "0", "DBAHE": "0",
        "CHR": "5", "CD": "150",  "PHR": "1", "PD": "800",
    }
    FIELD_MINS = {
        "BD": 1,  "TDB": 0,   "TOB": 0,
        "BDACRE": 0, "BDAB": 0, "DBAHE": 0,
        "CHR": 5, "CD": 150,  "PHR": 1, "PD": 800,
    }

    def __init__(self, parent, name, on_calculate=None, on_change=None):
        self.name         = name
        self.on_calculate = on_calculate
        self.results      = {}   # populated after calculate()

        self.vals     = {k: tk.StringVar(value=self.FIELD_DEFAULTS[k]) for _, k in self.FIELDS}
        self.toggs    = {k: tk.BooleanVar(value=False) for k in self.BONUS}
        self.additive = tk.BooleanVar(value=False)
        self.bd_raw   = tk.BooleanVar(value=False)

        # Dirty tracking — fire on_change whenever any input var is written
        if on_change:
            for v in (list(self.vals.values()) +
                      list(self.toggs.values()) +
                      [self.additive, self.bd_raw]):
                v.trace_add("write", lambda *_: on_change())

        self.out_labels: dict = {}
        self.out_tips:   dict = {}

        self.frame = tk.Frame(parent, bg=BG)
        self._build()

    # ── UI build ───────────────────────────────────────────────────────────────

    def _build(self):
        body = tk.Frame(self.frame, bg=BG, padx=16, pady=14)
        body.pack(fill="both", expand=True)
        self._input_panel(body)
        self._output_panel(body)

    def _input_panel(self, parent):
        col = tk.Frame(parent, bg=PANEL, padx=14, pady=14)
        col.pack(side="left", fill="y", padx=(0, 12))

        self._sec(col, "INPUT VALUES")

        for label, key in self.FIELDS:
            if key == "BDACRE":
                self._div(col)
                self._sec(col, "BONUS DAMAGE SOURCES")
            if key == "CHR":
                self._div(col)

            row = tk.Frame(col, bg=PANEL)
            row.pack(fill="x", pady=3)

            if key == "BD":
                self._bd_btn = ToggleBtn(row, self.bd_raw, "ON", "OFF",
                                         bg_on=T_ON, bg_off=T_OFF, width=4)
                self._bd_btn.pack(side="left", padx=(0, 8))
            elif key in self.BONUS:
                ToggleBtn(row, self.toggs[key], "ON", "OFF",
                          bg_on=T_ON, bg_off=T_OFF, width=4).pack(side="left", padx=(0, 8))
            else:
                tk.Label(row, text="", bg=PANEL, font=("Segoe UI", 8, "bold"),
                         padx=10, pady=4, width=4).pack(side="left", padx=(0, 8))

            tk.Label(row, text=label, font=("Segoe UI", 9),
                     bg=PANEL, fg=TEXT, anchor="w", width=40).pack(side="left")

            suffix = "%" if key != "BD" else " "
            tk.Label(row, text=suffix, font=("Segoe UI", 9),
                     bg=PANEL, fg=DIM, width=1).pack(side="right")

            e = tk.Entry(row, textvariable=self.vals[key], width=8,
                         bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("Segoe UI", 9),
                         justify="right", bd=4,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=RED)
            e.pack(side="right", padx=(4, 2))
            e.bind("<FocusOut>", lambda _, k=key: self._clamp(k))

        # Mode toggle row
        self._div(col)
        mrow = tk.Frame(col, bg=PANEL)
        mrow.pack(fill="x", pady=4)

        tk.Label(mrow, text="", bg=PANEL, font=("Segoe UI", 8, "bold"),
                 padx=10, pady=4, width=4).pack(side="left", padx=(0, 8))
        tk.Label(mrow, text="Bonus Damage Mode", font=("Segoe UI", 9),
                 bg=PANEL, fg=TEXT).pack(side="left")

        mode_btn = ToggleBtn(mrow, self.additive,
                             text_on="Additive", text_off="Multiplicative",
                             bg_on=BLUE, bg_off=RED)
        mode_btn.pack(side="right")

        Tooltip(self._bd_btn, (
            "When ON, the entered Base Damage value is used directly and outputs "
            "show actual damage numbers.\n\n"
            "When OFF, Base Damage is assumed to be 1 and all output values are "
            "shown as a percentage, representing the total damage multiplier "
            "rather than flat damage numbers."
        ))
        Tooltip(mode_btn, (
            "Multiplicative mode\n"
            "All enabled Bonus Damage sources are multiplied together:\n"
            "Total Bonus Damage Multiplier = (1 + Bonus Damage Against Close-Range Enemies)\n"
            "× (1 + Bonus Damage Against Bosses)\n"
            "× (1 + Damage Bonus Against Healthy Enemies)\n\n"
            "Additive mode\n"
            "All enabled Bonus Damage sources are summed together:\n"
            "Total Bonus Damage Multiplier = (1 + Bonus Damage Against Close-Range Enemies\n"
            "+ Bonus Damage Against Bosses\n"
            "+ Damage Bonus Against Healthy Enemies)"
        ))

        _calc_btn = tk.Button(col, text="C A L C U L A T E",
                              font=("Segoe UI", 11, "bold"),
                              bg=RED, fg=WHITE,
                              activebackground=RED_H, activeforeground=WHITE,
                              relief="flat", cursor="hand2", pady=10, bd=0,
                              command=self.calculate)
        _add_hover(_calc_btn, RED_HH)
        _calc_btn.pack(fill="x", pady=(16, 0))

    def _output_panel(self, parent):
        col = tk.Frame(parent, bg=PANEL, padx=14, pady=14, width=320)
        col.pack_propagate(False)
        col.pack(side="left", fill="both", expand=True)

        self._sec(col, "RESULTS")

        result_rows = [
            ("Damage",             "D",   TEXT),
            ("Critical Damage",    "C",   TEXT),
            ("Precision Damage",   "P",   TEXT),
            ("Average Hit Damage", "AHD", GOLD),
        ]
        for label, key, color in result_rows:
            card = tk.Frame(col, bg=CARD, padx=12, pady=8)
            card.pack(fill="x", pady=4)
            tk.Label(card, text=label, font=("Segoe UI", 8),
                     bg=CARD, fg=DIM, anchor="w").pack(fill="x")
            lbl = tk.Label(card, text="-", font=("Segoe UI", 17, "bold"),
                           bg=CARD, fg=color, anchor="e")
            lbl.pack(fill="x")
            self.out_labels[key] = lbl
            self.out_tips[key] = Tooltip(lbl, "", side="below")

        self._div(col)

        tbd_card = tk.Frame(col, bg=CARD, padx=12, pady=8)
        tbd_card.pack(fill="x", pady=4)
        tk.Label(tbd_card, text="Total Bonus Damage Multiplier", font=("Segoe UI", 8),
                 bg=CARD, fg=DIM, anchor="w").pack(fill="x")
        self.tbd_lbl = tk.Label(tbd_card, text="-",
                                font=("Segoe UI", 17, "bold"), bg=CARD, fg=RED, anchor="e")
        self.tbd_lbl.pack(fill="x")
        self.tbd_tip = Tooltip(self.tbd_lbl, "", side="below")

        self.err_v = tk.StringVar()
        tk.Label(col, textvariable=self.err_v, font=("Segoe UI", 8),
                 bg=PANEL, fg="#e74c3c", wraplength=240,
                 justify="left").pack(fill="x", pady=(8, 0))

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _sec(self, parent, text):
        tk.Label(parent, text=text, font=("Segoe UI", 8, "bold"),
                 bg=PANEL, fg=DIM, anchor="w").pack(fill="x", pady=(0, 6))

    def _div(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=8)

    def _clamp(self, key):
        try:
            v = float(self.vals[key].get())
        except ValueError:
            v = self.FIELD_MINS[key]
        clamped = max(v, self.FIELD_MINS[key])
        self.vals[key].set(str(int(clamped) if clamped == int(clamped) else clamped))

    def _pct(self, key) -> float:
        try:
            v = float(self.vals[key].get())
        except ValueError:
            v = self.FIELD_MINS[key]
        v = max(v, self.FIELD_MINS[key])
        return v if key == "BD" else v / 100.0

    def _calc_tbd(self, additive_override: bool = None) -> float:
        # Compute the bonus-damage multiplier from enabled sources.
        # additive_override lets the comparison tab impose a uniform mode.
        active = [k for k in self.BONUS if self.toggs[k].get()]
        use_additive = self.additive.get() if additive_override is None else additive_override
        if use_additive:
            return 1.0 + sum(self._pct(k) for k in active)
        result = 1.0
        for k in active:
            result *= (1.0 + self._pct(k))
        return result

    def compute_base_results(self, bd_raw_override: bool = None,
                             bd_val_override: float = None) -> dict:
        # Compute D/C/P/AHD with TBD=1.0 (no bonus damage sources).
        # bd_raw_override lets the comparison tab impose a uniform raw/% mode.
        # bd_val_override lets the comparison tab supply a shared Base Damage value.
        use_raw = self.bd_raw.get() if bd_raw_override is None else bd_raw_override
        if use_raw and bd_val_override is not None:
            BD = bd_val_override
        else:
            BD = self._pct("BD") if use_raw else 1.0
        TDB = self._pct("TDB")
        TOB = self._pct("TOB")
        CHR = self._pct("CHR")
        CD  = self._pct("CD")
        PHR = self._pct("PHR")
        PD  = self._pct("PD")
        D   = (BD + BD * TDB) * (BD + TOB)   # TBD = 1.0
        C   = D * CD
        P   = D * PD
        AHD = C * CHR + P * PHR + D * (1 - CHR - PHR)
        sfx = "" if use_raw else "%"
        if not use_raw:
            D *= 100; C *= 100; P *= 100; AHD *= 100
        return {"D": D, "C": C, "P": P, "AHD": AHD, "sfx": sfx}

    def compute_for_combo(self, active_keys: tuple, additive: bool = None,
                          bd_raw_override: bool = None,
                          bd_val_override: float = None) -> float:
        # Return AHD_base × bonus_multiplier(active_keys).
        # AHD_base is always computed with TBD=1.0; the combo multiplier is applied on top.
        ahd_base = self.compute_base_results(
            bd_raw_override=bd_raw_override,
            bd_val_override=bd_val_override)["AHD"]
        use_additive = self.additive.get() if additive is None else additive
        if use_additive:
            tbd = 1.0 + sum(self._pct(k) for k in active_keys)
        else:
            tbd = 1.0
            for k in active_keys:
                tbd *= (1.0 + self._pct(k))
        return ahd_base * tbd

    @staticmethod
    def _pick_font(text: str) -> tuple:
        n = len(text)
        if n <= 12: return ("Segoe UI", 17, "bold")
        if n <= 17: return ("Segoe UI", 14, "bold")
        if n <= 22: return ("Segoe UI", 11, "bold")
        return              ("Segoe UI",  9, "bold")

    def _set_out(self, key: str, value: float, suffix: str):
        display = f"{int(value):,}{suffix}"
        full    = f"{value:,}{suffix}"
        font    = self._pick_font(display)
        lbl     = self.out_labels[key]
        lbl.configure(text=display, font=font)
        self.out_tips[key].msg = f"Full value: {full}"

    # ── Calculate ──────────────────────────────────────────────────────────────

    def calculate(self):
        self.err_v.set("")
        try:
            BD  = self._pct("BD") if self.bd_raw.get() else 1.0
            TDB = self._pct("TDB")
            TOB = self._pct("TOB")
            CHR = self._pct("CHR")
            CD  = self._pct("CD")
            PHR = self._pct("PHR")
            PD  = self._pct("PD")
            TBD = self._calc_tbd()

            sfx = "%" if not self.bd_raw.get() else ""

            D   = ((BD + BD * TDB) * (BD + TOB)) * TBD
            C   = D * CD
            P   = D * PD
            AHD = C * CHR + P * PHR + D * (1 - CHR - PHR)

            if not self.bd_raw.get():
                D   *= 100
                C   *= 100
                P   *= 100
                AHD *= 100

            self._set_out("D",   D,   sfx)
            self._set_out("C",   C,   sfx)
            self._set_out("P",   P,   sfx)
            self._set_out("AHD", AHD, sfx)

            tbd_display = f"{int(TBD * 100):,}%"
            self.tbd_lbl.configure(text=tbd_display, font=self._pick_font(tbd_display))
            self.tbd_tip.msg = f"Full value: {TBD * 100:,}%"

            self.results = {"D": D, "C": C, "P": P, "AHD": AHD,
                            "TBD": TBD, "sfx": sfx}

            if self.on_calculate:
                self.on_calculate()

        except ValueError:
            self.err_v.set("Invalid input - enter numeric values only.")


# ── Comparison tab ─────────────────────────────────────────────────────────────
class ComparisonTab:
    # Displays all calculated loadout results side-by-side with high/low markers.

    ROWS = [
        ("Damage",                        "D",   False),
        ("Critical Damage",               "C",   False),
        ("Precision Damage",              "P",   False),
        ("Average Hit Damage",            "AHD", False),
        ("Total Bonus Damage Multiplier", "TBD", True),
    ]
    COMBOS = [
        ("Close Range Damage",           ("BDACRE",)),
        ("Boss Damage",                  ("BDAB",)),
        ("Healthy Enemy Damage",         ("DBAHE",)),
        ("Close Range + Boss",           ("BDACRE", "BDAB")),
        ("Close Range + Healthy",        ("BDACRE", "DBAHE")),
        ("Healthy + Boss",               ("BDAB",   "DBAHE")),
        ("Close Range + Healthy + Boss", ("BDACRE", "BDAB", "DBAHE")),
    ]
    _MODE_TIP = (
        "Multiplicative mode\n"
        "All enabled Bonus Damage sources are multiplied together:\n"
        "Total Bonus Damage Multiplier = (1 + Bonus Damage Against Close-Range Enemies)\n"
        "× (1 + Bonus Damage Against Bosses)\n"
        "× (1 + Damage Bonus Against Healthy Enemies)\n\n"
        "Additive mode\n"
        "All enabled Bonus Damage sources are summed together:\n"
        "Total Bonus Damage Multiplier = (1 + Bonus Damage Against Close-Range Enemies\n"
        "+ Bonus Damage Against Bosses\n"
        "+ Damage Bonus Against Healthy Enemies)\n\n"
        "This setting controls the mode used for the\n"
        "'Average Hit Damage by Bonus Source' rows."
    )

    def __init__(self, parent, get_loadouts, calc_all):
        self.get_loadouts = get_loadouts
        self.calc_all     = calc_all
        self.additive_var = tk.BooleanVar(value=False)
        self.bd_raw_var   = tk.BooleanVar(value=False)
        self.bd_val_var   = tk.StringVar(value="1")
        self.frame        = tk.Frame(parent, bg=BG)

        self._content = tk.Frame(self.frame, bg=BG)
        self._content.pack(fill="both", expand=True, side="top")

        tk.Frame(self.frame, bg=BORDER, height=1).pack(side="bottom", fill="x")
        self._build_footer()

        self._placeholder()

    def _build_footer(self):
        # Persistent sticky bar with mode toggle and Calculate All button.
        bar = tk.Frame(self.frame, bg=PANEL, padx=14, pady=10)
        bar.pack(side="bottom", fill="x")

        tk.Label(bar, text="", bg=PANEL, font=("Segoe UI", 8, "bold"),
                 padx=10, pady=4, width=4).pack(side="left", padx=(0, 8))
        tk.Label(bar, text="Bonus Damage Mode", font=("Segoe UI", 9),
                 bg=PANEL, fg=TEXT).pack(side="left")
        mode_btn = ToggleBtn(bar, self.additive_var,
                             text_on="Additive", text_off="Multiplicative",
                             bg_on=BLUE, bg_off=RED)
        mode_btn.pack(side="left", padx=(8, 0))
        Tooltip(mode_btn, self._MODE_TIP)

        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", padx=(16, 0), pady=2)

        # Base Damage raw / % toggle
        tk.Label(bar, text="Base Damage", font=("Segoe UI", 9),
                 bg=PANEL, fg=TEXT).pack(side="left", padx=(16, 0))
        bd_btn = ToggleBtn(bar, self.bd_raw_var, "ON", "OFF",
                           bg_on=T_ON, bg_off=T_OFF)
        bd_btn.pack(side="left", padx=(8, 0))
        Tooltip(bd_btn, (
            "When ON, the Base Damage value entered below is used directly "
            "for all loadouts and outputs show actual damage numbers.\n\n"
            "When OFF, Base Damage is assumed to be 1 and all output values are "
            "shown as a percentage, representing the total damage multiplier "
            "rather than flat damage numbers."
        ))
        tk.Entry(bar, textvariable=self.bd_val_var, width=7,
                 bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 9),
                 justify="right", bd=4,
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=RED).pack(side="left", padx=(6, 0))

        tk.Label(bar, text="", bg=PANEL, font=("Segoe UI", 8, "bold"),
                 padx=10, pady=4, width=4).pack(side="right", padx=(8, 0))
        calc_all_btn = tk.Button(
            bar, text="C A L C U L A T E   A L L",
            font=("Segoe UI", 11, "bold"),
            bg=RED, fg=WHITE,
            activebackground=RED_H, activeforeground=WHITE,
            relief="flat", cursor="hand2", padx=10, pady=10, bd=0,
            takefocus=0, highlightthickness=0,
            command=self.calc_all)
        _add_hover(calc_all_btn, RED_HH)
        calc_all_btn.pack(side="right")

    def _placeholder(self):
        for w in self._content.winfo_children():
            w.destroy()
        tk.Label(
            self._content,
            text="Add a loadout to begin comparing.",
            bg=BG, fg=DIM, font=("Segoe UI", 11), justify="center"
        ).pack(expand=True)

    def refresh(self):
        for w in self._content.winfo_children():
            w.destroy()
        loadouts = list(self.get_loadouts())
        if not loadouts:
            self._placeholder()
            return
        self._build_grid(loadouts)

    # ── Grid ──────────────────────────────────────────────────────────────────

    def _build_grid(self, loadouts):
        canvas  = tk.Canvas(self._content, bg=BG, highlightthickness=0)
        vscroll = ttk.Scrollbar(self._content, orient="vertical",
                                style="BH.Vertical.TScrollbar",
                                command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        outer  = tk.Frame(canvas, bg=BG, padx=24, pady=16)
        win_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        outer.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * e.delta / 120), "units")

        def _bind_tree(w):
            w.bind("<MouseWheel>", _scroll)
            for child in w.winfo_children():
                _bind_tree(child)

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        # Also directly bind to the canvas so it works when hovering the blank area
        canvas.bind("<MouseWheel>", _scroll)
        # Defer child binding until the grid is fully rendered
        outer.after(50, lambda: _bind_tree(outer))

        # Column sizing
        outer.columnconfigure(0, minsize=230)
        for ci in range(len(loadouts)):
            outer.columnconfigure(ci + 1, weight=1, minsize=160)

        # Header row
        tk.Label(outer, text="", bg=BG).grid(row=0, column=0, sticky="w", pady=(0, 8))
        for ci, l in enumerate(loadouts):
            tk.Label(outer, text=l.name,
                     font=("Segoe UI", 10, "bold"),
                     bg=BG, fg=TEXT, anchor="center").grid(
                row=0, column=ci + 1, padx=4, pady=(0, 8), sticky="ew")

        cur = 1

        bd_raw   = self.bd_raw_var.get()
        additive = self.additive_var.get()
        comp_sfx = "" if bd_raw else "%"   # uniform suffix for the whole grid

        # Resolve the comparison-wide Base Damage value (only used when bd_raw ON)
        bd_val: float | None = None
        if bd_raw:
            try:
                bd_val = max(float(self.bd_val_var.get()), 1.0)
            except (ValueError, TypeError):
                bd_val = 1.0

        # ── Standard results (D/C/P/AHD always exclude bonus damage) ─────────
        self._sec_hdr(outer, "RESULTS", cur, len(loadouts))
        cur += 1
        for row_label, key, is_pct in self.ROWS:
            vals = []
            for l in loadouts:
                if key == "TBD":
                    # Recompute live using comparison's additive mode
                    vals.append(l._calc_tbd(additive_override=additive) * 100)
                else:
                    # Recompute fresh with TBD=1.0 and the comparison settings
                    base = l.compute_base_results(bd_raw_override=bd_raw,
                                                  bd_val_override=bd_val)
                    vals.append(base.get(key))
            self._data_row(outer, cur, loadouts, row_label, vals, is_pct, comp_sfx)
            cur += 1

        # ── Avg Hit Damage by bonus source ────────────────────────────────────
        self._sec_hdr(outer, "AVG HIT DAMAGE BY BONUS SOURCE", cur, len(loadouts))
        cur += 1
        for combo_label, combo_keys in self.COMBOS:
            vals = []
            for l in loadouts:
                try:
                    vals.append(l.compute_for_combo(
                        combo_keys, additive=additive,
                        bd_raw_override=bd_raw, bd_val_override=bd_val))
                except Exception:
                    vals.append(None)
            self._data_row(outer, cur, loadouts, combo_label, vals, False, comp_sfx)
            cur += 1

    def _sec_hdr(self, parent, text, row, n_cols):
        tk.Label(parent, text=text,
                 font=("Segoe UI", 8, "bold"),
                 bg=BG, fg=DIM, anchor="w").grid(
            row=row, column=0, columnspan=n_cols + 1,
            sticky="w", pady=(14, 4))

    def _data_row(self, parent, row_idx, loadouts, label, raw_vals, is_pct,
                  comp_sfx: str = ""):
        tk.Label(parent, text=label,
                 font=("Segoe UI", 9),
                 bg=BG, fg=DIM, anchor="w").grid(
            row=row_idx, column=0, sticky="w", padx=(0, 12), pady=3)

        valid     = [v for v in raw_vals if v is not None]
        max_v     = max(valid) if valid else None
        min_v     = min(valid) if valid else None
        all_equal = (max_v == min_v)

        for ci, (l, v) in enumerate(zip(loadouts, raw_vals)):
            cell = tk.Frame(parent, bg=CARD, padx=10, pady=8)
            cell.grid(row=row_idx, column=ci + 1, padx=4, pady=3, sticky="ew")

            if v is None:
                tk.Label(cell, text="—", font=("Segoe UI", 14, "bold"),
                         bg=CARD, fg=DIM, anchor="e").pack(fill="x")
            else:
                sfx  = "%" if is_pct else comp_sfx
                disp = f"{int(v):,}{sfx}"

                if   not all_equal and v == max_v: marker, mfg = " ▲", GREEN
                elif not all_equal and v == min_v: marker, mfg = " ▼", RED
                else:                               marker, mfg = "",   DIM

                vrow = tk.Frame(cell, bg=CARD)
                vrow.pack(fill="x")
                tk.Label(vrow, text=disp, font=("Segoe UI", 14, "bold"),
                         bg=CARD, fg=TEXT, anchor="e").pack(side="left", fill="x", expand=True)
                if marker:
                    tk.Label(vrow, text=marker, font=("Segoe UI", 12, "bold"),
                             bg=CARD, fg=mfg).pack(side="right")


# ── App ────────────────────────────────────────────────────────────────────────
class App:
    MAX_LOADOUTS = 6

    def __init__(self, root: tk.Tk):
        self.root       = root
        self.loadouts: list = []
        self._count     = 0
        self._save_path = None   # path of the currently open save file
        self._dirty     = False  # unsaved-changes flag

        root.title("Blood Hunt - Damage Calculator")
        root.configure(bg=BG)

        self._style_notebook()
        self._build_header()
        self._build_notebook()

        self.add_loadout()

        root.update_idletasks()
        w  = root.winfo_width()
        h  = root.winfo_height()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        self._dirty = False
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Notebook styling ───────────────────────────────────────────────────────

    def _style_notebook(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("BH.TNotebook",
                    background=BG, borderwidth=0, tabmargins=[16, 0, 0, 0])
        s.configure("BH.TNotebook.Tab",
                    background=PANEL, foreground=TEXT,
                    padding=[16, 8], font=("Segoe UI", 9, "bold"),
                    borderwidth=0, focuscolor=PANEL,
                    lightcolor=PANEL, darkcolor=PANEL, bordercolor=PANEL)
        s.map("BH.TNotebook.Tab",
              background=[("selected", CARD),  ("active", BORDER)],
              foreground=[("selected", WHITE),  ("active", TEXT)],
              font      =[("selected", ("Segoe UI", 9, "bold"))])

        s.configure("BH.Vertical.TScrollbar",
                    troughcolor  = BG,       # invisible track
                    background   = BORDER_H, # thumb
                    darkcolor    = BG,
                    lightcolor   = BG,
                    bordercolor  = BG,
                    arrowcolor   = BG,       # hide up/down arrows
                    relief       = "flat",
                    borderwidth  = 0)
        s.map("BH.Vertical.TScrollbar",
              background=[("active",  RED),   # thumb on hover
                          ("pressed", RED_H)])

    # ── Header + toolbar ───────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="MARVEL RIVALS", font=("Segoe UI", 11, "bold"),
                 bg=BG, fg=DIM).pack()
        tk.Label(hdr, text="BLOOD HUNT", font=("Segoe UI", 26, "bold"),
                 bg=BG, fg=RED).pack()
        tk.Label(hdr, text="Damage Calculator", font=("Segoe UI", 10),
                 bg=BG, fg=DIM).pack()
        tk.Frame(self.root, bg=RED, height=2).pack(fill="x")

        bar = tk.Frame(self.root, bg=BG, padx=16, pady=8)
        bar.pack(fill="x")

        self.add_btn = tk.Button(
            bar, text="＋  Add Loadout",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT,
            activebackground=BORDER, activeforeground=TEXT,
            relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
            command=self.add_loadout)
        self.add_btn.pack(side="left")
        _add_hover(self.add_btn, BORDER_H)

        self.remove_btn = tk.Button(
            bar, text="✕  Remove Loadout",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=DIM,
            activebackground=BORDER_H, activeforeground=TEXT,
            relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
            state="disabled", command=self.remove_current)
        self.remove_btn.pack(side="left", padx=(8, 0))
        _add_hover(self.remove_btn, BORDER_H)

        self.rename_btn = tk.Button(
            bar, text="✎  Rename",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=DIM,
            activebackground=BORDER_H, activeforeground=TEXT,
            relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
            state="disabled", command=self.rename_current)
        self.rename_btn.pack(side="left", padx=(8, 0))
        _add_hover(self.rename_btn, BORDER_H)

        self.load_btn = tk.Button(
            bar, text="📂  Load",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT,
            activebackground=BORDER_H, activeforeground=TEXT,
            relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
            command=self._load_session)
        self.load_btn.pack(side="right")
        _add_hover(self.load_btn, BORDER_H)

        self.save_btn = tk.Button(
            bar, text="💾  Save",
            font=("Segoe UI", 9, "bold"), bg=PANEL, fg=TEXT,
            activebackground=BORDER_H, activeforeground=TEXT,
            relief="flat", cursor="hand2", padx=12, pady=4, bd=0,
            command=self._save_session)
        self.save_btn.pack(side="right", padx=(0, 8))
        _add_hover(self.save_btn, BORDER_H)

    # ── Notebook ───────────────────────────────────────────────────────────────

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root, style="BH.TNotebook")
        self.nb.pack(fill="both", expand=True)
        tk.Frame(self.root, bg=RED, height=2).pack(fill="x")
        tk.Frame(self.root, bg=BG, pady=8).pack(fill="x")

        self.comparison = ComparisonTab(
            self.nb,
            get_loadouts=lambda: self.loadouts,
            calc_all=self._calc_all)
        self.nb.add(self.comparison.frame, text="  ⚖  Comparison  ")

        # Keep toolbar buttons in sync when the user switches tabs
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._sync_buttons())

    # ── Loadout management ─────────────────────────────────────────────────────

    def _mark_dirty(self):
        self._dirty = True

    def add_loadout(self):
        if len(self.loadouts) >= self.MAX_LOADOUTS:
            return
        self._count += 1
        name = f"Loadout {self._count}"
        l = Loadout(self.nb, name,
                    on_calculate=self.comparison.refresh,
                    on_change=self._mark_dirty)
        self.loadouts.append(l)
        # Insert before the Comparison tab (always the last tab)
        self.nb.insert(len(self.loadouts) - 1, l.frame, text=f"  {name}  ")
        self.nb.select(len(self.loadouts) - 1)
        self._mark_dirty()
        self._sync_buttons()

    def remove_current(self):
        sel = self.nb.select()
        idx = self.nb.index(sel)
        if idx >= len(self.loadouts):   # Comparison tab selected - do nothing if there's no loadouts
            return
        if len(self.loadouts) <= 1:
            return
        self.nb.forget(sel)
        self.loadouts.pop(idx)
        self._mark_dirty()
        self.comparison.refresh()
        self._sync_buttons()

    def _calc_all(self):
        # Calculate every loadout silently, then refresh comparison once.
        for l in self.loadouts:
            orig, l.on_calculate = l.on_calculate, None
            l.calculate()
            l.on_calculate = orig
        self.comparison.refresh()

    def rename_current(self):
        # Prompt for a new name and apply it to the selected loadout tab.
        sel = self.nb.select()
        idx = self.nb.index(sel)
        if idx >= len(self.loadouts):
            return
        l = self.loadouts[idx]
        new_name = self._ask_rename(l.name)
        if new_name and new_name != l.name:
            l.name = new_name
            self.nb.tab(sel, text=f"  {new_name}  ")
            self._mark_dirty()
            self.comparison.refresh()

    def _ask_rename(self, current_name: str):
        # Show a themed modal dialogue for entering a new loadout name.
        # Returns the new name string, or None if the user cancelled.
        result   = tk.StringVar(value="")
        name_var = tk.StringVar(value=current_name)

        dlg = tk.Toplevel(self.root)
        dlg.title("Rename Loadout")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        def confirm(_=None):
            val = name_var.get().strip()
            if val:
                result.set(val)
            dlg.destroy()

        def cancel(_=None):
            dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", cancel)

        # ── Gold-border card ──────────────────────────────────────────────────
        border = tk.Frame(dlg, bg=GOLD, padx=1, pady=1)
        border.pack(padx=28, pady=28)
        inner = tk.Frame(border, bg=CARD, padx=32, pady=26)
        inner.pack()

        tk.Label(inner, text="Rename Loadout",
                 font=("Segoe UI", 14, "bold"), bg=CARD, fg=WHITE).pack(pady=(0, 16))

        entry = tk.Entry(inner, textvariable=name_var, width=24,
                         bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("Segoe UI", 10),
                         justify="center", bd=4,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=RED)
        entry.pack(pady=(0, 20))
        entry.select_range(0, "end")
        entry.focus_set()
        entry.bind("<Return>", confirm)
        entry.bind("<Escape>", cancel)

        btn_row = tk.Frame(inner, bg=CARD)
        btn_row.pack()

        ok_btn = tk.Button(btn_row, text="Rename",
                           font=("Segoe UI", 9, "bold"),
                           bg=RED, fg=WHITE,
                           activebackground=RED_H, activeforeground=WHITE,
                           relief="flat", cursor="hand2",
                           padx=14, pady=8, bd=0,
                           takefocus=0, highlightthickness=0,
                           command=confirm)
        ok_btn.pack(side="left", padx=(0, 8))
        _add_hover(ok_btn, RED_HH)

        cancel_btn = tk.Button(btn_row, text="Cancel",
                               font=("Segoe UI", 9, "bold"),
                               bg=PANEL, fg=DIM,
                               activebackground=BORDER_H, activeforeground=TEXT,
                               relief="flat", cursor="hand2",
                               padx=14, pady=8, bd=0,
                               takefocus=0, highlightthickness=0,
                               command=cancel)
        cancel_btn.pack(side="left")
        _add_hover(cancel_btn, BORDER_H)

        # Centre over main window
        dlg.update_idletasks()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        dw, dh = dlg.winfo_width(),       dlg.winfo_height()
        dlg.geometry(f"+{rx + (rw - dw) // 2}+{ry + (rh - dh) // 2}")

        dlg.wait_window()
        return result.get() or None

    def _sync_buttons(self):
        n = len(self.loadouts)
        self.add_btn.configure(
            state="normal" if n < self.MAX_LOADOUTS else "disabled",
            fg=TEXT if n < self.MAX_LOADOUTS else DIM)
        self.remove_btn.configure(
            state="normal" if n > 1 else "disabled",
            fg=TEXT if n > 1 else DIM)

        # Rename is only meaningful when a loadout tab is active
        try:
            on_loadout = self.nb.index(self.nb.select()) < n
        except Exception:
            on_loadout = False
        self.rename_btn.configure(
            state="normal" if on_loadout else "disabled",
            fg=TEXT if on_loadout else DIM)

    # ── Save / Load ────────────────────────────────────────────────────────────

    def _save_session(self) -> bool:
        # Serialize all loadout inputs to JSON.
        # Overwrites the current file if one is already open - otherwise prompts.
        path = self._save_path
        if not path:
            path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("Blood Hunt Save", "*.json"), ("All files", "*.*")],
                title="Save Loadouts",
                initialfile="bloodhunt_loadouts.json",
            )
            if not path:
                return False   # user cancelled the dialogue

        data = {"loadouts": []}
        for l in self.loadouts:
            data["loadouts"].append({
                "name":          l.name,
                "values":        {k: l.vals[k].get() for _, k in l.FIELDS},
                "bonus_toggles": {k: l.toggs[k].get() for k in l.BONUS},
                "additive":      l.additive.get(),
                "bd_raw":        l.bd_raw.get(),
            })

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

        self._save_path = path
        self._dirty = False   # clean state after a successful save
        return True

    def _load_session(self):
        """Open a saved JSON file and restore all loadouts from it."""
        path = filedialog.askopenfilename(
            filetypes=[("Blood Hunt Save", "*.json"), ("All files", "*.*")],
            title="Load Loadouts",
        )
        if not path:
            return

        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            return   # silently ignore corrupt/unreadable files

        # Clear all existing loadout tabs
        for l in self.loadouts:
            self.nb.forget(l.frame)
        self.loadouts.clear()
        self._count = 0

        for ld in data.get("loadouts", []):
            self._count += 1
            name = ld.get("name", f"Loadout {self._count}")
            l = Loadout(self.nb, name,
                        on_calculate=self.comparison.refresh,
                        on_change=self._mark_dirty)

            # Restore field values
            for _, k in Loadout.FIELDS:
                v = ld.get("values", {}).get(k)
                if v is not None:
                    l.vals[k].set(str(v))

            # Restore toggle states - trace fires, ToggleBtn refreshes automatically
            for k in Loadout.BONUS:
                state = ld.get("bonus_toggles", {}).get(k)
                if state is not None:
                    l.toggs[k].set(bool(state))

            l.additive.set(bool(ld.get("additive", False)))
            l.bd_raw.set(bool(ld.get("bd_raw", False)))

            self.loadouts.append(l)
            self.nb.insert(len(self.loadouts) - 1, l.frame, text=f"  {name}  ")

        if self.loadouts:
            self.nb.select(0)

        self._save_path = path
        self._dirty = False   # clean state - nothing has changed since load
        self.comparison.refresh()
        self._sync_buttons()

    # ── Close handling ─────────────────────────────────────────────────────────

    def _ask_save_on_quit(self) -> str:
        # Show a themed modal dialogue asking whether to save before closing.
        # Returns 'save', 'quit', or 'cancel'.
        result = tk.StringVar(value="cancel")

        dlg = tk.Toplevel(self.root)
        dlg.title("Blood Hunt – Unsaved Changes")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", lambda: (result.set("cancel"), dlg.destroy()))

        inner = tk.Frame(dlg, bg=CARD, padx=32, pady=26)
        inner.pack(padx=28, pady=28)

        tk.Label(inner, text="Save Your Work?",
                 font=("Segoe UI", 14, "bold"), bg=CARD, fg=WHITE).pack(pady=(0, 10))
        tk.Label(inner,
                 text="Would you like to save your loadouts\nbefore closing?",
                 font=("Segoe UI", 9), bg=CARD, fg=TEXT,
                 justify="center").pack(pady=(0, 22))

        btn_row = tk.Frame(inner, bg=CARD)
        btn_row.pack()

        def choose(val):
            result.set(val)
            dlg.destroy()

        save_b = tk.Button(btn_row, text="Save & Quit",
                           font=("Segoe UI", 9, "bold"),
                           bg=RED, fg=WHITE,
                           activebackground=RED_H, activeforeground=WHITE,
                           relief="flat", cursor="hand2",
                           padx=14, pady=8, bd=0,
                           takefocus=0, highlightthickness=0,
                           command=lambda: choose("save"))
        save_b.pack(side="left", padx=(0, 8))
        _add_hover(save_b, RED_HH)

        quit_b = tk.Button(btn_row, text="Quit Without Saving",
                           font=("Segoe UI", 9, "bold"),
                           bg=T_OFF, fg=TEXT,
                           activebackground=T_OFF_H, activeforeground=TEXT,
                           relief="flat", cursor="hand2",
                           padx=14, pady=8, bd=0,
                           takefocus=0, highlightthickness=0,
                           command=lambda: choose("quit"))
        quit_b.pack(side="left", padx=(0, 8))
        _add_hover(quit_b, T_OFF_H)

        cancel_b = tk.Button(btn_row, text="Cancel",
                             font=("Segoe UI", 9, "bold"),
                             bg=PANEL, fg=DIM,
                             activebackground=BORDER_H, activeforeground=TEXT,
                             relief="flat", cursor="hand2",
                             padx=14, pady=8, bd=0,
                             takefocus=0, highlightthickness=0,
                             command=lambda: choose("cancel"))
        cancel_b.pack(side="left")
        _add_hover(cancel_b, BORDER_H)

        # Centre over the main window
        dlg.update_idletasks()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        dw, dh = dlg.winfo_width(),       dlg.winfo_height()
        dlg.geometry(f"+{rx + (rw - dw) // 2}+{ry + (rh - dh) // 2}")

        dlg.wait_window()
        return result.get()

    def _on_close(self):
        if not self._dirty:
            self.root.destroy()   # nothing changed - close straight away
            return
        choice = self._ask_save_on_quit()
        if choice == "save":
            if self._save_session():   # False means user cancelled the file dialogue
                self.root.destroy()
        elif choice == "quit":
            self.root.destroy()
        # "cancel" - do nothing, leave the app open


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
