"""Reviewer a7: point-in-solid on an STL by ray parity along +z (print frame). Usage: stl_inside.py part.stl x,y,z ..."""
import sys, struct, numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
T = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
def inside(p):
    x, y, z = p; a, b_, c = T[:, 0], T[:, 1], T[:, 2]
    d = (b_[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b_[:, 1] - a[:, 1])
    ok = np.abs(d) > 1e-12
    l1 = ((b_[:, 1] - c[:, 1]) * (x - c[:, 0]) + (c[:, 0] - b_[:, 0]) * (y - c[:, 1])) / np.where(ok, d, 1)
    l2 = ((c[:, 1] - a[:, 1]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (y - c[:, 1])) / np.where(ok, d, 1)
    l3 = 1 - l1 - l2
    hit = ok & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    zz = l1 * a[:, 2] + l2 * b_[:, 2] + l3 * c[:, 2]
    return int(np.sum(hit & (zz > z))) % 2 == 1
for s in sys.argv[2:]:
    p = tuple(map(float, s.split(','))); print(s, 'SOLID' if inside(p) else 'void')
