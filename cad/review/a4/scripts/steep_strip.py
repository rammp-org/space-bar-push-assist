"""Reviewer a4: list faces steeper than 45 deg from vertical (angle-from-down < 44.5) in an STL, grouped by
(angle, z band, y band) so a long chamfer strip shows as one row. Usage: python3 -I steep_strip.py STL"""
import sys, struct, numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
v = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
cr = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); ar = np.linalg.norm(cr, axis=1) / 2
nz = cr[:, 2] / np.maximum(np.linalg.norm(cr, axis=1), 1e-12); c = v.mean(axis=1)
ang = np.degrees(np.arccos(np.clip(-nz, -1, 1)))
zmin = v[:, :, 2].min(); m = (ang < 44.5) & (v[:, :, 2].max(axis=1) > zmin + 0.25)
groups = {}
for a_, an, cc in zip(ar[m], ang[m], c[m]):
    k = (round(an), int(cc[2] // 5) * 5, int(cc[1] // 20) * 20)
    g = groups.setdefault(k, [0, 1e9, -1e9]); g[0] += a_; g[1] = min(g[1], cc[0]); g[2] = max(g[2], cc[0])
print(f"{sys.argv[1]}: {ar[m].sum():.0f} mm2 steeper than 45 deg from vertical")
for k, g in sorted(groups.items(), key=lambda kv: -kv[1][0])[:12]:
    print(f"  {g[0]:6.0f} mm2  angle-from-down {k[0]:2d} (={90-k[0]} from vertical)  z {k[1]}-{k[1]+5}  y {k[2]}..{k[2]+20}  x {g[1]:.0f}..{g[2]:.0f}")
