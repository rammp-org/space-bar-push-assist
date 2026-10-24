"""Side profile of the push-assist unit on the Corpus back plate. 2D only, for agreeing the shape
before the Blender build. Y rearward (toward the attendant), Z up, mm. Origin: plate face at grip
axis height. Run: uv run --with matplotlib python cad/profile/profile.py
"""
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle

sys.path.insert(0, "/Users/alxchunlin/code-stuff/alex-style-guide/matplotlib")
import alex_style as ax

P = dict(
    plate_tilt=15,      # deg past vertical, top leans rearward
    plate_t=40,         # extrusion plate thickness, in front of its rear face
    slope=60,           # deg from horizontal, rear face from the barrel down to the bottom
    reach=150,          # plate face to barrel lip, along the grip axis
    barrel_d=50,
    height=92,          # bridge: top of barrel to flat bottom; bottom must clear the block
    fin_height=140,     # end fins carry the wedge further down, outside the plate
    grip_len=135,
    wall=3,
    standoff=5,         # board standoff off the inside of the front wall
    land=40,            # mounting land at the top of the front face, flat on the plate
    bevel=15,           # deg the front face below the land turns away from the plate (15 = vertical)

    # Corpus back plate, from Alex's measurements (in = 25.4 mm)
    plate_above=0,      # plate top above the unit's top, along the plate
    clear_h=101.6,      # 4 in clear band from the plate top down to the central block
    clear_w=355.6,      # 14 in clear band width
    block_out=76.2,     # block sticks 3 in rearward of the plate face
    block_h=60,         # block height along the plate (not measured, drawn only)
    slot_span=304.8,    # 12 in between the outermost usable slots
    handle_spacing=355.6,
    fin_t=36,
)

t = math.tan(math.radians(P["plate_tilt"]))
plate_y = lambda z: z * t                      # plate face y at height z
r = P["barrel_d"] / 2
L = P["reach"]
z_bot = r - P["height"]
slope_y = lambda z: L - (-r - z) / math.tan(math.radians(P["slope"]))



def on_face(u, n, tilt=P["plate_tilt"], origin=(0, 0)):
    """Point u along a face leaning tilt deg past vertical (up) and n off it (rearward), in Y/Z."""
    a = math.radians(tilt)
    return (origin[0] + u * math.sin(a) + n * math.cos(a), origin[1] + u * math.cos(a) - n * math.sin(a))


def face_rect(u0, u1, n0, n1, **kw):
    return [on_face(u0, n0, **kw), on_face(u0, n1, **kw), on_face(u1, n1, **kw), on_face(u1, n0, **kw)]


on_plate = on_face
plate_rect = face_rect

# front face: flat on the plate for the land, then bevelled away from it down to the floor
u_top = r / math.cos(math.radians(P["plate_tilt"]))
knee = on_plate(u_top - P["land"], 0)
front_tilt = P["plate_tilt"] - P["bevel"]
front = dict(tilt=front_tilt, origin=knee)
front_y = lambda z: knee[0] + (z - knee[1]) * math.tan(math.radians(front_tilt))
outline = [(plate_y(r), r), (L, r), (L, -r), (slope_y(z_bot), z_bot), (front_y(z_bot), z_bot), knee]
z_fin = r - P["fin_height"]
fin_outline = [(plate_y(r), r), (L, r), (L, -r), (slope_y(z_fin), z_fin), (front_y(z_fin), z_fin), knee]


pal = ax.use("dark")
s = pal["series"]
fig, (a, b) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw=dict(width_ratios=[1, 1.15]))

# chair plate, clear band and central block
u_ptop = u_top + P["plate_above"]
u_blk = u_ptop - P["clear_h"]
a.add_patch(Polygon(plate_rect(-260, u_ptop, -P["plate_t"], 0), fc=pal["off"], ec=pal["muted"], lw=1, alpha=0.6))
a.text(*on_plate(u_ptop - 160, -P["plate_t"] / 2), "4040 PLATE", rotation=90 - P["plate_tilt"],
       color=pal["ink"], ha="center", va="center", fontsize=8, family="Roboto Mono")
a.add_patch(Polygon(plate_rect(u_blk - P["block_h"], u_blk, 0, P["block_out"]), fc="none", ec=pal["critical"], lw=1.5, ls="--"))
a.text(*on_plate(u_blk - P["block_h"] / 2, P["block_out"] / 2), "BLOCK", rotation=90 - P["plate_tilt"],
       color=pal["critical"], ha="center", va="center", fontsize=8, family="Roboto Mono")
a.plot(*zip(on_plate(u_ptop, -55), on_plate(u_blk, -55)), color=pal["good"], lw=1)
a.text(*on_plate((u_ptop + u_blk) / 2, -62), f"clear {P['clear_h']:.0f}", rotation=90 - P["plate_tilt"],
       color=pal["good"], ha="center", va="center", fontsize=8, family="Roboto Mono")

# printed unit
a.add_patch(Polygon(fin_outline, fc=pal["grid"], ec=pal["muted"], lw=1.5, ls="--", joinstyle="round"))
a.text(slope_y(z_fin) - 30, z_fin + 8, "FIN", color=pal["muted"], ha="center", fontsize=8, family="Roboto Mono")
a.add_patch(Polygon(outline, fc=pal["panel"], ec=pal["ink"], lw=2, joinstyle="round"))

# grip and barrel
a.add_patch(Rectangle((L, -16.5), P["grip_len"], 33, fc=pal["grid"], ec=pal["muted"], lw=1))
a.text(L + P["grip_len"] / 2, 0, "GRIP", color=pal["ink"], ha="center", va="center", fontsize=8, family="Roboto Mono")
a.add_patch(Rectangle((L - 45, -16.5), 45, 33, fc="none", ec=s[0], lw=1.5))
a.text(L - 22, -24, "piston", color=pal["muted"], ha="center", fontsize=7)
a.add_patch(Rectangle((L - 90, -15), 37, 30, fc=s[1], ec="none", alpha=0.8))
a.text(L - 71, -24, "load cell", color=pal["muted"], ha="center", fontsize=7)

# boards flat against the bevelled front wall, in front-face coordinates from the knee
n0 = P["wall"] + P["standoff"]
esp = (front_y(z_bot) + P["wall"] + 4, z_bot + P["wall"] + P["standoff"])
a.add_patch(Rectangle(esp, 55, 22, fc=s[2], ec="none", alpha=0.8))
a.text(esp[0] + 27.5, esp[1] + 11, "ESP32-P4", color=pal["ink"], ha="center", va="center", fontsize=7, family="Roboto Mono")
for poly, col, name, (u, n) in [
    (plate_rect(u_top - P["land"] + 2, u_top - P["land"] + 32, n0, n0 + 10), s[3], "HX711", (u_top - P["land"] + 17, n0 + 20)),
]:
    a.add_patch(Polygon(poly, fc=col, ec="none", alpha=0.8))
    a.text(*on_face(u, n, **(front if name == "ESP32-P4" else {})), name, rotation=90 - (front_tilt if name == "ESP32-P4" else P["plate_tilt"]), color=pal["ink"],
           ha="center", va="center", fontsize=7, family="Roboto Mono")

# RJ45 coupler through the floor
cy = slope_y(z_bot) - 28
a.add_patch(Rectangle((cy - 14, z_bot - 8), 28, 36, fc=s[4], ec="none", alpha=0.8))
a.text(cy, z_bot - 16, "RJ45", color=pal["muted"], ha="center", fontsize=7)

# T-nut bolts into the plate
for u in (u_top - 12, u_top - P["land"] + 10):
    a.plot(*zip(on_plate(u, -12), on_plate(u, P["wall"] + 2)), color=pal["accent"], lw=2.5)

# dimensions
mono = dict(color=pal["muted"], fontsize=8, family="Roboto Mono")
a.annotate("", (plate_y(r), r + 18), (L, r + 18), arrowprops=dict(arrowstyle="<->", color=pal["muted"], lw=1))
a.text((plate_y(r) + L) / 2, r + 22, f"{L - plate_y(r):.0f}", ha="center", **mono)
a.annotate("", (L + 20, r), (L + 20, z_bot), arrowprops=dict(arrowstyle="<->", color=pal["muted"], lw=1))
a.text(L + 24, (r + z_bot) / 2, f"{P['height']}", va="center", **mono)
a.annotate("", (L + 45, r), (L + 45, z_fin), arrowprops=dict(arrowstyle="<->", color=pal["muted"], lw=1))
a.text(L + 49, (r + z_fin) / 2 - 20, f"fin {P['fin_height']}", va="center", **mono)
a.annotate("", (front_y(z_bot), z_bot - 30), (slope_y(z_bot), z_bot - 30), arrowprops=dict(arrowstyle="<->", color=pal["muted"], lw=1))
a.text((front_y(z_bot) + slope_y(z_bot)) / 2, z_bot - 42, f"{slope_y(z_bot) - front_y(z_bot):.0f}", ha="center", **mono)
a.text(front_y(z_bot) - 4, z_bot + 4, f"gap {front_y(z_bot) - plate_y(z_bot):.0f}", ha="right", **mono)
a.text(front_y(z_bot + 8) + 4, z_bot + 34, f"{P['bevel']}°", **mono)
a.text(slope_y(-r - 45) + 8, -r - 45, f"{P['slope']}°", **mono)
a.text(plate_y(-150) - 4, -150, f"{P['plate_tilt']}°", ha="right", **mono)
a.text(plate_y(r) + 4, r - 12, f"{90 + P['plate_tilt']}°", **mono)

a.set_aspect("equal")
a.set_xlim(-110, 290)
a.set_ylim(-190, 100)
a.set_xlabel("Rearward from plate face, mm")
a.set_ylabel("Height from grip axis, mm")
a.grid(True, ls=(0, (2, 4)), color=pal["grid"])
ax.title(a, "Side profile", f"Bridge {P['height']} tall clears the block, fins {P['fin_height']} carry the {P['slope']}° wedge")

# back view, looking forward at the plate face. X across, U up along the plate from the grip axis.
hw = P["clear_w"] / 2
b.add_patch(Rectangle((-hw, -260), 2 * hw, u_ptop + 260, fc=pal["off"], ec=pal["muted"], lw=1, alpha=0.6))
for x in [i * 40 - hw + 20 for i in range(int(P["clear_w"] // 40))]:
    b.plot([x, x], [-260, u_ptop], color=pal["bg"], lw=1)
for x in (-P["slot_span"] / 2, P["slot_span"] / 2):
    b.plot([x, x], [-260, u_ptop], color=pal["good"], lw=1, ls=(0, (2, 4)))
b.text(0, u_ptop + 52, f"outer slots {P['slot_span']:.0f} apart", color=pal["good"], ha="center", fontsize=8, family="Roboto Mono")
b.add_patch(Rectangle((-60, u_blk - P["block_h"]), 120, P["block_h"], fc="none", ec=pal["critical"], lw=1.5, ls="--"))
b.plot([-260, 260], [u_blk - 25, u_blk - 25], color=pal["critical"], lw=6, alpha=0.5)
b.text(0, u_blk - P["block_h"] / 2, "BLOCK", color=pal["critical"], ha="center", va="center", fontsize=8, family="Roboto Mono")
b.text(230, u_blk - 40, "tube to armrests?\nlength not measured", color=pal["critical"], ha="center", fontsize=7, family="Roboto Mono")
hs = P["handle_spacing"] / 2
u_bot = z_bot / math.cos(math.radians(P["plate_tilt"]))
u_finb = z_fin / math.cos(math.radians(P["plate_tilt"]))
b.add_patch(Rectangle((-hs + P["fin_t"] / 2, u_bot), 2 * hs - P["fin_t"], u_top - u_bot, fc=pal["panel"], ec=pal["ink"], lw=2))
b.text(0, (u_top + u_bot) / 2, "BRIDGE", color=pal["ink"], ha="center", va="center", fontsize=8, family="Roboto Mono")
for sx in (-1, 1):
    b.add_patch(Rectangle((sx * hs - P["fin_t"] / 2, u_finb), P["fin_t"], u_top - u_finb, fc=pal["grid"], ec=pal["ink"], lw=2))
    b.add_patch(Circle((sx * hs, 0), 16.5, fc=pal["grid"], ec=pal["muted"], lw=1))
    for bx in (sx * P["slot_span"] / 2,):
        b.plot(bx, u_top - 12, "o", color=pal["accent"], ms=6)
b.annotate("", (-hs, u_top + 25), (hs, u_top + 25), arrowprops=dict(arrowstyle="<->", color=pal["muted"], lw=1))
b.text(0, u_top + 30, f"handles {P['handle_spacing']:.0f} (14 in)", ha="center", **mono)
b.text(-hw + 4, u_blk + 4, f"clear band {P['clear_h']:.0f} x {P['clear_w']:.0f}", color=pal["good"], fontsize=8, family="Roboto Mono")
b.plot([-hw, hw], [u_blk, u_blk], color=pal["good"], lw=1)
b.set_aspect("equal")
b.set_xlim(-300, 300)
b.set_ylim(-190, 100)
b.set_xlabel("Across the chair from centre, mm")
b.set_ylabel("Along the plate from grip axis, mm")
b.grid(True, ls=(0, (2, 4)), color=pal["grid"])
ax.title(b, "Back view", "Looking forward at the plate. Fins sit at the plate edges, bolts in the outer slots")
out = Path(__file__).with_name("profile.png")
ax.save(fig, out, dpi=110)
print(out)
