# Review: space-bar-push-assist, attempt 3

Checks re-run:
- `cad check` (designer `--only`): **PASS, 0 fail, 23 warn**, all 23 accepted. This is identical to `cadcheck_a3.json`.
  - Coverage: parts, interference over all four collections, fasteners, service, slide, distances, assembly, insertion, stacks, flexures, cables.
  - Not checked: pilot diameters, wrench access to nuts, multi-segment insertion, teardown count, aesthetics, and BOM correctness. BOM correctness was checked separately with `cad bom`: PASS.
- a2 review rows run verbatim: 3 fail, all against the old sleeve mechanism.
- Reviewer rows (`review_rows.json` on a check-only split of the moving link, `scripts/split_moving_link.py`): **PASS, 0 fail**.
- `cad printcheck` on `stl_cc`: **PASS, 11 parts, 0 fail, 8 warn**.
- Slicer: unusable (known Bambu CLI segfault).

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 7 | Works, but has majors, one without a <1 h CAD fix | The clamped cell carries ~47 % of the grip moment. The 0.25 stop isn't sized to the cell: 1.3-5.1 x FS nominal, up to 9.6 x worst case. |
| Manufacturability | 8 | Works, ≤2 majors (here 0) | 0 fails, no supports, 11 parts, ~22 h. A Ø15 washer is outside the hardware list, stale 3MFs sit beside the current plates, and a cell swap takes 21 operations plus glue. |
| Aesthetics | 7 | 10 minus one point per failed item (two failed) | Radii from one declared family, no visible wires, cover screws on a grid. Busy parting lines, and the clipped window reads as a dent. |

## Previous issues

| a2 issue | Status | New number |
|---|---|---|
| 1 Overload stop has no reaction | PARTIAL | The pin is seated in the cartridge post at 0.025. The ground is held by the fin at 0.15 in ±y (review slide rows). The gap is 0.25 (ray and nearest). Engagement is still 1.3-5.1 x FS, set by an unknown cell deflection. |
| 2 Sleeve friction | FIXED | No sliding fit. Piston to fin 1.09. Moving link to fin 1.0 (nearest distance, reviewer split). |
| 3 Lost motion | FIXED (model) | Piston blocked at 0.05. Cell faces 0 / 0. Gap stack RSS 0.107. PLA creep under the clamp is still a risk. |
| 4 Stop nut | FIXED | 7.2 AF pocket; nut to piston 9.675. |
| 5 Screw heads, README | FIXED | ISO 4762; counterbores Ø6.5 / 8 / 9.5. The Ø15 washer is new odd hardware. |
| 6 Lip notches | FIXED | Round bore for the last 4 mm (inside probe at y148 is solid). 7.7 mm skin over the teardrop tips. |
| 7 Piston supports | FIXED | Overhang 0 mm², ledge 0. |
| 8 Thread engagement | FIXED | No engagement warns. |
| 9 L-key / spanner | FIXED | Straight bit everywhere; lower M5s at 88 / 100 mm reach with the 150 mm extension. |
| 10 Halves not joined | FIXED | One 305 mm cover, 8 M3 across both trays. |
| 11 Cables | PARTIAL | Lead lengths declared, no kinks. The patch path is 149.97 for a 150 mm cable. |
| 12 Radius family | FIXED | R_out 6, R_in 2, EB 1 declared. |
| 13 Process | PARTIAL | See the list below. |

Details for a2 #13 (process):
- The rows were adapted faithfully:
  - The tongue/pin rays replace "piston to pin".
  - "Top link on the cell", plus "piston on the shoulder", replace "piston on the cell".
  - "Pin in the post" replaces "pin held by the fin". I added the missing half of that claim, the ground held by the fin: 0.15.
- `a2_review_rows_verbatim.json` is a report, not the rows.
- The claim that cad check "can't sweep" the moving link is wrong.
- The flexure stress in the flexures row is typed in, not computed.

## Measurements

| Item | Value | Source |
|---|---|---|
| Stop gap, push / pull | 0.25 / 0.25 | `distances` rays; reviewer nearest-distance row 0.25 |
| Moving link + piston + grip slid ±y, ±z | first hit `FST_Stop_pin` at 0.35 / 0.35 / 0.35 / 0.40 (step lag on a faceted pin) | `cadcheck_review.json` slide |
| Moving link slid ±x | fin at 1.05 | same |
| Moving link to fin, nearest | 1.0 / 1.0 | same, distances |
| Cartridge ground + pin slid ±y | fin at 0.15 | same (adapted a2 row) |
| Leaf pair stiffness | 31-43 N/mm | `scripts/flexure_calc.py` |
| Rear-leaf buckling | 1.1-1.9 kN | same |
| Leaf root stress at the stop | 4.6 MPa nominal; 9-12 MPa with sharp-root Kt; 18-22 MPa at the 0.475 worst case | same |
| Stop engagement / FS for cell FS deflection 0.05 / 0.10 / 0.15 / 0.20 mm | 5.1 / 2.6 / 1.7 / 1.3 (worst case 9.6 / 4.9 / 3.3 / 2.5) | same |
| Moment share through the clamped cell | ~47 % (3.9 N.m at 50 N down; 11.6 N.m at 150 N) | same |
| Moment share with Ø8 seat bosses | 0.8 % | same |
| Interlayer shear in the leaves, 150 N sideways | 11.8 MPa | same |
| Tongue wall under the Ø4.5 hole | 0.58 mm | same, and the `parts` warn (min 1.19 sampled) |
| Overhang > 46° | cartridge 30; piston 0; cover 0; fin 147 / 225; tray 704 / 663 mm² | `scripts/overhang_map.py`; locations listed below |
| Printcheck | max bridge 7.5 on the cartridge; fin 67 mm E-roof, arms anchored | `a3/printcheck/fin_R_inboard_z018.0_bridge.png` |
| Print | 11 parts, ~22 h, 1,118 g, 3 plates (2 x H2D, 1 x P1S), 0 supports | BOM, plates.txt |
| Patch slack | 0.03 mm (path 149.97) | `cables` |
| Cell swap | 21 fastener operations, plus glued stud threads | BOM / README steps |

Where the overhangs are:
- Cartridge: the crowns of the Ø5.5 stud holes.
- Fin: 167 mm² sits on the bed face (recesses); the rest is teardrop and pocket-roof facets.
- Tray: the Ø14 bit-hole crown (345 mm²), the lower M5 hole and counterbore crowns (78 mm²), and the upper M5 crowns (63 mm²).

## Issues

1. **MAJOR (F): the cell is a rigid parallel path for bending.**
   - Both Ø25.4 faces are clamped flat: one onto PLA (front plate plus fin floor), the other onto the top-link wall. So the cell takes about 47 % of the grip moment.
   - A 50 N downward lean puts 3.9 N.m through a 20 kg puck, an edge-load equivalent of 1.6 x FS.
   - Result: false push and turn commands when someone leans on a handle or hangs a bag, and a risk of overload.
   - **Fix:** a Ø8 x 1.0 seat boss on the front plate and on the top-link wall, with 1.0 mm face clearance outside it. The cell's share drops to 0.8 %.
   - Add rows: cell face to boss 0, and cell rim to plate and wall ≥ 0.8.
   - Bench test: hang 5 kg at the grip end; the reading should change by less than 2 % FS.
2. **MAJOR (F): stop gap not sized to the cell.**
   - The gap is a fixed 0.25, with a stack range of 0.025-0.475.
   - The stack also misses the systematic undersize of a printed Ø4.5 vertical hole.
   - With the cell's FS deflection unknown, the stop engages at 1.3-5.1 x FS, against a typical 1.5 x FS safe overload.
   - **Fix:** set stop_gap = 1.2 x the measured FS deflection.
   - Measure it with the HX711: print cartridges with gaps of 0.10 / 0.15 / 0.20 / 0.25 (1.1 h each) and pick the one where the reading plateaus between 1.2 and 1.5 x FS. Or fit 50 kg cells.
   - Add a stacks upper-bound row: gap_max x k_cell ≤ 1.5 FS.
3. **Minor (F): sharp leaf roots.**
   - The roots raise stress by Kt 2-2.5, to 18-22 MPa at the worst-case gap.
   - **Fix:** R1.5 root fillets. Compute the flexures stress instead of typing it in.
4. **Minor (F): PLA creep and heat at the clamp and leaves.**
   - **Fix:** print the cartridge in PETG or ASA (about 30 N/mm, still under 3 % of the cell). Re-torque the cell nuts after 24 h.
5. **Minor (M): stale plates in `cad/print`.**
   - `tonight_*.3mf`, `plate_1/2/3*.3mf`, `plate_H2D_2_tray_R_covers.3mf`, `stl/*_standing`, `stl/cover_L/R`. Printing any of them gives obsolete fins.
   - **Fix:** have export_prints.py clear the folder first.
6. **Minor (M): hardware and tools outside the brief.**
   - The Ø15 M5 washer is not in the user's hardware list.
   - The pin holes are reamed by hand through a compliant tongue.
   - The cell swap takes 21 operations, and superglue sits in both stud threads.
   - **Fix:** a printed Ø15 x 2 washer, or a Ø9 seat so the nut bears directly. Print the post holes at 4.0 and drive the pin in. Use hot glue on the nut faces instead of thread glue.
7. **Minor (F): patch cable has no slack.**
   - **Fix:** a 200 mm patch cable (cable_leads 200, giving 50 mm of slack), or move the coupler 20 mm toward the board.
8. **Minor (A): parting lines and the window.**
   - Each fin top has three parallel seams within 50 mm. The clipped window reads as a dent.
   - **Fix:** move the fin split under the barrel on the inboard side, or add a 1 x 1 V reveal at the seam.
   - Drop the window, or make it a 3 mm deep R6 pocket offset 8 mm from the fin outline.
9. **Minor (process).**
   - **Fix:** have `to_cadcheck.py` emit `PRT_movlink_*` check-only objects (or a split with a ±0.35 prismatic joint), and adopt `review_rows.json`.
   - Move the tongue V tip down 3 mm (tip at z -28, post groove 3 mm deeper). The 0.58 wall under the hole becomes 2.0 mm, and it is loaded by lift overload.
   - Correct the tray overhang note (it omits the M5 crowns), and the "verbatim rows" file.

## Check-config audit

- **allow:**
  - Nut, washer and grip entries: agreed.
  - `PRT_fin × BUY_load_cell` 3 mm³: no longer needed. The measured distance is 0.2 with no overlap. Drop it.
  - `PRT_cartridge × BUY_load_cell` 3 mm³: agreed (zero-gap seats).
- **stacks:**
  - "Overload stop gap" checks only that the gap does not close (lower bound). Add the upper bound against the cell (issue 2).
  - The Ø4.5 hole tolerance of 0.05 is optimistic for a printed vertical hole, which typically comes out 0.1-0.2 undersize.
  - "Top link to fin cavity": agreed.
- **flexures:** the orientation is right: leaves in the layer plane, angle 0. The stress is an input, not a calculation, and Kt is ignored.
- **Missing rows:**
  - The moving-link sweeps (now in `review_rows.json`).
  - Cell face and rim rows, once issue 1 is fixed.
  - A slack row for the patch cable.
- **assembly_order:** matches README steps 1-18. Every part is in a step (`assembly.step_of`).

## What is good

- The sliding fit is gone.
- The stop's reaction path is short and all inside one printed part: the pin is seated at 0.025, the ground is held at 0.15, and the moving link clears everything else by 1.0.
- The leaves bend in the layer plane, and buckling has a margin of 1.1-1.9 kN.
- Zero supports on every part.
- The overhangs I located are all short-span crowns or 45° facets.
- `cad bom` PASS.
- Every a2 tool complaint is resolved.
- One cover now ties both halves together.
