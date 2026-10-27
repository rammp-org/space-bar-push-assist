"""Reviewer a3 hand calcs for the parallel-leaf cartridge (numbers from manifest params + build_cartridge)."""
import math
b, t, d = 36.0, 1.5, 47.5            # leaf width (x), thickness (y), pitch (y 61.75 -> 109.25)
Lc, Le = 27.0, 35.0                   # free length at centre / at the chamfered edges (top link octagon)
y_leaf, y_cell, y_grip = 85.5, 53.65, 219.5
for E in (2500.0, 3500.0):
    I = b * t**3 / 12
    k1 = 12 * E * I / Lc**3            # guided-guided, centre length (upper bound)
    print(f"E={E:.0f}: leaf pair axial-y stiffness {2*k1:.0f} N/mm (centre L) ; buckling fixed-fixed rear leaf "
          f"{4*math.pi**2*E*I/Lc**2:.0f} N (t1.5), {4*math.pi**2*E*(b*1.4**3/12)/Lc**2:.0f} N (t1.4)")
E = 3000.0
for gap in (0.025, 0.25, 0.357, 0.475):
    s = 3 * E * t * gap / Lc**2
    print(f"gap {gap:.3f}: leaf root stress {s:.1f} MPa nominal, {2.0*s:.1f}-{2.5*s:.1f} MPa with sharp-root Kt 2.0-2.5")
print("stop engagement force vs 20 kg cell FS 196 N (cell FS deflection unknown):")
for dfs in (0.05, 0.10, 0.15, 0.20):
    kc = 196 / dfs
    row = []
    for gap in (0.025, 0.25, 0.475):
        F = gap * (kc + 45)
        row.append(f"gap {gap}: {F:.0f} N = {F/196:.1f} x FS")
    print(f"  dFS {dfs} mm (k {kc:.0f} N/mm): " + "; ".join(row))
# moment sharing between leaves and the clamped cell
ka = E * b * t / Lc                   # one leaf axial
k_leaf_rot = ka * d**2 / 2
I_face = math.pi * 12.7**4 / 4        # O25.4 cell face on PLA
k_front = E * I_face / 6.4            # 3.0 front plate + 3.4 fin floor
k_rear = E * I_face / 4.0             # top-link front wall 60 -> 64
k_cell_rot = 1 / (1 / k_front + 1 / k_rear)
frac = k_cell_rot / (k_cell_rot + k_leaf_rot)
print(f"rot stiffness: leaves {k_leaf_rot:.3g} N.mm/rad, clamped cell faces {k_cell_rot:.3g} -> cell share {frac*100:.0f} %")
for Fv in (50, 150):
    M = Fv * (y_grip - y_cell)
    print(f"  {Fv} N down at grip centre: M at cell {M/1000:.1f} N.m, through cell {frac*M/1000:.1f} N.m "
          f"= edge load {frac*M/12.7:.0f} N on the O25.4 puck ({frac*M/12.7/196:.1f} x FS)")
    Mleaf = Fv * (y_grip - y_leaf) * (1 - frac)
    print(f"     leaves: couple {Mleaf/d:.0f} N per leaf, {Mleaf/d/(b*t):.1f} MPa axial")
# with a O8 seat boss on both faces
I8 = math.pi * 4**4 / 4
kc8 = 1 / (1 / (E * I8 / 6.4) + 1 / (E * I8 / 4.0))
print(f"with O8 x 1 seat bosses: cell share {kc8/(kc8+k_leaf_rot)*100:.1f} %")
# sideways load: interlayer shear in leaves
for Fx in (50, 150):
    V = Fx * (y_grip - y_leaf) / d
    print(f"  {Fx} N sideways: {V:.0f} N per leaf in-plane shear -> {1.5*V/(b*t):.1f} MPa peak interlayer shear")
# tongue wall under the stop hole
print(f"tongue wall below the O4.5 hole: {4/math.sqrt(2) - 2.25:.2f} mm")
