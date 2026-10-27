# Review: space-bar push assist, attempt 5

Checks re-run: main `cad check` PASS 0 fail, 47 warn (all 47 accepted; the warn set matches cadcheck_a5.json exactly). Moving-link and bench rows PASS 0/0. `cad printcheck` on cad/print/stl: PASS, 17 parts, 0 fail, 16 warn. `cad bom` PASS, 14 rows. Reviewer rows (`review_rows.json` -> `cadcheck_review.json`): 2 FAIL, 2 pass.
(coverage: parts 17, interference 118 objects in all four collections, fasteners 57 screws / 24 nuts, service 3 ops, slide 13, assembly 19 steps with 0 parts in no step, insertion 36, stacks 12, flexures 4, cables 5; not checked: pilot diameters, wrench access to nuts, non-straight insertion, teardown count, aesthetics, BOM correctness.) No cad tool rewrote a file outside cad/review/a5/. I passed `--out` to printcheck, so stl/printcheck.json is unchanged.

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 8 | 8: works, 2 majors with fixes under 1 h | The stops are on the axis, the lip catch works and the leaves have a 5x margin. But the stops of the recommended 50 kg cell can't be set with the cradle as drawn, and the README never sets the cell's mV/V |
| Manufacturability | 6 | 6: a single blocker caps it | With the recommended cell, the stop-setting step fails: the cradle upright sees 54 MPa across layers and the jack stroke runs out. Otherwise 0 fails, no supports, brief hardware |
| Aesthetics | 9 | 9: every rubric item true, polish only | The tray seam now has a V reveal, the coupler is inside the tray, and one radius set is used throughout |

## Previous issues (a4)

| a4 issue | Status | New number |
|---|---|---|
| 1 Stop line 24 mm below the cell axis | FIXED | Push contacts at z 0. Adapted lean row 0 (a4: 0.475), jack-couple row 0.083 (a4: 0.363). Caveat: the cradle upright tilts the jack 2.5-7.6 deg (new #1) |
| 2 Rear leaf buckles with no vertical stop | FIXED | Buckles at 970-1357 N per grip (a4: 338-578). Lip contact at 181-254 N (my lever; designer 158-221). Leaf margin x5.3 at contact; push heads lift 0.13 of 0.5 |
| 3 20 kg cell overloaded | PARTIAL | Stop path 6.0-7.6 kN/mm (a4: 2.3). 20 kg still 1.44-1.92 x FS at 600 N. 50 kg (recommended) 1.18-1.21 x FS, but see new #1 |
| 4 Step-14 re-snug unreachable | FIXED | Re-snug moved to the bench. Verbatim a4 rows fail by design (piston at 3 mm, fin at 1 mm); adapted bench rows pass |
| 5 0.5 N.m snug unmeasurable | FIXED | Finger-tight, 100-200 N, 1.8-3.7 MPa on the boss; creep term 0.006 mm |
| 6 Moment share low end | FIXED | 2.2-7.0 % including the stud path; bench pass marks follow from it |
| 7 Tray seam and hanging coupler | FIXED | V reveal visible in 01_hero; coupler at z -63..-27, floor at -67 (a4: -76) |
| 8 Live-electronics bench step | PARTIAL | Cradle, plug, on-axis jack and sketch delivered. The cradle is undersized (new #1) and the mV/V step is missing (new #2) |

Do the adapted rows test the same claims?
- Lean and jacking rows: yes. The jacking row assumes a rigid cradle, though, and the cradle is not rigid.
- Step-14 rows: they now test bench access. That is a different claim, and the right one, because the step moved to the bench.
- ±z rows: these moved from "the fin cavity at 1.0" to "the lip at lip_c". Translation stands in for pitch, which is acceptable: the push heads move only 0.13 mm at contact, against 0.5 mm of clearance.

## Measurements

| Item | Value | Source |
|---|---|---|
| Stop path per pair | 6.0 kN/mm (shared PLA path in series), designer 7.6 | head_check_a5.txt A |
| 20 kg cell at 400 / 600 N | 1.30-1.52 / 1.44-1.92 x FS (dFS 0.20-0.05) | A |
| 50 kg cell at 600 N | 1.18-1.21 x FS (engages at 588 N) | A |
| Side load: one push screw closes | 0.017 / 0.042 / 0.083 mm at 20 / 50 / 100 N (0.17 / 0.42 / 0.83 FS at dFS 0.1) | B; designer row 0.166 |
| Leaf buckling | 3249-4549 N, i.e. 970-1357 N down per grip | C |
| Leaf root bending | 4.7 / 9.3 / 11.7 MPa at 0.12 / 0.24 / 0.30 mm travel; flexures row 21.1 MPa (with 150 N lean) | C; cadcheck flexures |
| Lip contact | 181-254 N (link only 596-835 N) | D |
| Piston at 300 / 600 / 800 N lean | 20 / 40 / 54 MPa; lip reaction 2.74 x lean | D |
| Lean crosstalk | 3.8 % of the vertical load (5.7 N at 150 N) | E; row a5R crosstalk |
| Cradle upright at 1.2 FS, 20 / 50 kg | 22 / 54 MPa across layers; tip 1.45 / 3.6-4.4 mm; jack tilt 2.5 / 6.4-7.6 deg | F; rows a5R cradle |
| Jack stroke needed (50 kg) vs available | 4.47 mm vs 3.0 | row a5R jack stroke; warn FST_Jack_screw |
| Clamp creep vs stud stretch | 6 um vs 0.4-0.8 um, so preload is lost over life; leaves take only 0.7 N across the gap | G |
| Fin roof spans | 7 / 10.7 / 16 mm, anchored on both sides (the tool's 59.9 / 76.5 / 32.1 mm is strip length) | scripts/layer_ascii.py z 18.2, 19.2 |
| overhang_gt_45 (mm²) | cartridge 159, cradle 154, fins 97-138, trays 824-875 (bed strips z 0-5), others ≤ 0.1 | cadcheck parts; steep_strip.py |
| Print | 17 parts + 2 bench tools, 0 supports, 24.3 h, 1211 g, 4 plates (2 H2D, 2 P1S; cover 305 mm is H2D only) | BOM, plates.txt |
| Long reach | board screws 2/3 at 104 mm, M5 bolts 4/5 at 98 mm (150 mm extension in the kit) | cadcheck warns |

## Issues

1. **Blocker (M) / major (F): the cradle cannot set the stops of the recommended 50 kg cell.**
   - Geometry: the rear upright is a free-standing 50 x 8 mm plate printed vertically. The side walls stop 42 mm short of it (slices at print z 9-50). The jack axis is 49.1 mm above the base.
   - Load at 1.2 x FS (589 N): 54 MPa across layers at the root and 56 MPa in the 7.9 mm base (row FAIL, 54.2 > 25).
   - Stroke: the upright tip moves 3.6-4.4 mm, but the jack head is only 3.0 mm off the upright, so the jack bottoms first (row FAIL, 4.47 > 3.0). The jack also tilts 6-8 deg, so it is no longer on the axis.
   - With a 20 kg cell: 22 MPa, and 27 MPa when README step 7 turns the jack on to about 150 %.
   - Fix:
     - Run both 6 mm side walls through to the upright, up to z -8, with 14 x 10 key windows. The load path is then in the layer plane: about 1.2 MPa in the walls and about 11 MPa in the upright.
     - Make the upright 10 mm thick.
     - Use an M5 x 30 jack.
     - Add R3 root fillets.
     - Reprint the cradle (1.6 h).
2. **Major (F): the README never sets the cell's mV/V.**
   - The sketch defaults to 1.0 mV/V. Step 4 is only `f 20`, `t`, and README.md has no mention of mV.
   - A 1.5 or 2.0 mV/V cell gets its stops at 80 % or 60 % of real FS. A 20 kg cell would then clip at 118 N.
   - Fix: step 4 becomes `f`, then `r <label mV/V>`, then `t`, then a known 10 kg check (50 % or 20 % ±3 %, else `c 10`). The sketch should refuse `m` until `r` or `c` has been given.
3. **Minor (major with a 20 kg cell): the 20 kg cell's residual risks.**
   - 1.44-1.92 x FS at 600 N.
   - 50 N of side load brings the push stop in at 154 N.
   - Fix: commit to the 50 kg cell once #1 is fixed.
4. **Minor: lean crosstalk of 3.8 %.**
   - The leaf tops sit 15 mm below the cell axis. When the link pitches, the leaf shear can only leave through the cell, so 150 N of lean reads as 5.7 N of axial force. head_calc doesn't model it.
   - Fix now: a firmware dead band of at least 10 N, with the coefficient recorded from the 5 kg bench check.
   - Fix at the next cartridge print: centre the leaf mid-length on the cell axis (leaf tops at z +13.5).
5. **Minor: head_calc section 4 uses the wrong lever.**
   - It levers the link pitch about the cell centre (96 mm) instead of the leaf centroid (64.5 mm).
   - Contact moves to 181-254 N. The conclusion stands.
6. **Minor: a cell swap needs a soldering iron.**
   - The lead is soldered to the HX711's JP4, and a soldering iron is not in the tool list.
   - Fix: an HX711 with a 4-way screw terminal, driven with a flat bit.
7. **Minor: lip friction above a lean of about 180-250 N.**
   - The piston reaches 40 MPa at 600 N.
   - Fix: keep the README's 150 N limit. Optionally add a PTFE tape band on the piston at y 146-150.
8. **Minor: stale text and a tool crash.**
   - The flexures row text says "R1.5 root"; leaf_r is 2.0.
   - check_stacks crashes on a missing param under `--only stacks` (a skills-repo bug, not the design).

## Check-config audit

- **allow/fits:** no `unbounded_allows`, no poses past limits.
- **Accepted warns:** all 47 agreed:
  - Fin bridges: verified as anchored 7-16 mm spans.
  - Cable overlaps: 5-25 mm³ at the plug ends.
  - Push-screw head stand-off: by design, because the head is a stop and is not clamped.
  - Long-reach screws: the 150 mm extension is in the kit.
- **Disputed:**
  - The adapted jacking row (0.083) assumes a rigid cradle. With the real upright the jack tilts 2.5-7.6 deg; see #1.
  - The flexures row text is stale.
- **Missing rows:** none for cradle strength, jack stroke or crosstalk. They are now in a5/review_rows.json for the designer to adopt.
- **assembly_order:** matches README steps 1-12. The re-snug and the stop setting sit inside step 1, on the bench.

## What is good

- The stops are on the cell axis, with the jack on the grip axis too. The a4 lean failure is gone: the lean row reads 0, against 0.475 in a4.
- The lip catch gives a real vertical and moment stop. The leaves have a 5x margin to buckling at contact.
- The cartridge is self-contained and is settled and set on the bench. Nothing in it is touched again inside the fin.
- The prints need no supports. The fin roofs are short bridges anchored on both sides.
- All hardware stays inside the brief, including the printed washers.
- The bench sketch is clean and needs no libraries.
- The tray reveal and the recessed coupler finish the form. The hero view reads as one designed body.
