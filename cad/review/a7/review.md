# Review: space-bar push assist, attempt 7

Checks re-run:
- Main check: CADCHECK PASS, 0 fail, 51 warn (0 untriaged). The warn set is identical to `cadcheck_a7.json`.
  - Coverage: parts, interference over 123 objects in all four collections, fasteners (61 screws, 24 nuts, 19 steps), service, 13 slides, 35 stacks, 6 flexures, 5 cables.
  - Not checked: pilot/clearance diameters, wrench access to nuts, insertion of parts within the same step, cable slack.
- Moving rows: PASS, 0 fail, 0 warn.
- printcheck on `cad/print/stl`: PASS, 18 parts, 0 fail, 20 warn.
- cad bom: PASS, 13 rows.
- Review rows (`review_rows.json` -> `cadcheck_review.json`): 5 FAIL, 1 PASS.

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 4 | ≤4, parts can't be assembled | The load cell can't be fitted: the stud slots open 3.2 mm across the motion for a 4.9 mm stud. Everything else works. About 7 once fixed |
| Manufacturability | 4 | ≤4, parts can't be assembled | Same blocker, also on the exported STL. Otherwise clean: 0 fails, no supports, 26.4 h, no iron. About 8 once fixed |
| Aesthetics | 9 | 9, all items hold | Exterior unchanged from a6. The cover heads still read as black holes |

## Previous issues
| a6 issue | Status | New number |
|---|---|---|
| 1 setting-plug lip 2.1 mm | FIXED | 7.24 / 9.05 MPa (limit 12; a6 17.23 / 21.54) |
| 2 soldering iron | FIXED | Qwiic Scale has a solderless spring terminal (SparkFun page). Male pins on the ESP32 board not verified |
| 3 lean crosstalk | FIXED | 0.000 % re-derived; 0.04 / 0.10 % for a 0.2 / 0.5 mm height error |
| 4 sketch gate and sign | FIXED | `m` gated (lines 356-361); `c` stores the pull as negative (311); f/r/c reset the check; PASS window 0.88 |
| 5 lip friction, 150 N lean limit | PARTIAL | Catch lands at 130-183 N. Its friction shunt is 13.2 / 33.0 N, not 3.3 / 8.3 |
| 6 docs (step4, buckling margin) | PARTIAL | step4 fixed. Past-contact model wrong: rear strips 929-1416 N, ×3.1-4.7 (claimed ×9.4) |
| 7 known-mass rig | FIXED | Rows 11.7 MPa, 1.35 MPa, offset 0 |

## Measurements
| Item | Value | Source |
|---|---|---|
| Stud slot opening at the inboard face, across the 45° motion | 3.2 mm (stud 4.9) | `cad q inside` at x 158.3, y 44/62.5, z -13..-8; `scripts/stl_inside.py` on the STL |
| Nut channel opening, across the motion | about 6.7 mm (nut 9.24 AC, washer Ø13) | `cad q inside` at y 67; slide row blocked at 24 mm |
| Cell path with the stops already in | blocked at 4 mm by a push screw | a7R slide row |
| Lean crosstalk | 0 (0.102 % at 0.5 mm error) | `scripts/head_a7.py` |
| Catch contact | 130-183 N (designer 147-206) | head_a7 |
| Share past contact, per extra N | front -1.86, rear +1.02…1.94, catch +1.06…1.84 | head_a7, three supports |
| Rear strips at 600 N | 929-1416 N vs 4407 N buckling | head_a7; row PASS 1345 < 1469 |
| Catch leg y-stiffness | free with offset 10.2, 3EI/L³ 27.5, guided 110 N/mm | head_a7 |
| Friction shunt | 13.2 N (dFS 0.10) / 33.0 N (0.30 setting) | rows FAIL vs 10 |
| Piston at 600 N on the catch | 52.3 MPa (×1.45 on 76 MPa) | head_a7, designer row |
| Push couple in the leaves | ±373 N at 589 N | head_a7 |
| Side load, 20 N | 0.17 FS (row 0.185, limit 0.2) | head_a7 |
| Stop stiffness / cell at 600 N | 7.2-7.5 kN/mm; 50 kg 1.19 × FS; 20 kg (dFS 0.10) 1.56 × FS | head_calc 3d terms, my re-solve |
| Washer across the slot at 1.2 × FS pull | about 35 MPa (estimate) | row FAIL vs 20 |
| Leaf bridge start | 26.7 mm span, 2.5 wide, anchored 0.97 | printcheck |
| Overhang >45° (STL) | cartridge 685, cradle 551, fin 3991, tray 843 mm²; plug, piston, hanger, cover 0 | `scripts/steep_strip.py` |
| Print | 18 parts, 26.4 h, 4 plates (2 H2D, 2 P1S), 0 supports | BOM, plates.txt |

## Issues
1. **Blocker (F, M): the cell cannot be fitted.**
   - Cause: `stud_slot()` uses d = (cart_hw+8)/√2 = 19.8 as both its x and z offset. The slots end 0.2 mm inside the inboard face, with a wedge of material over the exit.
   - Openings across the motion: 3.2 mm for the stud (needs 4.9) and about 6.7 mm for the nut (needs 9.24).
   - Fix: d = cart_hw + half + 1 (23.75 for the stud slots, 28.2 for the nut channel). Check the cut against the link corner, adopt the a7R slide row, and reprint both cartridges (3.2 h).
2. **Major (F): the catch friction shunt is 13-33 N, not 3.3-8.3.**
   - Under load the saddle is held square, so the legs work fixed-guided at 110 N/mm.
   - Fix: an R1.2 crown on the saddle face across y. The legs then work as free cantilevers at 10.2 N/mm, so the shunt is 1.2-3.1 N. Update the catch_k formula to match.
3. **Minor: the past-contact model is wrong.**
   - The rear strips keep loading: 929-1416 N at 600 N, ×3.1-4.7 to buckling, not ×9.4.
   - Fix: use the three-support solve in head_calc 4.
4. **Minor: the 1.6 mm washers bridge the 5.5 mm slot** (about 35 MPa at 1.2 × FS pull).
   - Fix: 2.4 mm washers. The 12.15 mm stud still reaches (11.4 mm stack). Or print them in PETG.
5. **Minor: the catch gap is 0.10 mm, and pull pitch uses 0.072 of it.**
   - 36 N of extra lean touches the saddle at full pull.
   - Fix: the crown from #2, plus a "slides through by hand" check in the README.
6. **Minor: piston at 52 MPa at 600 N** (×1.45).
   - Fix: 100 % infill with 6 walls or PETG, or move the catch to y 139 (46 MPa).
7. **Minor: the `assembly_order` text puts the stops before the cell.**
   - The row shows the cell is blocked at 4 mm if the stops go in first. Reorder the text to match the README.
8. **Minor: unverified purchased parts.**
   - The Qwiic Scale footprint comes from a forum post only.
   - Male header pins on the Waveshare board are not confirmed. The two-I2C-port plan is valid.
9. **Minor (A): the cover heads read as black holes.**

## Check-config audit
- `allow PRT_cartridge_*>BUY_load_cell_* max_mm3=3` (seat contact) is agreed for interference. It also blinds every slide row on the cell, though, which is how blocker #1 got through. Add the rear-nut/washer row, which has no allow.
- `assembly_order[3]`/`[9]` text order is disputed (issue 7).
- The catch_k row is disputed: wrong bound (issue 2).
- `catch_load_600` and the README ×9.4 are disputed (issue 3). The leg row stays conservative.
- The a6R crosstalk rows were adapted correctly. The verbatim a6 rows are stale (hard-coded a6 geometry).
- No missing drop tests apply (this is a force sensor). Stability was skipped, as agreed, because the unit is bolted to the chair.

## What is good
- **Lean crosstalk:** the cell on the leaves' mid-height is a real fix, and it re-derives to zero.
- **Bench rig:**
  - The plug lip, hanger and eye are done properly.
  - The sketch gate and sign logic are right.
  - The NAU7802 count constant is consistent with the chip's ±0.5 VREF/gain range.
- **Soldering:** none is needed on the cell side.
- **Checks:** zero cadcheck fails, and the warn set matches the designer's exactly.
- **Printing:** every part fits its plate and none needs supports.
- **Exterior:** unchanged and still clean.
