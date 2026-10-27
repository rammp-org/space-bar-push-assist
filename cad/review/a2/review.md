# Review: space-bar push assist (round 6 wedge unit), attempt 2

Checks re-run on a copy of `check.blend` (`cad/review/a2/cadcheck.json`, same `--only` as the designer): `CADCHECK PASS: 0 fail, 35 warn (35 untriaged)`. This is identical to `cad/review/cadcheck_a2.json`.

- Coverage: parts (10), interference (88 objects in all four collections; `joints swept []`, so there are no joints), fasteners (42 screws, 14 nuts), assembly (8 steps, 0 unplaced), insertion (29), cables (5 routes).
- Not checked: service access, hole diameters, wrench access, flexures (none declared), cable lead lengths, BOM.
- `checks.json` has no `distances`, `slide_out`, `service`, `stacks` or `flexures` rows. Five of the eleven checks in the designer's `--only` therefore checked nothing.
- Printcheck on `cad/print/stl_cc` (`cad/review/a2/printcheck.json`): PASS, 0 fail. Only the pistons need support.
- Reviewer rows (`review_rows.json` → `cadcheck_review.json`): **5 fail, 1 warn**.
- `cad bom`: PASS, 7/7 rows.
- No slicer: `cad slice --detect` reports that the Bambu Studio CLI segfaults.

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 5 | Blocker in the core function | The overload stop has nothing to push against. The pin moves 0.75 mm before it touches the fin, so the push stop is at about 1.15 mm, far past the cell's full-scale deflection. The stop nut also sits 0.3 mm into the sliding piston. On top of that, sleeve friction is 0.37-1.1 x the vertical hand load. |
| Manufacturability | 6 | Significant risk of rework at assembly | The stop nut has no pocket: it falls out when the outboard half goes on, and it binds the piston when snugged. The screws are hex socket caps, but the lab stocks hex head. Four screws need an L-key. Four thread engagements are short. Both pistons need supports. |
| Aesthetics | 6 | Capped at 6 by an unfinished element in a hero view | The sleeve-bore teardrop tips show as open wedge notches beside each piston on the lip face. There is still no radius family. |

## Previous issues

| # | Attempt-1 issue | Status | New number |
|---|---|---|---|
| 1 | Tray cavity deletes every boss | PARTIAL | The bosses now survive the cavity cut (`hollow` cut before `add`). M5 and M4 heads stand off 0.0 mm, the HX711 screws get 6.0-6.5 mm of thread, the rear cover screws 7.5 mm, and the RJ45 pad is present. Still short: the 4 ESP32 screws get **2.5 mm** (6 needed) and the 4 front cover screws get **5.0 mm** (fasteners warns). |
| 2 | Mount: 20 mm lever, 1.7 kN in two M5 | FIXED | The lever from the foot to the upper M5 row is now **75 mm**, with a lower M5 + foot at x ±120. Tray and fin touch the plate (`dist` 0.0). Hand calc: about 460 N in the upper pair at 150 N on one grip. The lower M5 x 25 engages only **2.88 of 3.8 mm** of its T-nut. |
| 3 | No overload protection | NOT FIXED (in effect) | A pin stop was added. The piston hits the pin at **0.40 mm** (slide row), but the pin then moves **0.75 mm** before any fin contact (slide row: `blocked_at_mm=0.75`). No fin material sits beside the pin from x 153 to 201 (`cad q inside`). See issue 1. |
| 4 | Sleeve friction and key-rib fillet | PARTIAL | The sleeve is 60 mm (was 45) and the rib is gone. Friction factor: (2·79.5+60)/60 = **3.65 F**, which gives 0.37-1.1 F at mu 0.1-0.3 (was 0.46-1.37 F). There is still no prismatic joint and no fits rows. |
| 5 | README hardware vs model and stock | PARTIAL | BOM and steps now match the model (`cad bom` PASS). Still wrong: the README hardware table says "M8 button heads"; the README says "no supports" while its plate table lists piston supports; the screws are hex socket caps while the lab stocks hex head; an 8 mm spanner and a Ø15 washer are needed but not in the kit. |
| 6 | Spigot printed standing | FIXED | The piston prints on its side, layers along the spigot (`print_rot` about Y). The cost is supports under 130 mm of spigot. |
| 7 | Rear M5 nut needs a 180 mm reach | FIXED | The nut is captive in an 8.5 AF pocket with a side slot. The new cost: the pocket is 5.0 deep for a 4.2 nut, so the nut has **0.8 mm** of axial play (see issue 3). |
| 8 | Cover lift and cell-swap teardown | PARTIAL | The cover lifts straight up (slide row passes, 0.00 mm to `cover_L` at the butt joint). A cell swap is still about 20 operations: 4 cover screws, 3 M4, 6 M3, pin and nut, front nut, the glued piston thread, the grip, and the lead off the HX711. |
| 9 | No cable lengths; patch kink R2.8 | NOT FIXED | No lead length on any of the 5 routes. The patch cable kinks at **R2.7** (cables warn). |
| 10 | No radius family; irregular cover holes | PARTIAL | The cover screws are now a 2 x 2 grid per half at x ±40/±120 (fixed). The radii are still 0.5/1/1.5/2/4/6/8/10/12, and manifest `params` is `{}`. |
| 11 | Process: stale renders, wrong hosts, untriaged warns | PARTIAL | Renders refreshed and board-screw hosts fixed. Not done: 35 warns untriaged, and none of the a1 `review_rows.json` adopted. |

## Measurements

| Item | Value | Source |
|---|---|---|
| Stop pin: piston pushed -y | blocked by `FST_Stop_pin_R` at 0.40 mm | review row slide "piston R pushed forward…" |
| Stop pin: pin + nut pushed -y | first fin contact at 0.75 mm (`PRT_fin_R_inboard`, head in the cbore) | review row slide "stop pin R pushed forward…" (FAIL) |
| Fin material beside the pin (y 122.6, z 0) | none from x 153 to 201; only the pin, the piston and the nut | `cad q inside x,122.6,0` for x = 153..202 |
| Wall from the sleeve-bore teardrop tip to the fin face | 1.34 mm inboard and 1.24 mm outboard, over y 89.5-151 | `ray 152.9,110,0 1,0,0` → 154.139; `inside 155,110,0` = [] |
| Stop nut vs piston | -1.511 mm³ overlap at y 121.5-128.5, \|z\| 2.6 (row: 0.094 nearest) | `cad q dist FST_Stop_nut_R PRT_piston_R`; review distances row FAIL |
| Piston face to cell rear face | 0.201 mm (floats; README says "seat") | review distances row FAIL |
| Rear M5 nut in its pocket | nut y 96.2-100.4 in pocket y 96-101, 0.8 mm axial play | `cad q list BUY_rear_nut_R`; build `rear nut pocket` |
| Sleeve radial clearance | 0.296 / 0.302 mm; sliding length 60 mm | `dist PRT_piston_R PRT_fin_R_inboard/outboard` |
| Grip lever | grip y 162-297, centre 229.5, 79.5 mm past the lip | `cad q list BUY_grip_R` |
| Mount lever | upper M5 at u +5.9, lower at u -54.9, foot bottom at u -69.4: 75 mm | `mount_bolts()`; fasteners rows |
| Tray/fin to plate | 0.0 at the land (z ≈ 12) | `dist PRT_tray_R / PRT_fin_R_inboard BUY_corpus_back_plate` |
| Thread engagement | ESP32 2.5/6, front cover 5.0/6, M4 2.6/3.2 nut, lower M5 2.88/3.8 T-nut | fasteners warns |
| Tool access | M4 `*2` and M5 bolts 4/5 need an L-key (15.5 mm); the rest are straight bits, reach 14-28 mm | fasteners `access` |
| Piston overhang | 2623 mm² >45°: spigot 2211 mm² (supported), Ø33 body 821 mm². The body overhang faces the bore's V-tip void (1.75 mm clearance at 22°, 0.36 mm at 40°), so it does not bind. Printcheck flags only the spigot. | cadcheck parts; `scripts/piston_body_overhang.py` |
| Fin and tray overhang warns | fins: flat bridge ceilings ≤ 13.7 mm (nut void 20 x 14, boss pocket 6.4, nut slots 7.5); trays: crowns of horizontal round holes (Ø4.5, Ø5.5, Ø8, Ø11). All printable. | `scripts/overhang_map.py`; printcheck max bridge 13.5 |
| Print | 10 parts, 3 plates (2 H2D, 1 P1S), est **19.3 h**, **981 g**; 2 parts with supports | cadcheck parts `est_total_*`; plates.txt |
| Fasteners | 42 screws (7 kinds) + 14 nuts + 6 cell nuts and washers | manifest `fastener_summary`; BOM |
| Cables | 5 routes, 0 exposed samples, no lead lengths, patch kink R2.7 | cables rows |

## Issues (ranked)

1. **BLOCKER (F): the overload stop has nothing to push against, and its nut rubs the sliding piston.**
   - **Where the material went.** The sleeve bore is a teardrop whose ±x tips (16.8·√2 = 23.76 mm) reach 1.3 mm from both fin faces along y 89.5-151. The stop pin's Ø8 counterbore (to 157.3) cuts through the inboard skin, and the "stop nut pocket" lies wholly inside the tip void.
   - **Effect in push and pull.** No fin material touches the pin on either side (`inside` probes). The piston reaches the pin at 0.40 mm, and the pin then travels another 0.75 mm before its head reaches a crescent of cbore wall at most 1.3 mm deep. The push stop is therefore at about 1.15 mm. A 20 kg puck reaches full scale at about 0.1-0.2 mm, so the cell is overloaded long before the stop acts. Pull behaves the same way.
   - **The nut.** It overlaps the Ø33 piston by 1.5 mm³ (0.3 mm radial at the corners). It has no shoulder facing +x, so README step 5's "snug" pulls it onto the piston and clamps it. That adds a friction path in parallel with the cell.
   - Evidence: review rows slide (0.40, 0.75) and distances (nut/piston FAIL); `cad q dist` -1.511 mm³; `08_head_open.png` shows the pin spanning the open trough.
   - **Fix:**
     - Truncate the teardrop at |x'| = 19.0 mm from the barrel axis, which leaves a flat 9.5 mm bridge roof and 6 mm of wall to each face. Keep the 45° flanks.
     - Bore the pin hole Ø4.0 and ream it with a 4.0 drill bit through both closed halves, so the hole locates the pin by construction.
     - Make the inboard counterbore Ø8 x 3 deep (not 5.5), so the pin bears on 3 mm of wall each side of the bore.
     - Move the nut to a real 7.2 AF x 3.6 hex pocket at x' 19.5-23.1, entered from the split face by a 7.2 mm slot (the same scheme as the M4 fin nuts). Use an M4 x 45.
     - Add `distances` rows: pin to slot face 0.15-0.35, and nut to piston ≥ 0.3.
     - Fit 50 kg cells (same Ø25.4 puck, M5 studs, about 490 N, 150 % safe ≈ 735 N). Then a 0.3 mm printed stop is a real backstop and not the only protection.

2. **MAJOR (F): sleeve friction gives hysteresis comparable to the push signal.**
   - The grip centre is 79.5 mm past a 60 mm sleeve, so the edge reactions sum to 3.65 x the vertical hand load. Friction is then 0.37-1.1 x that load (mu 0.1-0.3).
   - An attendant leaning 100 N on a grip can hide or invent 37-110 N of axial force. Proportional sum and difference steering can't tell that from a push.
   - **Fix (could work better):**
     - Replace the sliding fit with a parallel-leaf flexure guide: two PLA leaves 30 x 20 x 1.2 mm, printed flat, spaced 40 mm apart. Axial stiffness is about 45 N/mm against the cell's ~1.3-2 kN/mm, so 2-3 % linear shunt and no stick-slip. At 12 N·m, leaf stress is about 8 MPa; the leaf buckles at about 1.5 kN.
     - Or, as a minimum, lengthen the sleeve to 100 mm by moving the cell 40 mm forward (factor 2.6 F), and line the bore with PTFE tape (mu ≈ 0.08). Expect about 0.2 F.
     - Model the piston as a prismatic joint (±0.5 mm) with `fits` min 0.2.

3. **MAJOR (F): lost motion and an uncontrolled stop gap.**
   - As modelled, the piston face is 0.20 mm off the cell and the rear nut has 0.8 mm of axial play in its 5.0-deep pocket.
   - README step 4 backs the piston off "up to a quarter turn" (0-0.2 mm at 0.8 pitch). The superglue then bonds the nut to the stud, not to the pocket.
   - So push reaches the cell through the face after a 0-0.2 mm dead band, and pull goes through the pocket wall. The pin sits ±0.5 mm in its counterbore.
   - Stack: stop gap 0.3 ± (0.5 pin + 0.2 back-off + 0.15 printed slot) = **-0.55 to +1.15 mm**. At the low end the pin preloads the slot and shunts the cell at rest.
   - **Fix:**
     - Make the pocket 4.3 deep for the 4.2 nut.
     - Clamp the piston face to the cell by tightening, not backing off. Clock the stop instead with a 6-position slot (60° apart) or a round pin hole drilled through at assembly. With a drilled-through hole the stack becomes ±0.1.
     - Add a `stacks` row "stop gap" with `between` 0.15-0.45.

4. **MAJOR (M): the stop nut can't be fitted as the README says.** The "pocket" opens into the bore's V-tip in the outboard half. When the outboard half is turned over onto the inboard half (step 5), the nut falls into the bore. Once threaded, it can only sit at the bolt tip (x 194.0-197.2), where it touches the piston. That is rework at the first assembly. **Fix:** the hex pocket and split-face slot from issue 1, with the nut held by a drop of hot glue.

5. **MAJOR (M): the screw heads don't match the lab stock.**
   - The lab stocks "M3-M5 hex head" screws, but the model and README use hex socket caps throughout (6 M4 x 16, 2 M4 x 40, 6 M5).
   - If the stock is external hex, the M4 counterbores (Ø8.0) are smaller than an M4 hex head across corners (8.08), with no room for a 7 mm socket. The lower M5 sits in a Ø11 spot face, too small for an 8 mm socket (OD ≈ 12).
   - **Fix:** confirm which screws the lab stocks. For external hex, make the M4 counterbores Ø12 and the M5 spot faces Ø14 (socket OD + 1). Either way, correct the README hardware table (it still says M8 button heads).

6. **MAJOR (A): the teardrop tips break the lip face.**
   - The bore's ±x tips appear as open wedge notches about 7 mm long beside each piston on the barrel lip, in the hero close-up (`03_handle_closeup.png`, `cad/review/a2/r_lip_face_R.png`).
   - Along 60 mm the skin over them is only 1.24-1.34 mm, so print-through on both fin faces is likely.
   - **Fix:** end the teardrop 4 mm short of the lip and finish with a round Ø33.6 bore (a 4 mm long crown, fine as a bridge). The truncation from issue 1 also raises the skin to 6 mm.

7. minor (M): both pistons need tree supports under 130 mm of spigot. Printcheck flags only the spigot, but 821 mm² of the Ø33 body is also a >45° overhang (harmless here because it faces the V-tip). **Fix:** replace the 1.2 mm flat with a D-flat 11.1 mm from the axis on the inboard (-x) side of the body. It becomes tangent with the spigot bottom, so the piston prints with zero supports. That side faces the bore's V-void, so no bearing is lost.

8. minor (M): short thread engagements. **Fix:**
   - ESP32 standoffs Ø6.5 x 5 tall with Ø2.5 pilots 7 deep, and M3 x 12 screws. Also confirm the real board has no 3.75 mm spacers (allow `PRT_tray_L x BUY_esp32_p4`).
   - Front cover screws M3 x 12.
   - Fin bolts M4 x 20 (the slot has room).
   - Lower mount bolts M5 x 30.

9. minor (M): tools.
   - Four screws are reachable only with an L-key at 15.5 mm: M4 `L2`/`R2` near the tray floor, and M5 bolts 4/5 in the foot. The kit is a drill and bits.
   - Step 2 needs an 8 mm spanner in a 14 x 20 mm void.
   - **Fix:**
     - Raise the low fin bolt to z -50, which is 14 mm above the floor and clears a 14 mm bit holder.
     - Angle the foot spot face so a 150 mm bit extension reaches the lower M5 through a Ø14 hole in the floor.
     - List an 8 mm nut-driver bit in the README.

10. minor (F): the two halves are separate pods butted at x = 0 with no fastener between them (BOM). The "one unit" relies on the plate. The x = 0 seam shows through the cover and tray in `01_hero.png`, and any plate warp shows as a step. **Fix:** two M4 x 16 + nut through 12 x 12 x 6 mm tabs on the floor and the front wall at x = 0, or a 60 x 20 x 3 mm splice plate under the cover.

11. minor (F): cables. None of the 5 routes has a lead length. The patch cable kinks at R2.7 (OD 5). **Fix:** add `cable_leads` (cell lead as bought, 150 mm patch). Turn the coupler to the rear wall at z ≈ -45 so the patch runs straight about 40 mm, with R ≥ 20.

12. minor (A): no radius family. **Fix:** declare `EB = 1`, `R_out = 6` and `R_in = 2` in `P`. Use R6 on every exterior convex edge (fin, tray, cover rear edge) and R1-2 inside. Today the fin's R6 meets the cover's R4 and the tray's R0.5-2 at the fin/cover junction.

13. minor (process):
    - README errors: "M8 button heads", "PLA, no supports. `cad printcheck` passes every part with no supports", and "±0.3 mm, which protects the 20 kg cell". The build docstrings still say "four M8s".
    - Config: the a1 rows weren't adopted, 35 warns are untriaged, and five checks in `--only` had no rows.
    - `attempts.md` has no attempt-2 entry.
    - A tool gap: the interference check passed a 1.5 mm³ nut/piston overlap.

## Check-config audit
- `allow`:
  - Cell/nut/washer, grip/spigot, fin/cell (≤ 3 mm³; measured 0.028 mm) and piston/rear nut (≤ 1 mm³): **agreed**.
  - `FST_Board_screw_* x BUY_esp32_p4`: agreed (stand-in STL).
  - `PRT_tray_L x BUY_esp32_p4` (≤ 5 mm³, "STL's own 3.75 mm spacers on 1.2 mm standoffs"): **disputed**. It hides the 2.5 mm thread engagement. Confirm the real board has spacers, or model 5 mm standoffs.
- Missing rows:
  - a prismatic piston joint;
  - `distances` for the stop gap, nut to piston, and piston seated on the cell;
  - `slide_out` for the stop;
  - `service`;
  - `stacks` for the stop gap;
  - `cable_leads`.

  `review_rows.json` provides most of these: 3 distances FAIL, 2 slides FAIL, and the cover and service rows pass.
- `assembly_order` vs README: the README does the handles first and the T-nuts at step 10, while `checks.json` does the T-nuts first. `CAB_Load_cell_lead_*` sits in "electronics into the trays", before the cells exist: **disputed**. Move it to the handle steps.
- The designer's `--only` lists service, slide, distances, stacks and flexures, but `checks.json` has no rows for them, so the report claims coverage it doesn't have.

## What is good
- The mount is now sound. A 75 mm lever between the foot and the upper M5 row, and a land contact on the plate for both tray and fin.
- Every boss survives the cavity, and 0 heads stand off on the M4 and M5 joints.
- The rear nut is captive, so no 180 mm reach is needed.
- The spigot is printed with layers along it.
- The cover lifts straight up.
- `cad bom` matches the model 7/7.
- Printing is cheap: 10 parts on 3 plates, about 19 h and about 1 kg. Fins and trays need no supports; their overhang warns are bridges ≤ 13.7 mm and the crowns of round holes.
- No wire is exposed (0 exposed samples on 5 routes).
- The cover screws are on a regular counterbored grid.
- The two-tone wedge reads as one object from the hero angle. Fin outboard faces are clean.
