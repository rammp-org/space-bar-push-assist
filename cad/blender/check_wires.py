"""Clearance check for the load-cell leads in push_assist_concept.blend.

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b cad/blender/push_assist_concept.blend -P cad/blender/check_wires.py

Per lead: the closest it comes to any solid (printed parts, boards, hardware; it must not
touch), its tightest bend radius, and how far off the sensor's side it runs before the
first bend. Limits come from the scene (set from P in build_concept.py).
"""
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

scene = bpy.context.scene
LEAD_R = scene["lead_d"] / 2
MIN_BEND = scene["lead_bend_r"] - 0.2
STRAIGHT = 12.7 + scene["lead_straight"] - 0.2       # from the cell axis: sensor radius + straight run
dg = bpy.context.evaluated_depsgraph_get()
to_mm = bpy.data.objects["Assembly (mm)"].matrix_world.inverted()
RAYS = [Vector(d).normalized() for d in ((1, 0.13, 0.07), (-0.11, 1, 0.05), (0.06, -0.09, 1))]


def bvh_mm(obj):
    ev = obj.evaluated_get(dg)
    mesh = ev.to_mesh()
    m = to_mm @ obj.matrix_world
    tree = BVHTree.FromPolygons([m @ v.co for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])
    ev.to_mesh_clear()
    return tree


def inside(tree, p):
    votes = 0
    for d in RAYS:
        hits, o = 0, p.copy()
        while True:
            loc = tree.ray_cast(o, d)[0]
            if loc is None:
                break
            hits += 1
            o = loc + d * 1e-4
        votes += hits % 2
    return votes >= 2


def lead_points(obj):
    m = to_mm @ obj.matrix_world
    sp = obj.data.splines[0]
    return [m @ Vector(p.co[:3]) for p in sp.points]


solids = {o.name: bvh_mm(o) for o in bpy.data.objects
          if o.type == "MESH" and (not o.hide_render or o.name.startswith("Load cell "))
          and not o.name.startswith(("Floor", "Shadow gap"))}

failed = False
for lead in [o for o in bpy.data.objects if o.name.startswith("Load cell lead")]:
    side = lead.name[-1]
    cell = bpy.data.objects[f"Load cell {side}"]
    cm = to_mm @ cell.matrix_world
    PA = __import__("json").loads(scene["pa_params"])      # a7: the cell is clocked 45 deg, so take its axis from the build
    axis_x, axis_z = (1 if side == "R" else -1) * PA["HX"], PA["cz"]
    pts = lead_points(lead)

    # Skip the part of the lead inside the cell's boss.
    skip = next(i for i, p in enumerate(pts) if math.hypot(p.x - axis_x, p.z - axis_z) > 17.6)
    worst = {}
    for name, tree in solids.items():
        for p in pts[skip:]:
            d = tree.find_nearest(p)[3]
            if d is None or d > LEAD_R + 0.05 and not inside(tree, p):
                continue
            clear = -d if inside(tree, p) else d - LEAD_R
            if clear < 0 and clear < worst.get(name, (1e9,))[0]:
                worst[name] = (clear, p)

    radii = []
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        area2 = (b - a).cross(c - a).length
        radii.append(math.inf if area2 < 1e-9 else (b - a).length * (c - b).length * (c - a).length / (2 * area2))
    bend = min(zip(radii, pts[1:]), key=lambda rp: rp[0])
    first = next(i for i, r in enumerate(radii) if r < 1000)
    straight = math.hypot(pts[first + 1].x - axis_x, pts[first + 1].z - axis_z)   # radii[i] is centred on pts[i + 1]

    ok = not worst and bend[0] >= MIN_BEND and straight >= STRAIGHT
    failed |= not ok
    print(f"{lead.name}: {'OK' if ok else 'FAIL'}")
    print(f"  tightest bend radius: {bend[0]:.1f} mm (need {MIN_BEND + 0.2:.1f}) at {tuple(round(c, 1) for c in bend[1])}")
    print(f"  first bend starts {straight:.1f} mm from the cell axis (need {STRAIGHT + 0.2:.1f}: sensor r 12.7 + straight run)")
    for name, (clear, p) in sorted(worst.items(), key=lambda kv: kv[1][0]):
        print(f"  touches {name}: {-clear:.1f} mm overlap at {tuple(round(c, 1) for c in p)}")
    if not worst:
        print("  touches nothing")
print("RESULT", "FAIL" if failed else "OK")
