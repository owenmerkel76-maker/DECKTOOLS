# DECKTOOLS

Decking tools for Autodesk Revit and pyRevit. This repository contains the
user-uploaded extension, with material-estimate and cut-list improvements in
Deck Designer v0.5.

- **Trex Board Builder:** generate native Revit board families with adjustable
  instance length and a fixed, chosen rip width.
- **Deck AutoLayout:** lay out separate grooved board solids and schematic clips
  on a flat rectangular Floor, including rotated rectangles.
- **Material takeoff:** choose 12-, 16-, or 20-foot stock, crosscut saw kerf, and
  spare boards. Export cuts, numbered stock cutting schedules, and purchase totals.
- **Picture frames:** one to three square-edge border courses, mitered corner
  gaps, stock-length splits, and separate field/border purchase groups.
- **Deck Studio:** a central menu, tabbed settings window, Materials Studio, and
  tools to inspect, select, remove generated elements, or open existing reports.

## Install in Revit

Hover over any ribbon button to read what it does, what to select first, and
what happens next. Deck Studio displays descriptions and a first-deck guide.

1. Download the extension ZIP or clone this repository on Windows.
2. Put `DECKTOOLS.extension` in a pyRevit extension parent folder, such as
   `C:\RevitExtensions\DECKTOOLS.extension`. Back up an existing DECKTOOLS
   extension before replacing it; keep only one active copy.
3. In pyRevit Settings, register `C:\RevitExtensions` under Custom Extension
   Folders, then reload pyRevit.
4. Open **DECKTOOLS → Studio → Deck Studio → Design a deck**, or the
   **Layout → Deck Designer** button. Select the flat rectangular Floor.
5. In the settings window choose direction, stock length, picture-frame courses,
   spare allowance, kerf, joist source, and clips. The Materials tab selects
   different project materials for the field and border. Review quantities before
   generating elements. Canceling the settings or quantity preview leaves the
   existing layout intact.

The application targets Revit 2025 and newer with pyRevit. Revit 2025/2027
compatibility requires field testing; cloud tests do not run Autodesk Revit.
See [installation and first field test](DECKTOOLS.extension/README_INSTALL.txt)
and [manual validation checklist](docs/REVIT_TESTING.md).

For updates without downloading and replacing the folder each time, close Revit
and run **Setup Auto Updates.cmd** once from this repository. It updates your
existing linked folder at sign-in and every 15 minutes while Revit is closed,
keeping backups. See [automatic update setup and recovery](docs/AUTO_UPDATES.md).

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

Picture-frame cuts are tagged `FRAME`, with course, side, orientation, and cutting
notes in both cut reports. Field cuts are tagged `FIELD`. Frame lengths are
**long-point blank estimates**; verify miter saw allowances and end trimming.
Long border runs are divided to fit stock, independently of modeled joists.
Border backing, blocking, starter/face fasteners, and joint supports need separate
specification. The clip estimate covers gaps between field rows only.

## Color, texture, bump maps, and manufacturer materials

Open **Deck Studio → Materials studio**, or **Materials → Deck Materials**.
Give the material a new name, pick a color, and optionally browse to a color
texture and grayscale bump/height image. Adjust bump strength from 0 to 1.
The tool creates a native project material and an independent Generic appearance
asset. Existing material/appearance definitions are preserved. You can use an
imported project material as the appearance source; blank image paths retain
source maps unless you check **Remove inherited maps**.

For Trex assets, **Manufacturer website / BIM resources** opens the official Trex
website. Locate and download manufacturer-supplied materials/maps. Import an
`.adsklib` using **Revit Material Browser → Open existing library**, then add its
material to the project. You can select that project material directly in Deck
Designer; Materials Studio edits copies of Generic-schema sources. Advanced/PBR
schemas can be used directly but must be edited with Revit Material Browser.

This is a browser/download/import workflow, **not an automatic Trex catalog API**.
No manufacturer maps are bundled, scraped, or synthesized. The cloud network
blocked inspection of current Trex resource pages, so no live catalog integration
is claimed. Use supplied grayscale height maps for bump, not RGB normal maps.

Keep image files at their selected paths (or configure Revit rendering search
paths). Graphics colors appear in Shaded views; appearance textures and bump maps
appear in Realistic views/rendering. Verify scale/orientation in Material Browser.
To change an existing generated deck's materials, rerun Deck Designer for the same
Floor and choose the new field/border materials; regeneration replaces its solids.

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
python tools/estimate_deck.py --run 25 --width 15 --stock 16 --frame-courses 2
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
Additional checks exercise picture-frame polygons, settings validation, XAML
event wiring, and mocked Revit material/family workflows. WPF windows, native
appearance APIs, actual geometry, and rendered mapping still need Windows testing.
GitHub Actions runs both and creates an installable ZIP artifact. Packaging
writes `dist/DECKTOOLS.extension.zip` without Python bytecode caches.

Keep extension runtime modules compatible with IronPython 2.7; developer tools
and tests use Python 3. CPython checks are not a Revit or IronPython certification.

## Current scope

Layouts support flat four-corner rectangles. Irregular outlines, openings, posts,
stairs, fascia, and slopes require further development. Selected
joists used for common straight butt seams must be perpendicular and span the
full field width (inside any picture frame). Angled/partial members can receive clips at crossings but are
not used as common joint support.

Board grooves and built-in CAMO-style clip geometry are schematic. Clip quantities
exclude perimeter starters, finish fasteners, and butt-joint blocking details.
Nominal joist spacing does not confirm actual framing.

The original upload is preserved outside this checkout. Its SHA-256 is
`dddcd73fc5243bcd16e75448afd9b96b5cd8371a643287dee88e44464fe4eedb`.
