"""Copy the concept build into alex-3d-skills conventions so `cad check` can run on it.

The concept is built in build_concept.py (SDF parts under a mm-scaled root). This script opens that
.blend, re-creates every part in world millimetres with cadlib names, collections and metadata
(PRT_/BUY_/FST_/CAB_), and saves check.blend + manifest.json next to it.

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b cad/blender/push_assist_concept.blend -P cad/blender/to_cadcheck.py
Then: $CAD check cad/blender/check.blend cad/blender/checks.json
"""
import math
import os
import sys

import bpy
from mathutils import Vector, geometry

SKILL = os.environ.get("CAD_SKILL", os.path.expanduser("~/code-stuff/alex-3d-skills/skills/print-cad-blender"))
sys.path.insert(0, os.path.join(SKILL, "scripts"))
from cadlib import asm, export  # noqa: E402

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath))
src = {o.name: o for o in bpy.data.objects}

PRINTED = {
    # source object: (name, print_rot, orient)
    "Fin R inboard half": ("PRT_fin_R_inboard", asm.R_PX_DOWN, "split face down"),
    "Fin R outboard half": ("PRT_fin_R_outboard", asm.R_NX_DOWN, "split face down"),
    "Fin L inboard half": ("PRT_fin_L_inboard", asm.R_NX_DOWN, "split face down"),
    "Fin L outboard half": ("PRT_fin_L_outboard", asm.R_PX_DOWN, "split face down"),
    "Tray L": ("PRT_tray_L", asm.R_ID, "floor down, open top up"),
    "Tray R": ("PRT_tray_R", asm.R_ID, "floor down, open top up"),
    "Cover": ("PRT_cover", asm.R_ID, "flat, underside down"),
    "Piston R": ("PRT_piston_R", asm.R_NX_DOWN, "on its side, D-flat (inboard) down"),
    "Piston L": ("PRT_piston_L", asm.R_PX_DOWN, "on its side, D-flat (inboard) down"),
    "Cartridge R": ("PRT_cartridge_R", asm.R_NX_DOWN, "on its side, inboard face down (leaves bend in the layer plane)"),
    "Cartridge L": ("PRT_cartridge_L", asm.R_PX_DOWN, "on its side, inboard face down (leaves bend in the layer plane)"),
    "Washer front R": ("PRT_washer_front_R", asm.R_NY_DOWN, "flat"),
    "Washer front L": ("PRT_washer_front_L", asm.R_NY_DOWN, "flat"),
    "Washer rear R": ("PRT_washer_rear_R", asm.R_NY_DOWN, "flat"),
    "Washer rear L": ("PRT_washer_rear_L", asm.R_NY_DOWN, "flat"),
    # bench tools for setting the overload stops (one set serves both cartridges); they sit 250 mm outboard of the
    # right fin in the model
    "Cradle": ("PRT_cradle", asm.R_ID, "base down, open top up"),
    "Setting plug": ("PRT_setting_plug", asm.R_NX_DOWN, "on its side, D-flat down (T-slot up)"),
    "Mass hanger": ("PRT_mass_hanger", asm.R_ID, "flat, keyhole slot vertical"),
}
BENCH_OFF = (250.0, 0.0, 0.0)          # build_concept.BENCH_OFF
# the right cartridge group, copied into the cradle in check_moving.blend only (bench rows); not real extra parts
BENCH_COPY = {"PRT_cartridge_R": "PRT_bench_cartridge", "BUY_load_cell_R": "BUY_bench_load_cell",
              "PRT_washer_front_R": "PRT_bench_washer_front", "PRT_washer_rear_R": "PRT_bench_washer_rear",
              "BUY_front_nut_R": "BUY_bench_front_nut", "BUY_rear_nut_R": "BUY_bench_rear_nut"}
# Check-only copies of each cartridge's moving body (top link, leaves above the ground bar, tongue). They go into a
# second blend, check_moving.blend, so slide and distance rows can sweep the flexure's moving link (reviewer a3
# scripts/split_moving_link.py, now built from the same functions as the part). They are not printed parts.
# Attempt 5: the stop screws ride on the link and their heads act on the cartridge's block, so check_moving.blend also
# swaps each cartridge for its fixed body (PRT_cartfix_*: block, ground bar, leaf feet) next to its moving body.
MOVLINK = {"Movlink R": "PRT_movlink_R", "Movlink L": "PRT_movlink_L",
           "Cartfix R": "PRT_cartfix_R", "Cartfix L": "PRT_cartfix_L"}
PURCHASED = {
    "Load cell R": ("BUY_load_cell_R", 30, "JHD T/C puck, 50 kg recommended (20 kg fallback, same body; BOM), M5 studs 12.15 long, 12.7 between faces, cad/blender/parts/load_cell.stl"),
    "Load cell L": ("BUY_load_cell_L", 30, "JHD T/C puck, 50 kg recommended (20 kg fallback, same body; BOM), M5 studs 12.15 long, 12.7 between faces, cad/blender/parts/load_cell.stl"),
    "MTB grip R": ("BUY_grip_R", 90, "lock-on MTB grip, cad/blender/parts/mtb_grip.stl"),
    "MTB grip L": ("BUY_grip_L", 90, "lock-on MTB grip, cad/blender/parts/mtb_grip.stl"),
    "ESP32-P4 PoE": ("BUY_esp32_p4", 40, "Waveshare ESP32-P4 WiFi6 PoE, cad/blender/parts/esp32_p4.stl (its 3.75 mm spacers flattened; sits on 6 mm printed standoffs)"),
    "Amp L": ("BUY_amp_L", 4, "SparkFun Qwiic Scale, NAU7802 24-bit load-cell ADC, SEN-15242 (spring terminal for the cell, Qwiic socket for the logic: no soldering), stand-in built by build_concept.amp_board()"),
    "Amp R": ("BUY_amp_R", 4, "SparkFun Qwiic Scale, NAU7802 24-bit load-cell ADC, SEN-15242 (spring terminal for the cell, Qwiic socket for the logic: no soldering), stand-in built by build_concept.amp_board()"),
    "RJ45 panel coupler": ("BUY_rj45_coupler", 20, "panel RJ45 coupler, cad/blender/parts/rj45_coupler.stl"),
    "Patch plug (board)": ("BUY_patch_plug_board", 5, "RJ45 plug stand-in"),
    "Patch plug (coupler)": ("BUY_patch_plug_coupler", 5, "RJ45 plug stand-in"),
}
for s in "RL":
    for n, m in (("Front nut", 1), ("Rear nut", 1)):
        PURCHASED[f"{n} {s}"] = (f"BUY_{n.lower().replace(' ', '_')}_{s}", m, "M5 hardware on the load-cell studs")


def copy_mesh(o):
    """World-mm mesh copy of a source object (all sources are modelled in mm under the scaled root)."""
    if o.type == "MESH":
        me = o.data.copy()
    else:
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_basis)                       # step moves are zero at save; keeps it honest
    ob = bpy.data.objects.new(o.name + " cc", me)
    asm.coll("TMP").objects.link(ob)
    return ob


def curve_points(o):
    sp = o.data.splines[0]
    if sp.type == "POLY":
        return [tuple(p.co[:3]) for p in sp.points]
    pts = []
    bp = sp.bezier_points
    for a, b in zip(bp, bp[1:]):
        seg = geometry.interpolate_bezier(a.co, a.handle_right, b.handle_left, b.co, 10)
        pts += [tuple(v) for v in (seg if not pts else seg[1:])]
    return pts


made = []
for s, (name, R, orient) in PRINTED.items():
    made.append(asm.part(copy_mesh(src[s]), name, "PRT", "pla_b" if ("cover" in name or "cradle" in name) else "pla_a",
                         stl=name[4:], print_rot=R, orient=orient, supports="no",
                         infill=100 if ("washer" in name or "hanger" in name) else 40 if ("cartridge" in name or "piston" in name
                                                                     or "cradle" in name or "plug" in name) else 15))
for s, (name, mass, where) in PURCHASED.items():
    made.append(asm.part(copy_mesh(src[s]), name, "BUY", "buy_metal" if "washer" in name or "nut" in name else "buy",
                         mass_g=mass, src=where))
chair = [src[n] for n in src if n.startswith(("Plate 4040", "Central block")) and src[n].type == "MESH"]
if chair:
    import bmesh
    bm = bmesh.new()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in chair:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        bm.from_mesh(me)
    me = bpy.data.meshes.new("chair")
    bm.to_mesh(me)
    ob = bpy.data.objects.new("chair cc", me)
    asm.coll("TMP").objects.link(ob)
    made.append(asm.part(ob, "BUY_corpus_back_plate", "BUY", "buy_metal", mass_g=4000,
                         src="Permobil Corpus back plate stand-in from Alex's measurements"))

bench_fst = []                                          # (kind, name, at, into, extra) of the R stop hardware, for the bench copy
for o in list(src.values()):
    kind = o.get("cc_kind")
    if kind and o.name.startswith(("Stop screw", "Stop nut")) and " R " in o.name + " ":
        bench_fst.append((kind, "FST_Bench_" + o.name[:-2 if o.name.endswith((" R",)) else None].replace(" R ", " ").replace(" ", "_"),
                          [a + b for a, b in zip(o["cc_at"], BENCH_OFF)], list(o["cc_into"]),
                          dict(length=o.get("cc_len"), spec=o.get("cc_spec"), size=o.get("cc_size"), h=o.get("cc_h"),
                               label=o.get("cc_label"))))
    if kind == "screw":
        made.append(asm.fastener("FST_" + o.name.replace(" ", "_"), Vector(o["cc_at"]), Vector(o["cc_into"]), o["cc_len"],
                                 spec=o["cc_spec"], host=o.get("cc_host", ""), step=o.get("cc_step", "")))
    elif kind == "nut":
        made.append(asm.nut("FST_" + o.name.replace(" ", "_"), Vector(o["cc_at"]), Vector(o["cc_into"]),
                            size=o["cc_size"], h=o.get("cc_h"), label=o.get("cc_label")))

for o in list(src.values()):
    if o.type == "CURVE":
        pts = curve_points(o)
        mw = o.matrix_basis
        pts = [tuple(mw @ Vector(p)) for p in pts]
        r = o.data.bevel_depth
        made.append(asm.cable("CAB_" + o.name.replace(" ", "_").replace("(", "").replace(")", ""), pts, r))

ml_meshes = {}                                         # mm mesh copies, kept past the cleanup below
for s_, name in MOVLINK.items():
    me = src[s_].data.copy()
    me.transform(src[s_].matrix_basis)
    me.use_fake_user = True
    ml_meshes[name] = me

keep = set(made)
for o in list(bpy.data.objects):
    if o not in keep:
        bpy.data.objects.remove(o)
for c in list(bpy.data.collections):
    if c.name not in ("Printed", "Purchased", "Fasteners", "Cables"):
        bpy.data.collections.remove(c)

import json  # noqa: E402
asm.PARAMS.update(json.loads(bpy.context.scene.get("pa_params", "{}")))
bpy.context.scene["cad_params"] = json.dumps(asm.PARAMS, default=str)
asm.write_manifest(os.path.join(HERE, "manifest.json"))
export.export_stls(os.path.join(HERE, "..", "print", "stl_cc"))
export.save_blend(os.path.join(HERE, "check.blend"))
print("cadcheck blend:", len(made), "objects")

# check_moving.blend = check.blend with each cartridge split into its fixed and moving bodies (in Printed, so slide
# rows can move them)
from mathutils import Matrix  # noqa: E402
for nm, new in BENCH_COPY.items():                     # the right cartridge group sitting in the cradle
    me = bpy.data.objects[nm].data.copy()
    me.transform(Matrix.Translation(BENCH_OFF))
    ob = bpy.data.objects.new(new + " cc", me)
    bpy.context.scene.collection.objects.link(ob)
    if new.startswith("PRT_"):
        asm.part(ob, new, "PRT", "pla_a", stl="", print_rot=asm.R_ID, orient="bench copy (check only)", supports="no",
                 infill=40)
    else:
        asm.part(ob, new, "BUY", "buy_metal", mass_g=1, src="bench copy (check only)")
for kind, name, at, into, x in bench_fst:
    if kind == "screw":
        asm.fastener(name, Vector(at), Vector(into), x["length"], spec=x["spec"], step="bench")
    else:
        asm.nut(name, Vector(at), Vector(into), size=x["size"], h=x["h"], label=x["label"])
for nm in ("PRT_cartridge_R", "PRT_cartridge_L"):
    bpy.data.objects.remove(bpy.data.objects[nm])
for name, me in ml_meshes.items():
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections["Printed"].objects.link(ob)
    ob["check_only"] = "fixed or moving body of the cartridge (reviewer a3 split); not a printed part"
export.save_blend(os.path.join(HERE, "check_moving.blend"))
print("moving-link blend: cartridges -> +", len(ml_meshes), "check-only bodies")
