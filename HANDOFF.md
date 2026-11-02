# Push-assist handle concept: handoff (updated 2026-10-27, design/review loop attempt 8)

Wheelchair push-assist handles for rammp-org/space-bar-push-assist. One tension/compression
load cell per handle (20 kg JHD puck, chosen by Alex 2026-10-27: no hard shoves) (sum = forward force, difference = turning), read by two SparkFun Qwiic Scales (NAU7802; spring terminal + Qwiic cable, no soldering) and a Waveshare
ESP32-P4 PoE devkit, sent to the MIB over RTPS. This repo holds the printed-part concept; the
Onshape doc holds the bought-part models (see `~/code-stuff/onshape-slopify` for API access).

## Where things are

| Path | What |
|---|---|
| `cad/blender/build_concept.py` | The whole concept. Parametric Blender script: SDF-built printed parts, STL bought parts, lead routing, print check, renders. |
| `cad/blender/to_cadcheck.py`, `checks.json`, `manifest.json` | cadlib conversion and the `cad check` config; every motion, gap and service claim is a row. Run via the pipeline in `cad/review/attempts.md`. |
| `cad/blender/check_moving.blend`, `checks_moving.json` | `check.blend` with each cartridge split into check-only `PRT_cartfix_*` / `PRT_movlink_*`, plus a copy of the right cartridge in the cradle (written by `to_cadcheck.py`); moving-link and bench rows. Run with `--only slide,distances,sightlines`. |
| `firmware/` | ESP-IDF + espp app (ESP32-P4): two SparkFun HX711s (left CLK/DAT GPIO 21/20, right GPIO 5/4), zero tracking, forces served over ethernet (espp stream_frame on tcp :5555, `PUSH?` discovery on udp :5556) to `web/dashboard.html` through `tools/eth_bridge.py`; `tools/mock_board.py` stands in for the board. See `firmware/README.md`. |
| `docs/MIB-INPUT-DEVICES.md` | Devices measure, the MIB decides: how the MIB takes input devices, the reference push-to-drive conversion, and what is left per repo. |
| `cad/calc/head_calc.py`, `head_calc.txt` | Hand calcs from the manifest params: leaves, the cell's moment share, clamp stress, stop engagement and thermal drift, lip catch (leaf-centroid lever), lean crosstalk + dead band, cradle frame, known-mass check window. |
| `cad/blender/gen_bom.py`, `cad/BOM.md` | BOM generated from the manifest; `cad bom` checks it. |
| `cad/blender/export_prints.py` | Print STLs and 3MF plates into `cad/print/` (empties the folder first, keeps `stl_cc/`). |
| `cad/review/` | Design/review loop: `attempts.md` (history, scores, what changed), reviewer reports per attempt, `cadcheck_aN.json`. |
| `cad/blender/renders/*.png` | Current renders. `01_hero`, `02_side`, `03_handle_closeup`, `04_top`, `05_exploded`, `06_internals`, `07_lead_side`, `08_head_open`, and the README step renders `step0_cartridge` (a8: the cell going in along the 45 deg slots) to `step5_stop_setting`. |
| `cad/blender/renders/print_check.txt` | Each printed part's size in its print orientation vs the H2D bed. |
| `cad/profile/profile.py` | 2D side + back profile on the chair plate, for agreeing shape before 3D. |
| `cad/chair/*.stl` | Corpus bodies exported from the STEP by an agent that was stopped early; unverified frame. |
| `cad/blender/check_wires.py` | Lead clearance check: bend radius, straight run off the sensor, no contact with solids. |
| `cad/blender/parts/*.stl` | Bought parts exported from Onshape by `export_parts.mjs` (load cell, ESP32-P4, RJ45 coupler, MTB grip; `hx711.stl` is the old SparkFun board, unused: the Qwiic Scale stand-in is built in `amp_board()`). |
| `cad/blender/push_assist_concept.blend` | Last build, saved by the script. |
| `cad/featurescript/*.fs` | Onshape FeatureScript sources for the bought parts. |
| `/tmp/build_concept.v2..v5.py` | Backups of earlier concept rounds (not in the repo, will vanish). |

`05_junction.png` and `07_lead_closeup.png` in renders/ are stale (round 1); the script does not make them.

## How to run

```bash
# Full build + all renders (about 6 minutes)
/Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py
# Only some views
/Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py -- 01_hero 02_side
# Quick coarse build to flush errors (voxel 1.2 instead of 0.6)
PA_VOXEL=1.2 /Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py -- 01_hero
# Lead clearance check on the saved blend
/Applications/Blender.app/Contents/MacOS/Blender -b cad/blender/push_assist_concept.blend -P cad/blender/check_wires.py
```

Blender 5.1.2. Axes in mm: X across the chair, Y rearward toward the attendant, Z up. See round 6 for the origin. All design numbers are in the `P` dict at the top of the script.

## Current concept (round 6, Corpus mount)

The chair is now a Permobil Corpus seat (STEP: `~/Downloads/Permobil_F5_Corpus_seatAlex.stp`). Its
back is a plate of vertical 4040s, 15° past vertical. Shape was agreed in 2D first with
`cad/profile/profile.py` (`profile.png`, side + back view); port changes there before the Blender build.

- **Frame:** origin on the plate's rear face at grip axis height. `on_plate(u, n)` / `PLATE_M`
  map plate-local coordinates. No 4040 spine of our own.
- **Section:** level top at the grip axis, 60° rear face, front face flat on the plate for a 40 mm
  land then turned 15° off it (vertical). Bridge 92 tall (clears the central block 4 in below the
  plate top, 3 in proud); fins 140 tall carry the wedge. Lip at y 150.
- **Mount:** six M5 socket caps into 40-series drop-in T-nuts: four through land bosses at x ±40, ±120,
  two through feet by the floor at x ±120 (driven from below through a Ø14 floor hole with a 150 mm
  extension). 9-bar plate assumed: 360 wide, slots 40 apart.
- **Fin to bridge:** three M4 × 20 socket caps from inside the tray into nuts in slots on the fin's split face.
- **Head (attempt 7):** a self-contained printed parallel-leaf flexure cartridge carries the cell. Fixed: an 11.5 mm
  block + ground bar + a catch saddle behind the rear leaf; the front stud clamps the cell to the block (Ø15 printed
  washer and M5 nut in a Ø16 counterbore in the block's front face). Moving: the top link (piston socket on the grip
  axis) and a drop that reaches down to the cell; two leaves, each two 12.5 x 2.5 strips (r 2 roots), pitch 45. **The
  cell axis is at z -28.5, the leaves' mid-height**, so a lean turns the link about the cell and bends no leaf: lean
  crosstalk 0 (a6: 3.8 %). Both stud holes continue as a 45 deg slot to the inboard face, and the drop's nut bore as a
  Ø14.4 channel, so the cell (rear washer and nut on its stud) slides in; a6's round holes made it impossible to fit,
  and a7's slots stopped 0.2 inside the inboard face (a8: d = cart_hw + half + 1 in `stud_slot()`, proven by slide,
  insertion and STL-probe rows with no cartridge x cell allow).
  Each cell face bears on a Ø12 x 1.0 boss (split by the slot). Nuts finger-tight on the bare 8 mm bit, settled
  overnight, re-snugged, hot glue, on the bench (rear nut from the cartridge's rear end along the cell axis between
  the strips, on the 150 mm extension). Stops: four M3 caps beside the cell, nuts in the drop, heads on the block; push
  pair on the cell axis, pull pair 6.5 below; set per cell in the cradle with the jack on the grip axis and
  `firmware/` as the gauge. Leans (a8): the Ø24 piston lands on the catch saddle's R1.2 crown
  (0.15 radial, 200-280 N per grip); the crown holds no moment, so the two legs bend as free cantilevers (11 N/mm) and
  friction there takes 1.3-3.4 N from the cell (7.4 N at 300 N after a 600 N lean has flattened the crown; ~20 N
  while 600 N rests on one grip: open). The saddle is 9.5 thick in y because its span over the nut-driver gap bends
  across the layers (14 MPa at 600 N, point load). Past contact the rear strips keep loading: 1040-1540 N at 600 N,
  x 2.9 to buckle at E 2500 (three-support solve, `head_calc.txt` 4d). Piston Ø24 to y 141, then the Ø22.2 spigot:
  45.6 MPa at 600 N (x 1.67). Barrel lip 1.2 radial, the backup. Params `cell_z`, `drop_t`, `leaf_gap`, `catch_c`,
  `catch_z`, `catch_crown_r`, `piston_d`, `piston_step`, `lip_c`, `leaf_*`, `stop_*` in `P`; derived numbers in
  `leaf_stress()`. Printed washers 2.4 thick (a7: 1.6).
- **Bench tools (attempt 7):** cradle + setting plug + mass hanger (printed, P1S plate), M5 x 35 jack screw with two
  nuts, two M4 x 12 lip screws; modelled 250 mm outboard of the right fin, copied with the right cartridge into
  `check_moving.blend`. The cradle is a closed frame (side walls run to a 14 mm upright, R3 roots): 7 MPa in-layer,
  1.4 MPa across layers, 0.2 deg jack tilt at 1.2 x FS of the 50 kg cell. The plug's T-slot rear lip is 5.0 mm (a6:
  2.1). Known-mass check: the cradle hangs from an eye on the jack axis, the mass from a keyhole hanger under the jack
  head (no books). Lead notches in both side walls for the up-inboard lead.
- **Tray (attempt 5):** the centre seam is a 0.8 × 1.0 V reveal like the fin split; the RJ45 coupler sits on a 5 mm
  pad (flange on top, two M3 × 12) so nothing hangs below the floor.
- **Fin skin (attempt 4):** the fin's inboard edges are sharp where the tray and cover continue it (a
  bridge-section stub through the SDF opening, then an exact cut), the split is a 0.8 × 1.0 V reveal, and
  the outboard face has a 2 mm recessed panel 8 mm in from the outline. The a3 lightening window is gone.
- **Cover:** one part across both trays (H2D only, 305.6 long); it joins the two halves.
- **Electronics:** flat on the bridge floor: ESP32 on 6 mm standoffs at x -40, y 37; RJ45 coupler on a pad at
  x ≈ -101, where a 150 mm route with three R20 bends ends (a 200 mm patch cable: 50 mm slack); one SparkFun Qwiic
  Scale per side at x ±100 on four 6 mm drill-to-fit pads (a8: Ø10, no printed pilot; drill Ø2.5 through the board's
  holes) with M3 x 10 self-tappers (Ø3.3 holes from the Eagle files: verify),
  spring terminal outboard; 150 mm Qwiic-to-female-socket cables to the ESP32 header, one I2C port per board (fixed
  address 0x2A). Lead: up-inboard at 45 deg off the boss, one R13 bend into the tray high on the end wall, then down
  the wall and inboard to the terminal (R13). Fin bolts moved for the longer cartridge: M4 box bolts at (24,-18),
  (141,-19) (a8: 1 mm lower, under the wider piston bore), (110,-56); clamshell (138,-22) -> (88,-58).
- Assumed: the tube across the central block does not reach the fins.

## Round 5 (superseded)

- **Box only between the handles.** Tray and cover span x ±159.8. The 4040 is 385 long and ends
  inside the fins. The chair mount is not designed; no posts or clamps are modelled.
- **Each handle is a fin that is the box's end cap.** 36 thick, flush with the box front, back and
  sides, leaning back from the box to the grip. Barrel Ø50 in its top-rear corner as a collar,
  lip at y = 128, grip axis z = 195. Triangular window, recessed 36 × 36 panel on the outer face
  over the M8 that holds the fin to the extrusion's centre bore. Every convex edge R6 from an SDF
  opening pass. Printed as two halves on the centre plane with a 2 × 1.5 parting groove.
- **Fin to box:** M8 into the 4040 plus two M4 from inside the tray through its end wall into nuts
  dropped into slots in the fin from the split plane.
- **Tray:** open-top box, 4040 bay in front of a partition at y = 20, boards bay behind it,
  T-nut bolts into the extrusion's rear slot, standoffs for the boards, RJ45 coupler in the floor.
  Cover is light grey with a 3 mm crown, keys into the extrusion's top slot, M3s into nut slots in
  tray bosses.
- **Load-cell joint (unchanged since round 3):** two sandwiches with plain M5 nuts. Front: 6 mm
  floor between the cell face and nut + Ø15 washer, tightened with an 8 mm spanner in the void
  behind the floor while the halves are open. Rear: piston face between the cell's rear face and a
  nut, tightened with a 1/4 in drive 8 mm socket on a ~150 mm extension down the Ø16 spigot bore.
  Nuts turn, not the cell, so the wire boss lands in its slot.
- **Moment bypass:** piston Ø33 × 45 sleeve in a Ø33.6 bore with a key rib on top. PTFE tape.
  Sleeve friction gives hysteresis that scales with how hard the user leans; fine for push/no-push.
- **Lead:** off the boss, forward along the fin's front margin, down, back over the 4040, down
  into the boards bay, inboard through the end wall. All R13 bends. `check_wires.py` passes.

## Rules Alex has set (do not re-ask)

- PLA on a Bambu H2D (325 × 320 × 325) or P1S (256 cube), R&D test unit. Don't push PETG/CF. Prefer no supports.
- Hardware: only ISO 4762 socket head caps M3-M5 (Alex confirmed 2026-10-27 that "hex head" means internal
  hex), M3 self-tapping screws, M3-M5 nuts, 40-series M5 drop-in T-nuts, superglue, hot glue. **No
  countersunk screws anywhere**: flat-bottomed counterbores, head Ø + ~1 (M3 Ø6.5, M4 Ø8.0, M5 Ø9.5),
  hex-bit access along the axis. Self-tappers into printed pilots are allowed.
- Tools: DeWalt drill with a full bit set (hex bit holder, nut-driver bits); avoid L-key-only access and long
  extensions.
- Handles 14 in apart centre to centre. Handle printed as two halves split down the middle.
- The load-cell lead is 4 mm OD, needs 0.5 in straight off the sensor's side, R13 bends.
- Big shape changes are agreed with Alex in 2D first (`cad/profile/profile.py`): keep the Corpus mount, the
  one-unit wedge (60 deg rear, level top, land then bevel), fins 140, bridge 92.
- Design language (from the product render Alex showed, and the reviewer loop): one radius family
  (`R_out` 6 outside, `R_in` 2 inside, `EB` 1, in `P`), tapered lofts not prisms, one hard shoulder line,
  light upper / dark lower, orderly fasteners. Alex rejected: a diagonal strut with a triangle hole,
  a flared foot, a chin under the arm, and a hull running post to post ("wasteful, over 14 in").

## History in one paragraph each

1. Original: separate handle bolted to the rear of a tray, strut + triangle hole, cell threaded
   into captive nuts both ends. Problems: no moment bypass (a 5 kg lean bends an M5 stud), cell
   couldn't be clocked, looked like parts bolted together.
2. Bent bar handle with a chin, coupling nuts. Alex: "amateur", non-unified curves; wanted the
   handle inset into the box and a simpler joint.
3. Inset bent bar with a tongue in the tray, two-nut sandwich. Reviewer loop (separate agent)
   passed it for an investor demo after one R4 edge family, full-height clamps, single screw
   column, single step at the grip.
4. Hull: crowned two-tone cover, draft, belly, knuckles around the chair posts, raked tapered
   stems with skirts. Alex: wasteful and over the 14 in ask, mount location unknown.
5. Fins (current). Alex is reviewing.

## Open items / likely next asks

- Alex's review of round 5. Expect tuning of `fin_top_front`, `fin_top_rear`, `window`, grip
  reach (`lip_y`), and whether the cover should be dark and flat instead of light and crowned.
- Chair mount: where the back canes land is unknown. When known, the mount should attach to the
  4040 ends or the fins without widening the unit.
- Fin halves print at 320 × 158 × 25, within 5 mm of the bed limit; shrink `fin_top_front` z or
  raise `box_bottom_z` if the real bed is tighter.
- Cover prints crown-up on supports (key and bosses underneath).
- Done in attempt 3: the sliding sleeve is replaced by a parallel-leaf flexure cartridge (see above).
- Done in attempt 4: seat bosses (cell takes axial load only), stops set per cell on the bench, R1.5 leaf roots,
  printed washers, 200 mm patch cable, fin skin (sharp inboard edges, V reveal, recessed panel).
- Done in attempt 5: stops on the cell axis set with an on-axis jack in a printed cradle, 2.0 leaves + lip catch,
  ~7 kN/mm stop path, bench clamp/settle procedure, merged hand calc, tray reveal, RJ45 recess.
- Done in attempt 6: closed-frame cradle (M5 x 30 jack), scale-first bench procedure with a known-mass check, 50 kg cell committed in BOM/README (20 kg documented fallback), Adafruit HX711 with screw terminal, lip lever
  fixed in the calc, crosstalk dead band documented.
- Decided (Alex, 2026-10-27): 20 kg cells, no hard shoves (1.44-1.92 x FS at a 600 N shove). Qwiic Scale holes measured: 17.8 x 25.4 mm.
- Done in attempt 7: lean crosstalk designed out (cell on the leaves' mid-height), catch saddle (no friction path, no
  lean limit), cell insertable (45 deg stud slots), Qwiic Scale (no iron, no blade), 5 mm plug lip, PASS floor 0.88, hang-eye + hanger rig.
- Done in attempt 8: the cell fits (stud slots and nut channel run through the inboard face; cartridge x cell allow
  removed, cell-first steps in `assembly_order`), crowned catch saddle (free legs) 9.5 thick, three-support solve,
  Ø24 piston, 2.4 mm washers, catch gap 0.15 + paper check, drill-to-fit amp pads, chamfered cover counterbores,
  nut-driver sightline rows, step0 render.
- Open (firmware): `firmware/` reads both cells (SparkFun HX711s) and serves them over ethernet to the dashboard;
  no RTPS yet. The MIB side, its dead band max(10 N, 280 N x |c| x 1.2) per grip (README step 12) and what each repo
  still needs are in `docs/MIB-INPUT-DEVICES.md`. The CAD still models the Qwiic Scale boards.
- Open (Alex): verify the Qwiic Scale's hole pattern (0.8 x 1.2 in, Ø3.3, from SparkFun's Eagle files) on a board
  before printing the trays (the pads are drill-to-fit, so up to 1.5 mm off is fine), and that the Waveshare ESP32-P4
  board has male header pins for the Qwiic-to-female-socket cables (else Qwiic-to-male-pin cables).
- Open: the catch's friction shunt can reach ~20 N while a 600 N lean rests on one grip (crown flattened, legs held
  square); under 10 N up to 300 N. Rear strips x 2.9 to buckle at a 600 N single-grip lean (E 2500).
- Open: side load. The stops sit beside the cell, so a sideways force on the grip yaws the link and engages one
  screw early: 0.19 FS at 20 N (free model, dFS 0.1; row limit 0.2). Past 0.25 mm sideways the catch saddle takes it.
- Piston (a8): Ø24 in the socket and past the catch, 45.6 MPa at a 600 N lean (a7: 52).
- Open (Alex): PETG for the two cartridges and four washers if the chair is parked in heat (BOM note); everything
  else stays PLA.
- Open: the load-cell lead length as bought (modelled as at least 200 mm; the route uses 71 mm).

## Memory

Claude's memory for this project is in
`~/.claude/projects/-Users-alxchunlin-code-stuff-space-bar-push-assist/memory/`
(`push-assist-design.md`, `onshape-access.md`). It records the same decisions as above.
