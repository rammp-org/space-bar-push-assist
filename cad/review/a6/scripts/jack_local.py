"""Reviewer a6: local load path of the bench jack (not in head_calc / cradle_frame).
Plug T-slot rear lip (pull) and the cradle upright's nut-pocket skin (push). Geometry from build_concept.build_bench /
bench_layout: plug r 11.1, swivel pocket R 4.85 x 5.0 open on +x (|z| < 4.85), neck R 2.9 open on +x (|z| < 2.9),
lip = plug1 - (t0 + 5) = 2.1 mm. M5 nut AF 8.0 (flats), upright pocket hex AF 8.1 flats vertical, skin 4.55.
Plug prints D-flat down (print up = +x); cradle base down."""
import numpy as np
AF = 8.0
def in_hex(x, z, af):  # flats at x = +-af/2 (vertical flats), corners on z
    a = af / 2
    return (np.abs(x) <= a) & (np.abs(x) / 2 + np.sqrt(3) / 2 * np.abs(z) <= a)
g = np.linspace(-6, 6, 1201); X, Z = np.meshgrid(g, g); dA = (g[1] - g[0]) ** 2
R = np.hypot(X, Z)
# nut's own hex orientation in the plug is free (it swivels): take the worst (flats on z) and best
for name, xx, zz in (("nut flats vertical", X, Z), ("nut flats horizontal", Z, X)):
    nut = in_hex(xx, zz, AF) & (R > 2.5)
    lip = (R > 2.9) & (R < 4.85) & ~((X > 0) & (np.abs(Z) < 2.9))
    c = nut & lip
    A = c.sum() * dA; rbar = R[c].mean()
    print(f"plug lip, {name}: nut-on-lip contact {A:.1f} mm2, centroid r {rbar:.2f}")
t = 2.1
sup = np.pi * 4.85 + 2 * 4.6   # semicircle wall (x<0) + the two pocket-open edges |z| = 4.85 out to the nut's reach
for F in (588.6, 1.3 * 490.5, 1.5 * 490.5):
    tau = F / (sup * t); m = F * (4.85 - 3.75) / sup; sig = 6 * m / t ** 2
    print(f"  F {F:5.0f} N: lip shear {tau:4.1f} MPa (peak x1.5 {1.5*tau:4.1f}), plate bending {sig:4.1f} MPa; "
          f"at the D-flat side (x -4.85) the shear plane is a layer plane")
for tl in (4.0, 5.0):
    F = 1.5 * 490.5; tau = F / (sup * tl); sig = 6 * F * 1.1 / sup / tl ** 2
    print(f"  fix lip {tl} mm at {F:.0f} N: shear {tau:.1f} MPa, bending {sig:.1f} MPa")
# upright skin behind the jack nut (push)
nut = in_hex(X, Z, AF) & (R > 2.5)
skin = ~((R < 2.9) | ((np.abs(X) < 2.9) & (Z > 0)))
A = (nut & skin).sum() * dA
per = 2 * (11 + 2.34) + 2 * 4.68
for F in (588.6, 1.5 * 490.5):
    print(f"upright skin (push), F {F:.0f}: nut bearing {A:.1f} mm2 -> {F/A:.0f} MPa (in layer plane); skin shear {F/(per*4.55):.1f} MPa")
