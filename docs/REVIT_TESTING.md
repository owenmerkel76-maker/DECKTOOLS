# Manual Revit validation

These checks require Windows, Revit, and pyRevit. They have not been run in the
Linux cloud environment. Use a disposable project and back up the previous
extension before installing this version.

1. Reload pyRevit and confirm both buttons load without import errors.
2. Create a 12ft by 10ft horizontal Floor. Choose long-edge direction, 12ft stock,
   10% spares, 0.125in kerf, nominal 16in joists, and proxy clips. Verify 22 installed
   pieces, 22 base stock, 4 spares, and 26 boards to purchase. Spares are not modeled.
3. Confirm each board Mark appears once in `Cutlist.csv` and `StockCuts.csv`.
   Reports must show 12ft stock and zero crosscut kerf for these exact 12ft pieces.
   Check `Materials.csv` against the preview.
4. Repeat on a 25ft by 10ft floor for 12/16/20ft stock with 0% spares. Every cut
   must fit selected stock; check butt gaps and joints against the joist grid.
5. Rotate a floor and repeat. Verify direction, grooves, clips, and unchanged
   takeoff quantities for identical dimensions.
6. Rerun on the same floor. Previous DECKTOOLS elements must be replaced without
   duplicates; other floors must remain. Both export directories must survive.
7. Cancel each prompt and the preview. Existing model elements must remain.
   Negative kerf and `nan` must produce an error before model changes.
8. Select actual perpendicular joists spanning full width; verify joints and
   clips. On a run exceeding stock, choose only partial/diagonal joists: it must
   reject common seams without full-width support.
9. Test auto-generated clip families and a compatible loaded point-based Generic
   Model clip family. Verify orientations and quantities; record API tracebacks.
10. Generate half-inch square, left-grooved, and right-grooved board families.
    Verify solid creation and length changes. Half-inch opposed grooves must fail.
11. Verify irregular, sloping, curved, and holed floors fail before deleting prior
    elements. A failed modeling transaction must preserve the previous layout.

Record Revit/pyRevit versions, interpreter, inputs, expected/observed behavior,
and full pyRevit tracebacks for failures.
