"""Hand calcs for the load-cell head (flexure cartridge, seat bosses, overload stops, lip catch, clamps, bench checks).

Attempt 8 (a7 review): the catch saddle is crowned (free legs, 4c), 9.5 thick in y (across-layer bending, 4d), and section
4 solves three supports past contact (4d) with reviewer a7's contact model (4a); the piston is Ø24 in the socket (4e).
Attempt 7 (a6 review): the cell axis is on the leaves' mid-height (cz, 28.5 below the grip axis), so a lean puts no axial
force on the cell; each leaf is two 2.5 mm strips; a y-compliant catch saddle behind the rear leaf takes heavy leans
with no friction path; the known-mass check is a gate with a 0.88 floor; section 4 gives one buckling margin.
Attempt 6 (a5 review: lip lever about the leaf centroid, lean crosstalk, the closed-frame cradle, the known-mass check).
Attempt 5. One calc for both views: the designer's models and reviewer a4's (cad/review/a4/scripts/head_check.py,
merged here: moment share with the M5 stud bending path, jacking couple, lean, overload past engagement, rear-leaf
buckling, boss clamp stress). It reads cad/blender/manifest.json (written by to_cadcheck.py), so the numbers follow
the geometry. Run: python3 -I cad/calc/head_calc.py > cad/calc/head_calc.txt

All small-deflection and linear. E for printed PLA 2500-3500 MPa in the layer plane (3000 nominal). Two models for
how the link turns, as in the a4 review: "free" = the cell carries no shear, the leaves carry the whole grip load
(conservative for leaf forces and lean), "pinned" = the clamped cell pins the link at its centre (stiffer).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = json.load(open(os.path.join(HERE, "..", "blender", "manifest.json")))["params"]

E_lo, E, E_hi = 2500.0, 3000.0, 3500.0
E_st, nu = 200000.0, 0.35
Es = E / (1 - nu ** 2)
G_ = E / 2.6
KT = 1.35
SAFE = 1.5                                       # assumed safe overload of a JHD-type puck (check the datasheet)
CELLS = {"20 kg": 20 * 9.81, "50 kg": 50 * 9.81}
FS = CELLS["20 kg"]
out = []


def p(*a):
    out.append(" ".join(str(x) for x in a))


t, b = P["leaf_t"], P["leaf_b"]                  # a7: two strips per leaf, |x'| leaf_gap..cart_hw
L = P["leaf_free_len"]
Le = L - P["leaf_r"]
pitch = P["leaf_pitch"]
l0, l1 = P["link0"], P["link1"]
y_front, y_rear = P["leaf_f0"] + t / 2, l1 - t / 2      # a7: the front leaf stands behind the drop
y_leaf = (y_front + y_rear) / 2
y_cell = P["ye"] + 6.35                          # cell centre (along y)
cz = P["cell_z"]                                 # a7: cell axis height; the grip axis is z 0
y_grip = 219.5                                   # middle of the hand
y_end = y_grip + 60                              # grip end (bench check weight)
lip = P["lip_y"]
sx, zp, zq = P["stop_x"], P["stop_zp"] - cz, P["stop_zq"] - cz   # stop heights from the cell axis (the pitch axis)


def krot(e):                                     # leaf pair against pitch, free model (reviewer a4)
    return (e * b * t / L) * pitch ** 2 / 2


def krot_pinned(e):                              # turning about the cell centre
    return (e * b * t / L) * ((y_front - y_cell) ** 2 + (y_rear - y_cell) ** 2)


def kx_leaf(e):                                  # one leaf (two strips), in-plane (x) bending + shear
    ws, xs = P["cart_hw"] - P["leaf_gap"], (P["cart_hw"] + P["leaf_gap"]) / 2
    I_x = 2 * (t * ws ** 3 / 12 + t * ws * xs ** 2)
    return 1 / (1 / (12 * e * I_x / L ** 3) + 1 / (5 / 6 * e / 2.6 * b * t / L))


p("== 1. Leaves (two, each two strips: %.0f wide in all x %.1f, free length %.0f, %.0f between the r %.1f fillet tangents, "
  "pitch %.1f; mid-length on the cell axis)" % (b, t, L, Le, P["leaf_r"], pitch))
fac = (y_grip - y_front) / pitch                 # rear-leaf compression per N down on the grip (moments about the front leaf)
for e in (E_lo, E, E_hi):
    Pcr = 4 * math.pi ** 2 * e * (b * t ** 3 / 12) / L ** 2
    p("E %4.0f: pair y-stiffness %3.0f N/mm; rear leaf buckles at %4.0f N = %4.0f N down on one grip (leaf load %.2f x grip "
      "load); axial drop at buckling %.2f mm" % (e, 2 * 12 * e * (b * t ** 3 / 12) / Le ** 3, Pcr, Pcr / fac, fac,
                                                  Pcr * L / (e * b * t)))
p("a6: 36 x 2.0 full-width leaves, 1000-1400 N per grip. a7 strips 2 x %.1f x %.1f: the gap between them (|x'| < %.1f) is the "
  "8 mm nut-driver's line to the rear cell nut." % ((b / 2), t, P["leaf_gap"]))
for gap in (P["stop_gap"], P["stop_gap_max"]):
    sb = 3 * E * t * gap / Le ** 2
    p("root bending with the link at a %.2f stop setting: %.1f MPa nominal, %.1f MPa at the root" % (gap, sb, KT * sb))
for F in (50, 150):
    p("%3d N down on the grip: %.0f N in the rear leaf, %.1f MPa axial (%.1f at the root)"
      % (F, fac * F, fac * F / (b * t), KT * fac * F / (b * t)))
p("flexures row: Kt x (bending at stop_gap_max + axial at 150 N) = %.1f MPa, in the layer plane" % P["leaf_stress_mpa"])
p("")

p("== 2. Moment share: leaves vs the clamped cell (reviewer a4 section 1, a7: Ø12 bosses, the strip leaves)")
I_b = math.pi / 4 * ((P["seat_d"] / 2) ** 4 - 2.75 ** 4)
Is = math.pi * 4.1 ** 4 / 64                     # M5 stud core
stud_f = E_st * Is / (P["seat_h"] + P["block_c"] + 1.6)      # front stud: boss + block under the washer + washer
stud_r = E_st * Is / (P["seat_h"] + 3.0 + 1.6)               # rear stud: boss + link front wall + washer
share = {}
for Eh in (E_lo, E):
    Esh = Eh / (1 - nu ** 2)
    col = Eh * I_b / P["seat_h"]
    half = 4 / 3 * Esh * (P["seat_d"] / 2) ** 3
    face = 1 / (1 / col + 1 / half)
    models = (("boss as a 1 mm column, no half-space (stiff bound)", 1 / (1 / col + 1 / col)),
              ("boss + half-space, two faces in series", face / 2),
              ("+ M5 stud bending path in parallel at each face", 1 / (1 / (face + stud_f) + 1 / (face + stud_r))))
    for name, kc in models:
        s = kc / (kc + krot(Eh))
        share[(name, Eh)] = s
        p("  %-48s E%4.0f: k_cell %.3g, leaves %.3g N.mm/rad, share %.1f %%, 150 N down -> %.2f N.m through the cell"
          % (name, Eh, kc, krot(Eh), 100 * s, s * 150 * (y_grip - y_cell) / 1000))
s_hi = max(share.values())
M5 = 5 * 9.81 * (y_end - y_cell)
p("a4 with 1.5 leaves: 1.9 % (designer) / 2.9-6.7 % (reviewer); the 2.0 leaves raise k_rot by 4/3.")
p("")

p("== 3. Overload stops on the cell axis (a4 #1)")
p("push pair at x' +-%.1f, z %+.1f from the cell axis (on it); pull pair at x' +-%.1f, z %+.1f from it. Heads act on the block; nuts in the link."
  % (sx, zp, sx, zq))
p("3a. Setting. The cradle's jack screw is on the grip axis (z 0), as the grip is. Both act %.1f above the cell axis, so "
  "both turn the link by F x %.1f / k_rot about the cell; the push stops sit on the cell axis and do not move, the pull "
  "pair (%.1f below it) moves %.4f mm at 1.2 x FS of a 50 kg cell, but the jack loads it exactly as the grip does, so "
  "the setting includes it (error 0). That pitch bends no leaf (mid-length on the cell axis): the cell reads the push."
  % (-cz, -cz, -zq, 1.2 * CELLS["50 kg"] * (-cz) / krot(E) * abs(zq)))
p("3b. Lean / lift (link pitches theta about the cell): a stop contact at height z moves z x theta along the axis.")
for Fz in (50, 100, 150, 250):
    th = Fz * (y_grip - y_leaf) / krot(E)
    p("  %3d N down: theta %.5f rad; push contacts (z %+.1f) move %.4f mm (the a4 tongue moved %.3f); pull contacts "
      "(z %+.1f) move %+.4f mm, i.e. the pull gap opens (lift: closes by the same)"
      % (Fz, th, zp, abs(th * zp), th * 24 * krot(E) / ((E * b * 1.5 / 27) * 47.5 ** 2 / 2), zq, -th * zq))
th100 = 100 * (y_grip - y_leaf) / krot(E)
p("  100 N lift clips the pull stop early by %.3f mm = %.2f FS at dFS 0.10 (stack row limit 0.2)" % (th100 * abs(zq), th100 * abs(zq) / 0.1))
p("3c. Side load (link yaws, one screw of each pair closes by yaw x %.1f):" % sx)
for Fx in (10, 20, 30):
    for name, ky, lever in (("free", kx_leaf(E) * pitch ** 2 / 2, y_grip - y_leaf),
                            ("pinned at the cell", kx_leaf(E) * ((y_front - y_cell) ** 2 + (y_rear - y_cell) ** 2), y_grip - y_cell)):
        d = Fx * lever / ky * sx
        p("  %2d N sideways, %-18s: %.4f mm = %.2f FS early on one side at dFS 0.10 (%.2f at dFS 0.05)" % (Fx, name, d, d / 0.1, d / 0.05))
p("  The stops sit beside the cell (it is in the way of x' 0), so side load is the one direction they still feel. "
  "The 20 N row (free model) is in checks.json at limit 0.2. Past %.2f mm sideways the catch saddle round the piston "
  "takes a side load (y-compliant, as for a lean)." % P["catch_c"])

p("3d. Stop path stiffness (per screw, in series; two screws per direction in parallel)")
a_nut = 3 * math.sqrt(3) / 2 * (5.5 / math.sqrt(3)) ** 2 - math.pi / 4 * 3.4 ** 2
k_nut = 2 * Es * math.sqrt(a_nut / math.pi)
A_core = math.pi / 4 * 2.39 ** 2
k_thr = 50000.0                                  # M3 thread engagement in a steel nut (order of magnitude)
rows = {}
for name, d_in, shank, pla_len in (("push", 3.2, P["nut_p1"] - (P["pf"] + P["stop_gap"]), P["pf"] - P["yp"]),
                                   ("pull", P["stop_hole"], P["nut_q0"] - P["at_q"], P["yb"] - P["qf"])):
    a_head = math.sqrt((5.2 ** 2 - d_in ** 2) / 4)
    k_head = 2 * Es * a_head
    k_sh = E_st * A_core / shank
    k_pla = E * 60.0 / pla_len + E * 60.0 / 8.0  # block under the head (~60 mm2 spread) + link wall to the socket
    k_pla = 1 / (1 / (E * 60.0 / pla_len) + 1 / (E * 60.0 / 8.0))
    k1 = 1 / (1 / k_head + 1 / k_nut + 1 / k_sh + 1 / k_thr + 1 / k_pla)
    rows[name] = 2 * k1
    p("  %s: head on PLA (annulus Ø%.1f-5.2) %.1f, nut on PLA %.1f, shank (%.0f mm) %.0f, thread %.0f, PLA block + link "
      "%.1f kN/mm -> %.1f per screw, %.1f kN/mm per pair" % (name, d_in, k_head / 1e3, k_nut / 1e3, shank, k_sh / 1e3,
                                                             k_thr / 1e3, k_pla / 1e3, k1 / 1e3, 2 * k1 / 1e3))
p("  a4: 2.3 kN/mm (one M4 tip on PLA, a 3.45 mm post wall in bending) and 1.95 at the grip axis with the link turning.")
k_stop = rows["push"]
kl = P["leaf_k_pair"]
p("3e. Cell load past engagement (stop engages at 1.2 FS; past it the stop and leaves share the extra)")
p("  %-6s %-6s %-12s %-26s %s" % ("cell", "dFS", "gap mm", "cell at 400 / 600 N (x FS)", "under the assumed 1.5 x FS safe overload?"))
for cname, fs in CELLS.items():
    for dfs in (0.05, 0.075, 0.10, 0.15, 0.20):
        kc = fs / dfs
        Fe = 1.2 * fs * (1 + kl / kc)
        cs = []
        for F in (400, 600):
            x = F / (kc + kl) if F <= Fe else 1.2 * dfs + (F - Fe) / (kc + kl + k_stop)
            cs.append(kc * x / fs)
        p("  %-6s %-6.3f %-12.3f %.2f / %.2f %-16s %s" % (cname, dfs, 1.2 * dfs, cs[0], cs[1], "",
                                                     "yes" if cs[1] <= SAFE else "no (%.0f N push holds it to 1.5)"
                                                     % (1.2 * fs * (1 + kl / kc) + (SAFE - 1.2) * fs / kc * (kc + kl + k_stop))))
p("  The a4 review's target (about 3.5 kN/mm) is met (%.1f kN/mm). A stiff 20 kg cell (dFS 0.05-0.075) still passes "
  "1.5 x FS before 600 N; any 50 kg cell stays at or under 1.2 x FS at 600 N. Recommendation in the BOM: the 50 kg "
  "puck (same body and studs), with a 20 kg cell only if its full-scale travel is 0.1 mm or more. Alex decides."
  % (k_stop / 1e3))
p("3f. Thermal: push gap %+.4f, pull gap %+.4f mm per 10 C (PLA 68e-6, steel 12e-6 along each path)"
  % (P["stop_dT_p"] * 10, P["stop_dT_q"] * 10))
p("")

p("== 4. Lean stops: the catch saddle (a7, a6 #5; a8: crowned, three supports past contact), then the barrel lip (backup)")
# a8 (a7 #3): reviewer a7's model (cad/review/a7/scripts/head_a7.py), adopted: the leaves as two axial supports (statics),
# the link turning on their compression, plus the piston's own bending as a cantilever from the socket mouth.
y_c = P["catch_y"]
yf_, yr_ = P["leaf_f0"] + t / 2, l1 - t / 2


def dbar_I(d, flat, n=2000):
    r, I = d / 2, 0.0
    for i in range(n):
        z = -r + (i + 0.5) * 2 * r / n
        hw = math.sqrt(max(r * r - z * z, 0.0))
        I += z * z * max(hw - max(-hw, -flat), 0.0) * 2 * r / n
    return I


I_p = dbar_I(P["shaft_d"], P["shaft_flat"])      # Ø22.2 spigot (lip, step)
I_pc = dbar_I(P["piston_d"], P["shaft_flat"])    # a8: Ø24 in the socket and past the catch
L_grip = y_grip - l1


def drop_per_n(y, e, Ipp):
    kl_ = e * b * t / L
    wf, wr = -(y_grip - yr_) / pitch / kl_, (y_grip - yf_) / pitch / kl_
    a_ = y - l1
    return wr + (wr - wf) / pitch * (y - yr_) + a_ ** 2 * (3 * L_grip - a_) / (6 * e * Ipp)


p("catch_c %.2f radial over an R%.1f crown at y %.2f (%.1f behind the link), on two legs %.1f x %.1f x %.0f tall from the "
  "ground bar, under a saddle %.1f thick in y; lip_c %.2f round the Ø%.1f spigot at y %.0f; the piston is Ø%.0f to y %.0f"
  % (P["catch_c"], P["catch_crown_r"], y_c, y_c - l1, b / 2, t, P["catch_z"] - P["ground_z"][1], P["saddle_t"], P["lip_c"],
     P["shaft_d"], lip, P["piston_d"], P["piston_step"]))
p("4a. Contact (reviewer a7's model: two axial supports + the piston's bending; a7's designer model turned the link about the "
  "leaf centroid and read 10-13 % high):")
for name, yy, gap, Ipp in (("catch", y_c, P["catch_c"], I_pc), ("lip", lip, P["lip_c"], I_p)):
    for e in (E_lo, E, E_hi):
        per = drop_per_n(yy, e, Ipp)
        F_ = gap / per
        Pcr = 4 * math.pi ** 2 * e * (b * t ** 3 / 12) / L ** 2
        p("  %-5s E%4.0f: %.5f mm/N, contact at %4.0f N on the grip; the rear strips then carry %4.0f N (x %.1f to buckle)"
          % (name, e, per, F_, fac * F_, Pcr / (fac * F_)))
p("  Tolerance (row): the catch at E 3500 with its bore 0.1 big lands at %.0f N, before the lip at E 2500 with its bore 0.1 "
  "small, %.0f N. Link-only bound: the drop at the catch when the rear strips buckle is %.2f mm against catch_c + 0.2."
  % (P["catch_contact_hi_n"] * (P["catch_c"] + 0.1) / P["catch_c"], P["lip_contact_lo_n"] * (P["lip_c"] - 0.1) / P["lip_c"],
     P["catch_drop_buckle"]))
p("4b. Pull and lean together (a7 #5): 1.2 x FS of a 50 kg cell, pulled on the grip axis, turns the link and lowers the piston "
  "%.3f mm at the catch (a push raises it the same). catch_c %.2f leaves %.3f, which a further %.0f N of lean takes up "
  "(E 2500). So a full pull plus a 100 N lean does not land (row). If it did land, the free legs (4c) add about %.1f N."
  % (P["catch_push_motion"], P["catch_c"], P["catch_c"] - P["catch_push_motion"], P["catch_pull_lean_margin"],
     P["catch_k"] * (P["catch_c"] - P["catch_push_motion"])))
p("4c. No friction path (a7 #2). Once a lean rests on the saddle, stick friction drags it along with the piston, and the cell "
  "loses the legs' y-stiffness x its own travel.")
p("  a7's flat 2.5 mm saddle face could be held square by the contact (it needs ~116 N of normal force), so its legs worked "
  "fixed-guided: %.0f N/mm, 13-33 N (reviewer a7). a8 crowns the face R%.1f across y: the contact is a line, the normal force "
  "acts through the crown's centre, and the saddle is free to turn. The legs then bend as free cantilevers loaded %.2f mm "
  "above their tops: k = 2 / ((L^3/3 + h L^2 + h^2 L) / E I) = %.1f N/mm."
  % (P["catch_k_guided"], P["catch_crown_r"], P["catch_h"], P["catch_k"]))
p("  Shunt: %.1f N at the 1.2 x FS travel of a dFS 0.10 cell, %.1f N at the largest stop setting (0.30 mm). Rows, limit 10."
  % (P["catch_k"] * 1.2 * P["dfs_ref"], P["catch_k"] * P["stop_gap_max"]))
p("  Crown flattening: PLA yields at the crown under a heavy lean. After a 600 N lean the land is up to %.2f mm wide (load "
  "%.0f N, 10 mm of contact along the bore at 80 MPa), and a later lean holds up to N x %.2f mm against the saddle's turn, "
  "which adds %.4f N per N.mm at the contact. At a 300 N lean (catch %.0f N) the shunt is then %.1f N at the largest "
  "setting (row, limit 10). While a 600 N lean is on one grip it can reach %.1f N (capped by the guided value): the one "
  "case over the 10 N dead band (README)." % (2 * P["catch_land"], P["catch_load_600"], P["catch_land"], P["catch_g_mom"],
                                            P["catch_300"], P["catch_shunt_300"], P["catch_shunt_600"]))
p("4d. Past contact (a7 #3): a rigid link on three axial supports (front leaf, rear leaf, catch), solved for each extra N.")
ws = b / 2
Lc = P["catch_z"] - P["ground_z"][1]
ts, ds = P["saddle_t"], P["saddle_depth"]
span = 2 * P["leaf_gap"]
I_s = ts * ds ** 3 / 12


def three(e, kc):
    kl_ = e * b * t / L
    ys_, ks = [yf_, yr_, y_c], [kl_, kl_, kc]
    A_ = sum(ks)
    B_ = sum(k * (y - y_c) for k, y in zip(ks, ys_))
    C_ = sum(k * (y - y_c) ** 2 for k, y in zip(ks, ys_))
    Mg = y_grip - y_c
    det = A_ * C_ - B_ * B_
    w0, th_ = (C_ - B_ * Mg) / det, (A_ * Mg - B_) / det
    return [k * (w0 + th_ * (y - y_c)) for k, y in zip(ks, ys_)]


for e in (E_lo, E_hi):
    k_legs = 2 * e * ws * t / Lc
    k_sad = 1 / (span ** 3 / (192 * e * I_s) + span / (4 * 5 / 6 * e / 2.6 * ts * ds))
    kc = 1 / (1 / k_legs + 1 / k_sad)
    F0 = P["catch_contact_lo_n"] if e == E_lo else P["catch_contact_hi_n"]
    Pcr = 4 * math.pi ** 2 * e * (b * t ** 3 / 12) / L ** 2
    for nm, kcc in (("legs alone (stiff bound)", k_legs), ("legs + saddle", kc), ("legs + saddle at 1/3 (soft bound)", kc / 3)):
        Rf, Rr, Rc = three(e, kcc)
        r600 = F0 * fac + (600 - F0) * Rr
        p("  E%4.0f catch %-34s %5.0f N/mm: per extra N front %+.2f, rear %+.2f, catch %+.2f; at 600 N the rear strips carry "
          "%4.0f N (x %.1f to buckle), the catch %4.0f N" % (e, nm, kcc, Rf, Rr, Rc, r600, Pcr / r600, (600 - F0) * Rc))
p("  Rows: the rear strips at 600 N, %.0f N (soft bound, E 2500) against %.0f N to buckle: x %.1f (x %.1f on the fillets' "
  "Le 25). Reviewer a7's own model (legs-only catch) gives 1410 against its /3 limit. a7 claimed x 9.4 ('the strips stop "
  "loading'); that model was wrong: the catch is 7.5 mm behind the rear leaf, so the rear strips keep loading."
  % (P["leaf_rear_600"], P["leaf_rear_buckle"], P["leaf_rear_buckle"] / P["leaf_rear_600"],
     P["leaf_rear_buckle"] * (L / Le) ** 2 / P["leaf_rear_600"]))
p("  Catch legs at 600 N: %.0f N (stiff bound) against %.0f N to buckle (fixed at the ground bar, the saddle rigid and free to "
  "turn on the crown, held at the contact %.2f mm above the leg tops; E 2500): x %.1f. In the legs %.1f MPa, in the layer "
  "plane." % (P["catch_load_600"], P["catch_buckle_n"], P["catch_h"], P["catch_buckle_n"] / P["catch_load_600"],
              P["catch_load_600"] / (b * t)))
p("  Saddle across the layers (the cartridge prints inboard face down, so the saddle's span over the nut-driver gap bends "
  "across them): %.1f x %.2f section, span %.0f, clamped, the catch load as a point at mid-span: %.1f MPa at 600 N, %.1f MPa "
  "at 300 N (limit 15). a7's 2.5 mm saddle would have seen %.0f MPa at 600 N."
  % (ts, ds, span, P["saddle_600_mpa"], P["saddle_300_mpa"],
     P["catch_load_600"] * span / 8 / (2.5 * (P["catch_z"] + 11.1 + P["catch_c"]) ** 2 / 6)))
p("4e. Piston at a 600 N lean on one grip (a7 #6), bending in the layer plane (it prints on its side), Bambu PLA Basic "
  "flexural ~76 MPa:")
p("  Ø%.0f at the socket mouth %.1f MPa (bound: no relief from the catch reaction), at the catch %.1f; the Ø%.1f spigot at "
  "the step (y %.0f) %.1f. Worst %.1f: x %.2f (a7: Ø22.2 all along, 52.3 at the catch and about 56 at the mouth, x 1.45)."
  % (P["piston_d"], P["piston_mouth_mpa"], P["piston_catch_mpa"], P["shaft_d"], P["piston_step"], P["piston_step_mpa"],
     P["piston_600_mpa"], 76.0 / P["piston_600_mpa"]))
p("  The barrel lip (lip_c %.2f) is reached only if the catch were not there; it is the backup." % P["lip_c"])
p("")

p("== 5. Cell nuts: clamp, settling, creep (a4 #4, #5)")
a_boss = math.pi / 4 * (P["seat_d"] ** 2 - 5.5 ** 2)
k_stud = E_st * 14.2 / 12.0
k_mem = 1 / (1 / (E * a_boss / P["seat_h"]) + 1 / (E * 110.0 / 3.0) + 1 / (E * 120.0 / 1.6))
k_j = 1 / (1 / k_stud + 1 / k_mem)
p("joint stiffness (stud %.0f, clamped PLA %.0f kN/mm) %.0f kN/mm: an M5 nut turned 60 deg (0.133 mm) past finger-"
  "tight would put %.1f kN on a Ø12 boss (%.0f MPa): angle control is far too coarse for a 1 mm PLA boss." %
  (k_stud / 1e3, k_mem / 1e3, k_j / 1e3, k_j * 0.8 / 6 / 1e3, k_j * 0.8 / 6 / a_boss))
for T in (0.1, 0.2, 0.5, 1.0):
    Fp = T / (0.2 * 0.005)
    p("  %.1f N.m (K 0.2) -> %4.0f N preload, boss %4.1f MPa" % (T, Fp, Fp / a_boss))
p("Spec: finger-tight with the bare 8 mm nut-driver bit held in the fingers (no handle, no drill): about 0.1-0.2 N.m, "
  "100-200 N, 1.8-3.6 MPa on the boss. That holds the faces seated for push (push only adds to it) and for pull up "
  "to about the preload; past it a rear face can lift a few microns, which does not change the stud force the cell "
  "reads. A dab of hot glue over each nut stops it backing off. Settle overnight, re-snug, then set the stops.")
cl = 2 * (P["seat_h"] + 1.0)
p("creep term in the stop rows: %.1f mm of PLA in the stop chain under clamp stress (two bosses + 1 mm under each) x "
  "%.2f %% over the unit's life = %.4f mm = %.2f FS at dFS 0.10 (most of the creep at <= 4 MPa happens in the first "
  "day, before the stops are set)." % (cl, 100 * P["creep_strain"], cl * P["creep_strain"], cl * P["creep_strain"] / 0.1))
p("")

p("== 6. Bench (cradle) vs fin")
p("The jack is on the axis (3a). The block bears on the cradle's front wall round the same Ø16 counterbore as in the "
  "fin, so the push setting sees the same block. Pull: the cradle holds the block with two M4 lip screws at z %.0f and "
  "the front wall at the block's foot instead of the fin's lips all round; contact compliance there lets the block "
  "turn by roughly 0.01 / 40 rad, which moves the pull contacts (z %.1f) by %.4f mm: the bench_support term "
  "(%.3f mm) in the stop rows." % (P["bench_lip_z"], zq, abs(zq) * 0.01 / 40, P["bench_support"]))
p("")

p("== 7. Bench pass marks")
for dfs in (0.05, 0.10, 0.20):
    kc = FS / dfs
    p("  stop check, 20 kg cell, dFS %.2f: once past 120 %% the reading climbs at %.0f %% of its rate below 120 %%"
      % (dfs, 100 * (kc + kl) / (kc + kl + k_stop)))
p("  -> pass: turning the jack on past 120 % the reading climbs at under 40 % of its earlier rate, both ways (a stop that is not touching leaves it at 100 %).")
p("  5 kg hung from the grip end: %.1f N.m at the cell, %.2f N.m through it at the worst share above (%.1f %%); a "
  "cell bearing outside its bosses (a3: 47 %%) would take %.1f N.m. Pass: the reading changes by under 2 %% FS and "
  "the two grips agree within 1 %% FS; over 5 %% FS means a cell face or the link is touching where it should not."
  % (M5 / 1000, s_hi * M5 / 1000, 100 * s_hi, 0.47 * M5 / 1000))

p("")
p("== 8. Lean-to-axial crosstalk (a6 #3, reviewer a5 section E): leaf tops %.1f %s the cell axis"
  % (abs(P["leaf_top_below_cell"]), "above" if P["leaf_top_below_cell"] < 0 else "below"))
a_top = P["leaf_top_below_cell"]
for e in (E_lo, E, E_hi):
    w_per_N = (y_grip - y_leaf) / krot(e)
    xt = 2 * e * (b * t ** 3 / 12) / L ** 2 * (12 * a_top / L + 6) * w_per_N
    p("  E%4.0f: the cell reads %.4f N axial per N down on the grip (%.2f %%): 50 / 150 N lean -> %.2f / %.2f N"
      % (e, xt, 100 * xt, 50 * xt, 150 * xt))
p("  The link turns about the cell (the one stiff y constraint). Each leaf top moves theta x a and turns theta, so its "
  "shear is 2 E I / L^2 (12 a / L + 6) theta: zero for a = -L/2, the leaf mid-length on the cell axis. a7 puts the cell "
  "there (cz %.1f, the leaves' mid-height) and reaches it with the link's drop; a6 had the leaf tops 15 below the axis: "
  "3.8 %%, 5.7 N at 150 N." % cz)
for dz in (0.2, 0.5):
    xt = 2 * E * (b * t ** 3 / 12) / L ** 2 * (12 * dz / L) * (y_grip - y_leaf) / krot(E)
    p("  print tolerance: the cell axis %.1f mm off the leaves' mid-height reads %.3f %% (%.2f N at 150 N)" % (dz, 100 * xt, 150 * xt))
F_hi = P["catch_contact_hi_n"]
p("  Firmware backup (RTPS side, not in this repo): a dead band of max(10 N, %.0f N x |c| x 1.2) per grip, where c is the "
  "coefficient README step 12 measures (expected under 0.2 %%; reject the cartridge over 1 %%). %.0f N is the largest lean "
  "the leaves carry before the catch takes it (E 3500); past it the crowned catch adds at most %.1f N (4c). So with c = 1 %%: %.1f N."
  % (F_hi, F_hi, P["catch_k"] * P["stop_gap_max"], max(10.0, F_hi * 0.01 * 1.2)))
p("")

p("== 9. Cradle under the jack (a5 #1), 1.2 x FS of the 50 kg cell = %.0f N, E 2500" % P["cradle_jack_n"])
p("  geometry: closed frame (front wall, two %.0f mm side walls through to the upright, %.0f mm upright, %.1f base), "
  "R%.0f roots at the upright; prints base down, so every frame member carries the jack load in the layer plane."
  % (P["bench_wall_x"][1] - P["bench_wall_x"][0], P["bench_up_t"], P["bench_base_z"][1] - P["bench_base_z"][0], P["bench_root_r"]))
p("  upright between the walls (beam across x, band = t): %.1f MPa in the layer plane" % P["cradle_up_inlayer_mpa"])
p("  share sent down to the base (the only path across layers): %.1f %% -> %.2f MPa across layers"
  % (100 * P["cradle_up_share"], P["cradle_up_across_mpa"]))
p("  frame (U section, axis %.1f mm above its centroid): %.2f MPa in the layer plane" % (P["cradle_frame_e"], P["cradle_frame_mpa"]))
p("  jack tilt %.2f deg (a5: 6.4-7.6); push stroke needed %.2f mm (frame %.3f + upright %.3f + largest stop setting "
  "%.2f) against the M5 x 35 head's %.1f mm stand-off (a5: 4.47 needed, 3.0 available)"
  % (P["cradle_jack_tilt_deg"], P["cradle_stroke"], P["cradle_frame_defl"], P["cradle_beam_defl"], P["stop_gap_max"],
     P["bench_standoff"]))
ut = P["bench_up_t"]
for kg in (20, 50):
    F_ = 1.2 * kg * 9.81
    p("  reviewer a5's free-standing-cantilever model on this upright (no side walls at all, %d kg): %.1f MPa across layers, "
      "tip %.2f mm" % (kg, F_ * 49.1 / (50 * ut ** 2 / 6), F_ * 49.1 ** 3 / (3 * 2500 * 50 * ut ** 3 / 12)))
p("")

p("== 10. Scale before stops (a5 #2): what an unset mV/V does, and the known-mass check window")
for mvv in (1.0, 1.5, 2.0, 3.0):
    p("  cell rated %.1f mV/V with the sketch at 1.0: its '120 %%' is %.0f %% of true FS" % (mvv, 120 / mvv))
p("  The sketch now refuses 'm' until 'f', 'r' (or 'c') and 't' are given. Known-mass check ('k <kg>', cradle stood on "
  "its rear face, the mass hung from the jack screw): the flexure leaves carry kl / (kc + kl) of it beside the cell:")
for cname, fs in CELLS.items():
    sh = [kl / (fs / d + kl) for d in (0.05, 0.10, 0.20)]
    p("  %s: shunt %.1f / %.1f / %.1f %% at dFS 0.05 / 0.10 / 0.20, so a right scale reads %.3f-%.3f of the mass"
      % (cname, 100 * sh[0], 100 * sh[1], 100 * sh[2], 1 - sh[2] - 0.01, 1 - sh[0] + 0.01))
p("  PASS window 0.88-1.03 (a6 review #4: a6's 0.90 failed a right 20 kg cell at dFS 0.20); a 1.5x or 2x mV/V error reads 0.67 / 0.50 or "
  "1.5 / 2.0: FAIL, and the sketch then refuses 'm' (a6 review #4) unless 'm!' is typed. A soft 20 kg cell (dFS over "
  "about 0.17) reads under 0.88 and fails falsely: calibrate it with 'c' (safe). Calibrating with 'c' in this setup reads "
  "grip force, so the stops land 1-15 % under 1.2 x FS of the cell itself: the safe side. a7: the cradle hangs from its eye "
  "on the jack axis and the mass hangs from the printed hanger on the jack head, so the cord, the jack and the mass are one "
  "vertical line (no books).")
print("\n".join(out))
