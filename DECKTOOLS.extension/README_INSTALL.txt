DECKTOOLS v0.5 | SEPARATE STANDALONE PYREVIT EXTENSION
==================================================
Revit: planned compatibility with 2025 / 2027, untested in Revit here.
pyRevit: IronPython 2.7-compatible scripts; Python 3 CSV export supported.

REPLACE THE PRIOR DECKTOOLS, NOT ROBMEPTOOLS
1. Close Revit or reload pyRevit after the change.
2. Extract the folder DECKTOOLS.extension into the PARENT extension location
   you already registered with pyRevit, e.g. C:\RevitExtensions\DECKTOOLS.extension
3. IMPORTANT: Back up your OLD DECKTOOLS.extension before replacing it, and
   keep only one active copy. Do not nest it inside ROBMEPTOOLS.extension.
4. pyRevit Settings -> Custom Extension Folders: add the PARENT directory
   C:\RevitExtensions (not the .extension folder itself), if not registered.
5. Reload pyRevit. The separate DECKTOOLS tab contains:
   Studio -> Deck Studio (central menu)
   Boards -> Trex Board Builder (preserved from v0.2)
   Layout -> Deck Designer (tabbed settings + picture frames)
   Materials -> Deck Materials (color/texture/bump editor)
   Utilities -> Deck Tools (inspect/select/reports/resources/remove)

FIRST FIELD TEST
1. Create a simple FLAT rectangular Revit Floor. A 10ft x 12ft floor is ideal.
   It is the perimeter GUIDE, not actual board material.
2. Select that Floor first, then DECKTOOLS -> Layout -> Deck Designer.
3. Choose long-edge board direction.
4. Choose 12/16/20ft stock, extra spare boards (default 10%), and crosscut kerf
   in inches (default 0.125). Spares are extra whole boards, rounded up per
   width/profile group. They are not modeled.
   The same window selects 0-3 mitered picture-frame courses, board width,
   and separate field/border project materials on the Materials tab.
5. Choose nominal 16in O.C. joists for the first test. This mode IS ESTIMATED.
6. Choose auto-create schematic CAMO EDGECLIP family; if Revit cannot create
   or load it, the tool automatically uses native model-proxy clips instead.
   For another brand, choose "Load a different clip family (.rfa)" and select
   its type. Reuse it later with "Choose a loaded clip family/type".
   Supported: unhosted point-based Generic Model families, any name/brand.
   Origin: gap center at board underside. Local X along boards, Y across gap,
   Z up. Match the 3/16-inch gap; selecting a family does not change spacing.
7. Confirm the preview. Look for individual native 3D planks and clips.
8. CSVs export to a unique folder inside Documents\DECKTOOLS_Exports:
   Cutlist.csv, StockCuts.csv (numbered stock-board cuts), and Materials.csv.
   Board Marks, stock IDs, and cut sequences agree across reports.
9. Re-run on the SAME Floor to regenerate: previously generated elements for
   that floor are replaced rather than duplicated.

WHAT IS ACTUALLY IMPLEMENTED
- An individual Revit Generic Model DirectShape solid for EACH installed cut.
- Native grooved board profiles from board_profile.py (overall board size
  5.5 inches wide x 0.94 inches thick; GROOVE DETAILS APPROXIMATE).
- 3/16in SIDE gap; equal border board rips, with factory groove retained on
  the inside edge. 1/8in butt gaps on runs exceeding selected stock length.
- Native 3D model geometry for hidden clips at joist x board-gap crossings.
- Choice of selected line-based actual joists or nominal joist spacing.
- Clip family instances using the schematic placeholder or compatible loaded/
  browsed clip RFAs from any brand. Searchable family/type selection, without
  a clip/CAMO naming requirement. Unsupported hosted/adaptive types are excluded.
- Boards/fasteners Mark and Comments identification for Revit schedules.
- Board cutlist, stock cutting schedule, and material/purchase ESTIMATE CSVs.
  Selected actual joists must be perpendicular and span full field width to
  support common straight butt-joint seams across all rows.
- Picture-frame square-edge polygon solids with miter gaps. Long border cuts
  are stock-length divisions; provide border backing/blocking and fasteners.
- Native material creation with color, local texture, and grayscale bump maps.
  Opens Trex's website for manual manufacturer downloads/import. No catalog sync.

NOT YET SUPPORTED (v0.3)
- Floor shapes that are not 4-corner rectangles, curved edges, floor holes,
  posts, stairs, sloping decking, rotated members outside chosen rectangle.
- Fascia, starters/finish fasteners, true clip quantities for
  butt-joint blocking, structural validation or accurate joist layout unless
  actual modeled joists are selected.
- Clips on deck perimeters; rip clip/face-fastener engineering is user review.
- Genuine manufacturer CAMO solid. The included clip DXFs and automatically
  generated RFA are SCHEMATIC placeholders, not shop/fabrication parts.
- RFA instance for each board: v0.5 uses NATIVE DirectShape solids so it can
  generate boards regardless of whether v0.2 Trex Family Builder has passed
  its first real Revit test. They remain separate and quantifiable elements.
- Guaranteed globally optimal stock cutting. First-fit decreasing with chosen
  stock and kerf, sorted by rip width/profile, is a conservative ESTIMATE.
  Excludes factory end trim and longitudinal ripping loss. Linear loss includes
  crosscut kerf and offcuts, excluding spare boards and ripped width.

INSTALLATION/PRODUCT SAFETY
Treat the clip and groove geometry as diagrammatic. Manufacturer approval and
actual joist spacing/fastener installation must be confirmed in field.
A model using NOMINAL joist spacing does not prove framing is present there.
Actual Revit 2025 and 2027 API testing is still required.

SOURCE REFERENCES
CAMO Edge Clip official product: https://www.camofasteners.com/products/clips/edge-clips/
CAMO clip manufacturer submittal: https://www.camofasteners.com/wp-content/uploads/S005A0003-EdgeClip.pdf
Trex installation instructions: https://www.trex.com/build-your-deck/planyourdeck/deck-installation-guide/

If Revit reports an error, provide the warning screenshot and pyRevit output
traceback. No changes to ROBMEPTOOLS are made by this package.
