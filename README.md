# Space bar push assist

Push-assist handles for a powered wheelchair. A load cell in each handle measures how hard the
attendant pushes. The sum of the two forces is the forward command, and the difference is the
turn. An ESP32 reads both cells and sends push-assist commands to the MIB over RTPS
([rammp-org/rammp-rtps](https://github.com/rammp-org/rammp-rtps)).

This repo holds the mechanical concept: a parametric Blender build of the printed parts, and a 2D
profile script used to agree the shape before building it in 3D.

![Concept on the Corpus back plate](cad/blender/renders/01_hero.png)

## Hardware

| Part | Notes |
|---|---|
| 2x 20 kg tension/compression load cell | Ø25.4 × 12.6 mm puck, M5 studs, one per handle |
| 2x SparkFun HX711 | One amp per load cell |
| Waveshare ESP32-P4 WiFi6 PoE devkit | Reads the amps, talks RTPS over Ethernet |
| Panel-mount RJ45 coupler | Through the floor of the unit |
| MTB grips | Over the printed grip spigots (Ø33 flange) |
| M8 button heads + 4040 T-nuts | Bolt the unit to the chair's back plate |

Printed in PLA on a Bambu H2D. This is an R&D test unit.

## Current design (round 6)

The unit mounts on the back plate of a Permobil Corpus seat. That plate is a row of vertical 4040
extrusions leaning 15° past vertical.

- One unit, not two pods. The bridge between the handles holds the electronics, and each end
  carries a fin with a handle. Handles are 14 in apart.
- The side section is a wedge. The top is level with the grip axis, the rear face slopes at
  60°, and the front face sits flat on the plate for 40 mm before turning vertical.
- The bridge is 92 mm tall so it clears the seat's central block (the one that holds the
  armrests). The fins run down to 140 mm.
- In each handle, the grip pushes a piston that slides in a sleeve. The sleeve takes the bending,
  so the load cell only sees push and pull.

Every screw joint is a countersunk bolt into a captive nut or a T-nut. Nothing threads into
plastic. `HANDOFF.md` has the full design state, history and open items.

## Layout

| Path | What |
|---|---|
| `cad/blender/build_concept.py` | The whole concept. All design numbers are in the `P` dict at the top. |
| `cad/blender/check_wires.py` | Checks load-cell lead clearance and bend radius |
| `cad/blender/parts/` | Bought-part STLs exported from Onshape by `export_parts.mjs` |
| `cad/blender/renders/` | Review renders and `print_check.txt` (part sizes vs the H2D bed) |
| `cad/profile/profile.py` | 2D side and back profile on the chair plate |
| `cad/featurescript/` | Onshape FeatureScript for the bought parts |

## Running

Blender 5.1 and [uv](https://docs.astral.sh/uv/).

```bash
# 2D profile -> cad/profile/profile.png (seconds)
uv run --with matplotlib python cad/profile/profile.py

# Full build and all renders (about 4 minutes)
/Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py

# Quick coarse build of two views
PA_VOXEL=1.2 /Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py -- 01_hero 02_side

# Lead clearance check on the saved build
/Applications/Blender.app/Contents/MacOS/Blender -b cad/blender/push_assist_concept.blend -P cad/blender/check_wires.py
```

The profile script imports Alex's plotting style from `~/code-stuff/alex-style-guide`.
The `.blend` file is generated and not committed.
