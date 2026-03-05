# Spiderweb Recall Tool

Automatically generates a call chain (spiderweb) for unit recalls from a CSV roster. Each person is assigned callers and callees according to rank, appointment, and platoon rules. Produces a spreadsheet and an interactive HTML chart.

---

## Requirements

- Python 3.10 or later
- `openpyxl` library

```
pip install openpyxl
```

---

## Usage

```
python main.py <input.csv> [output_dir]
```

- `<input.csv>` — path to your roster file (required)
- `[output_dir]` — folder to write outputs to (optional, defaults to the same folder as the CSV)

**Example:**

```
python main.py roster.csv outputs/
```

Two files are produced in the output directory:

- `recall_assignments.xlsx` — spreadsheet listing each person's callers and callees
- `recall_chart.html` — interactive visual graph, open in any browser

> If you get a `PermissionError` when saving the spreadsheet, close `recall_assignments.xlsx` in Excel first and re-run.

---

## Input CSV Format

The CSV must have the following columns (in any order):

| Column | Description |
|---|---|
| `Rank` | Military rank (e.g. `LTA`, `2SG`, `3SG`, `CPL`, `PTE`) |
| `Name` | Full name |
| `Platoon` | Platoon or section identifier (e.g. `HQ`, `SCT`, `SIG`) — any label is accepted |
| `Appt` | Appointment held (e.g. `OC`, `PL COMD`, `PL SGT`, `TEAM COMD`) |
| `Availability` | `1` if available for recall, `0` if unavailable |

Unavailable personnel are excluded from the call chain but still appear in the spreadsheet (greyed out).

---

## How Appointments Are Interpreted

The `Appt` column determines calling rules and limits. Three tiers are recognised:

**Initiators** — start the recall cascade. Appointment must be one of:
- `OC`, `CSM`, `2IC`

**PC/PS (Platoon Commander / Platoon Sergeant equivalents)** — senior calling tier. Matched if the appointment contains:
- `PL COMD` in any spacing or dash variant (e.g. `PLCOMD`, `PL-COMD`, `PL COMD (ASST)`)
- Both `PL` and `SGT` in any order or spacing (e.g. `PL SGT`, `PL-SGT`, `ASST PL SGT`, `PL SGT (C)`)
- Known equivalents: `BSO` (and variants like `BSO (ASST)`)

**Everyone else** — called by those above them in the chain.

> To add more PC/PS-equivalent appointments (e.g. a unit-specific role), edit the `PL_COMD_EQUIVALENTS` set in `models.py`.

---

## Call Limits

All roles share a flat base limit of **4 outbound calls**. 3SGs may be boosted by the algorithm but are capped at 4.

Each non-initiator person is targeted to receive calls from **2 callers**. Initiators require at least **1 inbound caller** from another initiator.

---

## Calling Rules

### Direction
- Calls generally flow from higher to equal rank.
- **Reverse calls are blocked** (if A calls B, B cannot call A), except within the **HQ platoon** where bidirectional calls are permitted.

### Rank
- Caller must be equal to or higher rank than callee (by effective rank level).
- Same-platoon senior ranks (LTA, 2LT, 1SG, and PL-SGT 2SGs) may call each other freely regardless of direction.
- Cross-platoon senior-to-senior calls are allowed within 1 rank level of difference.
- Plain 2SGs (without a PL SGT appointment) are treated as 3SG level for all rank and limit calculations.

### Platoon scope

| Caller role | Who they can call cross-platoon |
|---|---|
| Initiator | Anyone except 3SGs outside their own platoon |
| PC/PS | Other PC/PS or initiators only — max **1 cross-platoon call** |
| Senior non-PC/PS (e.g. LTA with a staff appointment) | Other senior ranks and 3SGs — not troopers |
| 3SG and below | Same platoon only |

### 3SG priority
3SGs prioritise calling fellow 3SGs in their platoon before troopers. Boosting up to the 4-call cap is allowed for both 3SG peers and troopers.

---

## Build Order (Phases)

The call graph is built in phases to ensure correct priority:

1. **Initiators cross-connect** — each initiator calls all other initiators where capacity allows
2. **Initiators seed platoons** — remaining initiator slots go to uncalled PC/PS, then own-platoon members
3. **PC/PS call each other** — same-platoon PC/PS are connected first before cross-platoon links are formed
4. **PC/PS call down into platoon** — each PC/PS claims at least one call into their own non-PC/PS members before the main saturation runs, ensuring the leadership chain reaches into every platoon
5. **Top-down saturation** — all remaining callee slots are filled senior-first with prioritised caller selection
6. **Coverage rescue** — any unreached person triggers a call-limit boost for same-platoon callers
7. **Top-up passes** — up to 3 passes to bring everyone to 2 callers
8. **3SG trooper coverage** — ensures troopers have a 3SG caller where possible
9. **Same-platoon caller enforcement** — swaps cross-platoon callers for same-platoon ones where preferred

---

## Output Files

### `recall_assignments.xlsx`

One row per person, sorted by platoon then rank. Columns:

| Column | Contents |
|---|---|
| Rank | Person's rank |
| Name | Person's name |
| Platoon | Platoon identifier |
| People to Call | Comma-separated list of people this person calls |
| Called By | Comma-separated list of people who call this person |

Colour coding: gold = initiator, grey = unavailable, pastel shades = platoon groupings.

A **Summary** sheet shows total personnel, availability counts, and coverage percentage.

### `recall_chart.html`

An interactive force-directed graph. Open in any browser — no internet connection required.

- **Hover** over a node to highlight its direct connections (green = outbound calls, orange = inbound calls)
- **Click** a node to see full details in the sidebar
- **Search** by name using the search box
- **Drag** nodes to rearrange the layout
- Adjust link strength and charge with the sliders
- **Reset View** returns to the default zoom

---

## Customisation

| What to change | Where |
|---|---|
| Add a PC/PS-equivalent appointment (e.g. `BSM`) | `PL_COMD_EQUIVALENTS` set in `models.py` |
| Change the max cross-platoon calls for PC/PS | `PC_PS_MAX_CROSS_PLATOON_CALLS` in `graph_builder.py` |
| Change the 3SG boost cap | `MAX_3SG_CALL_LIMIT` in `models.py` |
| Change the HQ platoon label | Update the `"HQ"` string in `can_assign` in `graph_builder.py` |

---

## File Structure

```
recall_tool/
├── main.py            # Entry point
├── parser.py          # CSV parsing
├── models.py          # Person dataclass, rank/appointment rules, call limits
├── graph_builder.py   # Call chain assignment algorithm
├── xlsx_exporter.py   # Spreadsheet output
├── html_exporter.py   # Interactive HTML chart output
└── README.md          # This file
```