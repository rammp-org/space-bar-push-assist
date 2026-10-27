"""Reviewer a4: independent re-derivation of the load-cell head numbers (moment share, stop setting with the
stop line 24 mm below the cell axis, lean vs stop gap, overload past engagement, rear-leaf buckling under a
downward grip load, boss clamp stress). Reads params from cad/blender/manifest.json; geometry z values from
`cad q list` on check_moving.blend (cell axis z 0, link bottom z -15, stop screws z -24, grip axis z 0).
Run: python3 -I cad/review/a4/scripts/head_check.py"""
import json, math, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
P = json.load(open(os.path.join(root, "cad/blender/manifest.json")))["params"]
FS = 20 * 9.81
t, b, L, pitch = P["leaf_t"], 2 * P["cart_hw"], P["leaf_free_len"], P["leaf_pitch"]
y_leaf = (P["link0"] + P["link1"]) / 2          # 85.5
y_grip, z_cell, z_stop, z_link_bot = 219.5, 0.0, P["stop_z"], -P["link_h"]
arm = z_cell - z_stop                              # 24: stop line below the cell axis
print(f"stop line {arm:.0f} mm below the cell axis; leaf centroid y {y_leaf}, grip load at y {y_grip}")

def krot(E): return (E * b * t / L) * pitch ** 2 / 2   # leaf pair axial couple, N.mm/rad

print("\n== 1. moment share (cell rotational stiffness vs leaves)")
E = 3000.0; Es = E / (1 - 0.35 ** 2)
I = math.pi / 4 * ((P["seat_d"] / 2) ** 4 - 2.75 ** 4)
col = E * I / P["seat_h"]                          # boss column
half = 4 / 3 * Es * (P["seat_d"] / 2) ** 3          # rigid punch rocking on a half-space
face = 1 / (1 / col + 1 / half)
Is = math.pi * 4.1 ** 4 / 64                       # M5 stud core
stud_f = 200000 * Is / (P["seat_h"] + P["plate_t"] + P["floor_t"] + 1.6)
stud_r = 200000 * Is / (P["seat_h"] + 3.0 + 1.6)
designer = 1.29e5
for name, kc in (("designer column model", designer),
                 ("boss + half-space, 2 faces in series", face / 2),
                 ("+ stud bending path in parallel each face", 1 / (1 / (face + stud_f) + 1 / (face + stud_r)))):
    for Eh in (2500, 3000):
        s = kc / (kc + krot(Eh))
        print(f"  {name:45s} E{Eh}: k_cell {kc:.3g}, share {100*s:.1f} %, 150 N down -> {s*150*(y_grip-53.65)/1000:.2f} N.m in the cell")

print("\n== 2. stop set by jacking the tongue (z -24) vs use (grip force on the cell axis, z 0)")
print("  jack force F at the tongue makes a couple F*arm on the link, carried by the leaves -> extra tongue travel F*arm^2/k_rot")
for Eh in (2500, 3000, 3500):
    extra = 1.2 * FS * arm ** 2 / krot(Eh)
    row = ", ".join(f"dFS {d}: engages at {1.2 + extra / d:.2f} x FS" for d in (0.05, 0.1, 0.15, 0.2))
    print(f"  E{Eh}: extra {extra:.3f} mm -> {row}")
print("  designer stack (push) worst case 0.163 FS; with this term at dFS 0.1, E3000: 0.163 + %.2f = %.2f vs limit 0.3"
      % (1.2 * FS * arm ** 2 / krot(3000) / 0.1, 0.163 + 1.2 * FS * arm ** 2 / krot(3000) / 0.1))

print("\n== 3. downward lean on the grip consumes the push gap (link turns about the cell's attachment point)")
for Fz in (50, 100, 150, 250):
    th = Fz * (y_grip - y_leaf) / krot(3000)
    dy = th * arm
    out = []
    for d in (0.05, 0.1):
        gap = 1.2 * d + 1.2 * FS * arm ** 2 / krot(3000)
        out.append(f"dFS {d}: push clips at {max(0,(gap - dy)) / d:.2f} x FS")
    print(f"  {Fz:3d} N down: tongue moves {dy:.3f} mm toward the push screw; " + "; ".join(out))

print("\n== 4. load in the cell past engagement (20 kg cell), stop path 2.34 kN/mm (designer) in series with the link")
ks = 2340.0; ks_eff = 1 / (1 / ks + arm ** 2 / krot(3000))
print(f"  stop at the tongue referred to the grip axis: {ks_eff:.0f} N/mm")
for d in (0.05, 0.1, 0.15):
    kc = FS / d; ext = 1.2 * FS * arm ** 2 / krot(3000)
    Fe = (1.2 + ext / d) * FS * (1 + 44 / kc)
    cells = []
    for F in (400, 600):
        x = (Fe / (kc + 44)) + max(0, F - Fe) / (kc + 44 + ks_eff)
        cells.append(kc * x / FS)
    print(f"  dFS {d}: engages at {Fe:.0f} N; cell at 400 / 600 N push = {cells[0]:.2f} / {cells[1]:.2f} x FS")

print("\n== 5. rear leaf in compression under a downward grip load")
fac = (y_grip - y_leaf) / pitch + 0.5
for Eh in (2500, 3000, 3500):
    Ig = b * t ** 3 / 12; In = (b - 6.5) * t ** 3 / 12
    Pg = 4 * math.pi ** 2 * Eh * Ig / L ** 2; Pn = 4 * math.pi ** 2 * Eh * In / L ** 2
    print(f"  E{Eh}: leaf load = {fac:.2f} x grip load; buckles at {Pn/fac:.0f}-{Pg/fac:.0f} N down per grip;"
          f" axial drop at buckling {Pg*L/(Eh*b*t):.2f} mm (backstop at cav {P['cav']})")
for tt in (2.0,):
    Pg = 4 * math.pi ** 2 * 3000 * b * tt ** 3 / 12 / L ** 2
    print(f"  leaf_t {tt}: buckles at {Pg/fac:.0f} N per grip (E3000), pair y-stiffness {44*(tt/t)**3:.0f} N/mm, "
          f"root bending at 0.30 {1.35*3*3000*tt*0.30/(L-1.5)**2:.1f} MPa")

print("\n== 6. seat-boss clamp stress (M5, K 0.2)")
a = math.pi / 4 * (P["seat_d"] ** 2 - 5.5 ** 2)
for T in (0.5, 1.0, 1.5, 2.0):
    Fp = T / (0.2 * 0.005)
    print(f"  {T} N.m -> {Fp:.0f} N preload, boss {Fp/a:.1f} MPa")
