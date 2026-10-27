"""Reviewer a8: dump world-frame vertices of named objects from a .blend (run in Blender -b X.blend -P dump_verts.py -- OUTDIR NAME...)."""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
out, names = a[0], a[1:]
dg = bpy.context.evaluated_depsgraph_get()
for n in names:
    o = bpy.data.objects[n]; e = o.evaluated_get(dg); m = e.to_mesh()
    V = np.array([o.matrix_world @ v.co for v in m.vertices]); np.save(f"{out}/{n}.npy", V)
    print("DUMP", n, len(V), V.min(0).round(2), V.max(0).round(2))
