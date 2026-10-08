# DECKTOOLS

Decking tools for Autodesk Revit and pyRevit. This repository contains the
user-uploaded extension, with material-estimate and cut-list improvements in
Deck AutoLayout v0.4.

- **Trex Board Builder:** generate native Revit board families with adjustable
  instance length and a fixed, chosen rip width.
- **Deck AutoLayout:** lay out separate grooved board solids and schematic clips
  on a flat rectangular Floor, including rotated rectangles.
- **Material takeoff:** choose 12-, 16-, or 20-foot stock, crosscut saw kerf, and
  spare boards. Export cuts, numbered stock cutting schedules, and purchase totals.

## Install in Revit

1. Download the extension ZIP or clone this repository on Windows.
2. Put `DECKTOOLS.extension` in a pyRevit extension parent folder, such as
   `C:\RevitExtensions\DECKTOOLS.extension`. Back up an existing DECKTOOLS
   extension before replacing it; keep only one active copy.
3. In pyRevit Settings, register `C:\RevitExtensions` under Custom Extension
   Folders, then reload pyRevit.
4. Select a flat rectangular Floor in a project and choose
   **DECKTOOLS → Layout → Deck AutoLayout**.
5. Choose board direction, stock length, extra spare boards, saw kerf, joist
   source, and clip geometry. Review the estimate before generating elements.

The application targets Revit 2025 and newer with pyRevit. Revit 2025/2027
compatibility requires field testing; cloud tests do not run Autodesk Revit.
See [installation and first field test](DECKTOOLS.extension/README_INSTALL.txt)
and [manual validation checklist](docs/REVIT_TESTING.md).

## Clip placeholder and other brands

The original CAMO-style schematic placeholder is included. Choose either the
auto-generated Revit family or built-in placeholder solids when running layout.

To use a different brand, choose **Load a different clip family (.rfa)** and
select its type. Later, choose **Choose a loaded clip family/type** to reuse it.
The searchable list accepts any family name; it does not require "clip" or
"CAMO". Family and type names appear in the preview, clip element Comments,
and material report. Existing family definitions are not overwritten.

Alternate families must be **unhosted, point-based Generic Models**. Hosted,
face-based, work-plane-based, line-based, and adaptive types are excluded from
the current placement workflow. Families must suit the existing 3/16-inch board
gap. The insertion origin is the gap center at board underside; local X follows
board length, local Y crosses the gap, and local Z points up. Verify alignment
on a test deck. Selecting a brand does not change gap spacing or fastening counts.
Cancelling type selection or loading an incompatible family rolls back that load.

## Reports

Each run creates a new subfolder inside `Documents\DECKTOOLS_Exports` on Windows.
Previous reports are preserved, even when exports occur in the same second.

| Report | Contents |
| --- | --- |
| `Cutlist.csv` | One row per installed piece, matching its Revit Mark; feet/inches, width/profile, stock ID, and cut sequence |
| `StockCuts.csv` | Each numbered stock board's cuts in order, assigned piece IDs, kerf loss, and remaining offcut |
| `Materials.csv` | Base stock, whole spare boards, purchase totals, installed length/area, offcuts, kerf, and clip estimates |

Spare-board allowance defaults to **10%**, rounded up **separately for each
width/profile group**. Set it to **0%** to order only the base cutting estimate.
A 12-foot run across a 10-foot deck with 12-foot stock yields 22 installed
pieces, 22 base stock boards, and 4 spare boards at 10%: **26 boards to purchase**.
Spares do not create extra model elements.

Packing uses deterministic first-fit decreasing, keeping rip widths and profiles
separate. Each purchased board is assumed to start as full 5.5-inch raw stock;
opposite perimeter rips are not combined into one raw board. This is a conservative
estimate, not a guaranteed minimum. Kerf is counted for each crosscut that shortens
remaining stock, including a last trimmed piece. An exact full-length or exact
remaining-length piece needs no crosscut. Reports exclude factory end trimming
and longitudinal rip-saw loss. Linear loss percentage excludes spare boards and
width removed by ripping; remaining offcuts can be reusable.

## Preview estimates without Revit

Python 3.10 or newer is enough; no third-party packages are required. From the
repository root:

```bash
python tools/estimate_deck.py --run 12 --width 10 --stock 12 --spare-percent 10
```

`--run` is the dimension along the boards; `--width` is across them, both in feet.
`--spacing` is estimated joist spacing in inches (default 16); `--kerf` is crosscut
saw kerf in inches (default 0.125). Use `--output` to choose an export parent folder.
This command creates the same three CSV reports as the Revit button, with
placeholder Floor ID 0. It does not create a Revit model.

## Development and checks

```bash
python -m unittest discover -s tests -v
python DECKTOOLS.extension/Resources/QA/test_board_math.py
python tools/package_extension.py
```

The tests cover stock choices, kerf, spare rounding, material conservation,
cut-to-stock assignments, exports, CLI behavior, joist support, and narrow-board
profiles. The original QA script checks 7 fixed and 240 randomized layout cases.
GitHub Actions runs both and creates an installable ZIP artifact. Packaging
writes `dist/DECKTOOLS.extension.zip` without Python bytecode caches.

Keep extension runtime modules compatible with IronPython 2.7; developer tools
and tests use Python 3. CPython checks are not a Revit or IronPython certification.

## Current scope

Layouts support flat four-corner rectangles. Irregular outlines, openings, posts,
stairs, picture frames, fascia, and slopes require further development. Selected
joists used for common straight butt seams must be perpendicular and span the
full deck width. Angled/partial members can receive clips at crossings but are
not used as common joint support.

Board grooves and built-in CAMO-style clip geometry are schematic. Clip quantities
exclude perimeter starters, finish fasteners, and butt-joint blocking details.
Nominal joist spacing does not confirm actual framing.

The original upload is preserved outside this checkout. Its SHA-256 is
`dddcd73fc5243bcd16e75448afd9b96b5cd8371a643287dee88e44464fe4eedb`.
