"""Reviewer a8: independent head numbers from the manifest params and the build's geometry (no import of head_calc).
python3 -I head_a8.py cad/blender/manifest.json"""
import json, math, sys
P = json.load(open(sys.argv[1]))['params']
t, ws = P['leaf_t'], P['cart_hw'] - P['leaf_gap']            # 2.5, 12.5 per strip
b = 2 * ws                                                   # 25 per leaf
L = -P['link_h'] - P['ground_z'][1]                          # 27
Le = L - P['leaf_r']                                         # 25
yf, yr = P['leaf_f0'] + t / 2, P['link1'] - t / 2            # 76.75, 121.75
pitch = yr - yf
GY = 219.5                                                   # middle of the hand (grip 152..287)
cz = P['cell_z']
c0 = P['link1'] + 2 * P['leaf_r'] + 1.0; yc = c0 + t / 2      # catch legs centre 129.25
s0, s1 = P['link1'] + 1.5, c0 + t + P['leaf_r'] + 1.5         # saddle 124.5..134
Lc = P['catch_z'] - P['ground_z'][1]                          # legs 22
r0 = P['piston_d'] / 2 + P['catch_c']                         # saddle bore radius at the crown
h = -r0 - P['catch_z']                                        # contact above the leg tops 7.85
I_s = b * t ** 3 / 12                                         # one leaf, thin axis
I_leg = 2 * ws * t ** 3 / 12                                  # leg pair, thin axis
out = []
def p(*a):
    s = " ".join(str(x) for x in a); print(s); out.append(s)

def dbar_I(d, flat, n=4000):
    """I about the horizontal axis (bending in z) of a Ø d bar with a D-flat at x = flat (the inboard side)."""
    r = d / 2; I = 0.0; A = 0.0; dz = d / n
    for i in range(n):
        z = -r + (i + 0.5) * dz
        half = math.sqrt(max(r * r - z * z, 0)); x0, x1 = -half, min(half, flat)
        w = max(x1 - x0, 0); I += w * z * z * dz; A += w * dz
    return I, A
I24, _ = dbar_I(24.0, 7.8)
I222, _ = dbar_I(22.2, 7.8)
p(f"geometry: leaves yf {yf} yr {yr} pitch {pitch}; catch yc {yc}; saddle {s0}..{s1}; legs Lc {Lc}; contact h {h:.2f}")
p(f"piston I (D-flat at 7.8): Ø24 {I24:.0f}, Ø22.2 {I222:.0f} mm4 (designer 15358 / 11457)")

# 1. crosstalk
p("\n1. lean crosstalk (link turns about the cell; shear in the leaves per unit turn)")
for e in (0.0, 0.2, 0.5):
    for Lb in (L, Le):
        a = (-P['link_h'] - (L - Lb) / 2 - cz) + e          # the fillets shorten both ends equally: measure from the effective top
        E = 3000.
        V = 12 * E * I_s / Lb ** 3 * a - 6 * E * I_s / Lb ** 2
        k_rot = E * b * t / L * pitch ** 2 / 2
        th = (GY - (yf + yr) / 2) / k_rot
        p(f"  offset {e} Lb {Lb}: {2 * V * th * 100:.3f} % of the lean")

# 2. catch contact, pull pitch, pull + lean margin
p("\n2. catch contact (two axial supports, link turning on them, piston cantilever from the socket mouth y 123)")
wc = {}
for E in (2500., 3000., 3500.):
    kl = E * b * t / L
    Rf, Rr = -(GY - yr) / pitch, (GY - yf) / pitch
    wf, wr = Rf / kl, Rr / kl
    th = (wr - wf) / pitch
    w = wr + th * (yc - yr)
    a_ = yc - P['link1']; Lg = GY - P['link1']
    w += a_ ** 2 * (3 * Lg - a_) / (6 * E * I24)
    wc[E] = w
    # pull pitch: push/pull F on the grip axis, cell reaction at cz: leaf couple F*(0-cz)/pitch
    Fp = 1.2 * 490.5
    dl = Fp * (0 - cz) / pitch / kl
    th_p = 2 * dl / pitch
    drop = th_p * (yc - (yf + yr) / 2)
    margin = (P['catch_c'] - drop) / w
    p(f"  E {E:.0f}: {w*1e4:.2f}e-4 mm/N at the catch -> contact at {P['catch_c']/w:.0f} N (gap 0.15), {0.10/w:.0f} N (0.10), {0.25/w:.0f} N (0.25); "
      f"rear leaf {Rr:.2f} x lean; 1.2FS pull lowers the catch {drop:.4f} -> pull + lean margin {margin:.0f} N")
p(f"  designer: contact 200-280 N, pull drop 0.0716 (E3000), margin 104.6 N (pull at E3000, lean at E2500: mixed)")

# 3. three supports past contact
p("\n3. past contact: rigid link on front leaf, rear leaf, catch (legs in series with the saddle over the 15 mm gap)")
def three(E, kc):
    kl = E * b * t / L
    ys, ks = [yf, yr, yc], [kl, kl, kc]
    A = sum(ks); B = sum(k * (y - yc) for k, y in zip(ks, ys)); C = sum(k * (y - yc) ** 2 for k, y in zip(ks, ys))
    M = GY - yc; det = A * C - B * B
    w0 = (C - B * M) / det; th = (A * M - B) / det
    return [k * (w0 + th * (y - yc)) for k, y in zip(ks, ys)]
dsad = r0 + P['catch_z'] * -1 - 2 * r0 + r0                  # placeholder (replaced below)
dsad = -P['catch_z'] - r0                                     # saddle depth under the bore at mid-span 7.85
I_sad = (s1 - s0) * dsad ** 3 / 12
res = {}
for E in (2500., 3500.):
    k_legs = E * 2 * ws * t / Lc
    k_sad = 192 * E * I_sad / 15 ** 3
    k_ser = 1 / (1 / k_legs + 1 / k_sad)
    F0 = P['catch_c'] / wc[E]
    Rr0 = (GY - yf) / pitch
    for nm, kc in (("legs only", k_legs), ("legs+saddle", k_ser), ("1/3 (contact)", k_ser / 3)):
        Rf, Rr, Rc = three(E, kc)
        rear600 = F0 * Rr0 + (600 - F0) * Rr
        cat600 = (600 - F0) * Rc
        res[(E, nm)] = (rear600, cat600)
        p(f"  E {E:.0f} {nm:14s} kc {kc:6.0f}: per N front {Rf:+.2f} rear {Rr:+.2f} catch {Rc:+.2f}; at 600 N rear strips {rear600:.0f} N, catch {cat600:.0f} N")
    pcr = 4 * math.pi ** 2 * E * I_s / L ** 2; pcr_e = 4 * math.pi ** 2 * E * I_s / Le ** 2
    p(f"  rear leaf buckling fixed-fixed (no sway; the cell braces y): L27 {pcr:.0f} N, Le25 {pcr_e:.0f} N")
    worst = max(v[0] for k, v in res.items() if k[0] == E)
    p(f"  worst rear strips {worst:.0f} -> x{pcr/worst:.2f} (L27); plus a 1.2FS push couple +{1.2*490.5*(0-cz)/pitch:.0f} N -> x{pcr/(worst+1.2*490.5*(0-cz)/pitch):.2f}")
    p(f"  compressive stress in the rear strips at worst: {worst/(b*t):.1f} MPa (+push {(worst+1.2*490.5*(0-cz)/pitch)/(b*t):.1f})")

# 4. catch legs buckling with the saddle offset (fixed base; rigid saddle; contact pinned laterally by friction at h)
p("\n4. catch legs buckling: fixed base, rigid saddle, contact held laterally (friction) at h above the leg tops")
def f(k):
    return (math.sin(k * Lc) + h * k * math.cos(k * Lc)) / k - (Lc + h) * (math.cos(k * Lc) - h * k * math.sin(k * Lc))
lo, hi = 1e-4, 4.4 / Lc
k = lo; step = 1e-4; prev = f(k)
root = None
while k < 10 / Lc:
    k += step; v = f(k)
    if prev * v < 0: root = k; break
    prev = v
for E in (2500., 3000.):
    EI = E * I_leg
    Pcr = root ** 2 * EI
    p(f"  E {E:.0f}: k {root:.4f} -> Pcr {Pcr:.0f} N (pinned at the contact); sway (friction slips): ~{math.pi**2*EI/(4*(Lc+h*0.8)**2):.0f} N (fixed-free, length Lc+0.8h, estimate)")
p(f"  designer 2181 N; catch at 600 N: {max(v[1] for v in res.values()):.0f} N worst (legs-only bound)")

# 5. friction shunt
p("\n5. catch friction shunt (legs as cantilevers, saddle rigid, contact h above)")
for E in (2500., 3000., 3500.):
    EI = E * I_leg
    Cff = (Lc ** 3 / 3 + h * Lc ** 2 + h * h * Lc) / EI
    Cfm = (Lc ** 2 / 2 + h * Lc) / EI
    kfree = 1 / Cff; kg = 12 * EI / Lc ** 3
    p(f"  E {E:.0f}: k free {kfree:.2f}, guided {kg:.1f} N/mm; moment->shunt {Cfm/Cff:.4f} N per N.mm; "
      f"shunt free 0.12 mm {kfree*0.12:.2f} N, 0.30 mm {kfree*0.30:.2f} N")
E = 3000.; EI = E * I_leg
Cff = (Lc ** 3 / 3 + h * Lc ** 2 + h * h * Lc) / EI; Cfm = (Lc ** 2 / 2 + h * Lc) / EI; kfree = 1 / Cff
# crown land: (a) designer N/(2*10*80); (b) elliptical plastic contact, circumferential conformity R_eff = R r0/(r0-R)
Rx = 12.0 * r0 / (r0 - 12.0); Ry = P['catch_crown_r']
for Nlean, Nsad_hist in ((300, None), (600, None)):
    pass
for pm in (80., 120.):
    for Nsad in (184., 738.):
        A = Nsad / pm
        d = A / (math.pi * math.sqrt(Rx * Ry))                 # truncation model
        ax, ay = math.sqrt(Rx * d), math.sqrt(Ry * d)
        p(f"  crown at {Nsad:.0f} N, flow pressure {pm:.0f}: land {2*ax:.1f} mm round the bore x {2*ay:.2f} mm along y (designer: 10 x {2*Nsad/(2*10*80):.2f})")
for a_land, tag in ((738 / (2 * 10 * 80), "designer land a 0.46"), (0.30, "my land a 0.30")):
    for Nsad, tag2 in ((184., "later 300 N lean"), (738., "during 600 N lean")):
        Mcap = Nsad * a_land                                  # upper bound (rigid land, pressure at one edge)
        for u, tag3 in ((0.12, "dFS 0.10"), (0.30, "stop_gap_max")):
            Mneed = kfree * u * 0 + (12 * EI / Lc ** 3 * u) * (h + Lc / 2)   # guided moment
            M = min(Mcap, Mneed)
            p(f"  {tag}, {tag2}, {tag3}: M cap {Mcap:.0f} need {Mneed:.0f} -> shunt {kfree*u + M*Cfm/Cff:.1f} N")

# 6. saddle across layers
p("\n6. saddle bending across the layers (span 15 between the legs, 9.5 x 7.85 at mid-span)")
Z = (s1 - s0) * dsad ** 2 / 6
for N in (184., 738.):
    p(f"  {N:.0f} N: point, clamped PL/8 {N*15/8/Z:.1f} MPa; UDL clamped wL/12 {N*15/12/Z:.1f}; point simply supported PL/4 {N*15/4/Z:.1f}")
# with default print settings (2 walls 0.42, 15 % infill at ~0.1 E): shell of the y-z section in each layer
tw = 0.84
Is = 2 * (s1 - s0) * tw * (dsad / 2 - tw / 2) ** 2 + 2 * tw * dsad ** 3 / 12
Ii = 0.1 * (I_sad - Is)
p(f"  default print (2 walls, 15 % infill): I {Is+Ii:.0f} vs solid {I_sad:.0f} -> x{I_sad/(Is+Ii):.2f} stress: 738 N point clamped {738*15/8*dsad/2/(Is+Ii):.1f} MPa")

# 7. piston
p("\n7. piston at a 600 N lean (grip load at y 219.5)")
for F in (300., 600.):
    Rc = res[(2500., 'legs only')][1] * F / 600 if F == 600 else 184.
    M_mouth = F * (GY - P['link1']); M_mouth_rel = M_mouth - Rc * (yc - P['link1'])
    M_c = F * (GY - yc); M_step = F * (GY - P['piston_step'])
    p(f"  {F:.0f} N: mouth Ø24 {M_mouth*12/I24:.1f} MPa (bound; {M_mouth_rel*12/I24:.1f} with the catch reaction), "
      f"catch Ø24 {M_c*12/I24:.1f}, step Ø22.2 {M_step*11.1/I222:.1f} nominal, x Kt 1.3-1.5 at the 45 deg step -> "
      f"{M_step*11.1/I222*1.3:.0f}-{M_step*11.1/I222*1.5:.0f}")
# default print settings: 2 walls (0.84) + 15 % gyroid at ~0.1 E; the bending fibres (world z) are print-side walls
r = 12.0
I_ring = math.pi * (r - tw / 2) ** 3 * tw
I_eff = I_ring + 0.1 * (I24 - I_ring)
p(f"  default print (2 walls, 15 %): I_eff {I_eff:.0f} vs solid {I24:.0f} (x{I24/I_eff:.2f}) -> mouth at 600 N {600*(GY-P['link1'])*12/I_eff:.0f} MPa, at 300 N {300*(GY-P['link1'])*12/I_eff:.0f}; "
      f"lean that reaches 50 MPa in the walls: {50*I_eff/12/(GY-P['link1']):.0f} N")
for walls in (4, 6):
    tw2 = 0.42 * walls; I_r = math.pi * (r - tw2 / 2) ** 3 * tw2; I_e = I_r + 0.1 * (I24 - I_r)
    p(f"  {walls} walls + 15 %: I_eff {I_e:.0f} -> mouth at 600 N {600*(GY-P['link1'])*12/I_e:.0f} MPa")

# 8. stops and cell load for 50 and 20 kg cells
p("\n8. stops: per pair stiffness bounds and the cell load at a 600 N shove")
for ks in (6000., 7000., 12000.):
    for kg, FS in ((50, 490.5), (20, 196.2)):
        vals = []
        for dfs in (0.05, 0.10, 0.20):
            kcell = FS / dfs; kl = 150.
            Feng = 1.2 * FS + kl * 1.2 * dfs
            Fc = 600 * kcell / (kcell + kl) if 600 <= Feng else 1.2 * FS + (600 - Feng) * kcell / (kcell + ks + kl)
            vals.append(Fc / FS)
        p(f"  k_stop {ks:.0f} N/mm, {kg} kg: x FS at 600 N for dFS 0.05/0.10/0.20: " + " / ".join(f"{v:.2f}" for v in vals))
# my own stop-path stiffness estimate per screw (E 3500 solid floor)
Eh = 3500.
k_head = 0.8 * 2 * 2.75 * Eh / (1 - 0.35 ** 2)
k_shank = 200e3 * 5.03 / 18
k_nut = 0.8 * 2 * 2.9 * Eh / (1 - 0.35 ** 2)
k_thr = 50e3
k1 = 1 / (1 / k_head + 1 / k_shank + 1 / k_nut + 1 / k_thr)
p(f"  my estimate per screw (head punch {k_head:.0f}, shank {k_shank:.0f}, nut in slot {k_nut:.0f}, threads {k_thr:.0f}): {k1:.0f} N/mm, pair {2*k1:.0f} (solid PLA behind the floors)")

# 9. washers over the 5.5 slot
p("\n9. printed washers bridging the 5.5 mm stud slot (pull through the cell)")
nut_r_in, nut_r_out = 2.65, 4.3
frac = (nut_r_out - nut_r_in) * 5.5 / (0.9 * math.pi * (nut_r_out ** 2 - nut_r_in ** 2))
for OD, tag in ((13.0, "rear Ø13"), (15.0, "front Ø15")):
    bw = OD / 2 - nut_r_in
    for F, tagF in ((589., "1.2 FS"), (687., "1.4 FS (bench step 7)"), (200., "clamp preload (sustained)")):
        q = F * frac; wq = q / 5.5
        sc = wq * 5.5 ** 2 / 12 / (bw * 2.4 ** 2 / 6); ss = wq * 5.5 ** 2 / 8 / (bw * 2.4 ** 2 / 6)
        p(f"  {tag} at {tagF}: {q:.0f} N over the slot, strip {bw:.2f} wide x 2.4: clamped {sc:.1f} MPa, simply supported {ss:.1f} MPa")
p(f"  (nut bearing fraction over the slot {frac:.2f}; designer row 11.4 MPa uses a 6.05 mm strip, wider than the washer's own ring)")
open(sys.argv[2] if len(sys.argv) > 2 else '/dev/null', 'w').write("\n".join(out) + "\n")
