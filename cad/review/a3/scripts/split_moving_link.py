"""Reviewer a3: add the cartridge's MOVING body (top link + leaves above the ground bar + V tongue with its
O4.5 stop hole) as separate check-only objects PRT_movlink_R / _L, copied from build_concept.build_cartridge's
numbers, so cad check slide rows can sweep the flexure's moving link against the fin, pin and post.
Run:  Blender -b /tmp/a3_check.blend --python split_moving_link.py -- /tmp/a3_moving.blend"""
import sys, os, math, bpy
sys.path.insert(0, os.path.expanduser("~/code-stuff/alex-3d-skills/skills/print-cad-blender/scripts"))
from cadlib import geom as G

out = sys.argv[sys.argv.index("--") + 1]
w, lh, ch, cr, l1, g1, sy, sz, gap = 18, 15, 8, 60, 110, -42, 90, -21, 0.25
coll = bpy.data.collections["Printed"]
for side, X in (("R", 177.8), ("L", -177.8)):
    oc = [(X + a, b) for a, b in [(w, -lh + ch), (w, lh - ch), (w - ch, lh), (-w + ch, lh), (-w, lh - ch),
                                  (-w, -lh + ch), (-w + ch, -lh), (w - ch, -lh)]]
    link = G.prism("link", oc, cr, l1, "Y")
    leaves = [G.box("leaf", X - w, X + w, y0, y1, g1 + 0.3, -lh + ch + 1) for y0, y1 in ((61, 62.5), (108.5, 110))]
    tongue = G.prism("tongue", [(X - 10, -lh + 3), (X + 10, -lh + 3), (X + 10, -lh), (X, -lh - 10), (X - 10, -lh)],
                     sy - 6, sy + 6, "Y")
    body = G.csg(link, add=leaves + [tongue])
    body = G.csg(body, sub=[G.cyl("stop hole", (sy, sz), 2.0 + gap, X - w - 1, X + w + 1, "X", n=96),
                            G.cyl("rear stud hole", (X, 0), 2.75, cr - 1, cr + 4.5, "Y"),
                            G.prism("nut bore", G.teardrop((X, 0), 7.0, up=(1, 0)), cr + 4, 73.5, "Y")])
    sock = G.prism("socket", G.teardrop((X, 0), 22.2 / 2 + 0.15, up=(1, 0), n=48), 73, l1 + 1, "Y")
    xs = (X - 7.8 - 0.1, X + 13) if side == "R" else (X - 13, X + 7.8 + 0.1)
    sock = G.csg(sock, inter=[G.box("D", xs[0], xs[1], 72, l1 + 2, -20, 20)])
    body = G.csg(body, sub=[sock])
    body.name = body.data.name = f"PRT_movlink_{side}"
    for c in list(body.users_collection):
        c.objects.unlink(body)
    coll.objects.link(body)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)
