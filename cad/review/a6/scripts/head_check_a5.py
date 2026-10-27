"""Reviewer a5: independent re-derivation of the load-cell head numbers.
Reads cad/blender/manifest.json params only (geometry); every model below is the reviewer's own.
Run: python3 -I cad/review/a5/scripts/head_check_a5.py > cad/review/a5/head_check_a5.txt
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "..", "..", "..", "blender", "manifest.json")))["params"]
g = 9.81
t, b, L = P["leaf_t"], 2 * P["cart_hw"], P["leaf_free_len"]       # 2.0, 36, 27
pitch = P["leaf_pitch"]                                            # 47
y_leaf = (P["link0"] + P["link1"]) / 2                             # 85.5
y_grip, lip = 219.5, P["lip_y"]                                    # 219.5, 150
y_sock = P["link1"]                                                # 110, socket mouth
z_leaf_top = -15.0                                                 # cad q: link bottom / leaf tops (cell axis z 0)
sx = P["stop_x"]
I_leaf = b * t ** 3 / 12; A_leaf = b * t
def krot(E): return E * A_leaf / L * pitch ** 2 / 2                 # leaf pair push-pull, about the leaf centroid
def kpair(E): return 2 * 12 * E * I_leaf / L ** 3                   # parallel-guided y stiffness
out = []
def p(s=""): out.append(s)

p("== A. Overload stop: cell load past engagement (stop at 1.2 FS)")
# per-screw contacts (reviewer): head annulus Ø3.2-5.5 and nut (5.5 AF less Ø3.4) as flat punches on PLA,
# k = 1.13 E sqrt(A)/(1-nu^2); steel shank 23 mm on As 5.03; thread 50 kN/mm (designer).  Shared PLA path
# (link + block) 12.1 kN/mm taken from head_calc 3d, once for the pair (both screws load the same link/block).
E, nu = 3000.0, 0.35
def punch(A): return 1.13 * E * math.sqrt(A) / (1 - nu ** 2) / 1000
k_head = punch(math.pi / 4 * (5.5 ** 2 - 3.2 ** 2)); k_nut = punch(3 * math.sqrt(3) / 2 * (5.5 / math.sqrt(3)) ** 2 - math.pi / 4 * 3.4 ** 2)
k_sh = 210000 * 5.03 / 23 / 1000; k_th = 50.0
k_scr = 1 / (1 / k_head + 1 / k_nut + 1 / k_sh + 1 / k_th)
k_pair_shared = 1 / (1 / (2 * k_scr) + 1 / 12.1)
k_pair_designer = 7.6
p("  head %.1f, nut %.1f, shank %.1f, thread %.0f kN/mm -> %.2f per screw; pair with the shared PLA path in series: %.2f kN/mm (designer 7.6, PLA path per screw)"
  % (k_head, k_nut, k_sh, k_th, k_scr, k_pair_shared))
for name, kg in (("20 kg", 20), ("50 kg", 50)):
    FS = kg * g
    for dfs in (0.05, 0.1, 0.15, 0.2):
        kc = FS / dfs / 1000
        row = []
        for ks in (k_pair_shared, k_pair_designer):
            res = []
            for F in (400.0, 600.0):
                Fe = 1.2 * FS * (1 + kpair(E) / 1000 / kc)          # grip load at engagement (leaves shunt)
                if F <= Fe: c = F * kc / (kc + kpair(E) / 1000)
                else: c = 1.2 * FS + (F - Fe) * kc / (kc + ks + kpair(E) / 1000)
                res.append(c / FS)
            row.append("%.2f/%.2f" % tuple(res))
        p("  %s dFS %.2f: cell at 400/600 N = %s x FS (k_stop %.1f) | %s (k_stop 7.6)" % (name, dfs, row[0], k_pair_shared, row[1]))
p("  -> 50 kg: engagement itself is at 1.2 x 490 = 588 N, so a 600 N shove never takes it past 1.22 x FS. 20 kg: 1.36-1.88 x FS at 600 N.")

p("")
p("== B. Side load (link yaws, one screw of each pair closes by yaw x %.1f)" % sx)
kyaw = P["leaf_k_yaw"]; arm = y_grip - y_leaf
for F in (20, 50, 100):
    d = F * arm / kyaw * sx
    p("  %3d N sideways (free, k_yaw %.2e): one screw closes %.4f mm = %.2f FS at dFS 0.10; with a 20 kg cell the push stop on one side engages at %.2f FS = %3.0f N; 50 kg (gap 0.12 mm at dFS 0.1): %.2f FS = %3.0f N"
      % (F, kyaw, d, d / 0.1, 1.2 - d / 0.1, (1.2 - d / 0.1) * 20 * g, 1.2 - d / 0.1, (1.2 - d / 0.1) * 50 * g))

p("")
p("== C. Leaves")
fac = (y_grip - (P["link0"] + t / 2)) / pitch
for E_ in (2500, 3000, 3500):
    Pcr = 4 * math.pi ** 2 * E_ * I_leaf / L ** 2
    Pcr25 = 4 * math.pi ** 2 * E_ * I_leaf / (L - P["leaf_r"]) ** 2
    p("  E %d: fixed-fixed (sway held by the cell) %.0f N (L 27) / %.0f N (L 25); rear-leaf factor %.2f -> %.0f-%.0f N down per grip; pair y-stiffness %.0f N/mm"
      % (E_, Pcr, Pcr25, fac, Pcr / fac, Pcr25 / fac, kpair(E_)))
for gap in (0.12, 0.24, 0.30):
    sb = 3 * E * t * gap / (L - P["leaf_r"]) ** 2
    p("  root bending at a %.2f mm stop travel (guided, Le 25): %.1f MPa nominal, %.1f with Kt 1.35" % (gap, sb, 1.35 * sb))

p("")
p("== D. Lip catch and piston")
# D-section: Ø22.2 with a flat 7.8 from the axis (print height 18.9); bending about the horizontal axis
r = P["shaft_d"] / 2; cflat = P["shaft_flat"]
N = 4000; I = 0; A = 0
for i in range(N):
    z = -r + (i + 0.5) * 2 * r / N; dz = 2 * r / N
    w = 2 * math.sqrt(max(r * r - z * z, 0)); x0, x1 = -w / 2, w / 2
    x0 = max(x0, -cflat)                         # flat on one side (inboard)
    ww = max(x1 - x0, 0); A += ww * dz; I += ww * dz * z * z
p("  piston D-section: A %.0f mm2, I %.0f mm4 about the horizontal axis, c %.1f" % (A, I, r))
for E_ in (2500, 3000, 3500):
    th_per_N = (y_grip - y_leaf) / krot(E_)
    link_only = th_per_N * (lip - y_leaf)                            # rotation about the leaf centroid
    link_only_cell = th_per_N * (lip - (P["ye"] + 6.35))             # designer's lever (about the cell centre)
    a, Lg = lip - y_sock, y_grip - y_sock
    cp = a * a * (3 * Lg - a) / (6 * E_ * I)
    p("  E %d: lip closes %.5f mm/N link-only about the leaf centroid (designer lever about the cell: %.5f) + %.5f piston bending -> contact at %.0f N (link only %.0f N; designer-lever %.0f N)"
      % (E_, link_only, link_only_cell, cp, P["lip_c"] / (link_only + cp), P["lip_c"] / link_only, P["lip_c"] / (link_only_cell + cp)))
    Fc = P["lip_c"] / (link_only + cp)
    p("         rear leaf at contact %.0f N (buckle %.0f, x %.1f); push-head lift at contact (free, %.0f mm from the pivot): %.2f mm vs 0.5 radial"
      % (fac * Fc, 4 * math.pi ** 2 * E_ * I_leaf / L ** 2, 4 * math.pi ** 2 * E_ * I_leaf / L ** 2 / (fac * Fc), y_leaf - 45.85, Fc * th_per_N * (y_leaf - 45.85)))
for F in (300, 600, 800):
    s_lip = F * (y_grip - lip) * r / I
    s_sock = F * (y_grip - y_sock) * r / I
    R = F * (y_grip - y_sock) / (lip - y_sock)
    p("  %d N down: piston %.0f MPa at the lip (%.0f MPa at the socket mouth if the lip were absent); lip reaction about %.0f N" % (F, s_lip, s_sock, R))

p("")
p("== E. Vertical-to-axial crosstalk (new): the leaf tops are %.0f mm below the cell axis" % -z_leaf_top)
# Link pitches by w about the leaf centroid; the cell holds y at z 0, so the leaf tops shift 15 w along y while
# also turning w: end shear per leaf = EI/L^2 (12*15/L + 6) w, both terms the same sign.  That shear has to
# come out of the cell (the only other y path), so the cell reads it.
for E_ in (3000,):
    w_per_N = (y_grip - y_leaf) / krot(E_)
    F_shear = 2 * E_ * I_leaf / L ** 2 * (12 * (-z_leaf_top) / L + 6) * w_per_N
    p("  axial force in the cell per N down on the grip: %.4f (%.1f %%); 50 N -> %.1f N, 150 N -> %.1f N (%.1f %% / %.1f %% FS of a 50 kg cell)"
      % (F_shear, 100 * F_shear, 50 * F_shear, 150 * F_shear, 100 * 50 * F_shear / (50 * g), 100 * 150 * F_shear / (50 * g)))
    d0 = L / 2
    p("  it vanishes when the leaf tops sit L/2 = %.1f mm above the cell axis (leaf mid-length on the cell axis)" % d0)

p("")
p("== F. Bench cradle (new): rear upright is a free-standing 50 x 8 plate (layer_ascii.py slices at print z 12-50)")
h = 57.0 - 7.9                       # jack axis (print z 57) above the base top (print z 7.9)
bw, tw = 50.0, 8.0
Z = bw * tw ** 2 / 6; Iu = bw * tw ** 3 / 12
tb = 7.9; Zb = bw * tb ** 2 / 6
for kg in (20, 50):
    for frac in (1.2, 1.5):
        F = frac * kg * g
        M = F * h
        for E_ in (2500, 3000):
            dtip = F * h ** 3 / (3 * E_ * Iu); tilt = F * h ** 2 / (2 * E_ * Iu)
            p("  %d kg at %.1f FS: jack %.0f N, root moment %.1f N.m, %.0f MPa across layers at the upright root, %.0f MPa in the 7.9 base; E %d: tip moves %.2f mm, jack axis tilts %.1f deg"
              % (kg, frac, F, M / 1000, M / Z, M / Zb, E_, dtip, math.degrees(tilt)))
p("  jack head stands 3.0 mm off the upright (cadcheck warn FST_Jack_screw), so the push stroke ends when the upright")
p("  has bent ~3 mm minus the cell travel; PLA across layers is ~20-30 MPa.")

p("")
p("== G. Clamp creep vs stud stretch")
for Fp in (100, 200):
    stretch = Fp / 237000.0
    p("  preload %d N: stud stretch %.2f um; clamped PLA compression %.1f um (51 kN/mm). Creep of 0.15 %% over 4 mm = 6 um > stretch -> preload goes to ~0 over life" % (Fp, stretch * 1000, Fp / 51.0))
p("  with no preload a few-um gap only lets the leaves (110 N/mm) take 110 x 0.006 = %.1f N while it closes: negligible for the reading" % (110 * 0.006))

p("")
p("== H. Bench sketch scale")
for mvv in (1.0, 1.5, 2.0):
    p("  cell rated %.1f mV/V, sketch left at its 1.0 default (README never says r): '120 %%' is reached at %.0f %% of true FS" % (mvv, 120 / mvv))

print("\n".join(out))
