# Design loop: attempts and independent review scores

Target: 9+ on functionality, manufacturability and aesthetics, or 8 attempts. Each review is by a
separate agent using the cad-design-review skill; full reports in `cad/review/aN/`.

| Attempt | Functionality | Manufacturability | Aesthetics | cad check | printcheck |
|---|---|---|---|---|---|
| 1 | 5 | 5 | 7 | 0 fail, 65 warn | 10 parts, 0 fail, 12 warn |
| 2 | 5 | 6 | 6 | 0 fail, 35 warn | 10 parts, 0 fail, 0 warn; pistons need support |
| 3 | 7 | 8 | 7 | 0 fail, 23 warn (all triaged) | 11 parts, 0 fail, 8 warn; no supports |
| 4 | 7 | 8 | 8 | 0 fail, 39 warn (all triaged); moving-link rows 0 fail, 0 warn | 15 parts, 0 fail, 24 warn; no supports |
| 5 | 8 | 6 | 9 | 0 fail, 47 warn (all accepted); movlink/bench 0/0 | 17 parts, 0 fail; no supports |
| 6 | 8 | 8 | 9 | 0 fail, 47 warn (all accepted); movlink 0/0 | 17 parts, 0 fail; no supports |
| 7 | 4 | 4 | 9 | 0 fail, 51 warn (all accepted); movlink 0/0 | 18 parts, 0 fail; no supports |
| 8 | 8 | 8 | 9 | 0 fail, 51 warn (all accepted); movlink 0/0 | 18 parts, 0 fail; no supports |

## Attempt 1

Changes from round 6: fin 50 thick so the Ø50 barrel is flush both sides (the 7 mm bulge hit the
tray end wall); fins print flat; fasteners moved to the lab kit (M3 self-tappers from the hidden
inboard face, M4 caps into fin nuts, M5 caps + 40-series T-nuts, self-tappers for boards and
covers); parting groove removed; check.blend converter (`to_cadcheck.py`) and checks.json added.

Review (a1/review.md), ranked:
1. BLOCKER: the tray cavity cut deletes every internal boss (mount, fin-bolt, cover, standoffs, RJ45 pad).
2. BLOCKER: four M5s in one row 20 mm above the only plate contact; ~1.7 kN in two M5s at 150 N on a grip.
3. MAJOR: 0.5 mm push travel before the stop (cell full scale ~0.1-0.2 mm), no pull stop.
4. MAJOR: sleeve friction 0.46-1.4x hand load; key-rib fillet touches the slot.
5. MAJOR: README hardware list contradicts the model.
6. MAJOR: grip spigot printed standing, bent across layers (13-26 MPa vs ~15).
7. MAJOR: rear M5 nut needs a 180 mm reach with tools not in the lab kit.
8. minor: cover can't lift straight off; load-cell swap ~22 fastener operations.
9. minor: no cable lengths; patch cable bends R2.8.
10. minor: no single radius family; 10 cover-screw holes in an irregular pattern.

## Attempt 2 (designed by the coordinator)

Fixes for a1: tray bosses now survive the cavity cut (`sdf_part(hollow=...)`), every boss has a
45 deg underside; second mount row (M5 x 25 through feet at x +-120 that bridge the bevel down to the
floor), upper M5 x 20 through 12 mm land bosses; M4 x 40 overload-stop pin through a cross slot in
the piston (+-0.3 mm push and pull), key rib removed; rear M5 nut captive in the piston (slides in
from the side), no long socket; sleeve 45 -> 60 mm; teardrop sleeve bore and cell pocket for the
split-face-down fin print; piston printed on its side with a 1.2 mm flat (supports under the spigot,
hidden by the grip); cover 3 mm back from the plate line, 2 x 2 cover screws per half on the mount
x grid; deeper stand-in T-slot; BOM generated from the manifest (`gen_bom.py`, `cad bom` PASS);
README assembly rewritten; plates: H2D fins, P1S tray L + pistons, H2D tray R + covers.

Review (a2/review.md), ranked: (1) BLOCKER overload stop has no fin material around the pin (teardrop
tips cut it away), stop at ~1.15 mm; stop nut rubs the piston. (2) sleeve friction 0.37-1.1 x vertical
hand load. (3) lost motion piston/cell and uncontrolled stop gap. (4) stop nut not captive. (5) socket
cap vs "hex head" stock; counterbores too small for hex heads; README still says M8. (6) teardrop
notches visible at the barrel lip. (7) pistons need supports; printcheck missed 821 mm2 body overhang.
(8) short thread engagements. (9) L-key-only screws, 8 mm spanner. (10) halves not joined at x = 0.
(11) no lead lengths; patch kink. (12) no radius family. (13) checks listed with no rows; warns untriaged.

## Attempt 3

Results:
- `cad check` (`cadcheck_a3.json`, same `--only` as a2): **0 fail, 23 warn, 0 untriaged**. Every warn has a
  reason in `accepted_warns`.
- `cad printcheck cad/print/stl_cc`: **11 parts, 0 fail**. Its 8 warns are listed under "Printability" below.
- `cad bom`: **PASS**, 10 rows.
- Estimate: 1,118 g, 22 h, on three plates (H2D fins; P1S tray L + pistons; H2D cover + tray R + cartridges).

Scores pending review.

### What changed, by a2 issue

1. **Overload stop (BLOCKER) and stop nut (#4).** The stop is now inside a printed flexure cartridge (below).
   - An M4 × 30 socket cap runs through the cartridge's ground post and a Ø4.5 hole in a V tongue under the
     top link. The post holes are Ø4.05, reamed 4.0 at assembly.
   - The pin is supported on both sides of the tongue over 6-12 mm of post.
   - The nut sits in a 7.2 AF hex pocket on the post's outboard face, fitted on the bench. The head sits in
     a Ø8 counterbore.
   - Rows: push and pull gaps **0.25 / 0.25 mm** (`distances` rays, window 0.15-0.35); pin seated in the post
     **0.025 mm** both sides; stop nut to piston **9.7 mm**.
   - The tongue hole and the post holes are in one printed part, in its layer plane, so the gap does not
     depend on the fin or the cell. The `stacks` row is RSS **0.107**, worst case 0.225, against 0.25.
2. **Sleeve friction (MAJOR).** There is no sliding fit any more.
   - The cell sits in a one-piece printed parallel-leaf cartridge. A front plate and ground bar are fixed in
     fin pockets. A top link is clamped to the cell's rear face, on two 1.5 × 36 mm leaves, 27 mm long and
     47 mm apart.
   - The cartridge prints on its side, so each leaf bends in its layer plane (`flexures`: 0 deg to the bed,
     7.6 MPa at 0.35 mm).
   - Axial stiffness is about 43 N/mm, against about 1.5 kN/mm for the cell: a fixed 2-3 % shunt, linear and
     calibrated out.
   - Hand calc at 150 N down on one grip: rear leaf 530 N, buckling about 1.9 kN, SF 3.6.
   - Every moving face clears the fin by **1.0 mm** (10 ray rows per side).
   - The piston is a Ø22.2 D-bar that never touches the fin (nearest 1.09 mm).
3. **Lost motion (MAJOR).** Both cell joints are clamped by turned nuts, and the cell never turns.
   - The rear nut is tightened with an 8 mm nut-driver down the socket.
   - The front nut goes up a Ø16 bore that opens on the land face (hidden against the chair).
   - The piston bears on the socket shoulder for push and is held by two M3 × 12 self-tappers (pilots in both
     parts) for pull.
   - Rows: cell rear face to top link **0**; cell front face to front plate **0**; piston to shoulder **0**.
   - Slide "piston pushed -y": blocked by the cartridge at **0.05 mm** (one 0.05 step).
4. See 1.
5. **Screw heads.** Alex confirmed ISO 4762 socket caps.
   - Counterbores are M3 Ø6.5, M4 Ø8.0, M5 Ø9.5 (the lower M5 had a Ø11 spot face).
   - README hardware table: no M8; it now lists socket caps, M3 pan self-tappers, T-nuts and the 150 mm patch.
6. **Teardrop notches at the lip.** The bore at the lip is now Ø24.4, round for the last 4 mm (a 4 mm
   bridge). No teardrop reaches the lip face (`03_handle_closeup.png`).
7. **Pistons need supports.** The piston is a D-bar with its flat 7.8 mm from the axis. It prints flat-down
   with no supports: printcheck max ledge 0, `overhang_gt_45` **0 mm²**.
8. **Thread engagement.**
   - ESP32: 6 mm standoffs and M3 × 10. The stand-in STL's own 3.75 mm spacers are flattened, and the
     `PRT_tray_L × BUY_esp32_p4` allow is gone.
   - Front cover screws: M3 × 12 into land bosses with a flat top (the boss top used to slope).
   - Fin bolts: M4 × 20, full nut.
   - Lower mount bolts: M5 × 30.
   - No engagement warns remain.
9. **Tools.** Every M4 and upper M5 now takes a straight bit; the a2 L-key cases are gone.
   - The low fin bolt moved to (117.5, -46): 18 mm off the floor and 14.6 mm off the 60 deg rear wall.
   - The lower M5s are driven from below with a 150 mm extension through a Ø14 hole in the tray floor along
     the bolt axis (accepted warn).
   - The front cell nut needs an 8 mm nut-driver, not a spanner.
   - README tools: drill, 1/4 in bit holder, 3 and 4 mm hex bits, Phillips, 8 mm nut-driver, 150 mm
     extension, 4.0 mm drill bit, superglue, hot glue.
10. **Halves not joined.** One cover spans both trays (305.6 mm, H2D only) with eight M3s into both. It
    splices the halves at x = 0 and removes the top seam.
11. **Cables.** `cable_leads`:
    - Cell lead: 200 assumed, 71 used.
    - HX711 jumpers: 200 mm, 96 / 135 used.
    - Patch: 150 mm, 149.97 routed. It now leaves the board, rises, crosses under the cover and drops into
      the coupler, with three R20 bends. The coupler moved to x ≈ -95. No kink warn.
12. **Radius family.** `P` declares `R_out = 6`, `R_in = 2`, `EB = 1`.
    - Fin: profile corners R6 (the bottom corners were R10), window R6, opening R6, concave fillet R2.
    - Tray: section R6, inside R2. The tray's front-bottom edge is a 45 deg C6 chamfer, because it prints
      on the bed; its rear-bottom edge is left sharp (a 60 deg face prints clean).
    - Cover: 6 mm thick, so its rear top edge is one R6 that continues the fin's lip edge.
13. **Process.**
    - The a2 reviewer rows are adopted in `checks.json`, adapted to the new mechanism (see the table below).
    - New rows: 40 distances, 7 slides, 3 service ops, 4 stacks, 4 flexures, cable leads.
    - Assembly order: 18 steps, with bench groups for each cartridge and handle.
    - Every warn triaged. README: no M8, the support claim backed by evidence, tools.
    - The manifest now carries `params` (P plus derived frame numbers).

### Printability ("no supports" evidence)

`overhang_gt_45_mm2` per part, with each area located by an overhang map:

| Part | mm² | Where |
|---|---|---|
| Piston | 0 | none |
| Cover | 0.1 | none |
| Cartridge | 30 | crowns of the two Ø5.5 horizontal stud holes (5.5 mm bridges) |
| Fin | 130-148 | facets of 45 deg teardrop roofs (42-45 deg from down, no patch over 21 mm²) and the 4 mm round crown of the shaft bore at the lip |
| Tray | 700-733 | 45 deg boss undersides (SDF facets at 44.7-44.9 deg) and the top of the oblique Ø14 bit hole through the floor (70 mm²) |

The printcheck warns are:
- **"67 mm bridge" (one per fin half).** This is the E-shaped roof over the cartridge pockets. Its arms span
  7.2, 3.2 and 14.2 mm and are anchored on both sides; 67 mm is the E's length. Layer map:
  `a3_designer/printcheck_fin_pocket_roof_z18.png`.
- **1.1 mm ledges** around the M4 hole in two nut-slot roofs.

### a2 reviewer rows, as adopted

Run verbatim (`a3_designer/a2_review_rows_verbatim.json`) they give 3 fails, because they describe the a2
mechanism:

| a2 row | Attempt 3 equivalent |
|---|---|
| "piston pushed onto the pin within 0.35" | The piston bears on the cartridge shoulder at 0.05. The stop is the top link's tongue against the pin: ray rows 0.25 / 0.25. |
| "pin held by the fin within 0.1" | The pin is held by the cartridge post: ray rows 0.025. Verbatim, the slide test ignores the at-rest facet contact, so the pin slides. |
| "piston face seated on the cell" | The top link (not the piston) is clamped to the cell: ray row 0. The piston is 0.85 mm off the cell, because it plugs into the top link. |
| stop nut ≥ 0.3 from the piston; piston-to-fin clearance | Kept as they were (9.7 mm; 1.09 mm, min raised to 0.5). |
| cover-off slide and service rows | Moved to the single `PRT_cover`. |

### Not fixed, or changed only partly

- **50 kg cells (a2 #1 suggestion): not changed.** This is a hardware choice for Alex. If the 20 kg cell's
  full-scale deflection is under about 0.15 mm, the 0.25 mm stop still lets it reach 1.5-2.5 × FS. Measure
  one cell, or fit 50 kg (same puck and studs).
- **No prismatic joint for the piston.** The moving top link is part of the same printed part as the fixed
  ground (that is the point of a monolithic flexure), so cadcheck cannot sweep part of it. Travel is ±0.25
  mm. Ray rows hold every moving face 1.0 mm from the fin, and a `stacks` row covers that clearance (RSS
  0.42).
- **Window (flagged for Alex).** The fin's lightening window lost 10 mm at its top front corner, (52, -34)
  to (42, -34), to clear the cartridge pocket. The other outer shape is unchanged.
- **Splice.** The single cover is the splice. There is no extra floor tab at x = 0.
- **ESP32 screws 2 and 3** sit by the tray's front wall. They need the 150 mm extension (accepted warn) or
  fitting before the board is close to the wall.
- **Stale renders.** `05_junction.png` and `07_lead_closeup.png` in renders/ are stale untracked files from
  round 1. I left them alone.

Review (a3/review.md), ranked: (1) clamped cell carries ~47% of the grip bending moment (both cell
faces clamped flat) -> O8 x 1.0 seat bosses so only the stud axis loads the cell; (2) stop gap 0.25
not sized to the cell's deflection -> stop = 1.2 x measured deflection, or 50 kg cells; (3) sharp
leaf roots -> R1.5 fillets, computed stress row; (4) PLA creep/heat at clamp and leaves; (5) stale
plate files in cad/print; (6) O15 washer not on the hardware list, hand-reamed pin holes, heavy cell
swap; (7) patch cable has no slack; (8) aesthetics: three parallel seams on each fin top, clipped
window looks like a dent; (9) to_cadcheck should emit the moving link (reviewer's
scripts/split_moving_link.py), tongue wall 0.58 mm under the pin hole.

## Attempt 4

Results (full resolution, voxel 0.6):
- `cad check` (`cadcheck_a4.json`, same `--only` as a3): **0 fail, 39 warn, 0 untriaged**. Every warn has a reason in
  `accepted_warns`; every accept matches a warn.
- Moving-link rows (`cadcheck_a4_movlink.json`): the a3 reviewer's `review_rows.json`, adapted to the new stop, in
  `cad/blender/checks_moving.json`, run on `check_moving.blend` with `--only slide,distances`: **0 fail, 0 warn**.
- `cad printcheck cad/print/stl_cc` (and `cad/print/stl`): **15 parts, 0 fail, 24 warn** (listed below).
- `cad bom`: **PASS**, 11 rows. `check_wires.py`: OK (R13, 25.4 straight, touches nothing).
- Estimate: 1,121 g, 22.4 h, on the same three plates (the washers join the P1S plate).

Scores pending review.

### What changed, by a3 issue

1. **Cell carried ~47 % of the grip moment (MAJOR).** Each cell face now bears only on a Ø10 × 1.0 seat boss on the
   stud axis (front plate and top link), with 1.0 mm clear outside it.
   - Rows: cell face to boss **0 / 0**; cell face to plate and to link at r 11.3-11.4 in three clock positions,
     **1.0** each (min `seat_h - 0.2`).
   - `cad/calc/head_calc.py` (the reviewer's `flexure_calc.py`, adapted; it reads the manifest params): cell share
     **1.9 %** (a3: 46.5 %). 50 N down on the grip puts 0.15 N·m through the cell (a3: 3.86); 150 N, 0.46 N·m.
   - README step 13 adds the reviewer's bench check (5 kg at the grip end, < 2 % FS change).
2. **Stop gap not sized to the cell (MAJOR).** The pin is gone. A tongue under the top link sits in a slot in the
   ground post. Two M4 × 8 socket caps run through nuts in the post's front and rear walls, tips on the tongue.
   - They are set on the bench with the cartridge out of the fin, using the HX711 as the gauge: the pull screw jacks
     the link to +1.2 × FS and the push screw is brought to touch, then the push screw jacks to −1.2 × FS and the
     pull screw is brought to touch, and the push screw goes back to its pen mark. Each gap is then the link's travel
     at 1.2 × FS, so one print fits any cell. Procedure: README "Setting the overload stops".
   - Rows: modelled gaps **0.15 / 0.15** (rays, window `stop_gap ± 0.03`); moving link first hits the push screw
     at 0.2 (−y) and the pull screw at 0.2 (+y) (slide, 0.05 steps); each screw and nut, loaded by the tongue,
     bears on the post at once (slide **0.0**).
   - `stacks`, upper bound as the reviewer asked: engagement above 1.2 × FS, as a fraction of FS, with
     `dfs_ref` 0.1 mm: push RSS **0.109**, pull **0.096**, limit 0.3 (to 1.5 × FS). The terms include thermal drift
     computed from the geometry (`stop_dT_p/q`).
   - Stop screws, nuts and their access are in `fasteners` (bench step; a 3 mm key reaches the push screw through
     the front plate and front leaf, the pull screw through the rear leaf).
3. **Sharp leaf roots.** R1.5 fillets at every leaf root (top root carried across the chamfered link edges as a
   strip, so the free length is 27 everywhere). The `flexures` stress is `=leaf_stress_mpa`, computed by
   `build_concept.leaf_stress()`: Kt 1.35 × (bending at the largest setting, 0.30 mm, plus axial at a 150 N lean)
   = **19.0 MPa**, in the layer plane (angle 0). Bending alone at 0.30: 8.4 MPa (a3: 18-22 MPa at its worst-case gap).
4. **Creep / heat.** Bearing area: printed Ø15 and Ø13 washers under the nuts (3.3 / 4.6 MPa at a 500 N snug
   preload, against 15.8 MPa for a bare nut); nuts snug only (0.5 N·m), re-snugged after 24 h (README step 14). The
   boss is 1.0 tall, so even 1 % creep moves the cell 0.01 mm, and the stop gaps ride on the cell, not on the clamp.
   PETG: the BOM says to print the two cartridges and four washers in PETG if the chair is parked in heat; Alex's
   rule is PLA, so it is an option, not the default.
5. **Stale plates.** `export_prints.py` empties `cad/print/` first (keeping `stl_cc/`, which `to_cadcheck.py`
   owns). The folder now holds the three current 3MFs, `plates.txt`, `stl/` and `stl_cc/`.
6. **Hardware outside the brief.** The bought Ø15 washer is gone (printed washers). No reaming: there are no pin
   holes; the stop screws run in nuts. No superglue in the stud threads: a dab of hot glue on the front nut.
   The cell swap is lighter on glue only (see "Not fixed").
7. **Patch slack.** A 200 mm patch cable on the unchanged 150 mm route: `cable_leads` `=patch_lead`, path 149.97,
   so **50 mm** of slack, lying loose in tray L.
8. **Aesthetics.**
   - Seams: the fin's inboard edges are now sharp wherever the tray and cover continue it (a bridge-section stub
     goes through the SDF opening, then an exact cut at the inboard face). Fin, tray and cover meet on one hairline,
     and the a3 R6 trough at that joint is gone. The split is now a deliberate 0.8 × 1.0 V reveal round the whole
     outline (39° from vertical, so it prints as a bed-edge chamfer). The fin top shows the reveal and the cover
     hairline, not three seams.
   - Window: dropped. The outboard face carries a 2 mm recessed panel 8 mm in from the outline, with R6 corners
     and a 1 × 1 chamfered rim (`03_handle_closeup.png`).
   - Found and fixed while rendering: faces cut by the exact (Manifold) cutters had no material, so they rendered in
     Blender's default light grey. That was the bright face inside the head in a3's `08_head_open.png`. Cut faces
     now take the part's material, and the fins get crisp edges by angle.
9. **Process.** `to_cadcheck.py` writes `check_moving.blend` with `PRT_movlink_R/L`. These are built in
   `build_concept.py` from the same functions as the cartridge (`cartridge_link_raw()`), not from typed numbers.
   The tongue has no hole now, so the a3 0.58 mm wall under the pin hole is gone (its underside slopes at 45° so it
   prints without support). The tray overhang note now names the M5 hole crowns.

### Printability ("no supports" evidence)

`overhang_gt_45_mm2` per part: piston 0; washers 0; cover 0.1; cartridge 44 (crowns of the Ø5.5 stud holes); fin
108 (outboard) / 147 (inboard), on teardrop facets; tray 702-733 (boss undersides, the Ø14 bit-hole crown, the M5 hole
and counterbore crowns). The printcheck warns:
- Fin, **67.4 mm "bridge" at z 18**: an E-shaped roof at x' 18.1. The post-pocket roof bridges its 22.5 mm side, and the
  plate and ground strips are 3-7 mm. Layer map `a4_designer/fin_R_outboard_z018.0_bridge.png`.
- Fin, **29.5 mm at z 19**: a C made of the two leaf-slot roofs (6.5 wide) and the link-cavity side (15.2).
  `a4_designer/fin_R_outboard_z019.0_bridge.png`.
- Fin, 1.1-1.3 mm ledges (nut-slot roofs, a slot corner). Cartridge, 1.2 mm at the first layers of the key-hole
  doubler rings (`a4_designer/cartridge_R_z013.4_cantilever.png`). All are under the 3 mm limit.

### Two design findings from the checks

- The leaves' stop-key holes sit where the leaves carry the lean couple axially. A bare hole gives 25.8 MPa at a
  150 N lean, so each hole has a Ø14 doubler ring 1.5 proud on both faces: **12.7 MPa** (`head_calc.txt`).
- The stop nuts first slid in from the outboard face, and their slots cut the anchors of the post's outboard side
  wall (printcheck: a 4.3 mm cantilever, fail). They now slide in from the inboard (bed) face.

### Not fixed, or changed only partly

- **Cell choice (flagged for Alex).** The stops now engage at 1.2 × FS for any cell. But the printed stop path is
  about 2.3 kN/mm (screw tip on PLA, nut on PLA, post wall), so after engagement the cell keeps sharing load.
  Under a 600 N shove, a stiff 20 kg cell (0.05 mm at FS) still reaches about 2.35 × FS; a 0.15 mm cell reaches
  1.85 × FS. A 50 kg cell with the same puck and studs drops in with no CAD change. Not switched, per the brief.
- **Stop setting is a bench procedure.** The stops can't be adjusted inside the closed fin, so changing the cell
  means setting them again on the bench (the cartridge comes out for a swap anyway).
- **Cell swap count.** Still 21 fastener operations (cover 8, fin M4 3, clamshell 6, front nut 1, piston screws 2,
  rear nut 1), plus a stop setting for a new cell. The glue is gone. Fewer clamshell screws would leave the V
  reveal open at the ends, so they stay at six.
- **Visible cover screws.** The eight M3 heads stay on the cover's 2 × 4 grid. Hiding them needs a clip or plug
  that isn't in the hardware list.
- **Leaf worst case.** The flexures row is 19.0 MPa with the largest setting and a 150 N lean at once, in the
  layer plane. If the chair is parked in heat, the PETG option applies here too.
- **Shape.** The wedge, fins 140, bridge 92, Corpus mount and 14 in spacing are unchanged; the panel and reveal are
  surface details inside the agreed outline. `cad/profile/profile.py` is unchanged.
- **Stale renders.** `05_junction.png` and `07_lead_closeup.png` (round 1, untracked) are still in renders/;
  nothing uses them.

Review (a4/review.md), ranked: (1) stop screws 24 mm below the cell axis: bench jacking twists the
leaves (stop at 1.4-1.6 x FS), and a downward lean while pushing clips push readings at 0.65-0.93 x FS
-> stops on the cell axis (side lugs at z 0); (2) rear leaf buckles at 338-578 N straight down on one
grip, no vertical stop -> 2.0 mm leaves or a lip catch at 0.35 mm; (3) 20 kg cell still 2.0-2.55 x FS
at a 600 N shove -> 50 kg cell or 6 mm post wall; (4) README 24 h re-snug impossible on the assembled
unit; (5) 0.5 N.m snug unmeasurable with the kit, boss creep moves the stops; (6) moment share 2.9-6.7%
with the stud path; (7) tray centre seam visible on the sloped face, RJ45 coupler hangs 9 mm below the
floor; (8) stop setting needs a live HX711 every cell swap -> bench sketch + cradle.

## Attempt 5

Results (full resolution, voxel 0.6):
- `cad check` main (`cadcheck_a5.json`, same `--only` as a4): **0 fail, 47 warn, 0 untriaged**; every accept matches
  a warn, none stale. 118 objects, 57 screws, 24 nuts, 19 assembly steps, 13 slide rows, 12 stacks.
- Moving-link + bench rows (`cadcheck_a5_movlink.json`, `checks_moving.json` on `check_moving.blend`,
  `--only slide,distances,sightlines`): **0 fail, 0 warn**.
- `cad printcheck cad/print/stl_cc --manifest` and `cad/print/stl`: **17 parts, 0 fail, 16 warn** (fin roof bridges
  and ledges, below). `cad bom`: **PASS**, 14 rows. `check_wires.py`: OK.
- Estimate: 1,211 g, 24.3 h; four plates (a P1S plate for the bench tools added).

Scores pending review.

### What changed, by a4 issue

1. **Stops on the cell axis.** The tongue and post are gone. Four M3 socket caps per cartridge run along the grip
   axis beside the cell (x' ±14.9) and thread into M3 nuts in slots in the top link, so they move with it; their
   heads act on the cartridge's block. Push pair at z 0 (on the axis): heads in counterbores in the block's rear
   face, the head's top face meets the floor. Pull pair at z −6.5: through the block, heads in its front
   counterbores. They are set in a printed cradle whose M5 jack screw is on the grip axis (swivel nut in a setting
   plug that goes in the socket like the piston), so the jacking couple is zero. Rows: stop gaps 0.15 (rays, ±0.03,
   all eight); moving link + screws −y/+y blocked by the block at stop_gap; adapted a4R jacking row 0.083 (no couple
   term left); adapted a4R lean row **0** (push contacts on the axis; a4: 0.475); pull lean row 0 (the lean opens
   them), lift row 0.099.
2. **Vertical overload.** Leaves 2.0 (r 2 roots): rear leaf buckles at 970-1360 N down per grip (a4: 338-578). The
   barrel lip is now the moment stop: 0.70 radial (a4 1.1; rows 0.703 below and above). It engages at 160-220 N
   down with the piston's own bending, 400-560 N on the link alone; at the link-only engagement the rear leaf
   carries 1338-1873 N against 3249-4549 to buckle (×2.4). Past contact the piston levers on the lip and the leaf
   load stops rising. Stack row: lip_c + 0.2 = 0.9 against a 1.70 lip drop at buckling. The moving-link ±z rows
   now stop on the lip at lip_c (adapted from "fin cavity at 1.0").
3. **Stop stiffness.** Steel heads and nuts bearing flat on PLA, short PLA paths, two screws per direction: about
   7.6 kN/mm push, 7.2 pull (a4: 2.3; the review asked for ~3.5). Cell at a 600 N shove: any 50 kg cell ≤ 1.21 × FS;
   20 kg cells 1.81 / 1.66 / 1.56 / 1.45 / 1.39 × FS at dFS 0.05 / 0.075 / 0.10 / 0.15 / 0.20 (head_calc 3e). Only
   a 20 kg cell with ≥ 0.15 mm FS travel stays under an assumed 1.5 × FS safe overload. **The BOM now recommends
   the 50 kg puck (same body and studs); Alex decides.**
4. **Re-snug on the bench.** The cartridge is self-contained: the front stud clamps the cell to the 10.5 mm block on
   its own (washer and nut in a counterbore in the block's front face), so both nuts are done, settled overnight
   and re-snugged on the bench, before the stops are set; nothing in the stop chain changes when the cartridge goes
   into the fin. The fin floor and the land-face access bore are gone; the block bears on the fin's solid front wall
   and on fin lips behind it (rows: 0.1 each way, fixed body held within 0.15 both ways). README step 14 is deleted.
   The a4R step-14 slide rows, adapted: front nut out −y through the block counterbore and the cradle's Ø16 hole,
   rear nut out +y through the socket on the bench (both pass). Verbatim they fail (blocked by the piston and the
   fin), by design: that step no longer exists.
5. **Measurable snug + creep term.** Finger-tight on the bare 8 mm bit (0.1-0.2 N·m, 1.8-3.6 MPa on the boss), then
   overnight, re-snug, hot glue. "+60°" is not used: the stack is ~42 kN/mm, so 60° would put 5.6 kN on the boss
   (head_calc 5). Creep term in every stop row: 2 × (seat_h + 1) × 0.15 % = 0.006 mm. Push stack worst 0.163 /
   RSS 0.088, pull 0.178 / 0.099 (limit 0.3); terms: touch, second screw, jack hold, cradle-vs-fin support
   (0.002 mm), creep, thermal (+0.006 / −0.0075 mm per 10 °C).
6. **Calc.** `cad/calc/head_calc.py` now holds the reviewer's head_check models too (free and pinned link, boss +
   half-space, stud bending path): moment share 2.2-7.0 % (stud path 4.6-5.1 %). Bench pass marks: past 120 % on
   the jack the reading climbs at < 40 % of its earlier rate; 5 kg at the grip end changes the reading < 2 % FS
   (≤ 0.78 N·m through the cell) and the grips agree within 1 % FS; > 5 % FS means a face is touching.
7. **Aesthetics.** The tray centre seam is a 0.8 × 1.0 V reveal on every face (same as the fin split). The RJ45
   coupler sits on a 5 mm pad, flange on top with two M3 × 12, short body inside the pad and floor: nothing below the
   tray (the patch-cable run rose to z 16 to keep a straight lead out of the plug). The land face lost its Ø16 bore.
   Renders re-made; `step5_stop_setting.png` is new.
8. **Practical stop setting.** Printed cradle + setting plug (P1S plate), M5 × 20 jack screw with two nuts, two M4 ×
   12 lip screws (the cradle's pull reaction, put in after the cartridge drops in), and
   `firmware/bench_hx711/bench_hx711.ino` (no libraries; % FS from the cell's mV/V or a known mass; `m` marks and
   `TOUCH` shows the 1 % drop). Each screw is touched once; no pen marks, no counted angles, no setting inside the
   fin. Bench rows: the cartridge with plug and jack drops into the cradle (+z clear), key lines to all four stop
   heads through the cradle's windows (sightlines), 4 mm key line to the jack.

### Printability ("no supports" evidence)

`overhang_gt_45_mm2`: pistons, plug, washers 0; cover 0.1; cradle 153; cartridge 159 (upper faces of the corner-up
M3 nut pockets and teardrop flanks; layer check max bridge 5.7, max ledge 1.0); fins 97-138; trays 824-875, every one
of them a strip at print z 0-5 that starts on the bed (`steep_strip.py`). Printcheck warns: fin roofs at |x'| 18.1
(L-shaped, the block and ground pockets, 10.7 and 7.2 wide) and 19.1 (C-shaped: flank slot, link cavity, leaf slots),
every arm closed on all sides (layer maps in `cad/review/a5_designer/`); 1.1 and 1.8 mm ledges.

### Not fixed, or changed only partly

- **Cell choice:** recommended 50 kg in the BOM; not switched in the model, per the brief.
- **Side load:** the stops sit beside the cell (the cell is in the way of x' 0), so a sideways force yaws the link
  and one screw engages early: 0.17 FS at 20 N (free model, dFS 0.1; row in checks.json, limit 0.2), 0.07 pinned.
- **Lip friction:** a lean over ~160-220 N per grip puts the piston on the lip; push readings while leaning that
  hard are not trusted. The PLA piston sees 40 MPa at a 600 N lean (63 without the lip catch).
- **Moving-link translation rows:** the check split leaves a 0.3 gap at the leaf stubs, so the ±z rows ignore the
  fixed body; the stop screws' 0.5 radial clearance in the block is proved by ray rows instead (at the lip catch
  they move ≤ 0.15). Sideways translation is caught by the stop screws in their holes at 0.5 (row), the link is 1.0
  from the fin.
- **Cartridge play in the fin:** 0.1 each way (front wall / lips); harmless to the reading, may tick on reversal.
- **Flexures row:** 21.1 MPa (largest setting 0.30 + 150 N lean, Kt 1.35), up from 19.0 with the thicker leaves.
- **Firmware** syntax-checked only (the bundled avr-gcc is x86-only on this Mac); not compiled for a board.
- **Cell swap** count is unchanged in kind (cartridge out, stops re-set in the cradle); the cover screws stay visible.
- Stale round-1 renders `05_junction.png`, `07_lead_closeup.png` still sit untracked in renders/.

Review (a5/review.md), ranked: (1) BLOCKER (M): the printed setting cradle can't set the 50 kg
cell's stops (54 MPa across layers in the free-standing upright, tip moves 3.6-4.4 mm, jack tilts
6-8 deg) -> side walls to the upright, 10 mm upright, M5x30 jack, R3 roots; (2) README never sets
the cell's mV/V (sketch defaults 1.0) -> step 4 r <mV/V> + known-mass check, sketch refuses 'm'
until set; (3) 20 kg residual risk 1.44-1.92 x FS -> commit to 50 kg after fix 1; (4) lean-to-axial
crosstalk 3.8% (leaf tops 15 mm below the cell axis) -> 10 N dead band; leaf mid-length on the axis
next; (5) head_calc lip lever about the cell centre, not the leaf centroid; (6) soldering iron not
in the tool list -> HX711 with screw terminal; (7) lip friction past 180-250 N lean; (8) stale
flexures row text. Tool bug noted: a stacks formula naming a missing param crashes check_stacks
under --only stacks.

## Attempt 6

Results (full resolution, voxel 0.6):
- `cad check` main (`cadcheck_a6.json`, same `--only` as a5): **0 fail, 47 warn, 0 untriaged**, no stale accepts.
  114 objects, 53 screws / 24 nuts (the four HX711 board screws are gone), 19 assembly steps, 22 stacks (12 a5 +
  the 4 a5-review rows adopted verbatim + 6 new a6 rows).
- Moving-link + bench rows (`cadcheck_a6_movlink.json`): **0 fail, 0 warn**.
- `cad printcheck cad/print/stl_cc --manifest` and `cad/print/stl` (`--out cad/review/a6_designer/`): **17 parts,
  0 fail, 16 warn** (the same fin roof bridges and ledges as a5). Cradle: max bridge 4.1, max ledge 0.7,
  overhang_gt_45 153.5 mm² (lip-screw teardrop flanks, corner-up nut pockets, lead notches; unchanged in kind).
  `cad bom`: **PASS**, 13 rows. `check_wires.py`: OK. Firmware: host syntax check with a stub Arduino.h.
- Estimate: 1,247 g, 24.9 h (cradle 79 -> 114 g).
- The skills-repo `check_stacks` crash under `--only stacks` did not reproduce: every param the rows name is now in
  the manifest. It is still a tool bug when a row names a missing param (noted for Alex).

Scores pending review.

### What changed, by a5 issue

1. **Cradle (blocker).** Closed frame: both 6 mm side walls run from the front wall to the rear upright, and the
   upright is 14 mm thick (a5: 8 mm, free-standing). There are R3 roots where the upright meets the walls and the
   base. The base root ends 1.5 mm behind the ground bar, so the upright moved 3 mm rearward. The front wall, walls
   and upright are all 11 mm tall. The jack is an M5 × 30 (head 7.0 mm off the upright; a5: M5 × 20, 3.0 mm). The
   setting plug is 3 mm longer to match. The kinematics are unchanged: the plug, jack, cartridge and jack nut drop in
   together through the upright's open-top slot, so the a5 slide and sightline rows stand (the jack-head sightline
   moved to y 143.05). `cradle_frame()` in the build computes the rows' numbers at 1.2 × FS of a 50 kg cell (589 N),
   E 2500:
   - The upright is a beam across x between the walls, in the layer plane. Taking a conservative band only as tall as
     the upright is thick: **6.1 MPa** (row limit 20).
   - The share of the load the upright sends down to the base, the only path across layers: 5 %, **1.2 MPa** (limit
     10).
   - The walls and base as a U section, with the axis 31 mm above its centroid: **2.0 MPa** (limit 15).
   - Jack tilt: **0.16°** (limit 0.5; a5: 6.4-7.6°). As a jacking couple on the pull stop, with 0.25 mm swivel play
     added: 0.001 FS.
   - Push stroke: **0.41 mm** (frame 0.05 + upright 0.06 + the largest stop setting 0.30) against 7.0 mm.
   - The reviewer's a5 rows, adopted verbatim, also pass. They model the upright as a free cantilever with no walls,
     so they are a bound: 17.7 / 7.1 MPa across layers for the 50 / 20 kg cell (limit 25), and jack stroke 0.93 mm
     (limit 3.0).
   - README step 7 now stops the over-travel check at a 130 % reading, about 1.5 × FS on the jack, under 8 MPa. a5
     said only "past 120 %", which the stop path could have turned into kilonewtons.
2. **Scale before stops.** The sketch refuses `m` until `f`, `r <mV/V>` (or `c <kg>`) and `t` are given. The new
   `k <kg>` command is a known-mass check: PASS at 0.90-1.03 of the mass. The lower bound allows for the leaf shunt
   (1-10 %; `head_calc.txt` 10). `fsKg` defaults to 50.
   - README step 4 does it on the bench: `f 50`, `r <label mV/V>`, then the known-mass check. For the check, lift the
     jack nut out and stand the cradle on its rear face across two books, with the jack head in the gap. Tare, hang
     the mass from the jack head, `k 10`. The pull goes plug -> cell -> block -> lip screws, the pull-stop path. On
     FAIL, or with no label, `c 10`. Then re-tare base down.
   - Calibrating with `c` reads grip force, so the stops land on the safe side by the shunt.
3. **Cell committed.** The BOM and README say: buy two 50 kg pucks (Alex to confirm). The 20 kg puck is a
   documented fallback with its limits: 1.44-1.92 × FS at 600 N, and a 50 N side load brings a push stop in at about
   150 N. Use it only with a 2 × FS datasheet overload.
4. **Crosstalk.** Not designed out. Putting the leaf mid-length on the cell axis needs the top link above the axis
   and the socket out of it: a new cartridge and fin cavity, an outline-level change that needs the 2D/3D agreement
   first. Instead:
   - `head_calc.txt` 8 models it (reviewer a5 section E): 3.8 %, 5.7 N at the 150 N lean limit, E cancels.
   - The README documents a **10 N per-grip dead band** for the RTPS firmware (not in this repo), and README step 12
     measures each grip's coefficient (5 kg at the grip end). The dead band is max(10 N, 150 N × measured × 1.5).
   - Adopted row a5R crosstalk: 5.69 N against 10.
5. **Lip lever.** `head_calc` section 4 and `leaf_stress()` (`lip_drop_buckle`) now turn the link about the leaf
   centroid. Contact is at 182-254 N (a5 text: 160-220). `lip_drop_buckle` is 1.14 (a5: 1.70), and the lip stack row
   still passes (0.9 < 1.14). The README says 180-250 N and a 5.3× leaf margin at contact.
6. **No soldering.**
   - The amps are now the Adafruit HX711 (product 5974), which has a pre-soldered 6-way screw terminal for the cell.
     Its footprint comes from the Adafruit fab print: 25.4 × 22.86 mm, four Ø2.5 holes 0.1 in from the edges. The
     stand-in is built in `amp_board()`, with the terminal outboard toward the lead and the logic header inboard.
   - The holes are too small for the kit's M3, so each board sits on four plain 4 mm standoffs with hot glue. The 4
     M3 × 8 board screws are gone.
   - The README wiring section and steps 6 and 8 use the screw terminal, and the sketch header is updated.
   - Two flags in the BOM: the logic header ships loose (buy it fitted, or fit it once; it is never touched on a cell
     swap), and the 2 mm flat blade the terminal needs may not be in the DeWalt kit.
7. **Lip friction.** The README now states the limit plainly: no more than 150 N (15 kg) on a grip while pushing.
   The lip detail is unchanged (see below).
8. **Stale text.** The flexures rows now say r = leaf_r 2.0. The moving-config text about "fin cavity at 1.0" was
   dropped. The BOM, README, HANDOFF and gen_bom point at the a6 reports.

### Not fixed, or changed only partly

- **Crosstalk** is handled in firmware only (above). The leaf-on-axis layout is flagged for Alex as a cartridge and
  fin-cavity change.
- **Lip friction:** I found no friction-reducing lip detail inside the brief. PTFE tape is out, and a narrower land
  changes the contact stress, not μN. The 150 N limit stands, and readings past lip contact are not trusted.
- **HX711 logic header:** one solder joint is left unless the boards are bought with headers fitted. **Terminal
  blade:** a 2 mm flat blade, possibly not in the kit.
- **Known-mass check setup:** the cradle stood across two books with a mass on a cord is a bench improvisation. It is
  not modelled as a check row.
- **Side load** (0.17 FS at 20 N), **cartridge play** (0.1) and the **piston at 40 MPa** under a 600 N lean are
  unchanged from a5.
- The cradle grew 35 g. It still fits the P1S bench plate (100 × 107 used).
- Stale round-1 renders `05_junction.png` and `07_lead_closeup.png` are still untracked in renders/. `hx711.stl`
  (SparkFun) is unused.

Review (a6/review.md), ranked: (1) setting-plug T-slot rear lip 2.1 mm carries the whole pull-stop
load (17-22 MPa shear, layer plane) -> 5.0 mm lip; (2) HX711 logic header ships loose: soldering still
needed -> press-fit header or module sold with header; 2 mm slotted bit; (3) dead band sized for 150 N
but nothing stops a lean before the lip at 182-254 N -> wider band; long term leaf mid-length on the
cell axis; (4) known-mass check advisory, pull calibration flips sign, false FAIL at 0.889; (5) lip
friction limit README-only; (6) doc inconsistencies (step4 explodes the coupler downward; x1.6 vs x5.3);
(7) improvised known-mass rig -> printed hanger + feet. Functionality not 9 without the crosstalk fix.

## Attempt 7

Results (full resolution, voxel 0.6):
- `cad check` main (`cadcheck_a7.json`, same `--only` as a6): **0 fail, 51 warn, 0 untriaged**, no stale accepts.
  123 objects, 61 screws / 24 nuts, 19 assembly steps, 35 stacks (a6's 22, with the reviewer's four a6 rows adopted
  and adapted + 9 new a7 rows), 6 flexures.
- Moving-link + bench rows (`cadcheck_a7_movlink.json`): **0 fail, 0 warn**.
- `cad printcheck cad/print/stl --out cad/review/a7_designer/`: **18 parts, 0 fail, 20 warn**. `cad bom`: **PASS**, 13
  rows. `check_wires.py`: OK (first bend 25.4 from the cell axis, R13, touches nothing). Firmware: host syntax check
  with stub headers (ESP32 and AVR paths).
- Estimate: 1,315 g, 26.4 h (cartridge 53 -> 79 g, cradle 114 -> 139 g, hanger 3 g).

Scores pending review.

### What changed, by a6 issue

1. **Setting-plug lip (major).** The T-slot is 2.9 mm further forward, so the rear lip is 5.0 mm (a6: 2.1). The jack is
   an M5 × 35 (head 9.1 mm off the upright; the plug runs to 2 mm in front of it). Adopted rows a6R: 7.2 MPa at 1.2 ×
   FS and 9.0 MPa at 1.5 × FS (a6: 17.2 / 21.5; limit 12). README step 7 now stops at 125 %.
2. **No soldering (major).** The amp is now the SparkFun Qwiic Scale (NAU7802, SEN-15242). The cell's four wires go
   into a push-lever spring terminal, and the logic side is a Qwiic socket with a ready-made Qwiic-to-female-socket
   cable (PRT-14988 / Adafruit 4397) to the ESP32 header. No iron, and no 2 mm blade either: the lever opens with a
   fingertip, so the README tool list says the blade is not needed (the reviewer's 2 mm bit was for the a6
   terminal).
   - Footprint 25.4 × 35.6 with four Ø3.3 holes, from SparkFun's Eagle files via the forum (**not verified on a
     board**: README/BOM say to check). The boards now take the kit's M3 × 10 on 6 mm standoffs (a6: hot glue).
   - The fixed I2C address means one ESP32-P4 I2C port per board.
   - The bench sketch is now `firmware/bench_scale/bench_scale.ino` (SparkFun library); `bench_hx711` is gone.
3. **Crosstalk in hardware.** The cell moved to the leaves' mid-height (cell axis z -28.5, 28.5 below the grip axis).
   - **How.** The link reaches down to the cell with a "drop" carrying the rear seat boss, the rear nut bore and the
     four stop nuts. The block, stops, keys and cradle windows all moved down with the cell. Each leaf is now two
     12.5 × 2.5 strips (|x'| 7.5-20; the cartridge is 40 wide, a6 36), so the rear-nut driver can pass between them.
     The pitch is held at 45 by moving the rear leaf back (link1 123, a6 110).
   - **Result.** A lean turns the link about the cell and bends no leaf: 0 N at any lean (a5R row adapted: the
     hard-coded 15 became the param `leaf_top_below_cell` = -13.5, and 2 × cart_hw became `leaf_b`). A 0.5 mm print
     error in the cell height gives 0.1 % (head_calc 8).
   - **The push.** It still acts on the grip axis, so it pitches the link about the cell. Rotation about the leaf
     mid-length bends no leaf. The push stops are on the cell axis; the pull pair 6.5 below sees it, but the jack
     loads exactly as the grip does, so the setting includes it.
   - **Dead band kept as a backup.** It is max(10 N, 210 N × |c| × 1.2), where 210 N is the largest lean the strips
     carry before the catch (#5). README step 12 measures c (expect < 0.2 %, reject > 1 %) and records its sign.
   - The adopted a6R crosstalk rows were adapted the same way: lean = catch_contact_hi_n, threshold 1 %. Both pass
     (0 N; 2.1 N against 10).
   - Found and fixed on the way: **the a6 cell could not be fitted**. Both stud holes were round, on either side of a
     14.7 mm gap, and the cell with studs is 37 mm long. Now both holes continue as a 45° slot up-inboard to the
     inboard face, and the drop's nut bore as a Ø14 channel the same way. The cell slides in with its rear washer and
     nut already on (README step 1). The seat bosses are Ø12, split by the slot.
4. **Sketch.** `m` is refused unless the known-mass check passed; `m!` overrides with a warning. `c` stores a pull
   calibration as negative, so push reads + (README step 5). On the mV/V path, `k` sets the sign from the known pull.
   `f`, `r` and `c` clear the check. The PASS window is 0.88-1.03. head_calc 10 notes that a soft 20 kg cell (dFS
   over about 0.17) still fails falsely and goes to `c`, which is safe.
5. **Lean limit enforceable.**
   - Behind the rear leaf the fixed body has a **catch saddle** under the piston, 0.10 mm radial. It stands on two
     2.5 mm legs (stiff in z, about 28 N/mm in y).
   - A lean of 147-206 N per grip (E 2500-3500) lands there. Past it the legs follow the piston, so friction can't
     shunt the cell: at most 3.3 N for dFS 0.10, and 8.3 N at the largest setting (row, limit 10).
   - **There is no lean limit for the reading any more**; README's 150 N limit is gone. Rows:
     - catch before the barrel lip at the tolerance extremes: 412 vs 418 N
     - legs at a 600 N lean: 1815 vs 3402 N buckling
     - push-induced pitch at the catch: 0.072 vs 0.10 mm
     - piston at 600 N: 52 MPa (limit 60)
   - The barrel lip (lip_c 1.0, a6 0.7) is now a backup. The strips at catch contact carry 470-650 N against
     4400-6200 N to buckle (× 9.4).
6. **Docs.**
   - step4 now lifts the coupler above its pad (`rj_up`).
   - head_calc 4 now prints one model with both effects, plus the link-only bound labelled as the stack row's
     conservative case. a6's x1.6 / x5.3 mismatch is gone; the README quotes the same × 9.4.
7. **Known-mass rig.**
   - The cradle has a hang eye on its front wall, on the jack axis: a lug above the nut-driver hole with a 45°
     underside.
   - A printed stirrup hanger: its keyhole tab sits on the shank under the jack nut (run up to the head), two arms
     pass the nut and the head, and the cord sits in a notch in the cross bar on the axis. So the hook, the jack and
     the mass hang on one vertical line.
   - Rows: the cross bar at 11.7 MPa (2 × 10 kg, limit 20); the eye ligament 1.3 MPa across layers; zero offset.
   - **The reviewer's suggested feet were not used.** Stood on a table edge with a 10 kg mass hung beyond the support,
     the cradle tips over. Hanging it removes the support question.

Other changes:
- Fin bolts moved for the longer cartridge (internal only; the external outline is unchanged, 02_side identical):
  - M4 box bolts (128,-20) -> (141,-18) and (118.3,-46) -> (110,-56)
  - clamshell M3 (138,-22) -> (88,-58)
- The tray end-wall holes follow.
- The lead leaves the cell up-inboard at 45° (the cell is clocked) and makes one R13 bend into the tray high on the
  end wall. In the tray it makes two R13 bends, down the wall and inboard to the terminal. `check_wires.py` now takes
  the cell axis from the build params.
- Cradle: walls 6 mm at the wider cartridge; lead notches open to the top in both walls; plain Ø16 nut-driver hole on
  the cell axis (the block is 1 mm longer, so the stud tip no longer pokes out).
- Piston-screw counterbores are 2 mm deeper (the link is 2 mm wider), keeping 2 d of thread.

### Overhangs (>45°, located on the STLs with a6/scripts/steep_strip.py)

- **cartridge 685 mm².**
  - Flat roofs of the side-open stop-screw slots (x' 10-15, as a6).
  - The underside of each upper strip over the gap between strips: a 26.7 mm bridge, 2.5 wide, anchored at the
    ground bar and the link (printcheck warn).
  - The catch saddle's teardrop cut.
- **cradle 551 mm².** The hang lug's 45° underside (194 mm² at 44-46° on facets), the lead-notch and key-window roofs,
  and the lip-screw teardrops (max bridge 3.1).
- **fins about 4,000 mm².** The flat roofs of the closed cartridge pockets at |x'| 20.1/21: spans 7-21, accepted
  warns. a6 had the same roofs at |x'| 18.1/19. Plus 1.1 mm ledges.
- **hanger 0.**

### Not fixed, or open

- **Qwiic Scale hole pattern** is taken from a forum reading of SparkFun's Eagle files, not a board in hand.
- **Strip-gap bridge:** each upper strip starts over a 26.7 mm bridge. It is printable on the H2D/P1S, but it is a
  flexure; sagged first layers only trim the strip's inner edge (12.5 wide).
- **Side load:** 0.185 FS at 20 N (row limit 0.2; a6 0.17): the strips are softer in x than a6's full leaves.
- **Piston:** 52 MPa at a 600 N lean (a6 40 at the lip), because the catch is nearer the socket. 26 MPa at 300 N.
- **Catch:** c 0.10 is small. If the saddle cut prints undersize it touches at rest, which only adds its 28 N/mm
  shunt (calibrated out). The barrel lip is the backup if it prints oversize: the tolerance row passes 412 < 418.
- **Moment share** with the strips is 5-8 % (a6 2-7 %).
- **Firmware** is syntax-checked only. The RTPS side (not in this repo) still needs the backup dead band and the two
  I2C ports.
- **The external outline is unchanged.** The cartridge is 13 mm longer inside the fin, and the cradle is 25 mm longer.
- Stale round-1 renders `05_junction.png` and `07_lead_closeup.png` are still untracked in renders/.

Review (a7/review.md), ranked: (1) BLOCKER: the cell cannot be fitted: the 45 deg stud slots and nut
channel end 0.2 mm inside the cartridge's inboard face (open 3.2 mm across the motion for a 4.9 mm
stud; channel 6.7 vs 9.24 nut); missed because a cartridge x cell allow blinds the slide row and the
insertion check skips same-step parts -> d = cart_hw + half + 1; (2) catch friction shunt 13-33 N, not
3-8 (saddle held square) -> R1.2 crown on the saddle; (3) load sharing past catch contact wrong (x3.1-4.7
to buckling, not x9.4); (4) 1.6 mm printed washers over the stud slot ~35 MPa -> 2.4 mm; (5) catch gap
0.10; (6) piston 52 MPa at 600 N lean; (7) assembly_order text puts stops before the cell; (8) Qwiic
Scale footprint and ESP32 header pins unverified; (9) cover screw heads read as black holes.
Process lesson: an `allow` on a pair blinds slide rows through that pair; insertion rows need the
mating part in an earlier step.

## Attempt 8

Results (full resolution, voxel 0.6):
- `cad check` main (`cadcheck_a8.json`, same `--only` as a7): **0 fail, 51 warn, 0 untriaged**, no stale accepts, no
  unbounded allows. 123 objects, 61 screws / 24 nuts, 25 assembly steps (a7: 19; each cartridge is now four bench
  steps), 19 slides (13 + the six adopted a7R cell-path rows), 43 stacks, 6 flexures, 72 distances.
- Moving-link + bench rows (`cadcheck_a8_movlink.json`): **0 fail, 0 warn**, 20 slides, 9 sightlines (4 new: the
  nut-driver line to each rear cell nut).
- The a7 review rows (`cad/review/a7/review_rows.json`) are all in `checks.json`: the three cell-path slides (mirrored
  for L), the rear-strip row verbatim, and the shunt and washer rows adapted. All pass. See below.
- `cad printcheck cad/print/stl --out cad/review/a8_designer/printcheck.json`: **18 parts, 0 fail, 20 warn**. `cad
  bom`: **PASS**, 13 rows. `check_wires.py`: OK. `head_calc.py` reruns from the manifest.
- STL probe along the cell's whole 45° path (`cad/review/a8_designer/scripts/probe_path.py`, reviewer a7's ray-parity
  point test on `cad/print/stl/cartridge_R.stl`; output in `a8_designer/stl_path_probe.txt`): the narrowest opening
  across the motion is 5.5 mm in both stud slots (stud 4.9) and 14.0 mm in the nut channel (nut 9.24 AC, washer Ø13).
- Estimate: 1,323 g, 26.5 h (a7: 1,315 g, 26.4 h).

Scores pending review.

### What changed, by a7 issue

1. **The cell fits (blocker).**
   - `stud_slot()` now ends at d = cart_hw + half + 1 in x and in z (23.75 for the stud slots, 28.2 for the Ø14.4 nut
     channel), so each slot runs out through the inboard face. The channel's top corner cuts the link's lower inboard
     side over y 64-73. It stops at the socket shoulder (y 73) and stays 1.2 mm under the socket's D-flat.
   - **No blinding allow.** `PRT_cartridge_* > BUY_load_cell_*` is gone. It had measured 0.0 mm³ in a7 (zero-gap seats),
     so it hid slide rows and protected nothing. The cell × cartridge pair is now in interference, slide and insertion.
   - **Insertion sees the cartridge.** Each cartridge is four bench steps: the empty cartridge; the cell with its rear
     washer and nut (`insert_dirs` along the 45° line); the front washer and nut; the stop hardware. Then a merge into
     the inboard half. The insertion check finds the 45° line as the cell's only free direction.
   - **Rows.**
     - a7R 'cell first' (cell + rear washer + nut, 45°, 90 mm): free, closest PRT_cartridge_R at 0.0 (the faces slide
       on the seat bosses).
     - a7R rear nut + washer through the channel: free.
     - a7R 'stops already in': adopted as an end stop, blocked by FST_Stop_screw_push_R_in at 4 mm. The order in
       README step 1 and in `assembly_order` is now cell first.
     - All three are mirrored for L.
   - README step 1 adds the zero-gap seat note (press the link back about 15 N for 0.1 mm if the cell is tight) and a
     new render, `step0_cartridge.png`.
2. **Friction shunt (major).**
   - The saddle touches the piston only on an R1.2 crown across y (`catch_crown_r`), 0.5 relief either side
     (`saddle_cut()`, one lofted teardrop solid).
   - `catch_k` is now the free-saddle value with the contact h = 7.85 above the leg tops, 2 / ((L³/3 + hL² + h²L)/EI):
     11.2 N/mm. Reviewer a7's formula; their own number was 10.2 with h 8.9.
   - Rows: 1.35 N (dFS 0.10) and 3.37 N (largest setting), limit 10. The a7R stiff-bound rows are adopted and adapted:
     the crown is the reason the guided bound no longer applies.
   - New row: a crown that a 600 N lean has flattened (land N / (2 × 10 mm × 80 MPa)) holds a moment worth 0.0476 N per
     N·mm. At a later 300 N lean that gives 7.4 N < 10.
3. **Load sharing past contact.**
   - `head_calc.py` 4a uses reviewer a7's contact model; `leaf_stress()` uses it too.
   - 4d is the three-support solve. The catch is the legs in series with the saddle's bending and shear over the
     driver gap, with the legs alone as the stiff bound and a third as the soft bound.
   - Rear strips at a 600 N lean: 1043-1542 N against 4407 to buckle (E 2500, L 27): **× 2.9 at worst** (× 3.3 on Le
     25). The README quotes this.
   - Rows: a7R verbatim 1345 < 1469; a8 soft bound 1542 < 4407/2.5.
4. **Washers 2.4 mm** (a7: 1.6). a7R row adapted to the param `washer_r[1]`: 11.4 MPa < 20. Both stacks still reach:
   the front stud tip is 0.05 past its nut, the rear 1.05.
5. **Catch gap.**
   - catch_c 0.15 (a7: 0.10). Contact is at 200-280 N (reviewer model). A full 1.2 × FS pull lowers the piston 0.072
     at the catch, and a further 105 N of lean closes the rest (E 2500). Row: pull + 100 N lean = 0.147 < 0.15.
   - lip_c is 1.2 (a7: 1.0), so the lip still comes after the catch at the tolerance extremes: 467 < 491 N (row).
     Lip drop at buckling 1.40 < 1.447 (row).
   - README stop-setting step 1 adds the hand check: the plug slides through the saddle by hand, and 80 g/m² paper
     (about 0.1 mm) passes between the plug and the crown.
6. **Piston.**
   - Ø24 (`piston_d`) in the socket and past the catch, a 45° step to the Ø22.2 spigot at y 141 (`piston_step`).
   - The socket, the setting plug and the fin bore (now Ø26.6, wider than the lip) follow.
   - At a 600 N lean: the mouth 45.2 MPa (the bound: no relief from the catch reaction), the catch 42.3, the spigot at
     the step 45.6. **× 1.67 on 76.** Row limit 47.5 (76/1.6).
   - Found on the way: a7's row checked only the section at the catch. The socket mouth carries the same moment or
     more, about 56 MPa on Ø22.2.
7. **Step text.** The a7 single cartridge step (stops before the cell) is replaced by the four steps above. Their text
   matches README step 1.
8. **Purchased parts unverified.**
   - README and BOM mark the Qwiic Scale hole pattern "measure before printing the trays". They mark the ESP32 header
     pins "check before ordering the cables" (alternative: Qwiic-to-male-pin cables, still no iron).
   - The amp standoffs are now drill-to-fit pads (Ø10, solid, a centre dimple; the cadlib `drill_to_fit_boss` idea).
     You drill Ø2.5 through the board's holes, and a hole up to 1.5 mm off still leaves 1.5 mm of wall. The README tool
     list adds a Ø2.5 bit.
   - The ESP32 keeps printed pilots: Waveshare's drawing.
9. **Cover heads.**
   - The cover's holes are exact cuts after the SDF pass, with a 0.5 × 45° chamfer on each counterbore rim (a7: voxel
     cut, soft rims).
   - The black dots were mostly the heads themselves: plain mirror-steel cylinders reflecting the dark world. The screws
     are now satin steel, with a render-only drive recess (`Render details` collection, not exported). In 03 and 08
     they read as Phillips pan heads in chamfered counterbores.

### Self-review (README guide walked against the model), and what it found

- **The saddle bends across the layers.** The cartridge prints inboard face down, and the saddle spans the 15 mm
  nut-driver gap in x. a7's 2.5 mm saddle would see about 43 MPa across layers at a 600 N lean. It is now 9.5 thick in y
  (y 124.5-134, 1.5 behind the link; the legs stay 2.5): 14.2 MPa (point-load bound, limit 15), and 3.5 at 300 N.
  - The ground bar ends 1 mm further back, so the cradle grows 1 mm.
  - The fin's catch slot follows. The C-roof warn reads 45.5 (a7 43.3): the layer map gives 9-18 mm real spans.
- **Catch-leg buckling** now models the saddle 7.85 above the leg tops (fixed base, held at the contact, free to turn on
  the crown): 2181 N against 738 N at 600 N (× 3.0). a7's 3402 ignored the offset.
- **Lift.** With lip_c 1.2 > cav 1.0, a pure translation now meets the link cavity first, so the a3R lift row was
  adapted to that. A real lift turns the link about the cell, and then the lip lands first (new row: 0.56 < cav).
- **Rear nut access had no row.** New sightlines run from behind the cartridge along the cell axis. Rim rays at r 6.2 (a
  Ø12.4 socket) land on the rear washer, past the saddle, legs, strips and ground bar; rays at r 3.5 land on the nut.
- **The bench jack-key sightline** had a hard-coded origin (it broke with the 1 mm cradle change). It now reads
  `=bench_jack_at + 5.05`.
- **Fin bore vs the M4 nut slot.** The wider bore for the Ø24 piston left 1.0 mm over the (141, -18) nut slot. That box
  bolt moved to (141, -19), which leaves 2.0 mm. A tray ledge grows to 2.0 mm (accepted, under the 3 mm limit).
- **Clamshell counterbores** are Ø7.0 on the hidden inboard face. At full resolution the voxel cut left 0.25 radial and
  one head read as buried.
- **Accepts narrowed.** The blanket `PRT_cartridge_` accept is now four exact-text accepts (walls, overhang) plus the
  26.7 mm strip-bridge accept. The 0.07 thin-wall point was traced to the drop root fillet's tip where the nut channel
  ends.
- Walked all 12 README steps against `assembly_order`, insertion and fastener access: every part has a free straight
  path at its step, and every screw is reached with the kit. The cell needs the 45° line (step 0 render). The piston goes
  in along -y, through the Ø24.6 lip bore. The fin-to-tray M4s and the ESP32 screws need the 150 mm extension (as a7).

### Overhangs (>45°, a7's steep_strip.py on the STLs)

- cartridge 793 mm²: a7's 685, plus the longer 45° slot and channel flanks (45° nominal) and the saddle's teardrop.
  printcheck: max ledge 1.0, the 26.7 strip-gap bridges as a7.
- cradle 551, fin 4,070 (pocket roofs), tray 877; cover, piston, plug, hanger 0.

### Not fixed, or open

- **Shunt during a heavy lean.** While 600 N rests on one grip, a flattened crown can hold the saddle nearly square:
  up to about 20 N at the largest stop setting (13 N for a typical cell). That is over the 10 N dead band, but only while
  the lean lasts. Under 10 N for leans up to 300 N (rows). The flattening model (10 mm contact, 80 MPa) is an estimate.
- **Rear strips × 2.9** to buckle at a 600 N single-grip lean (E 2500, L 27, soft-catch bound). Reviewer a7's model gives
  × 3.1.
- **Saddle across layers** 14.2 MPa at 600 N, against 15. It is a point-load bound; the crown's contact spreads along the
  bore.
- **Pull + lean margin** 105 N at E 2500. If it lands, the free legs add about 1 N.
- **Purchased parts.** The Qwiic Scale pattern and the ESP32's male header pins are unverified (now marked, and the pads
  tolerate the first).
- **Firmware** is syntax-checked only. The RTPS dead band is now max(10 N, 280 N × |c| × 1.2).
- **Zero designed gap** between the cell faces and the seat bosses during insertion. The leaves give 0.1 mm at about
  15 N.
- Stale round-1 renders `05_junction.png` and `07_lead_closeup.png` are still untracked in renders/.

Review (a8/review.md, final), ranked: (1) no infill/wall settings anywhere: at slicer defaults the
piston and catch saddle are overstressed -> 100% infill for piston, cartridges, washers, setting plug
(per object in the 3MFs + BOM column), fins/trays 4 walls 25%; (2) right amp's Qwiic cable uses 142.8
of 150 mm and ties the halves together before they're hung separately -> plug it after mounting, or a
200 mm cable; (3) catch shunt 12-20 N while 600 N rests on a grip; (4) piston 45 deg step 59-68 MPa
with Kt -> R4 fillet at y 147; (5) rear Ø13 washer 20.5 MPa over the slot -> 3.0 mm; (6) README "100 N
lean" margin is really 85 N; (7) fin-to-tray M4s need a 3 mm ball-end hex key (not listed); (8) fin
pocket roof spans ~23 mm; (9) cradle print details; (10) Qwiic Scale holes / ESP32 pins unverified.

## Outcome

Stopped after 8 attempts without reaching 9+ on all three. Best: a8 8/8/9 (a6 also 8/8/9). The a8
majors are documentation/settings and cable-order fixes, not geometry; see a8/review.md.
