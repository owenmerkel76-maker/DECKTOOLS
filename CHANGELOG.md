# Changes

## Automatic updates

- Added one-time Windows setup for updates to the existing pyRevit-linked folder.
- Checks the published development branch at sign-in and every 15 minutes,
  waits while Revit is open, backs up previous versions, and preserves local edits.

## Tool descriptions

- Added detailed hover descriptions for all ribbon tools, including prerequisites
  and next steps. Deck Designer is marked as the starting point for a complete deck.
- Added visible descriptions for every Studio menu action and a first-deck guide.
- Clarified that material creation requires selecting the finish in Deck Designer,
  Board Builder is optional, and manufacturer resources use manual downloads/import.

## Deck Designer 0.5

- Added one to three mitered picture-frame courses with corner/butt gaps, recessed
  field layout, stock-length border splits, role-aware stock groups, and polygon
  area takeoffs. Frame cutting reports distinguish long-point blank estimates.
- Added Deck Studio, a tabbed WPF designer window, field/border material selectors,
  and menu/ribbon utilities for inspect, select, remove, and opening reports.
- Added Materials Studio with a Windows color picker, texture and grayscale bump
  file selection, strength controls, and independent Generic appearance assets.
- Added a browser/download/import workflow for Trex resources and imported Revit
  material libraries; no automatic catalog/API integration or maps are bundled.
- Preserved source material assets and provided explicit inherited-map removal.
- Added picture-frame CLI options and tests for geometry, reporting, settings,
  XAML event wiring, and mocked native material operations.

Windows/Revit validation of WPF, rendering assets, and placement is pending.

## Deck AutoLayout 0.4

- Imported the uploaded extension, icons, DXF references, and original layout QA;
  excluded generated Python bytecode.
- Added 12- and 16-foot stock alongside the original 20-foot default. Butt joints
  and piece lengths follow the selected stock length.
- Added adjustable crosscut saw kerf and whole spare-board quantities. Default
  spare allowance is 10%, rounded up per width/profile group.
- Added stock IDs and cut sequences to cut lists and a separate stock cutting
  schedule linked to the same Revit board Marks.
- Added purchase totals, installed length/area, crosscut kerf, offcuts, and a
  clearly defined linear loss percentage.
- Corrected missing kerf for shortened stock pieces and the final trimmed piece;
  full-length pieces do not incur a crosscut.
- Preserved prior CSVs in unique folders with UTF-8 text support.
- Rejected nonfinite dimensions/settings before geometry and quantity math.
- Corrected profile validation so half-inch rips can retain one groove.
- Required full-width perpendicular selected joists for common butt seams;
  midpoint intersections alone do not support every board-row joint.
- Added a CLI takeoff preview, regression tests, ZIP packaging, and CI.
- Kept the generic CAMO-style clip placeholder and added direct RFA loading plus
  searchable type selection for other brands, regardless of family name.
- Limited alternate clips to compatible unhosted point-based Generic Models;
  cancelled/incompatible family loads roll back without overwriting definitions.
- Recorded selected family/type in clip metadata, preview, and material reports,
  including non-ASCII names.

Trex Board Builder retains its v0.2 family workflow, with the narrow-profile
correction. Revit/pyRevit execution remains pending Windows field testing.
