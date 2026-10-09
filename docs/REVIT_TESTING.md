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
   Model clip family. Use "Load a different clip family (.rfa)" for another brand
   with multiple types, including a name without "clip" or "CAMO". Verify only
   the chosen type is placed and the preview, Comments, and Materials.csv record
   family/type. Rerun choosing that loaded family to replace prior placeholders.
   Cancel a type selection and verify the new family load rolls back. Try a hosted,
   face-based, or line-based family; it must reject and roll back. Verify existing
   definitions remain. Check family origin/orientation against the 3/16-inch gap.
10. Generate half-inch square, left-grooved, and right-grooved board families.
    Verify solid creation and length changes. Half-inch opposed grooves must fail.
11. Verify irregular, sloping, curved, and holed floors fail before deleting prior
    elements. A failed modeling transaction must preserve the previous layout.
12. Open Deck Studio and each menu command. Verify the settings window tabs and
    numeric validation, cancellation, loaded clip search, and direct ribbon buttons.
13. Generate 1-, 2-, and 3-course frames on rotated/unrotated rectangular floors.
    Check all four miter corners, 1/8-inch miter gaps, 3/16-inch course/field gaps,
    square-edge border geometry, recessed field, and clipped field fastener ranges.
    For borders longer than stock, inspect square butt splits; specify backing and
    fasteners independently. Verify FRAME/FIELD roles and border counts in reports.
14. Create a material with the color picker, a supplied color texture, and a supplied
    grayscale bump map. Verify a native material/appearance asset was created and
    source appearance is unchanged. Check unsupported schemas roll back the new
    material. Check inherited maps are retained or explicitly cleared as selected.
15. Select contrasting field/frame materials and regenerate the same Floor. Inspect
    materials on solid faces in a Realistic view/rendering and colors in Shaded.
    Verify map file availability, scale, orientation, and bump strength; fix mapping
    in Revit Material Browser as needed. These native APIs need actual Revit checks.
16. Import a manufacturer .adsklib through Material Browser and select its project
    material in Deck Designer. Test the Trex website launcher/download/file-picker
    workflow. No automatic online catalog is expected.
17. Inspect/select/remove generated elements for one Floor. Verify other floors,
    the footprint Floor, and unrelated Generic Models remain. Test remove cancel
    and Revit Undo. Open existing report folders without altering prior CSVs.

Record Revit/pyRevit versions, interpreter, inputs, expected/observed behavior,
and full pyRevit tracebacks for failures.
