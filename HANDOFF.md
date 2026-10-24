# Push-assist handle concept: handoff (2026-10-23)

Wheelchair push-assist handles for rammp-org/space-bar-push-assist. One 20 kg tension/compression
load cell per handle (sum = forward force, difference = turning), read by two HX711s and a Waveshare
ESP32-P4 PoE devkit, sent to the MIB over RTPS. This repo holds the printed-part concept; the
Onshape doc holds the bought-part models (see `~/code-stuff/onshape-slopify` for API access).

## Where things are

| Path | What |
|---|---|
| `cad/blender/build_concept.py` | The whole concept. Parametric Blender script: SDF-built printed parts, STL bought parts, lead routing, print check, renders. |
| `cad/blender/renders/*.png` | Current renders. `01_hero`, `02_side`, `03_handle_closeup`, `04_top`, `05_exploded`, `06_internals`, `07_lead_side`, `08_head_open`. |
| `cad/blender/renders/print_check.txt` | Each printed part's size in its print orientation vs the H2D bed. |
| `cad/profile/profile.py` | 2D side + back profile on the chair plate, for agreeing shape before 3D. |
| `cad/chair/*.stl` | Corpus bodies exported from the STEP by an agent that was stopped early; unverified frame. |
| `cad/blender/check_wires.py` | Lead clearance check: bend radius, straight run off the sensor, no contact with solids. |
| `cad/blender/parts/*.stl` | Bought parts exported from Onshape by `export_parts.mjs` (load cell, HX711, ESP32-P4, RJ45 coupler, MTB grip). |
| `cad/blender/push_assist_concept.blend` | Last build, saved by the script. |
| `cad/featurescript/*.fs` | Onshape FeatureScript sources for the bought parts. |
| `/tmp/build_concept.v2..v5.py` | Backups of earlier concept rounds (not in the repo, will vanish). |

Nothing is committed yet. `cad/` is untracked.

## How to run

```bash
# Full build + all renders (about 3 minutes)
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
- **Mount:** four M8 button heads through bosses on the land into T-nuts at x ±40, ±120 (9-bar plate
  assumed: 360 wide, outer slots 320 apart vs Alex's ~12 in).
- **Fin to bridge:** three M4s from inside the bridge into nuts in slots that open on the fin split.
- **Electronics:** flat on the bridge floor: ESP32 at x -40, RJ45 coupler behind it, one HX711 under
  each lead at x ±95. Lead: down off the boss, one R13 bend inboard, straight through the end wall.
  `check_wires.py` passes.
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

- PLA on a Bambu H2D (325 × 320 × 325), R&D test unit. Don't push PETG/CF.
- Every screw joint is a countersunk bolt into a captive nut or a 4040 T-nut. Never thread into
  plastic.
- Handles 14 in apart centre to centre. Handle printed as two halves split down the middle.
- The load-cell lead is 4 mm OD, needs 0.5 in straight off the sensor's side, R13 bends.
- Design language (from the product render Alex showed, and the reviewer loop): one radius family,
  tapered lofts not prisms, one hard shoulder line, light upper / dark lower, orderly fasteners,
  parting line as a deliberate groove. Alex rejected: a diagonal strut with a triangle hole,
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
- Revision 2 of the sensor mount could replace the sliding sleeve with two 1.2 mm PLA leaf
  flexures to remove friction hysteresis.
- `05_junction.png` and `07_lead_closeup.png` in renders/ are stale, from round 1; the script does
  not produce them.

## Memory

Claude's memory for this project is in
`~/.claude/projects/-Users-alxchunlin-code-stuff-space-bar-push-assist/memory/`
(`push-assist-design.md`, `onshape-access.md`). It records the same decisions as above.
