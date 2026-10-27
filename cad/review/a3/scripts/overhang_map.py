"""Reviewer a3: locate every down-facing face steeper than 45 deg (from vertical) in an exported STL (print
orientation), excluding the bed layer. Clusters by 10 mm cells; splits 'sloped' (45-80 deg) from 'ceiling'
(>80 deg, i.e. bridges/flat roofs). Usage: python3 overhang_map.py STL [STL...]"""
import sys, struct, numpy as np
def load(p):
    b = open(p, 'rb').read()
    n = struct.unpack('<I', b[80:84])[0]
    a = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
    return a['v'].astype(float)
for p in sys.argv[1:]:
    v = load(p)
    zmin = v[:, :, 2].min()
    e1, e2 = v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]
    cr = np.cross(e1, e2); ar = np.linalg.norm(cr, axis=1) / 2
    nz = cr[:, 2] / np.maximum(np.linalg.norm(cr, axis=1), 1e-12)
    c = v.mean(axis=1)
    onbed = v[:, :, 2].max(axis=1) < zmin + 0.25
    ang = np.degrees(np.arccos(np.clip(-nz, -1, 1)))  # 0 = facing straight down
    over = (nz < -np.sin(np.radians(45)) + 1e-3) & ~onbed
    slo = over & (ang > 10)       # 45..80 deg from vertical == 10..45 deg from straight down
    ceil = over & (ang <= 10)
    print(f"== {p.split('/')[-1]}: sloped(>45) {ar[slo].sum():.0f} mm2, near-flat ceilings {ar[ceil].sum():.0f} mm2, strictly <44.5deg-from-down faces {ar[over & (ang>10) & (ang<44.5)].sum():.0f} mm2")
    for lab, m in (("sloped", slo), ("ceiling", ceil)):
        if not m.any(): continue
        key = np.floor(c[m] / 10).astype(int)
        cells = {}
        for k, a_, z, an in zip(map(tuple, key), ar[m], c[m][:, 2], ang[m]):
            d = cells.setdefault(k, [0, 1e9, -1e9, 90]); d[0] += a_; d[1] = min(d[1], z); d[2] = max(d[2], z); d[3] = min(d[3], an)
        top = sorted(cells.items(), key=lambda kv: -kv[1][0])[:8]
        for k, (a_, z0, z1, an) in top:
            if a_ < 3: continue
            print(f"   {lab:7s} cell x{k[0]*10:+4d} y{k[1]*10:+4d}: {a_:6.1f} mm2  z {z0:.1f}-{z1:.1f}  min angle-from-down {an:.1f}")
