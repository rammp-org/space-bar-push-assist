"""Print files from the saved concept: one STL per printed part in its print orientation, and one
3MF per build plate for Bambu Studio (plain 3MF, objects placed on a 350 x 320 bed).

Run after build_concept.py:
  /Applications/Blender.app/Contents/MacOS/Blender -b cad/blender/push_assist_concept.blend -P cad/blender/export_prints.py
Out: cad/print/stl/*.stl, cad/print/plate_*.3mf, cad/print/plates.txt
Check: ~/code-stuff/alex-3d-skills/skills/print-cad-blender/scripts/cad printcheck cad/print/stl
"""
import math
import os
import struct
import zipfile

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(bpy.data.filepath))
OUT = os.path.join(HERE, "..", "print")
BED = (350.0, 320.0)          # H2D plate; single-nozzle prints keep within 325 x 320
GAP = 8.0

# Print orientation per part: rotation applied before dropping onto the bed.
R_INBOARD = Matrix.Rotation(math.radians(90), 4, "Y")     # split face (+X) down
R_OUTBOARD = Matrix.Rotation(math.radians(-90), 4, "Y")   # split face (-X) down
R_PISTON = Matrix.Rotation(math.radians(90), 4, "X")      # rear face (-Y) down, spigot up
R_FLAT = Matrix.Identity(4)                               # tray floor / cover underside down

PARTS = {
    "Fin R inboard half": ("fin_R_inboard", R_INBOARD),
    "Fin R outboard half": ("fin_R_outboard", R_OUTBOARD),
    "Fin L inboard half": ("fin_L_inboard", R_OUTBOARD),     # mirrored: its split face is -X
    "Fin L outboard half": ("fin_L_outboard", R_INBOARD),
    "Tray L": ("tray_L", R_FLAT),
    "Tray R": ("tray_R", R_FLAT),
    "Cover L": ("cover_L", R_FLAT),
    "Cover R": ("cover_R", R_FLAT),
    "Piston R": ("piston_R", R_PISTON),
    "Piston L": ("piston_L", R_PISTON),
}
# Fins standing on their bottom face (assembly orientation): four fit a P1S bed. Stress at the
# fin root is ~0.2 MPa at a 200 N push, so layers across the fin are fine for a test unit.
STANDING = {f"Fin {s} {h} half": (f"fin_{s}_{h}_standing", R_FLAT) for s in "RL" for h in ("inboard", "outboard")}

# Plates: rows of parts, packed left to right, rows front to back. A part may be turned 90 deg
# about Z on the bed (True) to pack better.
PLATES = [
    ("plate_1_fins", [[("fin_R_inboard", False), ("fin_R_outboard", False)],
                      [("fin_L_inboard", False), ("fin_L_outboard", False)]]),
    ("plate_2_trays", [[("tray_L", True), ("tray_R", True)]]),
    ("plate_3_covers_pistons", [[("cover_L", True), ("cover_R", True)],
                                [("piston_R", False), ("piston_L", False)]]),
]
# Structure-only set for one night on an H2D and a P1S (no covers).
TONIGHT = [
    ("tonight_H2D_trays_pistons", (325, 320), [[("tray_L", False), ("piston_R", False), ("piston_L", False)],
                                              [("tray_R", False)]]),
    ("tonight_P1S_fins_standing", (256, 256), [[("fin_R_inboard_standing", False), ("fin_R_outboard_standing", False),
                                               ("fin_L_inboard_standing", False), ("fin_L_outboard_standing", False)]]),
]


def oriented_tris(obj, R):
    """Triangles of obj in mm, rotated by R and dropped so min z = 0 and centred in XY."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.transform(R)
    xs, ys, zs = zip(*[v.co[:] for v in bm.verts])
    shift = Vector((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs)))
    bm.transform(Matrix.Translation(shift))
    verts = [tuple(v.co) for v in bm.verts]
    bm.verts.index_update()
    tris = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, tris


def size(verts):
    return [max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3)]


def write_stl(path, verts, tris):
    """Binary STL."""
    with open(path, "wb") as fh:
        fh.write(b"push assist".ljust(80, b" ") + struct.pack("<I", len(tris)))
        for a, b, c in tris:
            pa, pb, pc = Vector(verts[a]), Vector(verts[b]), Vector(verts[c])
            n = (pb - pa).cross(pc - pa).normalized()
            fh.write(struct.pack("<12fH", *n, *pa, *pb, *pc, 0))


def write_3mf(path, items):
    """items: [(name, verts, tris, (tx, ty))]. Plain 3MF core spec, millimetres."""
    objs, build = [], []
    for i, (name, verts, tris, (tx, ty)) in enumerate(items, start=1):
        vs = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in verts)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        objs.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
                    f'<triangles>{ts}</triangles></mesh></object>')
        build.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.3f} {ty:.3f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objs)}</resources><build>{"".join(build)}</build></model>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                   'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", model)


def main():
    os.makedirs(os.path.join(OUT, "stl"), exist_ok=True)
    meshes = {}
    for obj_name, (stl, R) in list(PARTS.items()) + list(STANDING.items()):
        verts, tris = oriented_tris(bpy.data.objects[obj_name], R)
        meshes[stl] = (verts, tris)
        write_stl(os.path.join(OUT, "stl", stl + ".stl"), verts, tris)

    report = []
    for plate, bed, rows in [(n, (325, 320), r) for n, r in PLATES] + TONIGHT:
        placed = []                      # (stl, verts, tris, footprint w, d)
        for row in rows:
            r = []
            for stl, turn in row:
                verts, tris = meshes[stl]
                if turn:
                    verts = [(-y, x, z) for x, y, z in verts]
                w, d, h = size(verts)
                r.append((stl, verts, tris, w, d, h))
            placed.append(r)
        total_d = sum(max(p[4] for p in r) for r in placed) + GAP * (len(placed) - 1)
        y = bed[1] / 2 - total_d / 2
        items, lines = [], []
        for r in placed:
            row_d = max(p[4] for p in r)
            row_w = sum(p[3] for p in r) + GAP * (len(r) - 1)
            x = bed[0] / 2 - row_w / 2
            for stl, verts, tris, w, d, h in r:
                items.append((stl, verts, tris, (x + w / 2, y + row_d / 2)))
                lines.append(f"  {stl:16s} {w:6.1f} x {d:6.1f} x {h:6.1f} mm")
                x += w + GAP
            y += row_d + GAP
        span = (max(sum(p[3] for p in r) + GAP * (len(r) - 1) for r in placed), total_d)
        fits = span[0] <= bed[0] and span[1] <= bed[1]
        write_3mf(os.path.join(OUT, plate + ".3mf"), items)
        report.append(f"{plate}: {span[0]:.0f} x {span[1]:.0f} mm used, {'fits' if fits else 'DOES NOT FIT'} {bed[0]} x {bed[1]}\n" + "\n".join(lines))
    text = "\n\n".join(report)
    print(text)
    with open(os.path.join(OUT, "plates.txt"), "w") as fh:
        fh.write(text + "\n")


main()
