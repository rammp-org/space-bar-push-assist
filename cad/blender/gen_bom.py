"""Write cad/BOM.md from cad/blender/manifest.json (made by to_cadcheck.py), so the hardware list
always matches the model. Check it with: cad bom cad/BOM.md cad/blender/manifest.json

Run: python3 -I cad/blender/gen_bom.py
"""
import json
import os
import re
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(os.path.join(HERE, "manifest.json")))
parts = m["parts"]
REPORT = os.path.join(HERE, "..", "review", "cadcheck_a8.json")
est = {}
if os.path.exists(REPORT):
    for row in json.load(open(REPORT))["checks"]["parts"]["rows"]:
        est[row["object"]] = (row.get("est_g", ""), row.get("est_h", ""))

USE = {
    "FST_M3_screw_": "Fin halves together, from the inboard face into pilots in the outboard half",
    "FST_Stop_screw_push_": "Push overload stop, on the cell axis (two per cartridge): goes in sideways with its nut on (after the cell); its head's top face meets a counterbore floor in the block; set per cell in the cradle (README)",
    "FST_Stop_screw_pull_": "Pull overload stop (two per cartridge): from the front through the block into its nut; its head's underside meets the block's front counterbore floor; set per cell in the cradle (README)",
    "FST_Stop_nut_push_": "Push stop nut, in a slot in the side of the link's drop",
    "FST_Stop_nut_pull_": "Pull stop nut, in a slot in the side of the link's drop",
    "FST_RJ45_screw_": "RJ45 coupler flange onto its pad in tray L, from above",
    "FST_Jack_screw_": "Bench tool: the cradle's jack, on the grip axis (one set for both cartridges); its head floats 9 mm behind the upright (room for the jack nut and the mass hanger in the known-mass check)",
    "FST_Jack_nut_": "Bench tool: in the cradle's rear upright",
    "FST_Jack_swivel_nut_": "Bench tool: superglued on the jack screw's tip, in the setting plug's T-slot",
    "FST_Jack_lip_screw_": "Bench tool: through the cradle's side walls behind the block (the pull reaction)",
    "FST_Jack_lip_nut_": "Bench tool: in pockets on the cradle side walls' inner faces",
    "FST_Piston_screw_": "Piston plug into the cartridge socket, from the top link's outboard face",
    "FST_M4_nut_": "Fin-to-tray nuts, in slots on the inboard half's split face",
    "FST_T-nut_": "In the chair plate's slots",
    "FST_M4_screw_": "Fin to tray end wall, from inside the tray into the fin's captive nuts",
    "FST_M5_bolt_": "Unit to the chair plate, into 40-series drop-in T-nuts",
    "FST_Cover_screw_": "The one cover onto both trays (land boss tops at the front, rear-wall bosses at the rear); it joins the halves",
    "FST_Board_screw_": "ESP32 onto its 6 mm printed standoffs (printed pilots); the two Qwiic Scale amps onto 6 mm drill-to-fit pads (drill the Ø2.5 pilots through the board's holes)",
}
HEAD = {"M3_selftap_pan": "pan self-tapping", "M4_cap": "socket head cap (ISO 4762)", "M5_cap": "socket head cap (ISO 4762)",
        "M3_cap": "socket head cap (ISO 4762)"}

screws = OrderedDict()
nuts = OrderedDict()
for name, p in sorted(parts.items()):
    if not name.startswith("FST_"):
        continue
    stem = re.sub(r"_(in|out|a|b)$", "", name)
    stem = re.sub(r"_?[RL]?\d*$", "", stem) + "_"
    if p.get("spec"):
        key = (p["spec"], p["length"], stem)
        screws.setdefault(key, []).append(name)
    else:
        key = (p.get("part", "nut"), stem)
        nuts.setdefault(key, []).append(name)

lines = ["# Bill of materials", "", "Generated from `cad/blender/manifest.json` by `cad/blender/gen_bom.py`; do not edit by hand.", "",
         "## Fasteners", "", "| Part | Qty | Model objects | Use |", "|---|---|---|---|"]
for (spec, length, stem), names in screws.items():
    size = spec.split("_")[0]
    lines.append(f"| {size} x {length:g} {HEAD.get(spec, spec)} | {len(names)} | {' '.join('`%s`' % n for n in names)} | {USE.get(stem, '')} |")
for (label, stem), names in nuts.items():
    lines.append(f"| {label} | {len(names)} | {' '.join('`%s`' % n for n in names)} | {USE.get(stem, '')} |")
lines += ["", "## Load-cell hardware (on the cell studs)", "", "| Part | Qty |", "|---|---|",
          "| M5 hex nut (front: on the front stud, on the printed Ø15 washer in the block's front counterbore; 8 mm nut-driver) | 2 |",
          "| M5 hex nut (rear: on the rear stud, on the printed Ø13 washer in the drop's bore; 8 mm nut-driver on the 150 mm extension along the cell axis, between the leaf strips and under the catch saddle, from the cartridge's rear end) | 2 |",
          "", "Both cell nuts are finger-tight on the bare 8 mm nut-driver bit (about 0.1-0.2 N.m), settled overnight on "
          "the bench, re-snugged, then locked with a dab of hot glue, all before the stops are set. The washers are "
          "printed (below), 2.4 mm thick: each bridges the 5.5 mm stud slot under its nut (11 MPa at 1.2 x FS pull, row "
          "a7R washer); no bought washers.", "",
          "## Load cell: 20 kg JHD puck (chosen by Alex, 2026-10-27)", "",
          "**Two 20 kg JHD tension/compression pucks** (Ø25.4 x 12.7 body, M5 studs 12.15 long). The unit is not "
          "meant for hard shoves: with the stops at 1.2 x FS a 600 N shove would reach 1.44-1.92 x FS, so keep pushes "
          "gentle. The 50 kg puck (same body and studs) drops in with no CAD change if that ever changes. Note the "
          "cell's rated output (mV/V) from its label or calibration sheet: the firmware's scale needs it (README).", "",
          "## Amplifiers: SparkFun Qwiic Scale (NAU7802, SEN-15242), no soldering iron and no blade", "",
          "Two SparkFun Qwiic Scale boards (a6 review #2: the Adafruit HX711's logic header shipped loose). Nothing on them "
          "needs an iron or a small screwdriver: the cell's four wires go into a push-lever spring terminal (press the lever "
          "with a fingertip or the tip of a hex key, push the stripped wire in, let go), and the logic side is a Qwiic "
          "(JST SH) socket. Per board, one Qwiic-to-female-socket cable (they come long; cut to length) (SparkFun PRT-14988 or Adafruit 4397) to "
          "the ESP32 header. The NAU7802 has a fixed I2C address, so the two boards go on the ESP32-P4's two I2C ports. "
          "Four Ø3.3 holes on a 17.8 x 25.4 mm pattern (measured on a board). "
          "Each amp sits on four 6 mm drill-to-fit pads (Ø10, solid, a centre dimple, no printed pilot). Set the "
          "board on them and drill the Ø2.5 pilots through its holes, 9 mm deep; a hole up to 1.5 mm off the modelled "
          "pattern still leaves 1.5 mm of wall round the pilot. Then four of the kit's M3 x 10 self-tappers per board.", "",
          "**ESP32 header: measure before ordering the cables.** The Qwiic-to-female-socket cables need male header pins "
          "on the Waveshare ESP32-P4 board's GPIO header. That the board ships with them fitted is not verified; if it "
          "does not, buy Qwiic-to-male-pin cables (or a Qwiic breakout) instead, still no soldering on our side. The "
          "ESP32's own four standoffs keep printed pilots (its hole pattern is from Waveshare's drawing).", "",
          "## Bench tools (one set, for setting the stops)", "",
          "The cradle and setting plug (printed, below), an M5 x 35 jack screw with two M5 nuts and two M4 x 12 lip screws "
          "with nuts (in the fastener table), the printed mass hanger, the unit's ESP32-P4 and one amp "
          "running `firmware/` as the force readout, a 2.5 mm and a 4 mm hex key, a "
          "known mass (5 or 10 kg, e.g. a bag or a water can) on a cord, and a hook or a door handle to hang the cradle "
          "from by its eye.", "",
          "## Printed parts", "",
          "PLA, as for the rest of the unit. The two cartridges and the four washers carry the cell's clamp and the "
          "flexure leaves: print them in PETG instead (same files, same orientation, no other change) if the chair will "
          "be parked in a hot car or in sun, because PLA softens near 55 C (`cad/calc/head_calc.txt`).", "",
          "Estimates from `cad check` (" + ("cad/review/cadcheck_a8.json" if est else "no report found") + ").", "",
          "| Part | Qty | Print orientation | Supports | Est. g | Est. h |", "|---|---|---|---|---|---|"]
for name, p in sorted(parts.items()):
    if name.startswith("PRT_"):
        g, h = est.get(name, ("", ""))
        lines.append(f"| {name[4:]} | 1 | {p.get('orient', '')} | {p.get('supports', '')} | {g} | {h} |")
lines += ["", "## Purchased", "", "| Part | Source |", "|---|---|"]
for name, p in sorted(parts.items()):
    if name.startswith("BUY_") and "nut" not in name and "washer" not in name:
        lines.append(f"| {name[4:]} | {p.get('src', '')} |")
out = os.path.join(HERE, "..", "BOM.md")
open(out, "w").write("\n".join(lines) + "\n")
print("wrote", os.path.normpath(out))
