"""Reviewer a7: independent head numbers from the manifest params (no import of head_calc).
python3 -I head_a7.py manifest.json"""
import json, math, sys
P = json.load(open(sys.argv[1]))['params']
E = 3000.0
t, ws = P['leaf_t'], P['cart_hw'] - P['leaf_gap']          # 2.5, 12.5
b = 2 * ws                                                 # 25 per leaf
L = -P['link_h'] - P['ground_z'][1]                        # 27
Le = L - P['leaf_r']                                       # 25 between fillet tangents
yf, yr = P['leaf_f0'] + t / 2, P['link1'] - t / 2          # 76.75, 121.75
pitch = yr - yf
GY = 219.5
cz = P['cell_z']
c0 = P['link1'] + 2 * P['leaf_r'] + 1.0; c1 = c0 + t; yc = (c0 + c1) / 2
I_s = b * t ** 3 / 12                                      # one leaf (two strips) about its thin axis
print(f"leaf: b {b} t {t} L {L} Le {Le} pitch {pitch} yc {yc}")

# 1. crosstalk: link turns theta about the cell (y-fixed at cz). leaf top at z_top = -link_h, bottom fixed at -42.
#    top moves dy = -theta*(z_top - cz) (sign irrelevant), rotates theta. Shear V = 12EI/L^3 dy - 6EI/L^2 theta.
for Lb in (L, Le):
    for e in (0.0, 0.2, 0.5):
        a = (-P['link_h'] - cz) + e                         # leaf top above the cell axis
        V = 12 * E * I_s / Lb ** 3 * a - 6 * E * I_s / Lb ** 2  # per unit theta, per leaf
        # theta per N of lean: leaves axial couple, k_rot = EA/L * pitch^2/2
        k_rot = E * b * t / L * pitch ** 2 / 2
        th = (GY - (yf + yr) / 2) / k_rot
        print(f"crosstalk Lb {Lb} offset {e}: {2*V*th*100:.3f} % of the lean")

# 2. lean before contact: link pitch about the cell? vertical load splits axially into leaves; theta from the couple
EA_L = E * b * t / L                                       # axial stiffness of one leaf, N/mm
print(f"leaf axial k {EA_L:.0f} N/mm")
I_p = math.pi * (P['shaft_d'] / 2) ** 4 / 4 - 435.0
for EE in (2500., 3500.):
    kl = EE * b * t / L
    # unit load at GY: leaf forces (statics, two supports): Rf = -(GY-yr)/pitch, Rr = (GY-yf)/pitch
    Rf, Rr = -(GY - yr) / pitch, (GY - yf) / pitch
    wf, wr = Rf / kl, Rr / kl                              # down displacement (+ = down) per N, compression = down
    th = (wr - wf) / pitch
    w_c = wr + th * (yc - yr)
    a_c = yc - P['link1']; Lg = GY - P['link1']
    w_c += a_c ** 2 * (3 * Lg - a_c) / (6 * EE * I_p)
    print(f"E {EE:.0f}: catch contact at {P['catch_c']/w_c:.0f} N (0.1); with c 0.2 {0.2/w_c:.0f} N; rear leaf {Rr:.2f} x lean")

# 3. past contact: three supports (front leaf, rear leaf, catch) on a rigid link, solve
def three(EE, kc_ax):
    kl = EE * b * t / L
    ys, ks = [yf, yr, yc], [kl, kl, kc_ax]
    # w(y) = w0 + th*(y - yc) ; sum k w = F ; sum k w (y-yc) = F (GY - yc)
    A = sum(ks); B = sum(k * (y - yc) for k, y in zip(ks, ys)); C = sum(k * (y - yc) ** 2 for k, y in zip(ks, ys))
    F, M = 1.0, GY - yc
    det = A * C - B * B
    w0 = (F * C - B * M) / det; th = (A * M - B * F) / det
    return [k * (w0 + th * (y - yc)) for k, y in zip(ks, ys)]
for EE in (2500., 3500.):
    lc = 2 * EE * ws * t / (P['catch_z'] - P['ground_z'][1])
    for kc in (lc, lc / 3, 1e9):
        Rf, Rr, Rc = three(EE, kc)
        F0 = 147 if EE == 2500 else 206
        rear_at_contact = F0 * (GY - yf) / pitch
        print(f"E {EE:.0f} k_catch_ax {kc:.0f}: per N past contact front {Rf:.2f} rear {Rr:.2f} catch {Rc:.2f}; at 600 N rear strips {rear_at_contact + (600-F0)*Rr:.0f} N, catch {(600-F0)*Rc:.0f} N")
    pcr = 4 * math.pi ** 2 * EE * I_s / L ** 2
    pcr_e = 4 * math.pi ** 2 * EE * I_s / Le ** 2
    print(f"  rear leaf buckling fixed-fixed L27 {pcr:.0f} N, Le25 {pcr_e:.0f} N")

# 4. catch legs y stiffness: free (tip at saddle), guided, with saddle height h to contact
Lc = P['catch_z'] - P['ground_z'][1]; h = P['catch_z'] - (-(P['shaft_d'] / 2))  # contact at piston bottom
h = abs(h)
I_l = ws * t ** 3 / 12
EI = E * I_l
d_free = (Lc ** 3 / 3 + h * Lc ** 2 + h * h * Lc) / EI     # per N at the contact, free saddle
print(f"catch legs: Lc {Lc} h {h:.1f}; k pair: 3EI/L^3 {2*3*EI/Lc**3:.1f}, free saddle at contact {2/d_free:.1f}, guided 12EI/L^3 {2*12*EI/Lc**3:.1f} N/mm")
for k in (2/d_free, 2*3*EI/Lc**3, 2*12*EI/Lc**3):
    print(f"  shunt at 0.12 mm (dFS 0.10 x1.2) {k*0.12:.1f} N, at 0.30 mm {k*0.30:.1f} N")
# guided-moment needed vs contact capacity N * t/2
M_need = 2 * 6 * EI * 0.12 / Lc ** 2
print(f"  moment to hold the saddle square at 0.12 mm: {M_need:.0f} N.mm -> contact normal force needed {M_need/(t/2):.0f} N (contact face {t} long)")

# 5. piston bending
for F in (300, 600):
    print(f"piston at {F} N on catch: {F*(GY-yc)*P['shaft_d']/2/I_p:.1f} MPa; on lip(150) {F*(GY-150)*P['shaft_d']/2/I_p:.1f}")

# 6. push couple in the leaves
for F in (490.5 * 1.2, 600):
    print(f"push {F:.0f} N: leaf couple +-{F*(P['arm_z']-cz)/pitch:.0f} N")
# 7. side load: link yaw on strips. stops at x +-14.9. lateral 20 N at grip
ws2 = ws; xs = (P['cart_hw'] + P['leaf_gap']) / 2
I_x = 2 * (t * ws2 ** 3 / 12 + t * ws2 * xs ** 2)
G = E / 2.6
kx = 1 / (1 / (12 * E * I_x / L ** 3) + 1 / (5 / 6 * G * b * t / L))
k_yaw = 2 * kx * (pitch / 2) ** 2
print(f"side: kx per leaf {kx:.0f} N/mm; k_yaw {k_yaw:.3g} N.mm/rad")
for Fs in (20,):
    for arm in (GY - (yf + yr) / 2,):
        yaw = Fs * arm / k_yaw
        print(f"  {Fs} N side: yaw {yaw:.2e} rad, stop closes {yaw*P['stop_x']:.4f} mm = {yaw*P['stop_x']/0.1:.2f} FS at dFS 0.10")
