# Marvel Rivals Blood Hunt Damage Calculator

A desktop damage calculator for the **Blood Hunt** limited mode in Marvel Rivals.  
Built with Python and tkinter - no external dependencies required.

---

## Requirements

- Python 3.10 or newer (uses `float | None` union type hints)
- No third-party packages - only the Python standard library

---

## Running the calculator

```bash
python bloodhunt_calc.py
```

---

## Overview

The calculator helps you model and compare damage output across different item/ability combinations (loadouts) by letting you enter your current stats and seeing exactly how much damage each configuration produces, both in raw numbers and as a percentage multiplier.

---

## Input fields

Each loadout has two sections of inputs.

### Input Values

| Field | Abbreviation | Description |
|---|---|---|
| Base Damage | BD | Your hero's base damage value. Toggle **ON** to enter a flat number (outputs show real damage); toggle **OFF** to treat it as 1 and see outputs as % multipliers. |
| Total Damage Bonus | TDB | A flat percentage bonus applied to base damage (e.g. 20 for +20%). |
| Total Output Boost | TOB | A separate multiplicative output boost percentage. |

### Bonus Damage Sources

Each of the three bonus sources has an **ON/OFF toggle**. Only enabled sources are included when calculating the Total Bonus Damage Multiplier.

| Field | Abbreviation |
|---|---|
| Bonus Damage Against Close-Range Enemies | BDACRE |
| Bonus Damage Against Bosses | BDAB |
| Damage Bonus Against Healthy Enemies | DBAHE |

### Critical / Precision

| Field | Abbreviation | Default |
|---|---|---|
| Critical Hit Rate | CHR | 5% |
| Critical Damage | CD | 150% |
| Precision Hit Rate | PHR | 1% |
| Precision Damage | PD | 800% |

---

## Bonus Damage Mode

Controls how the three bonus damage sources are combined into the **Total Bonus Damage Multiplier (TBDM)**.

| Mode | Formula |
|---|---|
| **Multiplicative** | `TBDM = (1 + BDACRE) × (1 + BDAB) × (1 + DBAHE)` |
| **Additive** | `TBDM = 1 + BDACRE + BDAB + DBAHE` |

Only sources with their toggle set to **ON** are included.

---

## Output values

| Output | Description |
|---|---|
| **Damage (D)** | Base hit damage, excluding bonus damage sources and crit/precision. |
| **Critical Damage (C)** | Damage on a critical hit. |
| **Precision Damage (P)** | Damage on a precision hit. |
| **Average Hit Damage (AHD)** | Weighted average across normal, critical and precision hits based on your rates. |
| **Total Bonus Damage Multiplier (TBDM)** | The combined multiplier from your enabled bonus sources, shown as a percentage. |

When **Base Damage is OFF**, all outputs are shown as **percentage multipliers** (e.g. `150%` means the build deals 1.5× a baseline). When it is **ON**, outputs are flat damage numbers.

Hovering over any output value shows the full untruncated number in a tooltip.

---

## Formulas

```
D   = (BD + BD × TDB%) × (BD + TOB%) × TBDM

C   = D × CD%
P   = D × PD%
AHD = C × CHR% + P × PHR% + D × (1 − CHR% − PHR%)
```

When Base Damage is OFF, `BD = 1` and all outputs are multiplied by 100 to display as percentages.

---

## Multiple loadouts

Up to **6 loadouts** can be open at once, each in its own tab.

| Toolbar button | Action |
|---|---|
| ＋ Add Loadout | Opens a new loadout tab with default values. |
| ✕ Remove Loadout | Removes the currently selected loadout tab (requires at least 2). |
| ✎ Rename | Opens a dialog to rename the currently selected loadout. |

---

## Comparison tab

The **Comparison** tab shows all loadouts side by side. It recalculates every value from scratch using its own settings - independently of what is shown on each individual loadout tab.

### Comparison-specific controls (sticky footer)

| Control                        | Description |
|--------------------------------|---|
| **Bonus Damage Mode** toggle   | Sets additive or multiplicative mode for all comparison calculations. |
| **Base Damage** toggle + field | When ON, the single value entered here is used as BD for every loadout in the comparison. When OFF, all values are shown as % multipliers. |
| **Calculate All**              | Triggers a fresh calculation on every loadout and refreshes the comparison grid. |

### Results section

Shows **D, C, P, AHD** and **TBDM** for each loadout, calculated with that loadout's enabled bonus sources and the comparison's BD/mode settings. The **▲** marker (green) highlights the highest value in each row; **▼** (red) highlights the lowest.

### Avg Hit Damage by Bonus Source

Shows what AHD would be for seven specific bonus source combinations, isolating the contribution of each source or group. Useful for deciding which bonus sources are worth prioritising.

| Combination |
|---|
| Close Range only |
| Boss only |
| Healthy Enemy only |
| Close Range + Boss |
| Close Range + Healthy Enemy |
| Healthy Enemy + Boss |
| Close Range + Boss + Healthy Enemy |

Each value is calculated as:

```
AHD_base × bonus_multiplier(selected sources)
```

where `AHD_base` is the loadout's average hit damage with no bonus sources active.

---

## Save and Load

| Button | Behaviour |
|---|---|
| 💾 Save | Saves all loadout inputs to a `.json` file. The first save prompts for a file location; subsequent saves in the same session overwrite the same file silently. |
| 📂 Load | Opens a previously saved `.json` file and restores all loadouts. |

### On close

When you press the window's close button (✕), the app checks whether any unsaved changes have been made since the last save or load. If there are none, it closes immediately. If there are, a dialog appears with three options:

- **Save & Quit** - saves (prompting for a path if needed) then closes.
- **Quit Without Saving** - closes without saving.
- **Cancel** - returns to the app.

### Save file format

Loadouts are stored as plain JSON and can be inspected or edited in any text editor.

```json
{
  "loadouts": [
    {
      "name": "Loadout 1",
      "values": {
        "BD": "1", 
        "TDB": "0", 
        "TOB": "0",
        "BDACRE": "0", 
        "BDAB": "0", 
        "DBAHE": "0",
        "CHR": "5", 
        "CD": "150", 
        "PHR": "1", 
        "PD": "800"
      },
      "bonus_toggles": { 
        "BDACRE": false, 
        "BDAB": false, 
        "DBAHE": false
      },
      "additive": false,
      "bd_raw": false
    }
  ]
}
```

---

## Field minimums and defaults

| Field | Default | Minimum |
|---|---|---|
| BD | 1 | 1 |
| TDB | 0% | 0% |
| TOB | 0% | 0% |
| BDACRE | 0% | 0% |
| BDAB | 0% | 0% |
| DBAHE | 0% | 0% |
| CHR | 5% | 5% |
| CD | 150% | 150% |
| PHR | 1% | 1% |
| PD | 800% | 800% |

Values entered below the minimum are automatically clamped when the field loses focus.
