"""a8 designer: probe the exported cartridge_R.stl (print frame) along the cell's 45 deg insertion path with reviewer a7's
point-in-solid (ray parity). World -> print: Rotation(-90 deg about Y) (asm.R_NX_DOWN), then the export's shift (centre XY,
min z = 0), recovered from the STL's own vertices. Usage: python3 -I probe_path.py cartridge_R.stl"""
import sys, struct, math
import numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
T = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
V = T.reshape(-1, 3)
c = math.cos(-math.pi / 2); s_ = math.sin(-math.pi / 2)
R = np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])          # rotation about Y
# world bbox of the cartridge (right): x 157.8..197.8, y yp..ground_end, z -49..15 -> rotated, then shifted
X, cz = 177.8, -28.5
W = np.array([[157.8, 34.8, -49.0], [197.8, 134.0, 15.0]])
corners = np.array([[x, y, z] for x in W[:, 0] for y in W[:, 1] for z in W[:, 2]]) @ R.T
lo, hi = corners.min(0), corners.max(0)
slo, shi = V.min(0), V.max(0)
shift = np.array([-(slo[0] + shi[0]) / 2 + (slo[0] + shi[0]) / 2, 0, 0])
off = slo - lo                                                # map rotated-world min to the STL min
def to_print(p): return np.array(p) @ R.T + off
def inside(p):
    x, y, z = p; a, b_, c_ = T[:, 0], T[:, 1], T[:, 2]
    d = (b_[:, 0] - a[:, 0]) * (c_[:, 1] - a[:, 1]) - (c_[:, 0] - a[:, 0]) * (b_[:, 1] - a[:, 1])
    ok = np.abs(d) > 1e-12
    l1 = ((b_[:, 1] - c_[:, 1]) * (x - c_[:, 0]) + (c_[:, 0] - b_[:, 0]) * (y - c_[:, 1])) / np.where(ok, d, 1)
    l2 = ((c_[:, 1] - a[:, 1]) * (x - c_[:, 0]) + (a[:, 0] - c_[:, 0]) * (y - c_[:, 1])) / np.where(ok, d, 1)
    l3 = 1 - l1 - l2
    hit = ok & (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
    zz = l1 * a[:, 2] + l2 * b_[:, 2] + l3 * c_[:, 2]
    return int(np.sum(hit & (zz > z))) % 2 == 1
print("STL bbox", slo.round(2), shi.round(2), " world bbox rotated", (hi - lo).round(2), "vs STL", (shi - slo).round(2))
# sanity: a point in the block's solid and one in the cell gap
for nm, p in (("block solid (x' 10, y 40, z 5)", (187.8, 40.0, 5.0)), ("cell gap (axis, y 54)", (177.8, 54.0, -28.5))):
    print("sanity", nm, "SOLID" if inside(to_print(p)) else "void")
u = np.array([-1, 0, 1]) / math.sqrt(2)                     # the slide direction (out), world
v = np.array([1, 0, 1]) / math.sqrt(2)                      # across the motion, in the x-z plane
for label, y, need in (("front stud slot, block (y 40, 44)", (40.0, 44.0), 4.9),
                       ("rear stud slot, drop wall (y 62.5)", (62.5,), 4.9),
                       ("rear nut channel (y 66, 69, 72)", (66.0, 69.0, 72.0), 9.24)):
    worst = 1e9
    for yy in y:
        for sdist in np.arange(0.0, 36.0, 0.5):             # along the path, from the axis out past the inboard face
            o = np.array([X, yy, cz]) + u * sdist
            # open width across the motion through o
            ws = [w for w in np.arange(-8.0, 8.01, 0.1) if not inside(to_print(o + v * w))]
            if not ws:
                width = 0.0
            else:
                # contiguous run through 0
                arr = np.arange(-8.0, 8.01, 0.1)
                op = [not inside(to_print(o + v * w)) for w in arr]
                i0 = int(np.argmin(np.abs(arr)))
                if not op[i0]:
                    width = 0.0
                else:
                    a_ = i0
                    while a_ > 0 and op[a_ - 1]: a_ -= 1
                    b2 = i0
                    while b2 < len(arr) - 1 and op[b2 + 1]: b2 += 1
                    width = arr[b2] - arr[a_] + 0.1
            if o[0] < 157.8 - 0.5: break                     # past the inboard face
            worst = min(worst, width)
    print("%-38s narrowest open width across the motion along the path: %.1f mm (needs %.2f)" % (label, worst, need))
