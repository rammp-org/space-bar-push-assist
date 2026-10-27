"""Reviewer a8: re-probe the cell insertion path on the exported cartridge STL.
1. Find the world->print transform by matching the world mesh (dumped from check.blend) to the STL vertices
   (all 48 axis permutations/signs, bbox-aligned; best mean nearest-neighbour distance).
2. Slide the cell, rear washer and rear nut (world vertices + face-free surface samples of an analytic puck/stud model)
   out along (-x, 0, +z)/sqrt2 from home in 1 mm steps to 60 mm and count points inside the STL solid (ray parity,
   reviewer a7's test, two ray directions must agree). The cell faces seat on the bosses with zero gap, so the y extent
   is shrunk by 'shrink' about the cell's mid-plane.
3. The reverse test: STL vertices inside the analytic moving solids at each step.
uv run --with numpy --with scipy python -I stl_cell_path.py STL VERTDIR [shrink]"""
import sys, struct, itertools, math
import numpy as np
from scipy.spatial import cKDTree
stl, vd = sys.argv[1], sys.argv[2]
shrink = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
b = open(stl, 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
T = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
SV = np.unique(T.reshape(-1, 3).round(4), axis=0)
W = np.load(f"{vd}/PRT_cartridge_R.npy")
tree = cKDTree(SV)
best = None
for perm in itertools.permutations(range(3)):
    for sg in itertools.product((1, -1), repeat=3):
        M = np.zeros((3, 3))
        for i in range(3): M[i, perm[i]] = sg[i]
        P = W @ M.T; P = P - P.min(0) + SV.min(0)
        if np.abs((P.max(0) - P.min(0)) - (SV.max(0) - SV.min(0))).max() > 0.5: continue
        d = tree.query(P)[0].mean()
        if best is None or d < best[0]: best = (d, M.copy(), SV.min(0) - (W @ M.T).min(0))
d, M, off = best
print(f"transform: mean NN {d:.3f} mm, M={M.tolist()}, off={off.round(3).tolist()}")
def to_p(p): return np.asarray(p) @ M.T + off
def inside_dir(pts, ax):
    # ray parity along +ax (0,1,2) in print frame
    o = [i for i in range(3) if i != ax]; a, b_, c = T[:, 0], T[:, 1], T[:, 2]
    res = np.zeros(len(pts), bool)
    d = (b_[:, o[0]] - a[:, o[0]]) * (c[:, o[1]] - a[:, o[1]]) - (c[:, o[0]] - a[:, o[0]]) * (b_[:, o[1]] - a[:, o[1]])
    ok = np.abs(d) > 1e-12; dd = np.where(ok, d, 1)
    for k, p in enumerate(pts):
        x, y, z = p[o[0]], p[o[1]], p[ax]
        l1 = ((b_[:, o[1]] - c[:, o[1]]) * (x - c[:, o[0]]) + (c[:, o[0]] - b_[:, o[0]]) * (y - c[:, o[1]])) / dd
        l2 = ((c[:, o[1]] - a[:, o[1]]) * (x - c[:, o[0]]) + (a[:, o[0]] - c[:, o[0]]) * (y - c[:, o[1]])) / dd
        l3 = 1 - l1 - l2
        hit = ok & (l1 > 0) & (l2 > 0) & (l3 > 0)
        zz = l1 * a[:, ax] + l2 * b_[:, ax] + l3 * c[:, ax]
        res[k] = int(np.sum(hit & (zz > z))) % 2 == 1
    return res
def inside(pts):
    return inside_dir(pts, 2) & inside_dir(pts, 1)
# sanity
print("sanity: block solid", inside(to_p([[187.8, 40.0, 5.0]])), " cell gap void", inside(to_p([[177.8, 54.0, -28.5]])))
X, cz = 177.8, -28.5
cell = np.load(f"{vd}/BUY_load_cell_R.npy"); wr = np.load(f"{vd}/PRT_washer_rear_R.npy"); nr = np.load(f"{vd}/BUY_rear_nut_R.npy")
# analytic samples: the puck (Ø25.4) between the seat faces, the studs (Ø4.9), the washer (Ø13) and nut (circumscribed Ø9.24)
ymid = None
cy = cell[:, 1]
rng = np.random.default_rng(1)
def disk_samples(r, y0, y1, nr_=10, nth=48, ny=6):
    pts = []
    for y in np.linspace(y0, y1, ny):
        for rr in np.linspace(0, r, nr_):
            for t in np.linspace(0, 2 * math.pi, nth, endpoint=False):
                pts.append((X + rr * math.cos(t), y, cz + rr * math.sin(t)))
    return np.array(pts)
# puck body y range from the dumped verts: points with radius > 6 from the axis
rad = np.hypot(cell[:, 0] - X, cell[:, 2] - cz)
body = cell[rad > 6.0]; by0, by1 = body[:, 1].min(), body[:, 1].max()
print(f"puck body y {by0:.2f}..{by1:.2f}, cell y {cy.min():.2f}..{cy.max():.2f}, washer y {wr[:,1].min():.2f}..{wr[:,1].max():.2f}, nut y {nr[:,1].min():.2f}..{nr[:,1].max():.2f}")
S = [("puck", disk_samples(12.7 - 0.05, by0 + shrink, by1 - shrink), 12.7),
     ("front stud", disk_samples(2.45, cy.min() + 0.05, by0 - 0.05, 4, 24, 12), 2.45),
     ("rear stud", disk_samples(2.45, by1 + 0.05, cy.max() - 0.05, 4, 24, 12), 2.45),
     ("rear washer", disk_samples(6.5 - 0.05, wr[:, 1].min() + 0.05, wr[:, 1].max() - 0.05, 8, 48, 4), 6.5),
     ("rear nut", disk_samples(4.0, nr[:, 1].min() + 0.05, nr[:, 1].max() - 0.05, 6, 36, 5), 4.0)]
u = np.array([-1, 0, 1]) / math.sqrt(2)
print("step_mm " + " ".join(f"{nm:>12s}" for nm, _, _ in S))
worst = {}
for s in np.arange(0, 61, 2.0):
    row = []
    for nm, pts, r in S:
        q = pts + u * s
        k = int(inside(to_p(q)).sum()); row.append(k); worst[nm] = max(worst.get(nm, 0), k)
    print(f"{s:6.1f}  " + " ".join(f"{k:12d}" for k in row))
print("max inside-points per member over the path:", worst)
# 3. reverse: STL vertices (dense: vertices + edge midpoints) inside the analytic moving solids
Minv = np.linalg.inv(M)
E = np.concatenate([T[:, 0], T[:, 1], T[:, 2], (T[:, 0] + T[:, 1]) / 2, (T[:, 1] + T[:, 2]) / 2, (T[:, 2] + T[:, 0]) / 2])
Wv = (E - off) @ Minv.T
cyl = [("puck", 12.7 - 0.05, by0 + shrink, by1 - shrink), ("front stud", 2.45, cy.min() + 0.05, by0),
       ("rear stud", 2.45, by1, cy.max() - 0.05), ("rear washer", 6.45, wr[:, 1].min() + 0.05, wr[:, 1].max() - 0.05),
       ("rear nut", 4.62 - 0.05, nr[:, 1].min() + 0.05, nr[:, 1].max() - 0.05)]
rw = {}
for s in np.arange(0, 61, 1.0):
    c = np.array([X, 0, cz]) + u * s
    for nm, r, y0, y1 in cyl:
        k = int(np.sum((np.hypot(Wv[:, 0] - c[0], Wv[:, 2] - c[2]) < r) & (Wv[:, 1] > y0) & (Wv[:, 1] < y1)))
        if k: rw.setdefault(nm, []).append((s, k))
print("reverse test, STL points inside moving solids (step, count):", rw if rw else "none")
