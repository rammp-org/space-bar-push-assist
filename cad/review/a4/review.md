# Review: space-bar push assist, attempt 4

Checks re-run: `cad check` (designer `--only`) **PASS 0 fail, 39 warn (all accepted)**, with a warn set identical to
`cadcheck_a4.json`. Designer moving-link rows: PASS 0/0. a3 `review_rows.json` verbatim: 16 FAIL. Two rows name the
deleted stop pin; the other 14 are stopped by the new rear washer and stop nuts, which the a3 rows don't list.
Reviewer rows: 5 FAIL, 1 WARN. `cad printcheck cad/print/stl`: PASS, 15 parts, 0 fail, 24 warn. `cad bom`: PASS, 11 rows.
The slicer is unusable (known segfault).
Coverage: parts, interference (99 objects, all 4 collections), fasteners (48 screws, 16 nuts), service (3 ops), slide
(11), assembly (18 steps, 0 unplaced), insertion, stacks (6), flexures (4), cables (5). Not checked: wrench access to
nuts, non-straight insertion, teardown count, aesthetics, BOM correctness. Stability was skipped (the unit is bolted to a chair).

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 7 | 3 or more majors | The stop line sits 24 mm below the cell axis; the rear leaf buckles at 340-580 N down with no vertical stop; a 20 kg cell is still overloaded past the stop |
| Manufacturability | 8 | at most 2 majors, fix under 1 h | 0 fails, no supports, hardware in the brief; README step 14 is unreachable |
| Aesthetics | 8 | 2 items fail | Tray centre seam on the attendant face; RJ45 coupler hangs under the bridge |

## Previous issues
| a3 issue | Status | New number |
|---|---|---|
| 1 cell takes 47 % of moment | FIXED | Ø10 bosses, rim 1.0 clear; 1.9 % (designer), 2.9-6.7 % (my model, adds the half-space and the stud path) |
| 2 stop gap not sized to cell | PARTIAL | set per cell, but it engages at 1.40 x FS (dFS 0.1) to 1.60 x FS (dFS 0.05); 600 N gives 2.0-2.55 x FS |
| 3 sharp leaf roots | FIXED | R1.5; 19.0 MPa computed and reproduced (6.2 bending + 7.8 axial, x Kt 1.35) |
| 4 PLA creep / heat | PARTIAL | printed washers 3.3/4.6 MPa; boss 9.1 MPa only at 0.5 N.m, which can't be set; re-snug unreachable |
| 5 stale 3MFs | FIXED | 3 current 3MFs + plates.txt only |
| 6 hardware outside brief | FIXED | no bought washer, reamer or thread glue; 21-op cell swap remains |
| 7 patch slack | FIXED | 200 mm lead on a 149.97 route |
| 8 parting lines / window | FIXED | V reveal, one hairline, recessed R6 panel |
| 9 moving-link process | FIXED, one claim weakened | movlink built from the cartridge functions; the ±z rows changed from "stop at 0.25" to "fin backstop at 1.0" |

## Measurements
| Item | Value | Source |
|---|---|---|
| Stop line below cell axis | 24 mm (cell z 0, screws z -24) | `cad q list` on check_moving.blend |
| Leaf pair rotational stiffness | 6.8e6 N.mm/rad (E 3000) | head_check.py |
| Extra gap from jacking couple | 0.017-0.024 mm, so it engages at 1.40 x FS (dFS 0.1) / 1.60 (0.05) | head_check.txt s2 |
| Push stack with that term | worst 0.363 > 0.3 | cadcheck_review.json stacks |
| Gap eaten by downward lean | 0.048 mm at 100 N; push clips at 0.93 / 0.65 x FS | head_check s3; stack row 0.475 FS > 0.2 FAIL |
| Cell at 600 N shove | 2.55 / 2.21 / 2.00 x FS (dFS 0.05/0.1/0.15) | head_check s4 |
| Rear-leaf buckling, per grip | 338-578 N down; elastic drop 0.27 mm vs 1.0 backstop | head_check s5 |
| Moment share | 1.9 % (designer) / 2.9-6.7 % | head_check s1 |
| Boss stress | 9.1 / 18.3 / 27.4 MPa at 0.5 / 1 / 1.5 N.m | head_check s6 |
| Stop gaps modelled | 0.15 / 0.15; moving link stops at 0.2 on each screw | cadcheck distances, cadcheck_movlink slide |
| Cell faces | 0 / 0 on bosses, 1.0 rim clear (x6) | cadcheck distances |
| Rear nut re-snug | blocked by piston at 3 mm | review slide row |
| Front nut re-snug | blocked by chair back plate at 34 mm | review slide row |
| overhang_gt_45 mm² | cartridge 44, fin 108/147, tray 702/733, others ≤ 0.1 | cadcheck parts |
| Steep faces located | tray: 2 bed-edge strips (52-54°, z 0-5, ~110 mm²) plus hole and boss crowns; fin: E/C roofs at z 18-19 | scripts/steep_strip.py, printcheck layer maps |
| Print | 15 parts, 22.4 h, 3 plates, 0 supports | cadcheck est_h, plates.txt |

## Issues
1. **Major (F). The stop line sits 24 mm below the cell axis.** The bench setting jacks the tongue, so the leaves twist
   and the set gap is 0.02 mm too large. The stop then engages at 1.40-1.60 x FS instead of 1.2. In use, 100 N down on
   the grip moves the tongue 0.048 mm toward the push screw, so pushing uphill while leaning clips at 0.65-0.93 x FS.
   *Fix:* put the stop on the cell axis: two lugs on the link side walls at z 0, x' ±15 (6 x 8), each with a
   push/pull M4 x 8 pair in the post side walls. As a stopgap, set the stops with a 24 kg load hung on the piston
   socket, on the axis.
2. **Major (F). The rear leaf buckles at 338-578 N down per grip.** Leaf load is 3.32 x the grip load. Buckling
   starts after 0.27 mm of drop and the fin backstop is at 1.0, so nothing catches a heavy lean. a3's pin did.
   *Fix:* leaf_t 2.0, which gives 1174 N per grip, 104 N/mm and 11.2 MPa at a 0.30 setting. Or set the piston-to-lip
   clearance to 0.35 as a moment stop.
3. **Major (F). A 20 kg cell still reaches 2.0-2.55 x FS at a 600 N shove** (1.6-1.9 at 400 N). *Fix:* fit the 50 kg
   cell, or thicken the post slab in front of the nut from 3.45 to 6 mm (about 3.5 kN/mm), together with fix 1.
4. **Major (M). README step 14 can't be done.** The rear nut sits under the piston inside the closed fin, and the front
   nut bore faces the chair plate (review rows). *Fix:* do the 24 h settle and re-snug on the bench before setting the
   stops, or delete the step.
5. **Minor (M/F). The 0.5 N.m snug can't be measured with the kit.** Boss stress is 18-27 MPa at 1-1.5 N.m. The bosses
   sit in the post-to-tongue chain, so creep moves the stop. *Fix:* specify finger-tight + 60°, and add a creep term to
   the stop stacks.
6. **Minor (F). The moment share is 2.9-6.7 %, not 1.9 %, once the stud path is included.** *Fix:* add the stud path to
   head_calc.py and set the 5 kg bench-check limit from measurement.
7. **Minor (A). The tray centre seam shows on the sloped attendant face, and the coupler hangs 9 mm below the floor.**
   *Fix:* a 0.8 x 1.0 V reveal on the seam; recess the coupler into a 34 x 30 x 10 floor pocket.
8. **Minor (M). The stop setting needs a live, calibrated HX711 on the bench, and again at every cell swap.**
   *Fix:* a bench serial sketch in the repo and a printed cartridge cradle.

## Check-config audit
- `checks_moving.json`: the push/pull, sideways and ground rows test the a3 claims with the new parts (agreed). The ±z
  rows weaken the claim from a stop at 0.25 to a fin backstop at 1.0, and that backstop can't protect a leaf that
  buckles at 0.27 mm (disputed).
- `stacks` push/pull rows: they leave out the jacking-couple term (+0.20 FS at dFS 0.1) and boss creep (disputed). The
  lean case has no row (added in review_rows.json).
- `service`: there is no op for README step 14 (added as slide rows).
- `flexures`: the 19.0 MPa row is computed and agreed. There is no buckling check (see issue 2).
- `accepted_warns`: all 39 agreed. The tray overhang reason leaves out the two 52-54° bed-edge strips (~110 mm²), which are harmless.

## What is good
- The a3 moment path is fixed in geometry and in rows: the cell faces sit on bosses with the rim clear.
- The moving-link split is now built from the same functions as the cartridge and swept in cad check.
- The stops are adjustable, use only brief hardware, and the cell itself is the gauge. It's a good idea; only the
  stop line's height is wrong.
- No supports, 0 printcheck fails, all hardware in the brief, BOM matches the model.
- Form: one hairline at fin/tray/cover, a deliberate reveal, a recessed panel that follows the outline, radii from one
  set (R_out 6, R_in 2, EB 1).
