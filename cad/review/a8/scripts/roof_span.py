"""Reviewer a8: true bridge/cantilever reach of a roof layer in an STL (print frame). Slices at z and z-dz by scanline,
marks cells solid at z but void at z-dz (unsupported), and for each unsupported cell measures the distance to the
nearest supported cell (solid at both). Reports the max distance (a bridge's half span, or a cantilever's reach) and
whether the unsupported region touches supports on opposite sides (bridge) or one side only (cantilever).
Usage: python3 -I roof_span.py STL z [dz] [cell]"""
import sys, struct, numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
T = np.frombuffer(b[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
z = float(sys.argv[2]); dz = float(sys.argv[3]) if len(sys.argv) > 3 else 0.2; cell = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
lo, hi = T.reshape(-1, 3).min(0), T.reshape(-1, 3).max(0)
xs = np.arange(lo[0], hi[0], cell) + cell / 2; ys = np.arange(lo[1], hi[1], cell) + cell / 2
def section(zc):
    d = T[:, :, 2] - zc
    m = (d.min(1) < 0) & (d.max(1) > 0)
    segs = []
    for t, dd in zip(T[m], d[m]):
        pts = []
        for i in range(3):
            a, c = t[i], t[(i + 1) % 3]; da, dc = dd[i], dd[(i + 1) % 3]
            if (da < 0) != (dc < 0):
                s = da / (da - dc); pts.append(a + s * (c - a))
        if len(pts) == 2: segs.append((pts[0][:2], pts[1][:2]))
    S = np.array(segs)
    G = np.zeros((len(ys), len(xs)), bool)
    for j, y in enumerate(ys):
        y0, y1 = S[:, 0, 1], S[:, 1, 1]
        hit = (np.minimum(y0, y1) <= y) & (np.maximum(y0, y1) > y)
        if not hit.any(): continue
        s = (y - y0[hit]) / (y1[hit] - y0[hit])
        X = np.sort(S[hit, 0, 0] + s * (S[hit, 1, 0] - S[hit, 0, 0]))
        for k in range(0, len(X) - 1, 2):
            G[j, (xs >= X[k]) & (xs < X[k + 1])] = True
    return G
A, B = section(z), section(z - dz)
U = A & ~B; S = A & B
print(f"{sys.argv[1]} z {z}: solid {A.sum()*cell*cell:.0f} mm2, unsupported {U.sum()*cell*cell:.0f} mm2")
if U.any():
    sy, sx = np.where(S); P = np.c_[xs[sx], ys[sy]]
    uy, ux = np.where(U); Q = np.c_[xs[ux], ys[uy]]
    # nearest supported distance per unsupported cell (chunked brute force)
    D = np.empty(len(Q)); V = np.empty((len(Q), 2))
    for i in range(0, len(Q), 2000):
        q = Q[i:i + 2000]; dd = ((q[:, None, :] - P[None, :, :]) ** 2).sum(-1)
        k = dd.argmin(1); D[i:i + 2000] = np.sqrt(dd[np.arange(len(q)), k]); V[i:i + 2000] = P[k] - q
    i = D.argmax()
    # bridge test at the worst cell: is there support in the direction opposite the nearest support?
    q = Q[i]; v = V[i] / (np.linalg.norm(V[i]) + 1e-9)
    opp = None
    for r in np.arange(cell, 60, cell):
        p = q - v * r
        jx, jy = int((p[0] - xs[0]) / cell + 0.5), int((p[1] - ys[0]) / cell + 0.5)
        if not (0 <= jx < len(xs) and 0 <= jy < len(ys)): break
        if S[jy, jx]: opp = r; break
        if not A[jy, jx]: break                               # left the roof into air: cantilever edge
    kind = f"bridge, span {D[i] + opp:.1f} mm" if opp else f"cantilever/ledge, reach {D[i]:.1f} mm"
    print(f"  worst unsupported cell at ({q[0]:.1f}, {q[1]:.1f}): {D[i]:.1f} mm to support -> {kind}")
    for thr in (3, 5, 10):
        print(f"  cells farther than {thr} mm from support: {(D > thr).sum()*cell*cell:.0f} mm2")
