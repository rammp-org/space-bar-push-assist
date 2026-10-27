"""Reviewer a8: locate every downward face steeper than 45 deg from vertical in an STL (print frame), cluster by shared
vertices, and report each cluster: area, angle range, print bbox, its overhang reach (horizontal extent along the
downhill direction) and whether material lies directly under it within 0.6 mm (a sloped face sitting on a ledge is
fine; one over air is the case the layer check misses). Usage: python3 -I overhang_locate.py STL [min_area]"""
import sys, struct, numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
T = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
mina = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
cr = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nn = np.linalg.norm(cr, axis=1); ar = nn / 2
nz = cr[:, 2] / np.maximum(nn, 1e-12)
ang_down = np.degrees(np.arccos(np.clip(-nz, -1, 1)))          # 0 = flat roof facing down
zmin = T[:, :, 2].min()
m = (ang_down < 44.0) & (T[:, :, 2].max(axis=1) > zmin + 0.25) & (ar > 1e-6)
idx = np.where(m)[0]
# union-find on shared (rounded) vertices
key = {}
par = list(range(len(idx)))
def f(i):
    while par[i] != i: par[i] = par[par[i]]; i = par[i]
    return i
for j, ti in enumerate(idx):
    for v in T[ti]:
        k = tuple(np.round(v, 3))
        if k in key: a, c = f(j), f(key[k]); par[a] = c
        else: key[k] = j
groups = {}
for j, ti in enumerate(idx): groups.setdefault(f(j), []).append(ti)
# helper: is there solid directly under a point (ray down hits a face within dz)?
def below(p, dz=0.6):
    x, y, z = p; a, b_, c = T[:, 0], T[:, 1], T[:, 2]
    d = (b_[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b_[:, 1] - a[:, 1])
    ok = np.abs(d) > 1e-12; dd = np.where(ok, d, 1)
    l1 = ((b_[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b_[:, 0]) * (y - c[:, 1])) / dd
    l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / dd
    l3 = 1 - l1 - l2
    hit = ok & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    zz = l1 * a[:, 2] + l2 * b_[:, 2] + l3 * c[:, 2]
    zz = zz[hit & (zz < z - 0.05)]
    return (z - zz.max()) if len(zz) else 1e9
rows = []
for g in groups.values():
    A = ar[g].sum()
    if A < mina: continue
    V = T[g].reshape(-1, 3)
    angs = 90 - ang_down[g]                                     # from vertical... report as from-vertical overhang
    flat = np.all(ang_down[g] < 1.0)
    # horizontal reach of the sloped part: extent of the cluster projected on its mean downhill direction
    hn = cr[g][:, :2].sum(0); hn = hn / (np.linalg.norm(hn) + 1e-12)
    reach = float(np.ptp(V[:, :2] @ hn)) if not flat else 0.0
    cen = (T[g].mean(axis=1) * ar[g][:, None]).sum(0) / A
    gap = below(cen)
    rows.append((A, 90 - ang_down[g].max(), 90 - ang_down[g].min(), V.min(0), V.max(0), reach, gap, flat, cen))
rows.sort(key=lambda r: -r[0])
print(f"{sys.argv[1]}: {ar[m].sum():.0f} mm2 steeper than 45 deg; {len(rows)} clusters >= {mina} mm2")
for A, a0, a1, lo, hi, reach, gap, flat, cen in rows[:25]:
    kind = "flat roof" if flat else f"slope {a0:.0f}-{a1:.0f} deg from vertical, reach {reach:.1f}"
    under = "air below" if gap > 50 else f"solid {gap:.1f} below"
    print(f"  {A:7.1f} mm2  {kind:45s} z {lo[2]:5.1f}-{hi[2]:5.1f}  x {lo[0]:6.1f}..{hi[0]:6.1f}  y {lo[1]:6.1f}..{hi[1]:6.1f}  centroid {np.round(cen,1).tolist()} {under}")
