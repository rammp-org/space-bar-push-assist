"""Push-assist handle concept: builds the printable parts in Blender and renders review images.

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py
Out:  cad/blender/push_assist_concept.blend and cad/blender/renders/*.png

Reference parts (load cell, boards, RJ45, grip) are STLs exported from Onshape by
export_parts.mjs, so they match the CAD. Printed parts (handle halves, pistons, tray halves,
covers) are built with SDF nodes so fillets and cut-outs stay robust; print_check reports
each one's size in its print orientation against the H2D bed.

Axes (mm): X across the chair, Y rearward toward the attendant, Z up.
Origin: the chair plate's rear face at grip axis height, x = 0 on the chair centreline.
The plate leans 15 deg past vertical; see on_plate().
"""

import math
import os
import sys
import time

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "parts")
RENDERS = os.path.join(HERE, "renders")

# ------------------------------------------------------------------ design parameters (mm)
P = dict(
    handle_spacing=355.6,    # 14 in, handle centre to handle centre

    # Chair: Permobil Corpus back plate, vertical 4040s side by side, 15 deg past vertical.
    # Origin is on the plate's rear face at grip axis height; u runs up the plate, n off it.
    plate_tilt=15,           # deg, top leans rearward
    plate_bars=9,            # 9 x 40 = 360 wide; outer slots 320 apart (Alex measured ~12 in)
    plate_len=320,           # drawn length below the plate top
    mount_slots=(40, 120),   # |x| of the slots the bridge bolts to, M5 socket caps into drop-in T-nuts
    clear_h=101.6,           # 4 in clear band from the plate top down to the central block
    block=(120, 60, 76.2),   # central block: width, height along the plate, rearward protrusion

    # Section: a wedge whose top is the grip axis level and whose front sits on the plate.
    lip_y=150,               # plate face to barrel lip along the grip axis
    slope=60,                # deg from horizontal, rear face from the barrel down to the bottom
    land=40,                 # top of the front face, flat on the plate, carries the upper M5s
    bevel=15,                # deg the front face turns off the plate below the land (15 = vertical)
    bridge_h=92,             # bridge between the fins, top to floor; clears the block
    fin_h=140,               # fins carry the wedge further down, outside the block
    wall=3,
    cover_t=6,               # one cover across both trays, flush with the fin tops; = R_out so its rear edge is one R6

    # Detail set (one radius family): every exterior convex edge R_out, inside corners R_in, small edges EB.
    R_out=6,
    R_in=2,
    EB=1,

    # Fin (one per handle, printed as two halves split on its centre plane).
    fin_t=50,                # X thickness of the fin plate = barrel Ø, so the barrel is flush both sides
    # Attempt 4: the a3 lightening window (clipped by the cartridge pocket, read as a dent) is gone. The outboard
    # face carries one recessed panel that follows the fin outline, and the split is one deliberate V reveal.
    panel_inset=8,           # panel edge from the fin outline (before its R_out corners)
    panel_depth=2.0,         # recess depth; the rim gets a 1 x 1 chamfer (= EB)
    reveal=(0.8, 1.0),       # split-line V reveal: depth into the skin, half width each side (39 deg from vertical, prints on the bed edge)
    open_r=6,                # every convex edge of the fin is R_out

    # Grip and sensor head (barrel along Y at z = arm_z, lip at the fin's top-rear corner).
    arm_z=0,
    barrel_d=50,
    cell_rear=60,            # y of the cell's rear face (moved 30 forward from attempt 2 for the flexure)
    # Seat bosses (a3 #1): each cell face bears only on a Ø10 x 1.0 boss on the stud axis, so the cell takes axial
    # load and the leaves take the grip's bending moment (cad/calc/head_calc.py: cell share ~4-5 % with the stud path).
    seat_d=12.0,             # a7: Ø12 (a6 Ø10), cut by the 5.5 stud slot into two lands either side of the axis
    seat_h=1.0,
    washer_f=(15.0, 2.4),    # printed washer under the front nut (Ø, thickness), in the block's front counterbore
    washer_r=(13.0, 2.4),    # printed washer under the rear nut (fits the Ø14 nut bore). a8 (a7 #4): 2.4 thick (a7 1.6):
                             # each bridges the 5.5 stud slot under the nut (11 MPa at 1.2 x FS pull, row a7R washer)
    # Attempt 5: the cartridge is self-contained. Its front plate is a 10.5 mm block that the front stud clamps on its
    # own (washer and nut sit in a Ø16 counterbore in the block's front face), so both cell nuts are done, settled and
    # re-snugged on the bench, and the overload stops are set on the bench in a printed cradle before the cartridge
    # goes into the fin. The fin's 3 mm floor and the Ø16 access bore in the land face are gone: the block bears on the
    # fin's solid front wall (push) and on fin lips behind it (pull), at `fit`.
    block_t=11.5,            # block, from its front face to the cell's front seat boss (a7: +1, so the stud tip stays
                             # 0.35 inside the block's front face and the cartridge drops into the cradle with nothing proud)
    block_c=4.0,             # block left under the front washer (the counterbore floor)
    nut_cb=16.0,             # front counterbore: Ø15 washer, M5 nut, 8 mm nut-driver
    # Flexure cartridge: block + ground bar (fixed) and a top link on two parallel leaves (moves with the cell's rear
    # face). One printed part, printed on its side so each leaf bends in its layer plane.
    cart_hw=20,              # half width in X (a7: 20, a6 18; the strip leaves need the width, the fin skin keeps 4 mm)
    link_h=15,               # top link half height in Z
    link_ch=8,               # 45 deg chamfer on the top link's four long edges (keeps the fin cavity roof <= 17 mm)
    leaf_pitch_min=45.0,     # a7: front-to-rear leaf pitch (the link grows rearward to keep it; a6 47)
    leaf_gap=7.5,            # a7: each leaf is two strips at |x'| >= leaf_gap, so the 8 mm nut-driver reaches the rear
                             # cell nut along the cell axis between them
    drop_t=11.5,             # a7: the link's drop (it reaches down to the cell axis): front face on the seat boss,
                             # 3 mm wall, rear washer + nut bore, stop nuts beside it
    leaf_t=2.5,              # a7: 2.5 strips (a6 2.0 full-width leaves)
    leaf_r=2.0,              # root fillets on every leaf root, r/t = 1
    ground_z=(-49, -42),     # ground bar
    # Overload stops on the cell axis (a4 #1). Four M3 socket caps per cartridge run along the grip axis beside the
    # cell, at x' = +-stop_x, and thread into M3 nuts in the top link; their heads act on the block. Push pair at z 0
    # (on the axis): heads in counterbores in the block's rear face, the head's top face meets the counterbore floor
    # when the link moves forward, turned with a 2.5 mm key through a hole in the block. Pull pair at z = stop_zq:
    # through the block, heads in counterbores in its front face, the head's underside meets the counterbore floor when
    # the link moves rearward. Set on the bench in the cradle (below) with the cell itself as the gauge.
    stop_x=14.9,             # |x'| of both pairs: shank 0.7 clear of the cell's Ø25.4 side, nut flush with the link side
    stop_zp=0.0,             # push pair: on the cell axis, so a lean (link pitch) does not move the push stop
                             # (relative to the cell axis; absolute z set below, a7)
    stop_zq=-6.5,            # pull pair, below the axis: a downward lean opens the pull gap (fail-safe direction)
    stop_gap=0.15,           # modelled setting (1.2 x an assumed 0.125 mm full-scale travel); set per cell on the bench
    stop_gap_max=0.30,       # largest setting the procedure allows (a cell with 0.25 mm FS travel); sizes the leaf stress
    dfs_ref=0.10,            # reference cell full-scale travel for the stop stacks (cad/calc/head_calc.py tables 0.05-0.20)
    stop_hole=4.0,           # pull screws' clearance through the block and the push heads' counterbores: 0.5 radial,
                             # so a lean up to the lip catch never lets a stop screw rub the block (no friction path)
    cav=1.0,                 # clearance from every moving cartridge face to the fin
    fit=0.1,                 # clearance of the cartridge's fixed parts in their fin pockets
    lip_c=1.2,               # radial clearance of the piston in the barrel lip (a8: 1.2, a7 1.0; a backup: the catch lands
                             # first, even with the catch printed 0.1 big and the lip 0.1 small)
    catch_c=0.15,            # a7 (a6 #5): radial clearance of the piston over the cartridge's catch saddle behind the rear
                             # leaf. The saddle stands on two thin legs (stiff in z, ~11 N/mm in y), so a heavy lean lands
                             # there with no friction path beside the cell: the legs just follow the piston. a8 (a7 #5):
                             # 0.15 (a7 0.10), so a full pull (1.2 x FS) plus a 100 N lean still clears it
    catch_z=-20.0,           # where the catch legs meet the saddle (the 8 mm nut-driver passes 2 mm under it)
    catch_crown_r=1.2,       # a8 (a7 #2): the saddle touches the piston only on a crown of this radius across y, so the
                             # contact cannot hold the saddle square and the legs bend as free cantilevers
    catch_relief=0.5,        # a8: the saddle's bore is this much bigger either side of the crown
    piston_d=24.0,           # a8 (a7 #6): the piston is Ø24 in the socket and past the catch (a7: Ø22.2 all along), so a
                             # 600 N lean puts 45 MPa on it at the socket mouth (a7: 52); it steps down to the grip's
    piston_step=141.0,       # Ø22.2 spigot here, ahead of the barrel lip
    creep_strain=0.0015,     # PLA creep strain over the unit's life at the seat bosses' <= 4 MPa (finger-tight nuts)
    bench_support=0.002,     # mm: the cradle supports the block a little differently from the fin (head_calc.txt)
    # Piston: one D-bar (Ø22.2 = grip bore), flat 7.8 from the axis on the inboard side so it prints with no support.
    shaft_d=22.2,
    shaft_flat=7.8,
    piston_show=2,           # shadow gap between barrel lip and grip flange (> stop travel)
    spigot_length=130,

    # Load-cell lead: 4 mm OD, 1/2 in straight off the sensor's side, R13 bends.
    lead_d=4.0,
    lead_straight=12.7,
    lead_bend_r=13.0,
    channel_d=5.5,

    fillet_r=2,              # concave blends = R_in
    esp_standoff=6,          # printed standoffs under the ESP32 (M3 x 10 self-tappers get 8 mm of thread)
    groove=None,             # no parting groove: it printed as a 43 mm bridge 1 mm off the bed
    patch_lead=200,          # Cat6 patch cable bought (a3 #7): the route is 150, so 50 mm of slack lies loose in tray L
    voxel=0.6,
)
P["voxel"] = float(os.environ.get("PA_VOXEL", P["voxel"]))   # coarser for quick checks
# a7 (a6 review #3): the cell sits on the leaves' mid-height, not on the grip axis. The link pitches about the cell
# (the only stiff y constraint); with the cell axis at the leaves' mid-length that rotation bends no leaf, so a vertical
# lean puts no axial force on the cell (a6: leaf tops 15 above the axis, 3.8 % crosstalk). The grip axis stays at z 0;
# the link reaches down to the cell with a drop, and the push's offset is carried by the leaves as a couple.
CELL_Z = (-P["link_h"] + P["ground_z"][1]) / 2          # -28.5: leaf mid-height
P["cell_z"] = CELL_Z
P["stop_zp"], P["stop_zq"] = CELL_Z + P["stop_zp"], CELL_Z + P["stop_zq"]

HX = P["handle_spacing"] / 2

# Fasteners: lab kit only. ISO 4762 socket caps (hex bit along the axis) and M3 pan self-tappers, in
# flat-bottomed counterbores of head Ø + ~1 (M3 6.5, M4 8.0, M5 9.5); never countersinks (no csk screws in stock).
M3 = dict(hole=3.4, head=6.7, nut_af=5.6, nut_t=2.6, pilot=2.5, cbore=6.5)     # self-tap pilot, pan/cap counterbore
M4 = dict(hole=4.5, head=8.8, nut_af=7.1, nut_t=3.4, cbore=8.0)
M5 = dict(hole=5.5, head=8.5, nut_af=8.1, nut_t=4.2, cbore=9.5)

# ------------------------------------------------------------------ scene setup

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    return scene


def material(name, rgb, rough=0.5, metal=0.0, coat=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    return m


ROOT = None  # scaled empty; everything is modelled in mm under it
COLL = {}


def collection(name):
    if name not in COLL:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLL[name] = c
    return COLL[name]


def add_object(name, mesh, mat, coll="Concept", smooth_angle=35):
    obj = bpy.data.objects.new(name, mesh)
    collection(coll).objects.link(obj)
    obj.parent = ROOT
    if mat:
        mesh.materials.append(mat)
    if smooth_angle:
        for poly in mesh.polygons:
            poly.use_smooth = True
        if hasattr(mesh, "set_sharp_from_angle"):
            mesh.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


def bm_to_object(name, bm, mat, **kw):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return add_object(name, mesh, mat, **kw)

# ------------------------------------------------------------------ geometry helpers

def round_corners(pts, radii, segs=12):
    """Polygon (list of 2D tuples, CCW or CW) with a fillet of radii[i] at vertex i."""
    out = []
    n = len(pts)
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        if r <= 0:
            out.append(tuple(p1))
            continue
        d0, d1 = (p0 - p1).normalized(), (p2 - p1).normalized()
        half = d0.angle(d1) / 2
        dist = r / math.tan(half)
        a, b = p1 + d0 * dist, p1 + d1 * dist
        bis = (d0 + d1).normalized()
        c = p1 + bis * (r / math.sin(half))
        a0 = math.atan2(a.y - c.y, a.x - c.x)
        a1 = math.atan2(b.y - c.y, b.x - c.x)
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(segs + 1):
            t = a0 + sweep * k / segs
            out.append((c.x + r * math.cos(t), c.y + r * math.sin(t)))
    return out


def prism(name, profile, axis, a0, a1, mat=None, **kw):
    """Extrude a 2D profile along an axis. Profile coords are the two remaining axes in order
    (X: (y, z), Y: (x, z), Z: (x, y))."""
    def to3(u, v, w):
        return {"X": (w, u, v), "Y": (u, w, v), "Z": (u, v, w)}[axis]

    bm = bmesh.new()
    lo = [bm.verts.new(to3(u, v, a0)) for u, v in profile]
    hi = [bm.verts.new(to3(u, v, a1)) for u, v in profile]
    bm.faces.new(lo)
    bm.faces.new(list(reversed(hi)))
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    return bm_to_object(name, bm, mat, **kw)


def cylinder(name, p0, p1, d, mat=None, segs=64, **kw):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=d / 2, radius2=d / 2, depth=axis.length)
    rot = axis.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=bm.verts)
    return bm_to_object(name, bm, mat, **kw)


def box(name, c0, c1, mat=None, **kw):
    (x0, y0, z0), (x1, y1, z1) = c0, c1
    return prism(name, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "Z", z0, z1, mat, **kw)


def cut(target, cutter, solver="EXACT"):
    """Boolean-difference cutter from target; the cutter stays as a hidden helper."""
    mod = target.modifiers.new(f"cut_{cutter.name}", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = solver
    cutter.hide_render = True
    cutter.hide_viewport = True
    for c in cutter.users_collection:
        c.objects.unlink(cutter)
    collection("Cutters").objects.link(cutter)
    return mod


def bevel(obj, width=1.5, segs=3, angle=40):
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = segs
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = False
    return mod


def cable(name, pts, d, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = d / 2
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(pts) - 1)
    for bp, p in zip(spline.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name, curve)
    collection("Concept").objects.link(obj)
    obj.parent = ROOT
    return obj


def import_stl(name, file, matrix, mat, coll="Bought parts"):
    path = os.path.join(PARTS, file)
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    obj = (set(bpy.data.objects) - before).pop()
    obj.name = name
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection(coll).objects.link(obj)
    obj.data.transform(matrix)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if hasattr(obj.data, "set_sharp_from_angle"):
        obj.data.set_sharp_from_angle(angle=math.radians(30))
    obj.parent = ROOT
    return obj


def strip_below(obj, z):
    """Flatten an imported part's vertices below z (mm) onto z, e.g. spacers a stand-in STL carries
    (flattened rather than deleted so the mesh stays closed)."""
    for v in obj.data.vertices:
        if v.co.z < z:
            v.co.z = z


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


# STL boards lie in XY with components up (+Z). On the box's front inner wall they stand in
# the XZ plane facing rearward: (x, y, z) -> (-x, z, y).
BOARD_TO_WALL = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))

def place_board(local_center, R, target):
    """Matrix putting an STL board's local_center at target with rotation R."""
    c = R @ Vector(local_center)
    return Matrix.Translation(Vector(target) - c) @ R

# ------------------------------------------------------------------ more geometry helpers

def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def rounded_rect_ring(a, b, r, per_corner=12):
    """Closed ring of 4*per_corner points; a, b half sizes, r corner radius. Same count for
    any a, b, r, so rings can be lofted, and a == b == r gives a circle."""
    pts = []
    for cx, cy, a0 in ((a - r, b - r, 0), (-(a - r), b - r, 90), (-(a - r), -(b - r), 180), (a - r, -(b - r), 270)):
        for k in range(per_corner):
            t = math.radians(a0 + 90 * k / per_corner)   # endpoint excluded: no duplicate verts
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def rounded_rect_ring4(a, b, radii, per_corner=12):
    """rounded_rect_ring with a radius per corner: (+a,+b), (-a,+b), (-a,-b), (+a,-b)."""
    pts = []
    for (cx, cy, a0), r in zip(((a, b, 0), (-a, b, 90), (-a, -b, 180), (a, -b, 270)), radii):
        r = min(r, a, b)
        ccx, ccy = math.copysign(a - r, cx), math.copysign(b - r, cy)
        for k in range(per_corner):
            t = math.radians(a0 + 90 * k / per_corner)
            pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    return pts


def frames_x(xs, rings):
    """Loft frames along X; rings are (y, z) point lists."""
    return [(Vector((x, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)), ring) for x, ring in zip(xs, rings)]


def loft(name, frames, mat=None, **kw):
    """Loft closed rings. frames: list of (centre, lateral, normal, ring2d)."""
    bm = bmesh.new()
    rings = [[bm.verts.new(c + lat * u + nrm * v) for u, v in ring] for c, lat, nrm, ring in frames]
    n = len(rings[0])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    return bm_to_object(name, bm, mat, **kw)


def tube(name, pts, d, **kw):
    """Round tube along a polyline (parallel-transport frames), for channel cutters."""
    pts = [Vector(p) for p in pts]
    frames = []
    t_prev = (pts[1] - pts[0]).normalized()
    n = t_prev.orthogonal().normalized()
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        axis = t_prev.cross(t)
        if axis.length > 1e-9:
            n = Matrix.Rotation(t_prev.angle(t), 3, axis.normalized()) @ n
        t_prev = t
        frames.append((p, n, t.cross(n), [(d / 2 * math.cos(a), d / 2 * math.sin(a)) for a in
                                          (2 * math.pi * k / 24 for k in range(24))]))
    return loft(name, frames, **kw)


def cone(name, p0, p1, d0, d1, mat=None, segs=48, **kw):
    p0, p1 = Vector(p0), Vector(p1)
    axis = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=d0 / 2, radius2=d1 / 2, depth=axis.length)
    rot = axis.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=bm.verts)
    return bm_to_object(name, bm, mat, **kw)


def hex_prism(name, centre, axis, af, depth0, depth1, **kw):
    """Hex nut pocket: across-flats af, along axis 'X'|'Y'|'Z' from depth0 to depth1."""
    r = af / math.sqrt(3)
    ring = [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)]
    cx, cy, cz = centre
    u0, v0 = {"X": (cy, cz), "Y": (cx, cz), "Z": (cx, cy)}[axis]
    return prism(name, [(u0 + u, v0 + v) for u, v in ring], axis, depth0, depth1, **kw)


class Turtle:
    """Polyline of straight runs and exact arcs, so bend radii are what they say."""

    def __init__(self, p, h):
        self.p, self.h = Vector(p), Vector(h).normalized()
        self.pts = [self.p.copy()]

    def line(self, length, step=2.0):
        n = max(1, int(abs(length) / step))
        start = self.p.copy()
        for i in range(1, n + 1):
            self.pts.append(start + self.h * (length * i / n))
        self.p = start + self.h * length
        return self

    def line_to(self, axis, value):
        i = "xyz".index(axis)
        return self.line((value - self.p[i]) / self.h[i])

    def arc(self, r, deg, axis):
        k = Vector({"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}[axis])
        c = self.p + k.cross(self.h) * (r * math.copysign(1, deg))
        n = max(4, int(abs(deg) / 5))
        v = self.p - c
        for i in range(1, n + 1):
            self.pts.append(c + Matrix.Rotation(math.radians(deg * i / n), 3, k) @ v)
        self.p = self.pts[-1].copy()
        self.h = Matrix.Rotation(math.radians(deg), 3, k) @ self.h
        return self


def poly_cable(name, pts, d, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = d / 2
    curve.bevel_resolution = 4
    curve.use_fill_caps = True
    spline = curve.splines.new("POLY")
    spline.points.add(len(pts) - 1)
    for sp, p in zip(spline.points, pts):
        sp.co = (*p, 1.0)
    curve.materials.append(mat)
    obj = bpy.data.objects.new(name, curve)
    collection("Wiring").objects.link(obj)
    obj.parent = ROOT
    return obj

# ------------------------------------------------------------------ SDF parts

def sdf_part(name, sources, mat, fillet_r=0.0, subtract=(), split_x=None, voxel=None, add=(), groove=None, groove_ymax=400,
             windows=(), open_r=0.0, hollow=()):
    """Printed part from Blender's SDF grid nodes: union of sources, closed by fillet_r so
    inside corners get fillets, plus `add` (unioned after the fillet, so no blend), minus
    `subtract`. With split_x, returns the two halves either side of the plane x = split_x
    (the handle clamshell). Baked to plain meshes."""
    voxel = voxel or P["voxel"]
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, link = ng.nodes, ng.links.new
    band = int(math.ceil(max(fillet_r, open_r, 2.0) / voxel)) + 4

    def grid_of(objs):
        join = N.new("GeometryNodeJoinGeometry")
        for o in objs:
            info = N.new("GeometryNodeObjectInfo")
            info.transform_space = "RELATIVE"
            info.inputs["Object"].default_value = o
            link(info.outputs["Geometry"], join.inputs["Geometry"])
            o.hide_render = True
            for c in o.users_collection:
                c.objects.unlink(o)
            collection("Part sources").objects.link(o)
        sdf = N.new("GeometryNodeMeshToSDFGrid")
        sdf.inputs["Voxel Size"].default_value = voxel
        sdf.inputs["Band Width"].default_value = band
        link(join.outputs["Geometry"], sdf.inputs["Mesh"])
        return sdf.outputs["SDF Grid"]

    def boolean(op, a, b):
        node = N.new("GeometryNodeSDFGridBoolean")
        node.operation = op
        if op == "DIFFERENCE":
            link(a, node.inputs[0])
            link(b, node.inputs[1])
        else:
            link(b, node.inputs[1])
            link(a, node.inputs[1])
        return node.outputs["Grid"]

    g = grid_of(sources)
    if fillet_r > 0:
        grow = N.new("GeometryNodeSDFGridOffset")
        grow.inputs["Distance"].default_value = fillet_r
        link(g, grow.inputs["Grid"])
        shrink = N.new("GeometryNodeSDFGridOffset")
        shrink.inputs["Distance"].default_value = -fillet_r
        link(grow.outputs["Grid"], shrink.inputs["Grid"])
        g = shrink.outputs["Grid"]
    if windows:
        g = boolean("DIFFERENCE", g, grid_of(windows))
    if open_r > 0:                                            # opening: rounds every convex edge
        shrink2 = N.new("GeometryNodeSDFGridOffset")
        shrink2.inputs["Distance"].default_value = -open_r
        link(g, shrink2.inputs["Grid"])
        grow2 = N.new("GeometryNodeSDFGridOffset")
        grow2.inputs["Distance"].default_value = open_r
        link(shrink2.outputs["Grid"], grow2.inputs["Grid"])
        g = grow2.outputs["Grid"]
    if hollow:                                   # cavities cut before `add`, so bosses survive inside them
        g = boolean("DIFFERENCE", g, grid_of(hollow))
    if add:
        g = boolean("UNION", g, grid_of(add))
    if subtract:
        g = boolean("DIFFERENCE", g, grid_of(subtract))
    if groove and split_x is not None:
        # Deliberate parting groove: the outer skin (depth) within a thin slab on the split plane.
        gw, gd = groove
        inner = N.new("GeometryNodeSDFGridOffset")
        inner.inputs["Distance"].default_value = -gd
        link(g, inner.inputs["Grid"])
        skin = boolean("DIFFERENCE", g, inner.outputs["Grid"])
        slab = box(f"{name} groove slab", (split_x - gw / 2, -400, -400), (split_x + gw / 2, groove_ymax, 400))
        g = boolean("DIFFERENCE", g, boolean("INTERSECT", skin, grid_of([slab])))

    out = N.new("NodeGroupOutput")
    join = N.new("GeometryNodeJoinGeometry")
    halves = [g]
    if split_x is not None:
        lo = box(f"{name} keep -X", (split_x - 400, -400, -400), (split_x, 400, 400))
        hi = box(f"{name} keep +X", (split_x, -400, -400), (split_x + 400, 400, 400))
        halves = [boolean("INTERSECT", g, grid_of([lo])), boolean("INTERSECT", g, grid_of([hi]))]
    for h in halves:
        mesh = N.new("GeometryNodeGridToMesh")
        mesh.inputs["Threshold"].default_value = 0.0
        link(h, mesh.inputs["Grid"])
        link(mesh.outputs["Mesh"], join.inputs["Geometry"])
    smooth = N.new("GeometryNodeSetShadeSmooth")
    link(join.outputs["Geometry"], smooth.inputs["Geometry"])
    setmat = N.new("GeometryNodeSetMaterial")
    setmat.inputs["Material"].default_value = mat
    link(smooth.outputs["Geometry"], setmat.inputs["Geometry"])
    link(setmat.outputs["Geometry"], out.inputs["Geometry"])

    live = add_object(name + " (live)", bpy.data.meshes.new(name), None, coll="Part sources", smooth_angle=0)
    live.modifiers.new("sdf", "NODES").node_group = ng
    t = time.time()
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(live.evaluated_get(dg))
    live.hide_render = live.hide_viewport = True
    for o in collection("Part sources").objects:
        o.hide_viewport = True
    print(f"  sdf {name}: {len(baked.polygons)} faces in {time.time() - t:.1f} s")
    if split_x is None:
        return [add_object(name, baked, None, coll="Printed parts", smooth_angle=0)]
    return [add_object(n, m, None, coll="Printed parts", smooth_angle=0)
            for n, m in zip((f"{name} -X half", f"{name} +X half"), split_loose(baked, split_x))]


def split_loose(mesh, split_x):
    """Two meshes from one: the shells on either side of x = split_x."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    parent = list(range(len(bm.verts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for e in bm.edges:
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[a] = b
    comp_x = {}
    for v in bm.verts:
        r = find(v.index)
        s = comp_x.setdefault(r, [0.0, 0])
        s[0] += v.co.x
        s[1] += 1
    side = {r: (s[0] / s[1] > split_x) for r, s in comp_x.items()}
    out = []
    for keep_hi in (False, True):
        b2 = bm.copy()
        b2.verts.ensure_lookup_table()
        drop = [b2.verts[i] for i in range(len(b2.verts)) if side[find(i)] != keep_hi]
        bmesh.ops.delete(b2, geom=drop, context="VERTS")
        m = bpy.data.meshes.new(mesh.name + ("+" if keep_hi else "-"))
        b2.to_mesh(m)
        b2.free()
        for mat in mesh.materials:
            m.materials.append(mat)
        for poly in m.polygons:
            poly.use_smooth = True
        out.append(m)
    bm.free()
    return out


def mirror_x(obj, name):
    """Mirror a baked part across x = 0 (left handle from the right one)."""
    m = obj.data.copy()
    m.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    m.flip_normals()
    return add_object(name, m, None, coll="Printed parts", smooth_angle=0)


# ------------------------------------------------------------------ chair plate frame

TILT = math.radians(P["plate_tilt"])
# Plate-local (x, n, u) -> world (x, y, z): u up the plate face, n off it (rearward).
PLATE_M = Matrix(((1, 0, 0, 0),
                  (0, math.cos(TILT), math.sin(TILT), 0),
                  (0, -math.sin(TILT), math.cos(TILT), 0),
                  (0, 0, 0, 1)))
U_TOP = P["barrel_d"] / 2 / math.cos(TILT)        # plate top = unit top, along the plate


def on_plate(u, n):
    """(y, z) of the point u up the plate face and n off it."""
    return (u * math.sin(TILT) + n * math.cos(TILT), u * math.cos(TILT) - n * math.sin(TILT))


def plate_box(name, c0, c1, mat=None, **kw):
    """Box given in plate-local (x, n, u) corners."""
    o = box(name, c0, c1, mat, **kw)
    o.data.transform(PLATE_M)
    return o


def plate_cyl(name, x, u, n0, n1, d, mat=None, **kw):
    """Cylinder along the plate normal at (x, u), from n0 to n1."""
    (y0, z0), (y1, z1) = on_plate(u, n0), on_plate(u, n1)
    return cylinder(name, (x, y0, z0), (x, y1, z1), d, mat, **kw)


def mount_bolts():
    """(x, u, n_head, length) of the M5s into T-nuts in the plate slots: an upper row through the
    land, and a lower row through feet that bridge the bevel gap down by the floor."""
    up = U_TOP - P["land"] / 2
    lo = (z_bridge() + 14) / math.cos(TILT)
    n_lo = foot_depth(lo)
    return ([(s * x, up, P["wall"] + 9, 20) for x in P["mount_slots"] for s in (-1, 1)] +
            [(s * P["mount_slots"][-1], lo, n_lo, 30) for s in (-1, 1)])


def foot_depth(u):
    """n of a foot's bearing face: through the gap to the bevelled front wall, its wall, and a 6 mm boss."""
    knee = on_plate(U_TOP - P["land"], 0)
    y, z = on_plate(u, 0)
    n_front = (knee[0] - y) / math.cos(TILT)                 # front face is vertical below the knee
    return n_front + P["wall"] + 6

# ------------------------------------------------------------------ section

def section_pts(z_bot, z_top=None):
    """Side outline (y, z), clockwise: plate top, barrel top-rear, barrel bottom-rear, down the
    rear slope to the floor, floor front, up the bevelled front face to the knee where the land
    starts. With z_top, the top edge is moved down to z_top (under the cover)."""
    r, L = P["barrel_d"] / 2, P["lip_y"]
    knee = on_plate(U_TOP - P["land"], 0)
    front_tilt = TILT - math.radians(P["bevel"])
    fy = knee[0] + (z_bot - knee[1]) * math.tan(front_tilt)
    sy = L - (-r - z_bot) / math.tan(math.radians(P["slope"]))
    zt = r if z_top is None else z_top
    return [(zt * math.tan(TILT), zt), (L, zt), (L, -r), (sy, z_bot), (fy, z_bot), knee]


def z_bridge():
    return P["barrel_d"] / 2 - P["bridge_h"]


def z_fin():
    return P["barrel_d"] / 2 - P["fin_h"]


def tray_top():
    return P["barrel_d"] / 2 - P["cover_t"]


def chamfer_corners(pts, cs):
    """Polygon with corner i replaced by a chamfer that runs cs[i] mm along each edge."""
    out = []
    n = len(pts)
    for i, p in enumerate(pts):
        if i not in cs:
            out.append(p)
            continue
        p1 = Vector(p)
        a = (Vector(pts[i - 1]) - p1).normalized() * cs[i]
        b = (Vector(pts[(i + 1) % n]) - p1).normalized() * cs[i]
        out += [tuple(p1 + a), tuple(p1 + b)]
    return out


def inset(pts, d):
    """Clockwise convex polygon with edge i (pts[i] -> pts[i+1]) moved inward by d[i]."""
    n = len(pts)
    lines = []
    for i in range(n):
        p, q = Vector(pts[i]), Vector(pts[(i + 1) % n])
        t = (q - p).normalized()
        lines.append((p + Vector((t.y, -t.x)) * d[i], t))
    out = []
    for i in range(n):
        (p1, t1), (p2, t2) = lines[i - 1], lines[i]
        den = t1.x * t2.y - t1.y * t2.x
        a = ((p2.x - p1.x) * t2.y - (p2.y - p1.y) * t2.x) / den
        out.append(tuple(p1 + t1 * a))
    return out

# ------------------------------------------------------------------ fin (handle + bridge end cap)

def handle_frame():
    """Shared head numbers (right fin, centred on x = HX). Along the grip axis, front to rear:
    fin front wall | front nut + washer in the block's counterbore | cartridge block | cell | link drop | front leaf |
    top link (socket, piston) | rear leaf. a7: the cell axis is at cz (the leaves' mid-height), below the grip axis az."""
    lip = P["lip_y"]
    cr = P["cell_rear"]                                     # cell rear face, on the drop's seat boss
    ye = cr - 12.7                                          # cell front face, on the block's seat boss (STL: 12.7)
    yb = ye - P["seat_h"]                                   # block rear face (1.0 clear of the cell outside the boss)
    yp = yb - P["block_t"]                                  # block front face, on the fin's front wall
    yf = yb - P["block_c"]                                  # front counterbore floor: printed washer, then the front nut
    sh, t = P["seat_h"], P["leaf_t"]
    l0 = cr + sh                                            # drop front face (1.0 clear of the cell outside the boss)
    d1 = l0 + P["drop_t"]                                   # drop rear face
    f0 = d1 + P["leaf_r"] + 1.0                             # front leaf: its front root fillet 1.0 clear of the drop
    l1 = f0 + t / 2 + P["leaf_pitch_min"] + t / 2           # rear leaf flush with the link's rear end
    return dict(az=P["arm_z"], cz=CELL_Z, lip=lip, cell_rear=cr, ye=ye, yb=yb, yp=yp, yf=yf,
                link0=l0,                                   # drop / top link front face
                wall1=l0 + 3.0,                             # rear face of the drop's 3 mm wall: rear washer, then the rear nut
                drop1=d1, leaf_f0=f0,
                link1=l1,                                   # top link rear end
                sock0=cr + 13,                              # piston plug face on the socket shoulder
                box_end=HX - P["fin_t"] / 2)                # x of the bridge end / fin inner face


def fin_profile():
    R, Rb = P["R_out"], P["R_out"]
    return round_corners(section_pts(z_fin()), [R, R, R, Rb, Rb, R], segs=10)


LEAD_DIR = math.radians(45)    # a7: the cell is clocked so its wire boss points up-inboard at 45 deg (a6: straight down)


def lead_path(sign):
    """Lead: a7: straight off the boss, up-inboard at 45 deg (between the block and the drop, above the stop screws),
    one R13 bend to horizontal, through the fin's inner face into the bridge."""
    F = handle_frame()
    d = Vector((-sign * math.sin(LEAD_DIR), 0, math.cos(LEAD_DIR)))
    t = Turtle(Vector((sign * HX, F["ye"] + 3.5, F["cz"])) + d * 15, d)
    t.line(12.7 + P["lead_straight"] - 15)                    # 1/2 in off the sensor's side
    t.arc(P["lead_bend_r"], -sign * 45, "Y")                  # to horizontal, inboard (ends just past the fin's inner face)
    if (sign * (F["box_end"] - 1) - t.p.x) * t.h.x > 0:
        t.line_to("x", sign * (F["box_end"] - 1))
    handle_part = list(t.pts) + [t.p - Vector((sign * 6, 0, 0))]
    return t, handle_part


def teardrop_x(name, x, z, d, y0, y1, cap=None):
    """Bore along Y whose section is a circle with 45 deg tips at +-X, so each fin half (printed
    split face down) prints its half of the bore as a pointed arch instead of a flat ceiling.
    cap: cut the tips flat at |x'| = cap (a short bridge) to keep wall to the fin faces."""
    r, tip = d / 2, d / 2 * math.sqrt(2)
    top = [(x + r * math.cos(math.radians(a)), z + r * math.sin(math.radians(a))) for a in range(45, 136, 5)]
    bot = [(x + r * math.cos(math.radians(a)), z + r * math.sin(math.radians(a))) for a in range(225, 316, 5)]
    if cap is None or cap >= tip:
        prof = [(x + tip, z)] + top + [(x - tip, z)] + bot
    else:
        h = tip - cap                                         # half height of the flat at the cap
        prof = [(x + cap, z - h), (x + cap, z + h)] + top + [(x - cap, z + h), (x - cap, z - h)] + bot
    return prism(name, prof, "Y", y0, y1, coll="Part sources")


def octagon(hw, hh, ch):
    """(x', z) outline of a hw x hh half-size rectangle with 45 deg chamfers ch on its four corners."""
    return [(hw, -hh + ch), (hw, hh - ch), (hw - ch, hh), (-hw + ch, hh), (-hw, hh - ch), (-hw, -hh + ch),
            (-hw + ch, -hh), (hw - ch, -hh)]


def leaf_ys():
    """(y0, y1) of the front and rear flexure leaves (a7: the front leaf stands behind the drop; the rear leaf is flush
    with the link's rear end). Each leaf is two strips, |x'| from leaf_gap to cart_hw."""
    F = handle_frame()
    t = P["leaf_t"]
    return [(F["leaf_f0"], F["leaf_f0"] + t), (F["link1"] - t, F["link1"])]


def leaf_b():
    """Total width of one leaf's two strips."""
    return 2 * (P["cart_hw"] - P["leaf_gap"])


LEAF_E = 3000.0       # MPa, printed PLA in the layer plane (2500-3500)
LEAF_KT = 1.35        # stress concentration of an r = t root fillet (r/t = 1, Peterson stepped bar in bending)
GRIP_Y = 219.5        # grip load point on the grip axis (middle of the hand)
LEAN_N = 150.0        # downward lean on one grip used for the leaf fatigue check (the lip catches heavier leans)


def leaf_stress():
    """Leaf numbers computed from the geometry, so the `flexures` row's stress follows the params (a3 #3):
    root bending stress with the link at the largest stop setting, plus the axial stress of the couple the leaves
    carry for a 150 N downward lean on the grip, both times the root fillet's Kt."""
    t, b = P["leaf_t"], leaf_b()
    L = -P["link_h"] - P["ground_z"][1]                     # 27: link bottom to ground bar top
    Le = L - P["leaf_r"]                                    # bending length between the fillet tangents
    (f0, f1), (r0, r1) = leaf_ys()
    pitch = (r0 + r1) / 2 - (f0 + f1) / 2
    sb = 3 * LEAF_E * t * P["stop_gap_max"] / Le ** 2      # guided-guided leaf, deflected by the stop travel
    couple = LEAN_N * (GRIP_Y - (f0 + f1) / 2) / pitch      # rear-leaf compression, moments about the front leaf
    sa = couple / (b * t)
    k_pair = 2 * 12 * LEAF_E * (b * t ** 3 / 12) / Le ** 3
    # the leaf pair against pitch (lean) and yaw (side load), with the cell taking no shear (the conservative case,
    # as reviewer a4's head_check.py): axial pair for pitch; in-plane bending + shear of each leaf for yaw
    k_rot = LEAF_E * b * t / L * pitch ** 2 / 2
    ws, xs = P["cart_hw"] - P["leaf_gap"], (P["cart_hw"] + P["leaf_gap"]) / 2     # a7: two strips per leaf
    I_x = 2 * (t * ws ** 3 / 12 + t * ws * xs ** 2)
    k_x = 1 / (1 / (12 * LEAF_E * I_x / L ** 3) + 1 / (5 / 6 * LEAF_E / 2.6 * b * t / L))
    k_yaw = k_x * pitch ** 2 / 2
    # lip catch (a4 #2): how far the piston drops at the barrel lip when the rear leaf reaches its buckling load
    # (gross section, E 2500, the low end), turning about the leaf centroid and ignoring the piston's own bending (which only
    # brings the lip in earlier). The lip clearance must be well under this.
    p_cr = 4 * math.pi ** 2 * 2500.0 * (b * t ** 3 / 12) / L ** 2
    f_buckle = p_cr / ((GRIP_Y - (f0 + f1) / 2) / pitch)
    theta = f_buckle * (GRIP_Y - (f0 + r1) / 2) / (k_rot * 2500.0 / LEAF_E)
    lip_drop = theta * (P["lip_y"] - (f0 + r1) / 2)          # a5 #5: the free link turns about the leaf centroid
    # a7 (a6 #3): lean-to-axial crosstalk, the a5 reviewer's formula with the leaf top's height measured from the cell
    # axis instead of the a6 constant 15: the pitching link (it turns about the cell) moves each leaf top by
    # theta x a and turns it by theta; the leaf shear 2 E I / L^2 (12 a / L + 6) theta goes into the cell.
    # a = leaf top below the cell axis; a = -L/2 (leaf mid-length on the axis) gives zero.
    a_top = CELL_Z - (-P["link_h"])
    xt = 2 * LEAF_E * (b * t ** 3 / 12) / L ** 2 * (12 * a_top / L + 6) * (GRIP_Y - (f0 + r1) / 2) / k_rot
    # a6 #3 / #5, a8 (a7 #3): where the piston lands on the barrel lip / the catch. Reviewer a7's model
    # (cad/review/a7/scripts/head_a7.py): the leaves as two axial supports (statics), the link turning on their
    # compression, plus the piston's own bending as a cantilever from the socket mouth. E 2500 / 3500.
    lip, l1 = P["lip_y"], handle_frame()["link1"]
    yf_, yr_ = f0 + t / 2, r1 - t / 2
    I_p = dbar_I(P["shaft_d"], P["shaft_flat"])             # spigot (lip, step)
    I_pc = dbar_I(P["piston_d"], P["shaft_flat"])           # a8: Ø24 in the socket and past the catch
    L_g = GRIP_Y - l1

    def drop_per_n(y, e, Ipp):
        kl = e * b * t / L
        wf, wr = -(GRIP_Y - yr_) / pitch / kl, (GRIP_Y - yf_) / pitch / kl
        a_ = y - l1
        return wr + (wr - wf) / pitch * (y - yr_) + a_ ** 2 * (3 * L_g - a_) / (6 * e * Ipp)
    contact = [P["lip_c"] / drop_per_n(lip, e, I_p) for e in (2500.0, 3500.0)]
    c0, c1 = catch_ys()
    yc = (c0 + c1) / 2                                      # the crown, on the legs' mid-plane
    catch = [P["catch_c"] / drop_per_n(yc, e, I_pc) for e in (2500.0, 3500.0)]
    # a8 (a7 #2): the saddle touches the piston on an R1.2 crown, so it cannot be held square: the legs bend as free
    # cantilevers with the contact h above their tops (a7's 3 E I / L^3 was neither bound; held square, fixed-guided,
    # they give 12 E I / L^3 = 110 N/mm)
    Lc = P["catch_z"] - P["ground_z"][1]
    hc = -(P["piston_d"] / 2 + P["catch_c"]) - P["catch_z"]  # contact (bottom of the saddle bore) above the leg tops
    ws = P["cart_hw"] - P["leaf_gap"]
    EIl = LEAF_E * ws * t ** 3 / 12
    d_free = (Lc ** 3 / 3 + hc * Lc ** 2 + hc * hc * Lc) / EIl
    k_catch = 2 / d_free
    k_guided = 2 * 12 * EIl / Lc ** 3
    g_mom = (Lc ** 2 / 2 + hc * Lc) / (Lc ** 3 / 3 + hc * Lc ** 2 + hc * hc * Lc)   # N at the contact per N.mm held
    # legs' buckling: fixed at the ground bar, the saddle rigid, held laterally (friction) at the contact hc above the
    # leg tops but free to turn on the crown: tan(kL)(1 + h(L + h)k^2) = kL, E 2500 (h = 0 gives 20.19 E I / L^2)
    EIb = 2 * 2500.0 * ws * t ** 3 / 12
    kk, prev = 1e-4, None
    while True:
        v = math.tan(kk * Lc) * (1 + hc * (Lc + hc) * kk * kk) - kk * Lc
        if prev is not None and prev * v < 0 and abs(v) < 50:
            break
        prev, kk = v, kk + 1e-5
    p_cr_c = kk * kk * EIb
    # push-induced pitch at 1.2 x FS of a 50 kg cell (the push acts on the grip axis, the cell on cz): the piston's
    # motion at the catch; a pull moves it down toward the saddle by the same
    th_push = 1.2 * 490.5 * (P["arm_z"] - CELL_Z) / k_rot
    pull_motion = th_push * (yc - (f0 + r1) / 2)
    pull_lean_margin = (P["catch_c"] - pull_motion) / drop_per_n(yc, 2500.0, I_pc)   # extra lean that lands it at full pull
    # a8 (a7 #3): past contact, a rigid link on three axial supports (front leaf, rear leaf, catch), reviewer a7's solve.
    # The catch's axial stiffness: the legs in series with the saddle's bending over the nut-driver gap; the bound
    # cases are the catch at 1/3 of that (crown contact, settling) for the rear strips, and at full for the catch
    s0, s1 = saddle_ys()
    ts, dsad = s1 - s0, P["catch_z"] - (-(P["piston_d"] / 2 + P["catch_c"]))
    dsad = abs(dsad)
    span = 2 * P["leaf_gap"]                                # clear span of the saddle between the legs
    I_s = ts * dsad ** 3 / 12

    def three(e, kc):
        kl = e * b * t / L
        ys_, ks = [yf_, yr_, yc], [kl, kl, kc]
        A_ = sum(ks)
        B_ = sum(k * (y - yc) for k, y in zip(ks, ys_))
        C_ = sum(k * (y - yc) ** 2 for k, y in zip(ks, ys_))
        Mg = GRIP_Y - yc
        det = A_ * C_ - B_ * B_
        w0, th_ = (C_ - B_ * Mg) / det, (A_ * Mg - B_) / det
        return [k * (w0 + th_ * (y - yc)) for k, y in zip(ks, ys_)]
    rear_share, catch_share = 0.0, 0.0
    for e in (2500.0, 3500.0):
        k_legs = 2 * e * ws * t / Lc
        k_sad = 1 / (span ** 3 / (192 * e * I_s) + span / (4 * 5 / 6 * e / 2.6 * ts * dsad))
        kc = 1 / (1 / k_legs + 1 / k_sad)
        if e == 2500.0:                                     # the rear strips' row is at E 2500 (their buckling load)
            rear_share = three(e, kc / 3)[1]                # soft bound: legs + saddle at a third (crown contact, settling)
        catch_share = max(catch_share, three(e, k_legs)[2]) # stiff bound: the legs alone (saddle and contact rigid)
    lo = catch[0]
    rear_600 = lo * (GRIP_Y - yf_) / pitch + (600.0 - lo) * rear_share
    catch_600 = (600.0 - lo) * catch_share
    p_cr_rear = 4 * math.pi ** 2 * 2500.0 * (b * t ** 3 / 12) / L ** 2
    # saddle across the layers: a beam over the nut-driver gap (clamped in the legs, span 2 x leaf_gap), the lean as a
    # point load at mid-span (bound; the crown's contact spreads along the bore), bending stress along x = across layers
    sad_600 = catch_600 * span / 8 / (ts * dsad ** 2 / 6)
    lean_mod = 300.0
    catch_300 = (lean_mod - lo) * catch_share
    sad_300 = catch_300 * span / 8 / (ts * dsad ** 2 / 6)
    # crown land after a 600 N lean: it may yield flat to a land a = N / (2 len p) (contact along the bore >= 10 mm, PLA
    # contact pressure 80 MPa); a later lean holds up to N x a against the legs' turn, adding g_mom x that to the shunt
    land = catch_600 / (2 * 10.0 * 80.0)
    shunt_300 = k_catch * P["stop_gap_max"] + g_mom * catch_300 * land
    shunt_600 = min(k_catch * P["stop_gap_max"] + g_mom * catch_600 * land, k_guided * P["stop_gap_max"])
    catch_drop = theta * (yc - (f0 + r1) / 2)               # link-only drop at the catch when the rear strips would buckle
    # piston bending at 600 N on one grip: at the socket mouth (no relief from the catch reaction: the bound), at the
    # catch, and on the Ø22.2 spigot at the step
    pist = dict(mouth=600.0 * (GRIP_Y - l1) * P["piston_d"] / 2 / I_pc, catch=600.0 * (GRIP_Y - yc) * P["piston_d"] / 2 / I_pc,
                step=600.0 * (GRIP_Y - P["piston_step"]) * P["shaft_d"] / 2 / I_p)
    return dict(leaf_free_len=L, leaf_pitch=round(pitch, 2), leaf_k_pair=round(k_pair, 1), leaf_b=b,
                leaf_top_below_cell=round(a_top, 3), lean_crosstalk=round(xt, 5),
                lip_contact_lo_n=round(contact[0], 1), lip_contact_hi_n=round(contact[1], 1),
                catch_contact_lo_n=round(catch[0], 1), catch_contact_hi_n=round(catch[1], 1),
                catch_k=round(k_catch, 2), catch_k_guided=round(k_guided, 1), catch_h=round(hc, 2),
                catch_g_mom=round(g_mom, 4), catch_buckle_n=round(p_cr_c), catch_y=round(yc, 2),
                catch_push_motion=round(pull_motion, 4), catch_pull_lean_margin=round(pull_lean_margin, 1),
                catch_rear_share=round(rear_share, 3), catch_share=round(catch_share, 3),
                leaf_rear_600=round(rear_600), leaf_rear_buckle=round(p_cr_rear),
                saddle_t=round(ts, 2), saddle_depth=round(dsad, 2), saddle_600_mpa=round(sad_600, 2),
                saddle_300_mpa=round(sad_300, 2), catch_300=round(catch_300), catch_land=round(land, 3),
                catch_shunt_300=round(shunt_300, 2), catch_shunt_600=round(shunt_600, 1),
                leaf_rear_at_lip_n=round(catch[1] * (GRIP_Y - yf_) / pitch, 1),
                leaf_stress_at_lip_mpa=round(LEAF_KT * (sb + catch[1] * (GRIP_Y - yf_) / pitch / (b * t)), 2),
                piston_at_catch_mpa=round(catch[1] * (GRIP_Y - yc) * P["piston_d"] / 2 / I_pc, 1),
                piston_600_mpa=round(max(pist.values()), 1), piston_mouth_mpa=round(pist["mouth"], 1),
                piston_catch_mpa=round(pist["catch"], 1), piston_step_mpa=round(pist["step"], 1),
                piston_I=round(I_p), piston_I_c=round(I_pc),
                catch_load_600=round(catch_600), catch_drop_buckle=round(catch_drop, 3),
                leaf_k_rot=round(k_rot, -3), leaf_k_yaw=round(k_yaw, -3), leaf_buckle_grip_n=round(f_buckle),
                lip_drop_buckle=round(lip_drop, 3),
                leaf_bend_mpa=round(sb, 2), leaf_axial_mpa=round(sa, 2),
                leaf_stress_mpa=round(LEAF_KT * (sb + sa), 2))


def dbar_I(d, flat, n=2000):
    """Second moment of the piston's D-bar (Ø d, a flat at `flat` from the axis on the inboard side) about the
    horizontal axis, i.e. against a vertical lean."""
    r, I = d / 2, 0.0
    for i in range(n):
        z = -r + (i + 0.5) * 2 * r / n
        hw = math.sqrt(max(r * r - z * z, 0.0))
        I += z * z * max(hw - max(-hw, -flat), 0.0) * 2 * r / n
    return I


STOP_LP, STOP_LQ = 25.0, 30.0     # M3 x 25 push screws, M3 x 30 pull screws
M3_HEAD_H = 3.0


def stop_layout():
    """Overload stop numbers (y along the grip axis, right cartridge). Each stop screw threads into an M3 nut held in
    a slot in the top link, so it moves with the link; its head acts on the block. Push: the head sits in a
    counterbore in the block's rear face and its top face is stop_gap behind the counterbore floor (pf). Pull: the
    screw passes through the block and its head sits in a counterbore in the block's front face, its underside
    stop_gap in front of the floor (qf). Nothing in either path is clamped or preloaded, so the gap rides on the
    cell alone (plus the two seat bosses)."""
    F = handle_frame()
    g = P["stop_gap"]
    pf = F["yb"] - 3.6                                      # push counterbore floor
    qf = F["yp"] + 5.5                                      # pull counterbore floor (a7: the block is 1 mm longer)
    at_p = pf + g + M3_HEAD_H                               # push head underside (bearing face of the screw)
    at_q = qf - g                                           # pull head underside
    l0 = F["link0"]
    return dict(pf=pf, qf=qf, at_p=at_p, at_q=at_q, Lp=STOP_LP, Lq=STOP_LQ,
                tip_p=at_p + STOP_LP, tip_q=at_q + STOP_LQ,
                nut_p0=l0 + 2.6, nut_p1=l0 + 5.0,           # push nut (M3, 2.4 thick) in the link
                nut_q0=l0 + 5.5, nut_q1=l0 + 7.9)           # pull nut


def stop_thermal():
    """Change of each stop gap per deg C (mm/C): PLA (68e-6) and steel (12e-6) along each path from the cell's front
    face to the head's stop face. Push: block (ye - pf) + cell + link (cell rear face to the push nut's rear face, which
    the nut bears on at the stop) minus the screw (head top to nut). Pull: the mirror image."""
    F, st = handle_frame(), stop_layout()
    ap, as_, cell = 68e-6, 12e-6, 12.7
    ye, cr, g = F["ye"], F["cell_rear"], P["stop_gap"]
    dp = (ye - st["pf"]) * ap + cell * as_ + (st["nut_p1"] - cr) * ap - (st["nut_p1"] - (st["pf"] + g)) * as_
    dq = -(ye - st["qf"]) * ap - cell * as_ - (st["nut_q0"] - cr) * ap + (st["nut_q0"] - st["at_q"]) * as_
    return dict(stop_dT_p=round(dp, 7), stop_dT_q=round(dq, 7))


def clamshell_bolts():
    """(y, z, half thickness) of the M3 self-tappers that close the fin, clear of every bore and pocket."""
    ht = P["fin_t"] / 2
    return [(25, 15, ht), (12, -26, ht), (60, -62, ht), (100, -72, ht), (88, -58, ht), (40, -100, ht)]   # a7: (138, -22) moved


def box_bolts():
    """(y, z) of the M4s from inside the bridge through its end wall into nuts in the fin.
    The low one sits 8 mm above the tray floor's top and 19 mm off the 60 deg rear wall (a 1/4 in bit holder clears the
    floor by 2 mm)."""
    # a7: the cartridge is 13 mm longer (rear leaf at 120.5-123): the rear pair moved back and down, clear of its pocket
    # a8: the rear one 1 mm lower (a7: z -18), so its nut slot keeps 2 mm of wall under the bore round the Ø24 piston
    return [(24, -18), (141, -19), (110, -56)]


# cadlib (exact Manifold booleans) for the cartridge and piston: 2.0 mm leaves and a 0.15 mm stop gap
# need exact geometry, not a 0.6 mm voxel grid.
sys.path.insert(0, os.path.join(os.path.expanduser("~/code-stuff/alex-3d-skills/skills/print-cad-blender"), "scripts"))
from cadlib import geom as G  # noqa: E402


def adopt(ob, name, mat, coll="Printed parts"):
    """Move a cadlib object (world mm) into this build: rename, collection, ROOT parent, material."""
    ob.name = name
    ob.data.name = name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    collection(coll).objects.link(ob)
    ob.parent = ROOT
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    for poly in ob.data.polygons:
        poly.use_smooth = False
        poly.material_index = 0
    return ob


def fillet2d(yc, zc, sy, sz, r, n=8):
    """(y, z) outline of a concave R`r` fillet in the corner at (yc, zc) between a leaf face (plane y = yc, open
    toward +sy) and a base face (plane z = zc, open toward +sz). It overlaps 0.2 into both, so it unions cleanly."""
    cy, cz = yc + sy * r, zc + sz * r
    a0, a1 = math.atan2(-sz, 0.0), math.atan2(0.0, -sy)
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    arc = [(cy + r * math.cos(a0 + d * k / n), cz + r * math.sin(a0 + d * k / n)) for k in range(n + 1)]
    return [(yc - sy * 0.2, zc - sz * 0.2), (cy, zc - sz * 0.2)] + arc + [(yc - sy * 0.2, cz)]


LEAF_SPLIT = 0.3      # the moving link's leaves start this far above the ground bar (check-only split, PRT_movlink_*)
CHECK_SPLIT = 2.5     # check-only split: fixed leaf stubs (with the bottom root fillets) up to 2.2, moving leaves from 2.5
NUT3_AF = 5.6         # M3 nut pocket across flats


def td_cap(c, r):
    """Teardrop for a hole along Y in the cartridge (prints inboard face down, so +x' is up), with its 45 deg point
    cut flat at r above the centre: a short bridge instead of a point that would thin the wall to the side face."""
    t = G.teardrop(c, r, up=(1, 0))
    return [(min(x, c[0] + r), z) for x, z in t]


def catch_ys():
    """(y0, y1) of the catch legs and saddle, behind the rear leaf: its root fillet, 1 mm, the catch's fillet."""
    l1 = handle_frame()["link1"]
    y0 = l1 + 2 * P["leaf_r"] + 1.0
    return y0, y0 + P["leaf_t"]


def saddle_ys():
    """a8: (y0, y1) of the catch saddle. It is 9.5 thick in y (a7: 2.5, the legs' thickness), from 1.5 behind the link's
    rear end to the ground bar's end, so its x-span over the nut-driver line (which bends it across the layers: the
    cartridge prints inboard face down) carries a 600 N lean at about 14 MPa (point-load bound). Only its crown touches
    the piston."""
    return handle_frame()["link1"] + 1.5, catch_ys()[1] + P["leaf_r"] + 1.5


def ground_end():
    """y of the ground bar's rear end: the catch saddle's rear face (a8; a7: the catch's rear root fillet + 0.5)."""
    return saddle_ys()[1]


def saddle_cut():
    """a8 (a7 #2): the saddle's bore. Radius piston_d / 2 + catch_c only on an R catch_crown_r crown across y at the legs'
    mid-plane; catch_relief bigger either side of it. Every ring is the same teardrop (point +x', up in print), lofted
    along y as one closed solid."""
    X = HX
    r0, R, rel = P["piston_d"] / 2 + P["catch_c"], P["catch_crown_r"], P["catch_relief"]
    s0, s1 = saddle_ys()
    yc = sum(catch_ys()) / 2
    dmax = math.sqrt(R * R - (R - rel) ** 2)                # crown half width where it meets the relief
    prof = [(s0 - 3.0, rel)]
    for k in range(-8, 9):
        dy = dmax * k / 8
        prof.append((yc + dy, R - math.sqrt(max(R * R - dy * dy, 0.0))))
    prof.append((s1 + 3.0, rel))
    unit = G.teardrop((0.0, 0.0), 1.0, up=(1, 0), n=96)
    bm = bmesh.new()
    rings = [[bm.verts.new((X + (r0 + e) * u, y, (r0 + e) * v)) for u, v in unit] for y, e in prof]
    for a, b in zip(rings, rings[1:]):
        for i in range(len(a)):
            j = (i + 1) % len(a)
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return G._obj("catch saddle cut", bm)


def stud_slot(name, y0, y1, half=2.75):
    """a7: the cell goes in from the inboard side, sliding up-inboard to down-outboard at 45 deg along this slot, with
    both studs in it (a6: round stud holes either side of a 14.7 mm gap, so the cell could not be fitted at all). The
    slot runs from the stud axis out through the inboard face above the stop screws; the printed washers bridge it."""
    F = handle_frame()
    X, cz = HX, F["cz"]
    o = half / math.sqrt(2)
    # a8 (a7 review #1, blocker): the far end runs past the inboard face by the slot's own half width plus 1 mm, in x and
    # in z (a7 used (cart_hw + 8) / sqrt 2 = 19.8 for both, so the slot ended 0.2 inside the face, under a wedge of
    # material, and the cell could not be fitted). d is the end's offset along each axis, not along the slot.
    d = P["cart_hw"] + half + 1.0
    pts = [(X + o, cz + o), (X - o, cz - o), (X - o - d, cz - o + d), (X + o - d, cz + o + d)]
    return G.prism(name, pts, y0, y1, "Y")


def strip_xs():
    """x ranges of a leaf's two strips (right cartridge)."""
    X, w, g = HX, P["cart_hw"], P["leaf_gap"]
    return [(X + g, X + w), (X - w, X - g)]


def cartridge_link_raw(check=False):
    """Moving body of the right cartridge, before holes: top link (socket, piston) on the grip axis, the drop that
    reaches down to the cell axis with the rear seat boss, the strip leaves above the ground bar and their top-root
    fillets. check=True: the check-only copy, whose leaves start CHECK_SPLIT above the ground bar so it clears the fixed
    body's leaf stubs (PRT_movlink_* / PRT_cartfix_*)."""
    F = handle_frame()
    X, w = HX, P["cart_hw"]
    cr, l0, l1, d1, cz = F["cell_rear"], F["link0"], F["link1"], F["drop1"], F["cz"]
    g1 = P["ground_z"][1]
    lh, ch, r = P["link_h"], P["link_ch"], P["leaf_r"]
    oc = [(X + a, b) for a, b in octagon(w, lh, ch)]
    parts = [G.prism("top link", oc, l0, l1, "Y"),
             G.box("drop", X - w, X + w, l0, d1, g1 + P["cav"], -lh + ch),
             G.cyl("rear seat boss", (X, cz), P["seat_d"] / 2, cr, l0 + 0.2, "Y", n=72),
             G.prism("drop root fillet", fillet2d(d1, -lh, 1, -1, r), X - w, X + w, "X")]
    (f0, f1), (r0, r1) = leaf_ys()
    z0 = g1 + (CHECK_SPLIT if check else LEAF_SPLIT)
    for (y0, y1), faces in (((f0, f1), ((f0, -1), (f1, 1))), ((r0, r1), ((r0, -1),))):
        # the link's underside is made flat across the leaf (its 45 deg chamfers filled), so every strip has the same
        # 27 mm free length and a filleted root
        ys = (y0 - r - 0.1 if len(faces) == 2 else y0 - r - 0.1, y1 + (r + 0.1 if len(faces) == 2 else 0))
        parts.append(G.box("top root slab", X - w, X + w, ys[0], ys[1], -lh - 0.01, -lh + ch + 1))
        for xa, xb in strip_xs():
            parts.append(G.box("leaf strip", xa, xb, y0, y1, z0, -lh + 0.5))
            for yc, sy in faces:
                parts.append(G.prism("top root fillet", fillet2d(yc, -lh, sy, -1, r), xa, xb, "X"))
    return G.csg(parts[0], add=parts[1:])


def cartridge_link_holes():
    """Holes in the moving body: rear stud and its slot, rear washer + nut bore (open at the back, on the cell axis, so
    the 8 mm nut-driver reaches it between the leaf strips), piston socket, piston screws, and for each stop screw its
    clearance and its nut slot. The push screws (z = stop_zp) go in sideways with their nuts on (their heads sit in the
    block), so their channel and nut slot open to the drop's side face; the pull nuts slide in from the side and the
    pull screws thread into them from the front. Every hole along Y is a teardrop pointing +x' (up in print: the
    cartridge prints inboard face down)."""
    F = handle_frame()
    X, w = HX, P["cart_hw"]
    cr, l0, l1, cz = F["cell_rear"], F["link0"], F["link1"], F["cz"]
    sx, zp, zq = P["stop_x"], P["stop_zp"], P["stop_zq"]
    st = stop_layout()
    sock = G.prism("socket", G.teardrop((X, 0), P["piston_d"] / 2 + 0.15, up=(1, 0), n=48), F["sock0"], l1 + 1, "Y")
    sock = G.csg(sock, inter=[G.box("socket D", X - P["shaft_flat"] - 0.1, X + 13, F["sock0"] - 1, l1 + 2, -20, 20)])
    k = [G.cyl("rear stud hole", (X, cz), 2.75, cr - 1, F["wall1"] + 0.5, "Y"),
         stud_slot("rear stud slot", cr - 1, F["drop1"] + 0.5),
         G.prism("nut bore", G.teardrop((X, cz), 7.0, up=(1, 0)), F["wall1"], F["drop1"] + 0.5, "Y"),
         # the rear washer and nut ride in on the rear stud with the cell: behind the wall the slot is Ø14 wide
         stud_slot("rear nut channel", F["wall1"], F["drop1"] + 0.5, half=7.2),
         sock]
    gmax = P["stop_gap_max"] - P["stop_gap"]                # screws sit up to this much further in at the largest setting
    hn = NUT3_AF / 2 / math.cos(math.pi / 6)                # nuts sit corners up and down (cadlib's nut frame); the
                                                            # inner half of the hex pocket stops them turning
    for s in (1, -1):
        xs = X + s * sx
        side = sorted((xs, X + s * (w + 1)))
        # push: shank channel from the drop's front face past the tip, open to the side face
        y0, y1 = l0 - 0.2, st["tip_p"] + gmax + 0.6
        k += [G.prism("push channel", G.teardrop((xs, zp), 1.7, up=(1, 0)), y0, y1, "Y"),
              G.box("push channel side", side[0], side[1], y0, y1, zp - 1.7, zp + 1.7),
              G.prism("push nut slot", G.hexagon((xs, zp), NUT3_AF, math.pi / 2), st["nut_p0"] - 0.1, st["nut_p1"] + 0.1, "Y"),
              G.box("push nut slot side", side[0], side[1], st["nut_p0"] - 0.1, st["nut_p1"] + 0.1, zp - hn, zp + hn)]
        # pull: clearance hole from the front face past the tip; nut slot open to the side
        y1 = st["tip_q"] + gmax + 0.6
        k += [G.prism("pull hole", td_cap((xs, zq), 1.7), y0, y1, "Y"),
              G.prism("pull nut slot", G.hexagon((xs, zq), NUT3_AF, math.pi / 2), st["nut_q0"] - 0.1, st["nut_q1"] + 0.1, "Y"),
              G.box("pull nut slot side", side[0], side[1], st["nut_q0"] - 0.1, st["nut_q1"] + 0.1, zq - hn, zq + hn)]
    for y, z in piston_screws():
        k += [G.cyl("piston pilot", (y, z), 1.25, X + 3, X + w + 1, "X"),
              G.cyl("piston screw cbore", (y, z), 3.25, X + w - 4.6, X + w + 1, "X")]   # a7: 2 mm deeper (link 2 wider)
    return k


def cartridge_fixed_raw(check=False):
    """Fixed body of the right cartridge, before holes: block with its front seat boss (on the cell axis), ground bar,
    the strips' feet and their bottom-root fillets."""
    F = handle_frame()
    X, w = HX, P["cart_hw"]
    yb, yp, cz = F["yb"], F["yp"], F["cz"]
    g0, g1 = P["ground_z"]
    r = P["leaf_r"]
    parts = [G.box("block", X - w, X + w, yp, yb, g0, 11),
             G.cyl("front seat boss", (X, cz), P["seat_d"] / 2, yb - 0.2, F["ye"], "Y", n=72),
             G.box("ground bar", X - w, X + w, yp, ground_end(), g0, g1)]
    for y0, y1 in leaf_ys():
        for xa, xb in strip_xs():
            parts.append(G.box("leaf foot", xa, xb, y0, y1, g1 - 0.5, g1 + (CHECK_SPLIT - 0.3 if check else LEAF_SPLIT + 0.05)))
            for yc, sy in ((y0, -1), (y1, 1)):                   # bottom roots, both faces
                parts.append(G.prism("bottom root fillet", fillet2d(yc, g1, sy, 1, r), xa, xb, "X"))
    # a7 (a6 #5): the catch. Two legs (the strips' x ranges, so the nut-driver line between them stays open) from the
    # ground bar up to a saddle under the piston; the saddle's cut is the piston's circle + catch_c, teardrop-pointed
    # outboard (up in print), open above the axis so a lift goes to the barrel lip as before.
    c0, c1 = catch_ys()
    zc = P["catch_z"]
    s0, s1 = saddle_ys()
    parts.append(G.box("catch saddle", X - w, X + w, s0, s1, zc, 0.0))
    for xa, xb in strip_xs():
        parts.append(G.box("catch leg", xa, xb, c0, c1, g1 - 0.5, zc + 0.5))
        for yc, sy in ((c0, -1), (c1, 1)):
            parts.append(G.prism("catch root fillet", fillet2d(yc, g1, sy, 1, r), xa, xb, "X"))
            parts.append(G.prism("catch top fillet", fillet2d(yc, zc, sy, -1, r), xa, xb, "X"))
    return parts


def cartridge_fixed_holes():
    """Holes in the block: front stud and its slot, the front counterbore (Ø15 washer + M5 nut + 8 mm nut-driver), a
    1 mm relief in the ground bar under the cell, and for each stop pair: push key hole + push head counterbore (open to
    the side so the push screw goes in sideways), pull clearance hole + pull head counterbore."""
    F = handle_frame()
    X, w = HX, P["cart_hw"]
    ye, yb, yp, yf, cz = F["ye"], F["yb"], F["yp"], F["yf"], F["cz"]
    sx, zp, zq, sh = P["stop_x"], P["stop_zp"], P["stop_zq"], P["stop_hole"]
    g1 = P["ground_z"][1]
    st = stop_layout()
    rc = 3.25                                               # M3 cap head Ø5.5 + 0.5 radial
    k = [G.cyl("front stud hole", (X, cz), 2.75, yp - 1, ye + 1, "Y"),
         stud_slot("front stud slot", yp - 1, ye + 1),
         G.prism("front counterbore", G.teardrop((X, cz), P["nut_cb"] / 2, up=(1, 0)), yp - 1, yf, "Y"),
         G.box("cell relief", X - 13.7, X + 13.7, yb + 0.5, F["cell_rear"] + 0.5, g1 - 1.0, g1 + 0.1),
         saddle_cut()]
    for s in (1, -1):
        xs = X + s * sx
        side = sorted((xs, X + s * (w + 1)))
        k += [G.prism("push key hole", td_cap((xs, zp), 1.6), yp - 1, st["pf"] + 0.1, "Y"),
              G.prism("push head counterbore", G.teardrop((xs, zp), rc, up=(1, 0)), st["pf"], yb + 0.5, "Y"),
              G.box("push head slot", side[0], side[1], st["pf"], yb + 0.5, zp - rc, zp + rc),
              G.prism("pull hole", td_cap((xs, zq), sh / 2), yp - 1, yb + 1, "Y"),
              G.prism("pull head counterbore", G.teardrop((xs, zq), rc, up=(1, 0)), yp - 1, st["qf"], "Y"),
              G.box("pull head slot", side[0], side[1], yp - 1, st["qf"], zq - rc, zq + rc)]
    return k


def build_cartridge(M):
    """Right flexure cartridge (x' = x - HX), one printed part. Fixed: block with its seat boss (the front stud clamps
    the cell's front face to it on its own) + ground bar. Moving: top link with its seat boss (clamped to the cell's
    rear face by the rear nut; carries the piston socket and the four stop nuts) on two parallel leaves with root
    fillets. Stops: four M3 screws from the link's nuts to the block, push pair on the cell axis.
    Returns the part and check-only copies of its moving body (PRT_movlink_*) and fixed body (PRT_cartfix_*)."""
    fx = cartridge_fixed_raw()
    body = G.csg(fx[0], add=fx[1:] + [cartridge_link_raw()])
    body = G.csg(body, sub=cartridge_fixed_holes() + cartridge_link_holes())
    cart = adopt(body, "Cartridge R", M["printed"])
    link = G.csg(cartridge_link_raw(check=True), sub=cartridge_link_holes())
    link = adopt(link, "Movlink R", M["printed"], coll="Check only")
    link.hide_render = True
    fx = cartridge_fixed_raw(check=True)
    fixed = G.csg(G.csg(fx[0], add=fx[1:]), sub=cartridge_fixed_holes())
    fixed = adopt(fixed, "Cartfix R", M["printed"], coll="Check only")
    fixed.hide_render = True
    return cart, link, fixed


RJ_PAD = 5.0          # RJ45 pad height above the tray floor: the coupler's flange sits on it
RJ_FLANGE = 5.0       # coupler STL: flange 5 thick, long body 27 above it, short body 4 below it

BENCH_OFF = Vector((250.0, 0.0, 0.0))   # the bench tools sit 250 mm outboard of the right fin in the model


BENCH_UP_T = 14.0        # a5 #1: rear upright thickness (a5: 8, free-standing)
BENCH_TOP = 11.0         # top of the front wall, side walls and upright
BENCH_FILLET = 3.0       # R3 roots where the upright meets the side walls and the base
BENCH_JACK_L = 35.0      # a7: M5 x 35 jack screw (a6: M5 x 30): the plug's T-slot moved 2.9 forward for a 5.0 mm rear
                         # lip, and the stand-off behind the upright takes the jack nut + the mass hanger for the k check
BENCH_LIP_T = 5.0        # a6 review #1: the setting plug's T-slot rear lip (a6: 2.1)
HANGER_PARK_X = 30.0     # the hanger's parked offset from the jack axis (model only)
HANGER_T = 3.5           # a6 review #7: printed known-mass hanger, a keyhole tab on the jack screw under its head
CELL_50 = 50 * 9.81      # recommended cell (BOM): 50 kg full scale, N


def bench_layout():
    """Numbers for the stop-setting cradle (right-cartridge frame, before BENCH_OFF): the jack screw runs on the grip
    axis from behind the cradle's rear upright into the setting plug, so the cell is loaded exactly as the grip loads
    it (a4 #1: no jacking couple). Attempt 6 (a5 #1): the side walls run through to the upright, so the cradle is a
    closed frame (front wall, two side walls, upright, base) and the jack load goes round it in the layer plane."""
    F = handle_frame()
    yp, l1 = F["yp"], F["link1"]
    up0 = ground_end() + 4.5                                # rear upright: 1.5 behind the ground bar's end + the R3 root
    up1 = up0 + BENCH_UP_T
    plug1 = up0 - 2.0                                       # plug end (through the catch saddle), 2 mm in front of the upright
    tip = plug1 - BENCH_LIP_T - 4.9                         # jack screw tip = front face of its glued swivel nut (a7: the
                                                            # T-slot is 5.0 deep for the 4.7 nut, so the lip is BENCH_LIP_T)
    at = tip + BENCH_JACK_L                                 # M5 x 30 head underside, behind the upright
    nut0 = up0 + (BENCH_UP_T - 4.9) / 2                     # jack nut pocket in the middle of the upright
    return dict(fw0=yp - 12.0, fw1=yp - 0.1, up0=up0, up1=up1, up_t=BENCH_UP_T, plug0=F["sock0"], plug1=plug1,
                jack_tip=tip, jack_at=at, jack_L=BENCH_JACK_L, standoff=round(at - up1, 3), top=BENCH_TOP,
                base_z=(-57.0, P["ground_z"][0] - 0.1), wall_x=(P["cart_hw"] + 1.0, P["cart_hw"] + 7.0), root_r=BENCH_FILLET,
                nut_up=(nut0, nut0 + 4.9), jack_z=0.0,
                lip_y=F["yb"] + P["fit"] + 2.0, lip_z=-20.0, lip_t=BENCH_LIP_T,
                eye_y=yp - 12.0 - 7.0, eye_d=8.0, eye_top=12.0,      # a7: hang eye on the jack axis, in front of the front wall
                hanger_y=up1 + 0.05, hanger_t=HANGER_T)    # parked on the shank against the upright


def cradle_frame():
    """Cradle under the jack load at 1.2 x FS of the recommended 50 kg cell (a5 #1), E 2500 (the low end).
    The cradle prints base down, so every face of its frame is a stack of layers in the XY plane.
    1. Upright as a beam spanning x between the two side walls (clamped at the walls, load at mid-span), bending
       stress along x: in the layer plane. Conservative: only a band as tall as the upright is thick, under the
       open-top jack slot (the 44 mm of upright below the slot and the base are ignored).
    2. Share of the jack load the upright sends down to the base instead (a cantilever in z, the only path that
       loads layers across their bonds): stiffness split of the two paths, then that share's root stress.
    3. Frame: the jack and the block both act on the cell axis (z 0); the walls + base (a U section) carry it as
       tension along y plus a bending moment F x e (e = axis height above the section's centroid), in the layer plane.
    4. Jack tilt: the frame's bending turns the upright against the front wall (theta = M L / E I), plus the slope
       of the cantilever share at the jack.
    5. Jack stroke: frame stretch on the axis + upright beam deflection (bending + shear) + cell travel, against the
       head's stand-off behind the upright."""
    B = bench_layout()
    E, G_ = 2500.0, 2500.0 / 2.7
    Fj = 1.2 * CELL_50
    z0, z1 = B["base_z"]
    wx0, wx1 = B["wall_x"]
    t, top = B["up_t"], B["top"]
    span = 2 * wx0                                          # between the side walls' inner faces
    band = t
    Ib = band * t ** 3 / 12
    M_b = Fj * span / 8                                     # clamped-clamped, central load
    s_inlayer = M_b / (band * t ** 2 / 6)
    d_beam = Fj * span ** 3 / (192 * E * Ib) + Fj * span / (4 * 5 / 6 * G_ * band * t)
    h = B["jack_z"] - z1                                    # jack axis above the base top
    k_beam = 1 / (span ** 3 / (192 * E * Ib) + span / (4 * 5 / 6 * G_ * band * t))
    Iz = span * t ** 3 / 12
    k_cant = 3 * E * Iz / h ** 3
    share = k_cant / (k_cant + k_beam)
    s_across = share * Fj * h / (span * t ** 2 / 6)
    # U section of the frame: base (2 wx1 x base) + two walls (wx1 - wx0) x (top - z1)
    bw, bt = 2 * wx1, z1 - z0
    ww, wh = wx1 - wx0, top - z1
    A = bw * bt + 2 * ww * wh
    zc = (bw * bt * (z0 + z1) / 2 + 2 * ww * wh * (z1 + top) / 2) / A
    I = bw * bt ** 3 / 12 + bw * bt * ((z0 + z1) / 2 - zc) ** 2 + 2 * (ww * wh ** 3 / 12 + ww * wh * ((z1 + top) / 2 - zc) ** 2)
    e = B["jack_z"] - zc
    Lf = B["up0"] - B["fw1"]                                # length of the walls between the front wall and the upright
    s_frame = Fj / A + Fj * e * max(top - zc, zc - z0) / I
    theta_frame = Fj * e * Lf / (E * I)
    d_frame = Fj * Lf / (E * A) + Fj * e * e * Lf / (E * I)
    theta_cant = share * Fj * h ** 2 / (2 * E * Iz)
    tilt = math.degrees(theta_frame + theta_cant)
    stroke = d_frame + d_beam + P["stop_gap_max"]           # the largest stop setting the procedure allows
    return dict(cradle_jack_n=round(Fj, 1), cradle_up_inlayer_mpa=round(s_inlayer, 2), cradle_up_share=round(share, 4),
                cradle_up_across_mpa=round(s_across, 3), cradle_frame_mpa=round(s_frame, 3),
                cradle_frame_e=round(e, 2), cradle_jack_tilt_deg=round(tilt, 4), cradle_beam_defl=round(d_beam, 4),
                cradle_frame_defl=round(d_frame, 4), cradle_stroke=round(stroke, 4))


def build_bench(M):
    """Printed bench tools for setting the stops (a4 #8): the cradle and the setting plug, plus the M5 x 30 jack screw,
    its nut in the cradle's rear upright and the swivel nut glued on its tip. The cradle copies the fin's support of
    the block: a front wall it bears on (with holes for the 8 mm nut-driver and the 2.5 mm key) and lips behind it.
    The cartridge drops in from above; the plug goes into the socket like the piston (two M3 x 12 self-tappers) with
    the jack screw's swivel nut in its T-slot; the screw drops into the upright's slot with its nut. Turning the screw
    with a 4 mm key pushes or pulls the link on the cell axis."""
    F = handle_frame()
    B = bench_layout()
    X, w = HX, P["cart_hw"]
    z0, z1 = B["base_z"]
    wx0, wx1 = B["wall_x"]
    sx, zp, zq = P["stop_x"], P["stop_zp"], P["stop_zq"]
    yb = F["yb"]
    top, rr = B["top"], B["root_r"]
    parts = [G.box("base", X - wx1, X + wx1, B["fw0"], B["up1"], z0, z1),
             G.box("front wall", X - wx1, X + wx1, B["fw0"], B["fw1"], z0, top),
             G.box("rear upright", X - wx1, X + wx1, B["up0"], B["up1"], z0, top)]
    for s in (1, -1):
        # a5 #1: the side walls run through to the upright (a5: they stopped 42 mm short), so the cradle is a closed
        # frame and the upright spans between them in the layer plane
        xa = sorted((X + s * wx0, X + s * wx1))
        parts.append(G.box("side wall", xa[0], xa[1], B["fw0"], B["up1"], z0, top))
        # R3 root where the upright meets the side wall (vertical edge)
        parts.append(G.prism("upright-wall root", fillet2d(X + s * wx0, B["up0"], -s, -1, rr), z1 - 0.2, top, "Z"))
    # R3 root where the upright meets the base (it ends 1.5 behind the ground bar's end)
    parts.append(G.prism("upright-base root", fillet2d(B["up0"], z1, -1, 1, rr), X - wx0 - 0.2, X + wx0 + 0.2, "X"))
    # (the hole is open to the top: the cell's front stud tip sits 0.5 into it, and the cartridge drops in from above)
    # a7: the 8 mm nut-driver hole is on the cell axis; nothing pokes out of the block's front face now, so it is a plain
    # hole (a6: a slot open to the top for the stud tip)
    cz = F["cz"]
    holes = [G.prism("nut-driver hole", G.circle((X, cz), P["nut_cb"] / 2, 48), B["fw0"] - 1, B["fw1"] + 1, "Y")]
    # a7 (a6 review #7): hang eye on the jack axis, so the cradle hangs from a hook for the known-mass check and the cord,
    # the jack and the mass are on one vertical line. A plate from the base up, so it prints with no overhang.
    ey, er = B["eye_y"], B["eye_d"] / 2
    fw = B["fw0"]                                           # a lug on the front wall, above the nut-driver hole, 45 deg
    # underside, so it prints with no overhang, and it stays above the 8 mm nut-driver line on the cell axis
    lug = [(fw + 0.5, -18.5), (fw + 0.5, B["eye_top"]), (ey - 7.0, B["eye_top"]), (ey - 7.0, -18.5 + (fw - ey + 7.0))]
    parts.append(G.prism("hang lug", lug, X - 5.0, X + 5.0, "X"))
    holes.append(G.prism("hang eye", G.teardrop((ey, 0.0), er, up=(0, 1)), X - 6, X + 6, "X"))
    for s in (1, -1):
        holes.append(G.prism("key window", G.rrect(X + s * sx - 4.0, X + s * sx + 4.0, zq - 4.0, zp + 3.5, 3.9),
                             B["fw0"] - 1, B["fw1"] + 1, "Y"))
        xa = sorted((X + s * (wx0 - 1), X + s * (wx1 + 1)))
        # a7: the lead leaves the cell up-inboard (the left cartridge's toward the other wall), so both walls have a notch
        holes.append(G.box("lead notch", xa[0], xa[1], F["ye"] + 3.5 - 4.5, F["ye"] + 3.5 + 4.5, -13.0, top + 1))
        # lip screw: an M4 x 12 through each side wall into a nut in a pocket on the wall's inner face; its shank lies
        # behind the block (as the fin's lips do) and takes the pull when the jack pulls the link
        ly, lz = B["lip_y"], B["lip_z"]
        xw = sorted((X + s * (wx0 - 1), X + s * (wx1 + 1)))
        holes.append(G.prism("lip screw hole", G.teardrop((ly, lz), 2.25, up=(0, 1)), xw[0], xw[1], "X"))
        xn = sorted((X + s * (wx0 - 0.1), X + s * (wx0 + 3.4)))
        holes.append(G.prism("lip nut pocket", G.hexagon((ly, lz), 7.2, math.pi / 2), xn[0], xn[1], "X"))
    # rear upright: open-top slot for the screw and a hex pocket (flats vertical) for its nut
    holes += [G.box("jack slot", X - 2.9, X + 2.9, B["up0"] - 1, B["up1"] + 1, 0, 20),
              G.prism("jack hole", G.circle((X, 0), 2.9, 24), B["up0"] - 1, B["up1"] + 1, "Y"),
              G.prism("jack nut pocket", G.hexagon((X, 0), 8.1, math.pi / 2), B["nut_up"][0], B["nut_up"][1], "Y"),
              G.box("jack nut drop", X - 4.05, X + 4.05, B["nut_up"][0], B["nut_up"][1], 0, 20)]
    cradle = G.csg(G.csg(parts[0], add=parts[1:]), sub=holes)
    # setting plug: the piston's D-bar from the socket shoulder to 2 mm past the link, the same two pilots, and a
    # T-slot at its rear for the jack screw's swivel nut (open on +x', which is up in print and closed by the socket)
    r = P["piston_d"] / 2                                   # a8: the piston's Ø24 (socket and saddle)
    plug = G.cyl("plug", (X, 0), r, B["plug0"], B["plug1"], "Y", n=72)
    plug = G.csg(plug, inter=[G.box("D", X - P["shaft_flat"], X + r + 1, B["plug0"] - 1, B["plug1"] + 1, -r - 1, r + 1)])
    t0 = B["jack_tip"] - 0.1
    plug = G.csg(plug, sub=[G.cyl("pilot", (y, z), 1.25, X + 3, X + r + 1, "X") for y, z in piston_screws()] +
                 [G.prism("swivel pocket", G.circle((X, 0), 4.85, 32), t0, t0 + 5.0, "Y"),
                  G.box("swivel pocket open", X, X + r + 1, t0, t0 + 5.0, -4.85, 4.85),
                  G.prism("neck", G.circle((X, 0), 2.9, 24), t0 + 4.9, B["plug1"] + 1, "Y"),
                  G.box("neck open", X, X + r + 1, t0 + 4.9, B["plug1"] + 1, -2.9, 2.9)])
    out = []
    for ob, nm in ((cradle, "Cradle"), (plug, "Setting plug")):
        ob = adopt(ob, nm, M["light"] if nm == "Cradle" else M["printed"], coll="Bench")
        ob.data.transform(Matrix.Translation(BENCH_OFF))
        out.append(ob)
    o = BENCH_OFF
    screw("Jack screw", (X + o.x, B["jack_at"], 0), (0, -1, 0), B["jack_L"], "M5_cap", M, step="bench")
    nut("Jack nut", (X + o.x, B["nut_up"][1], 0), (0, -1, 0), "M5", M, u=(0, 0, 1))
    nut("Jack swivel nut", (X + o.x, B["jack_tip"] + 4.7, 0), (0, -1, 0), "M5", M, label="M5 hex nut (glued on the jack screw tip)")
    # a7 (a6 review #7): known-mass hanger, a stirrup on the jack screw: a keyhole tab slides onto the shank under the
    # jack nut (run up to the head), two arms pass either side of the nut and the head, and a cross bar behind the head
    # takes the cord in a notch on the jack axis, so with the cradle hung from its eye the mass pulls on the axis.
    hy, ht_ = B["hanger_y"], B["hanger_t"]
    a0, a1 = hy + ht_, hy + ht_ + 13.0                      # arms clear the nut (4.7) and the head (5.0)
    tab = G.box("hanger tab", X - 10, X + 10, hy, a0, -6.0, 6.0)
    tab = G.csg(tab, add=[G.box("arm", X + 5.6, X + 8.6, a0 - 0.2, a1 + 0.2, -6.0, 6.0),
                          G.box("arm", X - 8.6, X - 5.6, a0 - 0.2, a1 + 0.2, -6.0, 6.0),
                          G.box("cross bar", X - 8.6, X + 8.6, a1, a1 + 6.0, -6.0, 6.0)],
                sub=[G.box("keyhole", X - 2.8, X + 2.8, hy - 1, a0 + 1, 0.0, 7.0),
                     G.cyl("keyhole round", (X, 0.0), 2.8, hy - 1, a0 + 1, "Y", n=32),
                     G.prism("cord notch", [(X - 3.0, a1 + 6.1), (X + 3.0, a1 + 6.1), (X, a1 + 3.0)], -7.0, 7.0, "Z")])
    hanger = adopt(tab, "Mass hanger", M["printed"], coll="Bench")
    # parked against the upright's rear face beside the jack while the stops are set (it blocks the 4 mm key when on the
    # jack); it goes on the jack only for the known-mass check
    hanger.data.transform(Matrix.Translation(BENCH_OFF + Vector((HANGER_PARK_X, 0.0, 0.0))))
    out.append(hanger)
    for s, nm in ((1, "a"), (-1, "b")):
        xo = X + o.x + s * wx1
        screw(f"Jack lip screw {nm}", (xo, B["lip_y"], B["lip_z"]), (-s, 0, 0), 12, "M4_cap", M, step="bench")
        nut(f"Jack lip nut {nm}", (X + o.x + s * (wx0 + 3.2), B["lip_y"], B["lip_z"]), (-s, 0, 0), "M4", M, u=(0, 0, 1))
    for ob in bpy.data.objects:
        if ob.name.startswith("Jack ") and ob.type == "MESH":
            for c in list(ob.users_collection):
                c.objects.unlink(ob)
            collection("Bench").objects.link(ob)
    return out


# a7 (a6 #2): SparkFun Qwiic Scale (NAU7802, SEN-15242), chosen because nothing on it needs an iron or a blade: the cell's
# four wires go into a push-to-open spring terminal, and the logic side is a Qwiic (JST SH) socket taking a ready-made
# Qwiic-to-female-socket cable to the ESP32's header. (a6: Adafruit HX711 5974, whose 0.1 in logic header ships loose.)
# Four Ø3.3 holes on a 17.8 x 25.4 mm pattern (measured by Alex, 2026-10-27), so it takes the kit's M3 x 10
# self-tappers. Board outline assumed as the pattern + 2.54 mm each side. Local frame: x across (0..AMP_W), spring
# terminal on the x = 0 edge, Qwiic sockets on the x = AMP_W edge; y along (0..AMP_L); components up.
AMP_W, AMP_L = 17.8 + 5.08, 25.4 + 5.08
AMP_HOLES = ((2.54, 2.54), (2.54, 27.94), (20.34, 2.54), (20.34, 27.94))
AMP_STANDOFF = 6.0
AMP_PAD_D = 10.0       # a8: drill-to-fit pads under the amps (no printed pilot)
AMP_X = 100.0          # |x| of the amp's centre (terminal outboard, under the lead's drop)


def amp_board(name, m, M):
    """Stand-in for the Qwiic Scale: board, spring terminal, NAU7802 and the two Qwiic sockets, placed by matrix m."""
    pcb = G.box("pcb", 0, AMP_W, 0, AMP_L, 0, 1.6)
    pcb = G.csg(pcb, sub=[G.cyl("hole", h, 1.65, -1, 3, "Z", n=24) for h in AMP_HOLES])
    term = G.box("spring terminal", 0.0, 8.0, AMP_L / 2 - 8.0, AMP_L / 2 + 8.0, 1.6, 11.0)
    chip = G.box("chip", AMP_W / 2 - 2.5, AMP_W / 2 + 2.5, AMP_L / 2 - 2.5, AMP_L / 2 + 2.5, 1.6, 2.6)
    q1 = G.box("qwiic a", AMP_W - 4.3, AMP_W, 5.0, 11.0, 1.6, 4.5)
    q2 = G.box("qwiic b", AMP_W - 4.3, AMP_W, AMP_L - 11.0, AMP_L - 5.0, 1.6, 4.5)
    ob = G.csg(pcb, add=[term, chip, q1, q2])
    ob = adopt(ob, name, M["pcb_red"], coll="Electronics")
    ob.data.transform(m)
    return ob


def piston_screws():
    """(y, z) of the two M3 self-tappers from the top link's +x face into the piston plug."""
    F = handle_frame()
    return [(F["sock0"] + 7, 3.5), (F["sock0"] + 27, -3.5)]


def build_piston(M):
    """Right piston: one D-bar Ø22.2 (flat on the inboard side, the print bed), plug in the cartridge
    socket from sock0, grip spigot to the end."""
    F = handle_frame()
    X, r, rp, ys = HX, P["shaft_d"] / 2, P["piston_d"] / 2, P["piston_step"]
    p1 = F["lip"] + P["piston_show"]
    y1 = p1 + P["spigot_length"]
    # a8 (a7 #6): Ø24 in the socket and past the catch, a 45 deg step down to the Ø22.2 spigot ahead of the barrel lip
    bar = G.csg(G.cyl("piston", (X, 0), rp, F["sock0"], ys - (rp - r), "Y", n=72),
                add=[G.cone("piston step", (X, 0), rp, r, ys - (rp - r) - 0.01, ys, "Y", n=72),
                     G.cyl("spigot", (X, 0), r, ys - 0.01, y1, "Y", n=72)])
    bar = G.csg(bar, inter=[G.box("D", X - P["shaft_flat"], X + rp + 1, F["sock0"] - 1, y1 + 1, -rp - 1, rp + 1)])
    bar = G.csg(bar, sub=[G.cyl("pilot", (y, z), 1.25, X + 3, X + rp + 1, "X") for y, z in piston_screws()])
    return adopt(bar, "Piston R", M["printed"])


def build_fin(M):
    """Right fin as two printed halves (-X = inboard, +X = outboard), plus its head hardware.

    Load path: grip -> piston (D-bar) -> socket shoulder (push) / two M3 (pull) -> cartridge top link ->
    rear M5 nut + cell rear face -> cell -> front stud + front nut -> cartridge block -> fin front wall (push) or the
    fin lips behind the block (pull) -> fin -> three M4s -> tray end wall -> six M5s -> chair plate. Bending and
    side load: top link -> two parallel leaves -> ground bar -> fin pocket; a lean past ~200 N puts the piston on the
    barrel lip (lip_c). Overload: top link -> four M3 stop screws -> block.
    """
    F = handle_frame()
    x, az, ye, cr, lip = HX, F["az"], F["ye"], F["cell_rear"], F["lip"]
    ht = P["fin_t"] / 2
    bd = P["barrel_d"]
    w, c, f = P["cart_hw"], P["cav"], P["fit"]
    g0, g1 = P["ground_z"]

    R = P["R_out"]
    sources = [prism("fin plate", fin_profile(), "X", x - ht, x + ht, coll="Part sources"),
               cylinder("barrel", (x, 30, az), (x, lip, az), bd, coll="Part sources"),
               # the bridge section carried 6 mm past the inboard face: the opening pass rounds its far edges, and the
               # exact cut at the inboard face (head_cuts) then leaves the fin's edges sharp wherever the tray and
               # cover continue them, so fin, tray and cover read as one body with one hairline (a3 #8)
               prism("bridge stub", round_corners(section_pts(z_bridge()), [R, R, R, 0, 0, R], segs=10), "X",
                     x - ht - 6, x - ht + 1, coll="Part sources")]

    cuts = []
    _, lead = lead_path(1)
    cuts.append(tube("lead channel", lead, P["channel_d"], coll="Part sources"))

    def skin_cuts(half):
        """Exact cutters for the outer skin of one half: the inboard face flat and sharp (inboard half), the split
        V reveal on each half's bed edge, and the recessed panel on the outboard face (outboard half)."""
        O = list(reversed(fin_profile()))                       # CCW outline at the split plane
        d, h = P["reveal"]
        hh = h + 0.3                                            # loft runs 0.3 past the reveal's edge (0.24 outside the skin)
        big = (-60, 260, -200, 100)
        k = []
        if half == "inboard":
            k.append(G.box("inboard face", x - ht - 20, x - ht, *big))
            v = G.box("reveal -", x - hh, x, *big)
            keep = G.loft("reveal keep -", G.offset_convex(O, -d + d * hh / h), G.offset_convex(O, -d), x - hh, x, "X")
        else:
            v = G.box("reveal +", x, x + hh, *big)
            keep = G.loft("reveal keep +", G.offset_convex(O, -d), G.offset_convex(O, -d + d * hh / h), x, x + hh, "X")
        k.append(G.csg(v, sub=[keep]))
        if half == "outboard":
            pi = round_corners(G.offset_convex(list(reversed(section_pts(z_fin()))), -P["panel_inset"]),
                               P["R_out"], segs=10)
            dp = P["panel_depth"]
            k.append(G.loft("panel rim", pi, G.offset_convex(pi, 2.0), x + ht - 1.0, x + ht + 1.0, "X"))
            k.append(G.prism("panel", pi, x + ht - dp, x + ht - 0.99, "X"))
        for o in k:                                             # same frame as the halves (mm under the scaled root)
            o.parent = ROOT
        return k

    def head_cuts():
        """Exact (Manifold) cutters for the head, applied to each half after the SDF pass: the cartridge's
        0.1 mm pocket fits and 1 mm running gaps must not move with the voxel grid."""
        k = []
        # cell (a7: on its own axis cz, below the grip axis), its wire boss (clocked up-inboard at 45 deg) and the lead's
        # first straight
        cz = F["cz"]
        k.append(teardrop_x("cell pocket", x, cz, 26.2, F["yb"] - 0.1, cr + 0.5))
        dv, nv = Vector((-math.sin(LEAD_DIR), math.cos(LEAD_DIR))), Vector((math.cos(LEAD_DIR), math.sin(LEAD_DIR)))
        bp = [Vector((x, cz)) + dv * a + nv * b for a, b in ((11.0, 3.3), (11.0, -3.3), (21.5, -3.3), (21.5, 3.3))]
        # swept outboard to the split plane, so the head lifts out of the inboard half along x (slide row)
        hull = [tuple(bp[2]), tuple(bp[3]), (x + 0.5, bp[3].y), (x + 0.5, bp[1].y), tuple(bp[1])]
        k.append(prism("boss pocket", hull, "Y", ye + 0.2, ye + 6.8))
        # cartridge pockets: fixed parts at `fit`, moving parts (top link, leaves, stop screws) at `cav`
        lh, ch = P["link_h"], P["link_ch"]
        oc = [(x + a, b) for a, b in octagon(w + c, lh + c, ch + c * (math.sqrt(2) - 1))]
        k.append(prism("top link cavity", oc, "Y", F["link0"] - c, F["link1"] + c))
        # a7: the drop that carries the cell's rear face, down to the ground pocket
        k.append(box("drop cavity", (x - w - c, F["link0"] - c, g1), (x + w + c, F["drop1"] + c, -lh + ch)))
        # the stop screws cross the gap between the block and the link beside the cell: a slot `cav` round them
        zp, zq = P["stop_zp"], P["stop_zq"]
        k.append(box("stop screw flank", (x - w - c, F["yb"] - 0.1, zq - 1.5 - c), (x + w + c, F["link0"] - c + 0.1, zp + 3.25 + 0.5)))
        # leaf slots (room for the root fillets); no other pocket under the link now the a4 stop post is gone
        rr = P["leaf_r"]
        for y0, y1 in leaf_ys():
            k.append(box("leaf slot", (x - w - c, y0 - c - rr, g1 - 1), (x + w + c, y1 + c + rr, -lh + ch)))
        k.append(box("ground pocket", (x - w - f, F["yp"] - f, g0 - f), (x + w + f, ground_end() + f, g1 + f)))
        s0, s1 = saddle_ys()                                    # a7: the catch's legs and saddle move a little in y
        k.append(box("catch slot", (x - w - c, s0 - c, g1 - 1), (x + w + c, s1 + c, c)))
        # the block: its front face bears on the fin's solid front wall, its rear face on the fin behind it (pull)
        k.append(box("block pocket", (x - w - f, F["yp"] - f, g0 - f), (x + w + f, F["yb"] + f, 11 + f)))
        # piston shaft: teardrop bore, round for the last 4 mm so the lip shows a plain circle
        sb = P["piston_d"] + 2 * P["lip_c"] + 0.2               # a8: round the Ø24 piston, wider than the lip
        k.append(teardrop_x("shaft bore", x, az, sb, F["link1"], lip - 4))
        # the lip is the moment stop (a4 #2): lip_c radial round the piston, so a heavy lean puts the piston on the
        # barrel lip long before the rear leaf could buckle (cad/calc/head_calc.py)
        k.append(cylinder("shaft bore lip", (x, lip - 4.5, az), (x, lip + 1, az), P["shaft_d"] + 2 * P["lip_c"], coll="Part sources"))
        return k

    # Clamshell: M3 self-tappers from the inboard face (hidden against the tray) into pilots in the outboard half.
    for i, (y, z, hw) in enumerate(clamshell_bolts()):
        cuts.append(cylinder(f"m3 hole {i}", (x - hw - 1, y, z), (x + 0.5, y, z), M3["hole"], coll="Part sources"))
        # a8: Ø7.0 on this hidden face (M3["cbore"] 6.5 elsewhere): the voxel-cut bore kept only 0.25 radial round the
        # Ø6 pan head, and the full-resolution check read one head as buried
        cuts.append(cylinder(f"m3 cbore {i}", (x - hw - 1, y, z), (x - hw + 3.5, y, z), M3["cbore"] + 0.5, coll="Part sources"))
        cuts.append(cylinder(f"m3 pilot {i}", (x, y, z), (x + 10, y, z), M3["pilot"], coll="Part sources"))
    # Bridge bolts: M4 from inside the bridge through its end wall into nuts dropped into slots
    # that open on the split plane.
    for i, (y, z) in enumerate(box_bolts()):
        cuts.append(cylinder(f"m4 hole {i}", (x - ht - 1, y, z), (x - ht + 10.5, y, z), M4["hole"], coll="Part sources"))
        cuts.append(box(f"m4 nut slot {i}", (x - ht + 6, y - 3.7, z - 3.7), (x + 0.5, y + 3.7, z + 3.7)))

    inboard, outboard = sdf_part("Fin R", sources, M["printed"], fillet_r=P["fillet_r"],
                                 open_r=P["open_r"], subtract=cuts, split_x=x)
    inboard.name, outboard.name = "Fin R inboard half", "Fin R outboard half"
    for half, which in ((inboard, "inboard"), (outboard, "outboard")):
        G.csg(half, sub=head_cuts() + skin_cuts(which))
        half.data.materials.clear()                              # cut faces come in with no material (default grey)
        half.data.materials.append(M["printed"])
        for poly in half.data.polygons:                          # SDF skin stays smooth; exact cuts get crisp edges
            poly.use_smooth = True
            poly.material_index = 0
        half.data.set_sharp_from_angle(angle=math.radians(30))

    cart, movlink, cartfix = build_cartridge(M)
    piston = build_piston(M)
    p1 = lip + P["piston_show"]
    grip = import_stl("MTB grip R", "mtb_grip.stl", Matrix.Translation((x, p1, az)) @ rot("Z", 90), M["rubber"], coll="Hardware")
    cz = F["cz"]                                               # a7: the cell axis, at the leaves' mid-height
    cell = import_stl("Load cell R", "load_cell.stl", Matrix.Translation((x, ye + 6.35, cz)) @ rot("Y", -math.degrees(LEAD_DIR)),
                      M["steel"], coll="Hardware")                 # wire boss up-inboard (STL: boss on +z)
    # printed washers under both cell nuts (a3 #4, #6): the front one sits in the block's counterbore
    (dwf, twf), (dwr, twr) = P["washer_f"], P["washer_r"]
    yf, w1 = F["yf"], F["wall1"]
    wf = adopt(G.csg(G.cyl("front washer", (x, cz), dwf / 2, yf - twf, yf, "Y", n=72),
                     sub=[G.cyl("hole", (x, cz), 2.75, yf - twf - 1, yf + 1, "Y")]), "Washer front R", M["printed"])
    wr = adopt(G.csg(G.cyl("rear washer", (x, cz), dwr / 2, w1, w1 + twr, "Y", n=72),
                     sub=[G.cyl("hole", (x, cz), 2.75, w1 - 1, w1 + twr + 1, "Y")]), "Washer rear R", M["printed"])
    nh = NUTS["M5"][1]                                         # ISO 4032 M5: 8 AF, 4.7 thick
    fn = hex_prism("Front nut R", (x, 0, cz), "Y", 8.0, yf - twf - nh, yf - twf, mat=M["steel"], coll="Hardware")
    rn = hex_prism("Rear nut R", (x, 0, cz), "Y", 8.0, w1 + twr, w1 + twr + nh, mat=M["steel"], coll="Hardware")
    return dict(inboard=inboard, outboard=outboard, piston=piston, cartridge=cart, movlink=movlink, cartfix=cartfix,
                washers=[wf, wr], other=[grip, cell, fn, rn], cell=cell)

# ------------------------------------------------------------------ bridge: tray and cover

def build_tray_half(sign, M, electronics=None):
    """Bridge half from x = 0 to the fin's inner face: open-top tray, front land bolted to the
    plate with two M5s, a foot with one more M5 by the floor, floor carrying the boards."""
    F = handle_frame()
    w, tz, zb, L = P["wall"], tray_top(), z_bridge(), P["lip_y"]
    ex = F["box_end"]
    x0, x1 = sorted((0, sign * ex))
    side = "L" if sign < 0 else "R"

    outer = section_pts(zb, tz)
    R, Ri, EB = P["R_out"], P["R_in"], P["EB"]
    outer = chamfer_corners(outer, {4: R})                      # front bottom edge prints on the bed: 45 deg chamfer, not R6
    src = [prism("bridge", round_corners(outer, [EB / 2, 0.01, R, 0, 0, 0, R], segs=10), "X", x0, x1, coll="Part sources")]
    xi0, xi1 = sorted((0, sign * (ex - w)))
    cav = inset(section_pts(zb, tz + 30), [0, w, w, w, w, w])
    hollow = [prism("bay", round_corners(cav, [0, Ri, Ri, R - w, R - w, Ri], segs=8), "X", xi0, xi1, coll="Part sources")]
    cut, add = [], []

    # Lead from the fin enters through the end wall.
    t_lead, _ = lead_path(sign)
    cut.append(cylinder("lead hole", (sign * (ex - w - 1), t_lead.p.y, t_lead.p.z), (sign * (ex + 1), t_lead.p.y, t_lead.p.z),
                        P["channel_d"] + 1, coll="Part sources"))
    # Fin bolts: M4 caps in counterbores from inside, through the end wall into nuts in the fin.
    for y, z in box_bolts():
        cut.append(cylinder("fin bolt hole", (sign * (ex - w - 8), y, z), (sign * (ex + 1), y, z), M4["hole"], coll="Part sources"))
        cut.append(cylinder("fin bolt cbore", (sign * (ex - w - 9), y, z), (sign * (ex - w - 4), y, z), M4["cbore"], coll="Part sources"))
        xi, xo = sign * (ex - w - 8), sign * (ex - w + 0.5)                      # 45 deg underside to the wall
        add.append(prism("fin bolt boss", [(xo, z + 7), (xi, z + 7), (xi, z - 7), (xo, z - 7 - 8.5)], "Y", y - 7, y + 7,
                         coll="Part sources"))
    # M5 caps from inside into drop-in T-nuts: upper row through land bosses that run up to the
    # cover (the front cover screws bite into their tops), lower row through feet across the bevel gap.
    u_cover = tz / math.cos(TILT)
    for x, u, nh, _ in mount_bolts():
        if x * sign <= 0:
            continue
        if u > 0:                                    # land boss with a 45 deg gusset down to the wall
            F_, R_ = on_plate(u - 11, 0.05), on_plate(u - 11, nh)
            knee = on_plate(U_TOP - P["land"], 0)
            t = R_[0] - (knee[0] + 1.0)
            # flat top at the cover so the front cover screws get full thread, stepping back at 45 deg to the
            # head's bearing plane above the M5 head
            B, C = on_plate(u_cover, nh), on_plate(u + 5, nh)
            prof = [on_plate(u_cover, 0.05), (B[0] + 3, tz), (B[0] + 3, C[1] + 1.2 * (B[0] + 3 - C[0])), C, R_,
                    (knee[0] + 1.0, R_[1] - t), (knee[0] + 1.0, knee[1]), F_]
            add.append(prism("land boss", prof, "X", x - 11, x + 11, coll="Part sources"))
        else:                                        # foot down to the floor, counterbored for the head
            y_top = on_plate(u + 11, 0)[0]
            z_top = on_plate(u + 11, 0)[1]
            y_r = on_plate(u, nh)[0] + 6
            prof = [(on_plate(zb / math.cos(TILT), 0)[0] + 0.05, zb), (y_r, zb), (y_r, z_top + 4), (y_top + 0.05, z_top)]
            add.append(prism("foot", prof, "X", x - 11, x + 11, coll="Part sources"))
            cut.append(plate_cyl("m5 cbore", x, u, nh, nh + 7, M5["cbore"], coll="Part sources"))
            # bit access along the bolt axis: it runs rearward and down, so it leaves through the floor
            cut.append(plate_cyl("m5 bit access", x, u, nh + 6, nh + 70, 14.0, coll="Part sources"))
        cut.append(plate_cyl("m5 hole", x, u, -1, nh + 1, M5["hole"], coll="Part sources"))
    # Cover screws: M3 self-tappers on a 2 x 2 grid at the mount x positions; front into the land
    # bosses, rear into bosses on the rear wall.
    for x, y_c, z_b in cover_screw_pts(sign):
        if y_c > L / 2:                              # rear boss with a 45 deg underside to the rear wall
            add.append(prism("cover boss", [(L - w + 0.5, tz), (L - w - 11, tz), (L - w - 11, tz - 10), (L - w + 0.5, tz - 21.5)],
                             "X", x - 5, x + 5, coll="Part sources"))
        cut.append(cylinder("cover pilot", (x, y_c, tz - 10), (x, y_c, tz + 1), M3["pilot"], coll="Part sources"))

    if electronics:
        fz = zb + w                                           # floor top
        for kind, holes, standoff in electronics["boards"]:
            for (hx_, hy_) in holes:
                if kind == "amp":
                    # a8 (a7 #8): the Qwiic Scale's hole pattern is from SparkFun's design files, not a board in hand, so
                    # its standoffs are drill-to-fit pads (cadlib features.drill_to_fit_boss): Ø10, solid, a centre dimple.
                    # Set the board on them and drill the Ø2.5 pilots through its holes; a hole up to 1.5 mm off still
                    # leaves 1.5 mm of wall round the pilot
                    add.append(cylinder("standoff", (hx_, hy_, fz - 0.5), (hx_, hy_, fz + standoff), AMP_PAD_D, coll="Part sources"))
                    cut.append(cone("standoff dimple", (hx_, hy_, fz + standoff - 1.0), (hx_, hy_, fz + standoff + 0.3), 0.2, 2.8,
                                    coll="Part sources"))
                else:
                    add.append(cylinder("standoff", (hx_, hy_, fz - 0.5), (hx_, hy_, fz + standoff), 6.5, coll="Part sources"))
                    cut.append(cylinder("standoff pilot", (hx_, hy_, fz - 1), (hx_, hy_, fz + standoff + 1), M3["pilot"], coll="Part sources"))
    if electronics and electronics["rj45"]:
        # a4 #7: the coupler sits on a 5 mm pad, flange on top (two M3 x 12 self-tappers from above), so its short
        # rear body stays inside the pad and the floor: nothing hangs below the tray. The PoE cable plugs in from
        # below through the square opening.
        fz = zb + w
        rx, ry_ = electronics["rj45"]
        pt = fz + RJ_PAD
        add.append(box("rj45 pad", (rx - 22, ry_ - 20, fz - 0.5), (rx + 22, ry_ + 18, pt)))
        cut.append(box("rj45 opening", (rx - 12.2, ry_ - 12.2, zb - 1), (rx + 12.2, ry_ + 12.2, pt + 1)))
        for dx in (-15.3, 15.3):
            cut.append(cylinder("rj45 pilot", (rx + dx, ry_, pt - 9.5), (rx + dx, ry_, pt + 1), M3["pilot"], coll="Part sources"))

    cut.append(box("below floor", (min(x0, x1) - 5, -100, zb - 60), (max(x0, x1) + 5, 300, zb)))
    tray = sdf_part(f"Tray {side}", src, M["printed"], fillet_r=1.0, hollow=hollow, add=add, subtract=cut)[0]
    # a4 #7: the centre seam is a deliberate V reveal like the fin's split (reveal depth into the skin, half width
    # each side), on every face of the section; exact cut after the SDF pass
    d, h = P["reveal"]
    hh = h + 0.3
    O = list(reversed(round_corners(outer, [EB / 2, 0.01, R, 0, 0, 0, R], segs=10)))      # CCW section outline
    big = (-60, 260, -200, 100)
    xa, xb = sorted((0.0, sign * hh))
    v = G.box("tray reveal", xa, xb, *big)
    inner, outer_ = G.offset_convex(O, -d), G.offset_convex(O, -d + d * hh / h)
    keep = G.loft("tray reveal keep", *((inner, outer_) if sign > 0 else (outer_, inner)), xa, xb, "X")
    k = G.csg(v, sub=[keep])
    k.parent = ROOT
    G.csg(tray, sub=[k])
    tray.data.materials.clear()
    tray.data.materials.append(M["printed"])
    for poly in tray.data.polygons:
        poly.use_smooth = True
        poly.material_index = 0
    tray.data.set_sharp_from_angle(angle=math.radians(30))
    return tray


def build_cover(M):
    """One cover across both trays (it is also the splice that joins the two halves at x = 0), flush with
    the fin tops, from 3 mm off the plate to the lip. Rear top edge R_out = cover_t, so it continues the
    fin's R6 lip edge."""
    F = handle_frame()
    tz, ct, L = tray_top(), P["cover_t"], P["lip_y"]
    ex = F["box_end"]
    prof = round_corners([(tz * math.tan(TILT) + 3, tz), (L, tz), (L, tz + ct), ((tz + ct) * math.tan(TILT) + 3, tz + ct)],
                         [P["EB"] / 2, 0, P["R_out"], P["EB"]], segs=8)
    src = [prism("cover plate", prof, "X", -ex + 0.3, ex - 0.3, coll="Part sources")]   # 0.3 shadow gap at each fin
    cover = sdf_part("Cover", src, M["light"], fillet_r=1.0)[0]
    # a8 (a7 #9): the screw holes are exact cuts after the SDF pass (a7: voxel-cut, so the counterbore rims were soft and
    # the heads read as black holes), with a 0.5 x 45 deg chamfer on each counterbore's rim
    cut = []
    ztop = tz + ct
    for sign in (-1, 1):
        for x, y_c, _ in cover_screw_pts(sign):
            cut += [G.cyl("cover hole", (x, y_c), M3["hole"] / 2, tz - 1, ztop + 1, "Z", n=32),
                    G.cyl("cover cbore", (x, y_c), M3["cbore"] / 2, ztop - 2.6, ztop + 1, "Z", n=48),
                    G.cone("cover cbore chamfer", (x, y_c), M3["cbore"] / 2 - 0.01, M3["cbore"] / 2 + 1.5, ztop - 0.5, ztop + 1.0, "Z", n=48)]
    for o in cut:
        o.parent = ROOT
    G.csg(cover, sub=cut)
    cover.data.materials.clear()
    cover.data.materials.append(M["light"])
    for poly in cover.data.polygons:
        poly.use_smooth = True
        poly.material_index = 0
    cover.data.set_sharp_from_angle(angle=math.radians(30))
    return cover


# ------------------------------------------------------------------ fasteners (for the assembly steps)

def join(name, objs, mat):
    """One mesh object from several (all modelled in mm under ROOT)."""
    bm = bmesh.new()
    for o in objs:
        bm.from_mesh(o.data)
        bpy.data.objects.remove(o)
    return bm_to_object(name, bm, mat, coll="Hardware")


HEADS = {"M3_selftap_pan": (3.0, 6.0, 2.4), "M3_cap": (3.0, 5.5, 3.0), "M4_cap": (4.0, 7.0, 4.0), "M5_cap": (5.0, 8.5, 5.0)}
NUTS = {"M3": (5.5, 2.4), "M4": (7.0, 3.2), "M5": (8.0, 4.7), "M5T": (8.0, 3.8)}   # M5T: 40-series drop-in T-nut


def screw(name, at, into, length, spec, M, host="", step=""):
    """Screw whose head bears at `at`, shank `length` along `into`. Tagged for cad check."""
    d, hd, hh = HEADS[spec]
    at, w = Vector(at), Vector(into).normalized()
    o = join(name, [cylinder(name + " h", at - w * hh, at, hd, segs=24, coll="Hardware"),
                    cylinder(name + " s", at - w * 0.1, at + w * length, d, segs=16, coll="Hardware")], M["screw"])
    # a8 (a7 #9): render-only drive recess on the head's top face (a Phillips cross on the pan self-tappers, a hex socket
    # on the caps), dark and 0.02 proud, so a head in its counterbore reads as a screw head and not as a hole. Not a
    # fastener for cad check (no cc_kind; to_cadcheck.py skips it).
    top = at - w * (hh + 0.02)
    q = w.to_track_quat("Z", "Y").to_matrix().to_4x4()
    bm = bmesh.new()
    if spec.endswith("pan"):
        for sx, sy in ((hd * 0.62, 0.7), (0.7, hd * 0.62)):
            bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation(top) @ q @ Matrix.Diagonal((sx, sy, 0.04, 1)))
    else:
        bmesh.ops.create_circle(bm, cap_ends=True, segments=6, radius={3.0: 1.44, 4.0: 1.73, 5.0: 2.31}[d],
                                matrix=Matrix.Translation(top) @ q)
    recess = bm_to_object(name + " recess", bm, M["gap"], coll="Render details", smooth_angle=0)
    recess["render_only"] = True
    o["cc_kind"], o["cc_spec"], o["cc_len"] = "screw", spec, float(length)
    o["cc_at"], o["cc_into"], o["cc_host"], o["cc_step"] = list(at), list(w), host, step
    return o


def nut(name, face, into, size, M, label=None, u=None):
    """Hex nut: bearing face at `face`, body along `into`, a corner toward `u` (default: any)."""
    af, h = NUTS[size]
    face, w = Vector(face), Vector(into).normalized()
    r = af / 2 / math.cos(math.pi / 6)
    u = Vector(u).normalized() if u else w.orthogonal().normalized()
    o = loft(name, [(face + w * t, u, w.cross(u),
                     [(r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)])
                    for t in (0, h)], M["steel"], coll="Hardware")
    o["cc_kind"], o["cc_size"], o["cc_at"], o["cc_into"], o["cc_h"] = "nut", size[:2], list(face), list(w), float(h)
    o["cc_label"] = label or f"{size} hex nut"
    return o


def build_fasteners(M, boards):
    """Every screw and nut at its installed position, named per side so the steps can move them."""
    F = handle_frame()
    ex, ht, w = F["box_end"], P["fin_t"] / 2, P["wall"]
    for sign, side in ((1, "R"), (-1, "L")):
        x = sign * HX
        for i, (y, z, _) in enumerate(clamshell_bolts()):           # self-tappers from the hidden inboard face
            screw(f"M3 screw {side}{i}", (x - sign * (ht - 3.5), y, z), (sign, 0, 0), 30, "M3_selftap_pan", M,
                  host=f"Fin {side} outboard half", step="close fin")
        cw = P["cart_hw"]
        st, sx = stop_layout(), P["stop_x"]                          # overload stops: two pairs either side of the cell
        for s_, o in ((1, "out"), (-1, "in")):
            xs = x + sign * s_ * sx
            screw(f"Stop screw push {side} {o}", (xs, st["at_p"], P["stop_zp"]), (0, 1, 0), st["Lp"], "M3_cap", M,
                  step="cartridge")
            nut(f"Stop nut push {side} {o}", (xs, st["nut_p0"], P["stop_zp"]), (0, 1, 0), "M3", M, u=(0, 0, 1))
            screw(f"Stop screw pull {side} {o}", (xs, st["at_q"], P["stop_zq"]), (0, 1, 0), st["Lq"], "M3_cap", M,
                  step="cartridge")
            nut(f"Stop nut pull {side} {o}", (xs, st["nut_q0"], P["stop_zq"]), (0, 1, 0), "M3", M, u=(0, 0, 1))
        for i, (y, z) in enumerate(piston_screws()):                 # piston plug held in the top link socket
            screw(f"Piston screw {side}{i}", (x + sign * (cw - 4.6), y, z), (-sign, 0, 0), 12, "M3_selftap_pan", M,
                  host=f"Piston {side}", step="piston")
        for i, (y, z) in enumerate(box_bolts()):                     # M4 cap from inside the tray into fin nuts
            screw(f"M4 screw {side}{i}", (sign * (ex - w - 4), y, z), (sign, 0, 0), 20, "M4_cap", M, step="fin to tray")
            nut(f"M4 nut {side}{i}", (sign * (ex + 6.4), y, z), (sign, 0, 0), "M4", M)
        for i, (cx, cy, z) in enumerate(cover_screw_pts(sign)):
            front = cy < P["lip_y"] / 2
            screw(f"Cover screw {side}{i}", (cx, cy, z), (0, 0, -1), 12 if front else 10,
                  "M3_selftap_pan", M, host=f"Tray {side}", step="cover")
    for i, (x, u, n0, ln) in enumerate(mount_bolts()):               # M5 cap + 4040 drop-in T-nut
        y0, z0 = on_plate(u, n0)
        screw(f"M5 bolt {i}", (x, y0, z0), (0, -math.cos(TILT), math.sin(TILT)), ln, "M5_cap", M, step="mount")
        y1, z1 = on_plate(u, -2.2)
        nut(f"T-nut {i}", (x, y1, z1), (0, -math.cos(TILT), math.sin(TILT)), "M5T", M, label="M5 drop-in T-nut, 40 series")
    for i, (bx, by, top, ln) in enumerate(boards):                   # boards: self-tappers into standoffs
        screw(f"Board screw {i}", (bx, by, top), (0, 0, -1), ln, "M3_selftap_pan", M,
              host="Tray L" if bx < 0 else "Tray R", step="electronics")


def cover_screw_pts(sign):
    """(x, y, z_bearing) of the cover's M3 self-tappers on side `sign`: 2 x 2 at the mount x."""
    w, tz, ct, L = P["wall"], tray_top(), P["cover_t"], P["lip_y"]
    y_front = on_plate(tz / math.cos(TILT), 0)[0] + 10.0       # over the land boss top, 2 mm from the cover's front edge
    return [(sign * x, y, tz + ct - 2.6) for x in P["mount_slots"] for y in (y_front, L - w - 6.0)]

# ------------------------------------------------------------------ build

def build():
    global ROOT
    scene = reset_scene()
    ROOT = bpy.data.objects.new("Assembly (mm)", None)
    scene.collection.objects.link(ROOT)
    ROOT.scale = (0.001, 0.001, 0.001)
    t0 = time.time()

    M = dict(
        printed=material("PLA matte black", (0.03, 0.03, 0.033), rough=0.62, coat=0.05),
        light=material("PLA light grey", (0.42, 0.42, 0.43), rough=0.6, coat=0.05),
        glass=material("See-through PLA", (0.05, 0.05, 0.06), rough=0.3, alpha=0.12),
        alu=material("Anodised 4040", (0.11, 0.11, 0.12), rough=0.38, metal=1.0),
        steel=material("Steel", (0.72, 0.72, 0.74), rough=0.22, metal=1.0),
        screw=material("Steel satin", (0.58, 0.58, 0.60), rough=0.38, metal=0.35),   # a8: screw heads read under the key light
        rubber=material("Grip rubber", (0.018, 0.018, 0.018), rough=0.88),
        accent=material("Accent", (0.78, 0.33, 0.2), rough=0.45),
        gap=material("Shadow gap", (0.0, 0.0, 0.0), rough=1.0),
        pcb_dark=material("ESP32 PCB", (0.02, 0.02, 0.02), rough=0.4),
        pcb_red=material("HX711 PCB", (0.55, 0.05, 0.04), rough=0.4),
        nickel=material("RJ45 nickel", (0.6, 0.6, 0.6), rough=0.3, metal=1.0),
        chair=material("Chair frame", (0.35, 0.36, 0.38), rough=0.4, metal=0.6),
        wire=material("Wire", (0.04, 0.04, 0.045), rough=0.5),
        wire_red=material("Wire red", (0.5, 0.04, 0.03), rough=0.5),
        patch=material("Patch cable", (0.15, 0.3, 0.6), rough=0.5),
    )

    # --- chair: Corpus back plate (vertical 4040s) and the central block -----------------
    slot = [(-4.1, 21), (-4.1, 18), (-8, 18), (-8, 13.5), (-4, 9.5), (4, 9.5), (8, 13.5), (8, 18), (4.1, 18), (4.1, 21)]   # 40-series slot 10, ~11.5 deep
    u0, u1 = U_TOP - P["plate_len"], U_TOP
    nb = P["plate_bars"]
    for i in range(nb):
        xc = 40 * (i - (nb - 1) / 2)
        bar = plate_box(f"Plate 4040 {i}", (xc - 20, -40, u0), (xc + 20, 0, u1), M["alu"], coll="Chair", smooth_angle=0)
        cutter = prism(f"plate slot {i}", [(xc + a, -20 + b) for a, b in slot], "Z", u0 - 1, u1 + 1, coll="Chair")
        cutter.data.transform(PLATE_M)
        cut(bar, cutter)
    bw, bh, bo = P["block"]
    ub = U_TOP - P["clear_h"]
    plate_box("Central block", (-bw / 2, 0, ub - bh), (bw / 2, bo, ub), M["chair"], coll="Chair")
    print(f"  [{time.time() - t0:6.1f} s] chair")

    # --- handles: build the right one, mirror for the left ---------------------------
    H = build_fin(M)
    left = dict(inboard=mirror_x(H["inboard"], "Fin L inboard half"),
                outboard=mirror_x(H["outboard"], "Fin L outboard half"),
                piston=mirror_x(H["piston"], "Piston L"),
                cartridge=mirror_x(H["cartridge"], "Cartridge L"),
                washers=[mirror_x(o, o.name.replace(" R", " L")) for o in H["washers"]])
    ml = mirror_x(H["movlink"], "Movlink L")
    cf = mirror_x(H["cartfix"], "Cartfix L")
    for o in (ml, cf):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        collection("Check only").objects.link(o)
        o.hide_render = True
    for o in [left["piston"], left["cartridge"], ml, cf] + left["washers"]:
        o.data.materials.clear()
        o.data.materials.append(M["printed"])
    for o in H["other"]:
        if o.type == "MESH":
            m = mirror_x(o, o.name.replace(" R", " L"))
            m.data.materials.clear()
            m.data.materials.append(o.data.materials[0])
            for c in m.users_collection:
                c.objects.unlink(m)
            collection("Hardware").objects.link(m)
    print(f"  [{time.time() - t0:6.1f} s] handles")

    # --- electronics: flat on the bridge floor. ESP32 left of centre, one amp under each lead.
    fz = z_bridge() + P["wall"]
    es = P["esp_standoff"]
    esp_m = place_board((27.5, 34, 0), rot("Z", 180), (-40, 37, fz + es))
    esp = import_stl("ESP32-P4 PoE", "esp32_p4.stl", esp_m, M["pcb_dark"], coll="Electronics")
    strip_below(esp, fz + es + 0.05)            # the stand-in's own 3.75 mm spacers: the board sits on 5 mm printed standoffs
    esp_holes = [esp_m @ Vector((hx_, hy_, 0)) for hx_, hy_ in ((3.5, 25.75), (51.5, 25.75), (3.5, 58.75), (51.5, 58.75))]
    F = handle_frame()
    lead_y = F["ye"] + 3.5
    amps = {}
    for side, sx, R in (("L", -1, Matrix.Identity(4)), ("R", 1, rot("Z", 180))):
        # a7: the spring terminal faces outboard, under the lead's drop from the end wall
        amp_m = place_board((AMP_W / 2, AMP_L / 2, 0), R, (sx * AMP_X, lead_y, fz + AMP_STANDOFF))
        amp_board(f"Amp {side}", amp_m, M)
        amps[side] = amp_m
    amp_pts = {s_: [amps[s_] @ Vector((a, b, 0)) for a, b in AMP_HOLES] for s_ in "LR"}
    boards_l = [("esp", [(p.x, p.y) for p in esp_holes], P["esp_standoff"]),
                ("amp", [(p.x, p.y) for p in amp_pts["L"]], AMP_STANDOFF)]
    boards_r = [("amp", [(p.x, p.y) for p in amp_pts["R"]], AMP_STANDOFF)]

    # Patch cable (150 mm, 5 mm OD): out of the board jack, up, across under the cover and down into the
    # coupler's plug. Three R20 bends (4 x OD); the coupler sits where 150 mm of cable ends.
    bz = z_bridge()
    jack = esp_m @ Vector((29.93, -1.5, 7))
    rj_o = bz + P["wall"] + RJ_PAD + RJ_FLANGE                 # coupler origin = flange top, on the pad
    plug_top = rj_o + 27 + 18
    run_z, R_patch, patch_len = 16.0, 20.0, 150.0      # routed length; the cable bought is P["patch_lead"]
    fixed = 5 + 3 * (math.pi / 2 * R_patch) + (run_z - R_patch - (jack.z + R_patch)) + (run_z - R_patch - plug_top)
    tp = Turtle((jack.x, jack.y + 10, jack.z), (0, 1, 0))
    tp.line(5).arc(R_patch, 90, "X").line_to("z", run_z - R_patch).arc(R_patch, -90, "Y")
    tp.line(patch_len - fixed).arc(R_patch, -90, "Y").line_to("z", plug_top)
    rj = (tp.p.x, tp.p.y)
    trays = [build_tray_half(-1, M, dict(boards=boards_l, rj45=rj)), build_tray_half(1, M, dict(boards=boards_r, rj45=None))]
    covers = [build_cover(M)]
    print(f"  [{time.time() - t0:6.1f} s] trays + cover")

    import_stl("RJ45 panel coupler", "rj45_coupler.stl",
               Matrix.Translation((rj[0], rj[1], rj_o)) @ rot("Z", 90) @ rot("X", 180), M["nickel"], coll="Electronics")
    box("Patch plug (coupler)", (rj[0] - 6, rj[1] - 7, rj_o + 27), (rj[0] + 6, rj[1] + 7, plug_top), M["patch"], coll="Electronics")
    box("Patch plug (board)", (jack.x - 6, jack.y, jack.z - 6), (jack.x + 6, jack.y + 10, jack.z + 6), M["patch"], coll="Electronics")
    poly_cable("Patch cable", tp.pts, 5, M["patch"])

    # --- wiring ------------------------------------------------------------------------
    leads = []
    for sign, side in ((-1, "L"), (1, "R")):
        t, _ = lead_path(sign)
        jp4 = amps[side] @ Vector((0.0, AMP_L / 2, 6.0))           # the spring terminal's wire entries (outboard edge)
        stop = jp4.x + 15 * sign                                  # jacket ends 15 mm short; conductors fan out to the terminals
        rb = P["lead_bend_r"]
        # a7: in through the end wall high up, down the inside of the wall, then inboard to the amp's terminal
        t.line_to("x", sign * (F["box_end"] - P["wall"] - 4))
        t.arc(rb, -90 * sign, "Y")
        t.line_to("z", jp4.z + rb)
        t.arc(rb, 90 * sign, "Y")
        if (stop - t.p.x) * t.h.x > 0:
            t.line_to("x", stop)
        leads.append(poly_cable(f"Load cell lead {side}", t.pts, P["lead_d"], M["wire"]))
        j1 = amps[side] @ Vector((AMP_W - 2.2, 8.0 if side == "L" else AMP_L - 8.0, 3.0))   # the front Qwiic socket
        hdr = esp_m @ Vector((27.5 + (18 if side == "L" else -18), 64.8, 8.5))
        cable(f"Amp to ESP32 {side}", [j1, (j1.x - sign * 8, j1.y, j1.z + 12),
                                       (hdr.x, hdr.y - 4, hdr.z + 12), hdr], 2.0, M["wire_red"])

    board_tops = ([(p.x, p.y, fz + es + 1.6, 10) for p in esp_holes] +
                  [(p.x, p.y, fz + AMP_STANDOFF + 1.6, 10) for s_ in "LR" for p in amp_pts[s_]])   # a7: amps screwed too
    build_fasteners(M, board_tops)
    for i, dx in enumerate((-15.3, 15.3)):                        # RJ45 flange onto its pad, from above
        screw(f"RJ45 screw {i}", (rj[0] + dx, rj[1], rj_o), (0, 0, -1), 12, "M3_selftap_pan", M, host="Tray L",
              step="electronics")
    bench = build_bench(M)
    for o in collection("Bench").objects:
        o.hide_render = True                                      # shown only in the stop-setting step render

    for k in ("lead_d", "lead_straight", "lead_bend_r"):
        scene[k] = P[k]                                           # read by check_wires.py
    import json
    derived = dict(handle_frame(), HX=HX, U_TOP=U_TOP, tray_top=tray_top(), z_bridge=z_bridge(),
                   patch_len=patch_len, patch_lead=P["patch_lead"], rj45=list(rj), **stop_layout(),
                   **leaf_stress(), **stop_thermal(), **cradle_frame(),
                   **{"bench_" + k: v for k, v in bench_layout().items()})
    scene["pa_params"] = json.dumps(dict(P, **derived), default=list)   # to_cadcheck.py puts these in the manifest
    print(f"  [{time.time() - t0:6.1f} s] done")
    parts = dict(handles=[H["inboard"], H["outboard"], left["inboard"], left["outboard"]],
                 pistons=[H["piston"], left["piston"]], trays=trays, covers=covers,
                 knuckles=[H["cartridge"], left["cartridge"]], washers=H["washers"] + left["washers"], bench=bench)
    return scene, M, parts, leads


def print_check(parts):
    """Bounding box of each printed part in its print orientation vs the H2D's single-nozzle volume."""
    bed = (325, 320, 325)
    rows = []
    for o in (parts["handles"] + parts["pistons"] + parts["trays"] + parts["covers"] + parts["knuckles"] + parts["washers"]
              + parts["bench"]):
        vs = [v.co for v in o.data.vertices]
        ext = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
        if o in parts["handles"]:
            plate, h, how = (ext[1], ext[2]), ext[0], "split face down"
        elif o.name == "Cradle":
            plate, h, how = (ext[0], ext[1]), ext[2], "base down"
        elif o in parts["pistons"] or o.name == "Setting plug":
            plate, h, how = (ext[1], ext[2]), ext[0], "on its side, D-flat down"
        elif o in parts["trays"]:
            plate, h, how = (ext[0], ext[1]), ext[2], "bottom down, open top up"
        elif o in parts["covers"]:
            plate, h, how = (ext[0], ext[1]), ext[2], "flat, underside down"
        elif o in parts["washers"]:
            plate, h, how = (ext[0], ext[2]), ext[1], "flat"
        else:
            plate, h, how = (ext[1], ext[2]), ext[0], "on its side, inboard face down"
        a, b = sorted(plate, reverse=True)
        fits = a <= bed[0] and b <= bed[1] and h <= bed[2]
        rows.append(f"{o.name:28s} {a:6.1f} x {b:6.1f} x {h:6.1f} mm  {how:28s} {'fits' if fits else 'DOES NOT FIT'}")
    text = "Print check (H2D single nozzle 325 x 320 x 325 mm)\n" + "\n".join(rows)
    print(text)
    with open(os.path.join(RENDERS, "print_check.txt"), "w") as fh:
        fh.write(text + "\n")


# ------------------------------------------------------------------ exploded assembly steps

def axis_line(name, p0, p1, mat):
    """Thin accent rod showing where a bolt travels."""
    return cylinder(name, p0, p1, 1.0, mat, segs=12, coll="Step lines")


def render_steps(scene, M, parts):
    """Exploded renders for the README assembly guide, one per step group. Each step shows only
    its parts, moves them apart along their bolt axes, and draws each axis in the accent colour."""
    obs = bpy.data.objects
    F = handle_frame()
    ex = F["box_end"]
    nrm = Vector((0, math.cos(TILT), -math.sin(TILT)))            # plate normal (rearward) in Y/Z

    def named(*prefixes):
        return [o for o in obs if o.type == "MESH" and o.name.startswith(prefixes)
                and not any(c.name in ("Part sources", "Cutters") for c in o.users_collection)]

    head = ("Cartridge {s}", "Piston {s}", "MTB grip {s}", "Load cell {s}", "Washer front {s}", "Front nut {s}",
            "Washer rear {s}", "Rear nut {s}", "Stop screw push {s}", "Stop screw pull {s}", "Stop nut push {s}",
            "Stop nut pull {s}", "Piston screw {s}")
    handle_R = named("Fin R ", "M3 screw R", "M4 nut R", *[h.format(s="R") for h in head])
    handle_L = named("Fin L ", "M3 screw L", "M4 nut L", *[h.format(s="L") for h in head])

    def shot(file, show, moves, lines, cam, glass=()):
        saved = {o: o.hide_render for o in obs}
        for o in obs:
            if o.type in ("MESH", "CURVE"):
                o.hide_render = o not in show
        mats = {o: list(o.data.materials) for o in glass}
        for o in glass:
            for i in range(len(o.data.materials)):
                o.data.materials[i] = M["glass"]
        for o, d in moves:
            o.location += d
        made = [axis_line(f"line {file} {i}", a, b, M["accent"]) for i, (a, b) in enumerate(lines)]
        render(scene, cam, file)
        for o in made:
            bpy.data.objects.remove(o)
        for o, d in moves:
            o.location -= d
        for o, ms in mats.items():
            for i, m in enumerate(ms):
                o.data.materials[i] = m
        for o, h in saved.items():
            o.hide_render = h

    # Step 0 (a8, bench): the cartridge alone. The cell with its rear washer and nut drawn out up-inboard along the 45 deg
    # stud slots (the way it goes in), the front washer and nut forward, the stop screws and nuts out of their side slots.
    cz = F["cz"]
    d45 = Vector((-1.0, 0.0, 1.0)).normalized()
    moves = [(o, d45 * 70) for o in named("Load cell R", "Washer rear R", "Rear nut R")]
    moves += [(o, Vector((0, -28, 0))) for o in named("Washer front R", "Front nut R")]
    for o in named("Stop screw push R", "Stop nut push R"):
        moves.append((o, Vector((26 if o.name.endswith("out") else -26, 0, 0))))
    for o in named("Stop nut pull R"):
        moves.append((o, Vector((22 if o.name.endswith("out") else -22, 0, 0))))
    moves += [(o, Vector((0, -45, 0))) for o in named("Stop screw pull R")]
    c0 = Vector((HX, F["ye"] + 6.35, cz))
    lines = [(tuple(c0), tuple(c0 + d45 * 100)), ((HX, F["yp"] - 40, cz), (HX, F["yb"], cz))]
    shot("step0_cartridge.png", named("Cartridge R", "Load cell R", "Washer rear R", "Rear nut R", "Washer front R",
                                      "Front nut R", "Stop screw push R", "Stop screw pull R", "Stop nut push R",
                                      "Stop nut pull R"), moves, lines,
         camera(scene, "Cam step0", (HX / 1000 - 0.23, -0.06, 0.12), (HX / 1000 - 0.015, 0.075, -0.010), lens=50))

    # Step A: the head. Cartridge with its stop pin, cell and nuts, piston drawn back out of the socket,
    # outboard half and the M3s off along X; the inboard half stays put.
    out_d, scr_d, pis_d = Vector((80, 0, 0)), Vector((-90, 0, 0)), Vector((0, 70, 0))
    up_d = Vector((0, 0, 75))
    moves = [(o, out_d) for o in named("Fin R outboard")]
    moves += [(o, scr_d) for o in named("M3 screw R")]
    moves += [(o, up_d) for o in named("Cartridge R", "Load cell R", "Washer rear R", "Rear nut R", "Stop screw push R",
                                         "Stop screw pull R", "Stop nut push R", "Stop nut pull R", "Washer front R",
                                         "Front nut R")]
    moves += [(o, up_d + pis_d) for o in named("Piston R", "MTB grip R", "Piston screw R")]
    lines = [((HX - 130, y, z), (HX + 90, y, z)) for y, z, _ in clamshell_bolts()]
    lines.append(((HX, F["ye"] - 15, F["az"] + 75), (HX, F["lip"] + 90, F["az"] + 75)))   # piston into the socket
    lines.append(((HX, F["ye"], F["az"]), (HX, F["ye"], F["az"] + 75)))              # cartridge drops in
    shot("step1_handle.png", handle_R, moves, lines,
         camera(scene, "Cam step1", (HX / 1000 + 0.44, 0.46, 0.34), (HX / 1000 + 0.04, 0.07, 0.0), lens=42))

    # Step B: fin onto the tray end. Handle off along +X; M4s pulled into the tray; the fin is
    # see-through so the nuts in its slots show.
    tray = obs["Tray R"]
    fin_d, m4_d = Vector((90, 0, 0)), Vector((-45, 0, 0))
    moves = [(o, fin_d) for o in handle_R] + [(o, m4_d) for o in named("M4 screw R")]
    lines = [((ex - 70, y, z), (ex + 110, y, z)) for y, z in box_bolts()]
    m3 = named("M3 screw R")                                      # already in; hidden so the M4s read
    shot("step2_fin_to_tray.png", [o for o in handle_R if o not in m3] + [tray] + named("M4 screw R"), moves, lines,
         camera(scene, "Cam step2", (-0.02, 0.42, 0.30), (HX / 1000 + 0.01, 0.06, -0.03), lens=40),
         glass=named("Fin R inboard", "Fin R outboard"))

    # Step C: hang both halves on the plate. Each half moves straight off the plate along its
    # normal, the M5s further still; T-nuts stay in the slots.
    chair = named("Plate 4040", "Central block")
    halves = handle_R + handle_L + named("Tray ", "M4 screw", "ESP32", "Amp ", "RJ45", "Patch")
    off_d, bolt_d = nrm * 110, nrm * 170
    moves = [(o, off_d) for o in halves] + [(o, bolt_d) for o in named("M5 bolt")]
    lines = []
    for x, u, _, _ in mount_bolts():
        y0, z0 = on_plate(u, -10)
        y1, z1 = on_plate(u, 200)
        lines.append(((x, y0, z0), (x, y1, z1)))
    shot("step3_mount.png", chair + halves + named("M5 bolt", "T-nut"), moves, lines,
         camera(scene, "Cam step3", (-0.55, 0.85, 0.42), (0.0, 0.10, -0.06), lens=45))

    # Step E (bench): the cartridge in the stop-setting cradle with the setting plug and the jack; lip screws drawn
    # out along their axes, the cartridge lifted a little to show it drops in.
    cart = named("Cartridge R", "Load cell R", "Washer rear R", "Rear nut R", "Washer front R", "Front nut R",
                 "Stop screw push R", "Stop screw pull R", "Stop nut push R", "Stop nut pull R")
    bench = [o for o in collection("Bench").objects if o.type == "MESH"]
    lift = Vector((0, 0, 28))
    moves = [(o, BENCH_OFF + lift) for o in cart]
    moves += [(o, lift) for o in bench if o.name.startswith(("Setting plug", "Jack screw", "Jack swivel", "Jack nut"))]
    moves += [(o, Vector((18 if "a" == o.name[-1] else -18, 0, 0))) for o in bench if o.name.startswith("Jack lip screw")]
    B = bench_layout()
    bx = HX + BENCH_OFF.x
    lines = [((bx, B["jack_at"] + 40, 0), (bx, F["yp"] - 40, 0))]
    for s_ in (1, -1):
        lines.append(((bx + s_ * 45, B["lip_y"], B["lip_z"]), (bx + s_ * 10, B["lip_y"], B["lip_z"])))
    shot("step5_stop_setting.png", cart + bench, moves, lines,
         camera(scene, "Cam step5", (bx / 1000 + 0.26, 0.21, 0.20), (bx / 1000, 0.075, -0.012), lens=50))

    # Step D: electronics into tray L. Boards lifted off their standoffs; the coupler lifted off its pad too (a6 review
    # #6: it goes in from above, short end down into the opening; a6 drew it below the floor).
    elec_up, rj_up = Vector((0, 0, 60)), Vector((0, 0, 45))
    boards = named("ESP32", "Amp L", "Patch plug (board)", "Board screw")
    moves = [(o, elec_up) for o in boards] + [(o, rj_up) for o in named("RJ45", "Patch plug (coupler)")]
    shot("step4_electronics.png", [obs["Tray L"]] + boards + named("RJ45", "Patch plug (coupler)"), moves, [],
         camera(scene, "Cam step4", (-0.30, 0.45, 0.40), (-0.08, 0.06, -0.04), lens=45))

# ------------------------------------------------------------------ lighting, cameras, renders

def setup_render(scene):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1100
    scene.render.film_transparent = False
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -1.3

    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.012, 0.014, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    def area(name, loc, power, size, color=(1, 1, 1)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.size = size
        data.color = color
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        direction = Vector((0, 0.05, 0.05)) - Vector(loc)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return obj

    area("Key", (0.9, 1.1, 0.9), 120, 0.9)
    area("Fill", (-1.0, 0.6, 0.3), 35, 1.2, (0.85, 0.9, 1.0))
    area("Rim", (0.1, -1.0, 0.8), 90, 0.6, (1.0, 0.93, 0.85))
    area("Under", (0.0, 0.8, -0.8), 12, 1.0)

    floor = bpy.data.meshes.new("Floor")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=3)
    bm.to_mesh(floor)
    bm.free()
    fobj = bpy.data.objects.new("Floor", floor)
    scene.collection.objects.link(fobj)
    fobj.location = (0, 0, -0.33)
    floor.materials.append(material("Floor", (0.02, 0.02, 0.022), rough=0.35))


def camera(scene, name, loc, target, lens=50, ortho=None):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start = 0.01
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return obj


def render(scene, cam, file):
    scene.camera = cam
    scene.render.filepath = os.path.join(RENDERS, file)
    bpy.ops.render.render(write_still=True)
    print("rendered", file)


def main():
    os.makedirs(RENDERS, exist_ok=True)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    t0 = time.time()
    scene, M, parts, leads = build()
    print(f"[{time.time() - t0:6.1f} s] built")
    print_check(parts)
    setup_render(scene)
    hidden = [o for o in bpy.data.objects if o.name.startswith("Load cell ") and o.type == "MESH"] + leads
    for o in hidden:
        o.hide_render = True

    views = {
        "01_hero": camera(scene, "Cam hero", (0.62, 0.95, 0.38), (0.0, 0.07, -0.05), lens=50),
        "02_side": camera(scene, "Cam side", (1.5, 0.08, -0.06), (0.0, 0.08, -0.06), ortho=0.52),
        "03_handle_closeup": camera(scene, "Cam handle", (0.52, 0.42, 0.22), (0.17, 0.09, -0.03), lens=50),
        "04_top": camera(scene, "Cam top", (0.0, 0.10, 1.5), (0.0, 0.10, 0.0), ortho=0.62),
    }
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "push_assist_concept.blend"))
    print(f"[{time.time() - t0:6.1f} s] saved")
    for name, cam in views.items():
        if not only or name in only:
            render(scene, cam, name + ".png")

    # Exploded: cover up, right handle halves apart, piston back.
    if not only or "05_exploded" in only:
        moves = [(o, Vector((0, 0, 70))) for o in parts["covers"]]
        lift = Vector((40, 0, 0))                                    # right fin off the box end
        moves += [(o, lift + Vector((45, 0, 0))) for o in bpy.data.objects if o.name.startswith("Fin R outboard")]
        moves += [(o, lift) for o in bpy.data.objects if o.name.startswith("Fin R inboard")]
        moves += [(o, lift + Vector((0, 0, 60))) for o in bpy.data.objects
                  if o.name in ("Load cell R", "Cartridge R", "Washer rear R", "Rear nut R", "Washer front R", "Front nut R")
                  or o.name.startswith(("Stop screw push R", "Stop screw pull R", "Stop nut push R", "Stop nut pull R"))]
        moves += [(o, lift + Vector((0, 60, 60))) for o in bpy.data.objects
                  if o.name in ("Piston R", "MTB grip R") or o.name.startswith("Piston screw R")]
        for o, d in moves:
            o.location += d
        cell = bpy.data.objects["Load cell R"]
        cell.hide_render = False
        render(scene, camera(scene, "Cam exploded", (0.78, 0.66, 0.30), (0.16, 0.08, -0.04), lens=45), "05_exploded.png")
        cell.hide_render = True
        for o, d in moves:
            o.location -= d

    # Head with the outboard half off: cartridge (leaves, stop), cell, nuts, piston in its socket.
    if not only or "08_head_open" in only:
        out = bpy.data.objects["Fin R outboard half"]
        out.hide_render = True
        moves = []
        for o, d in moves:
            o.location += d
        cell = bpy.data.objects["Load cell R"]
        cell.hide_render = False
        F = handle_frame()
        tgt = (HX / 1000, (F["ye"] + F["link1"]) / 2000, -0.016)
        render(scene, camera(scene, "Cam head", (tgt[0] + 0.21, tgt[1] + 0.05, tgt[2] + 0.11), tgt, lens=55), "08_head_open.png")
        cell.hide_render = True
        out.hide_render = False
        for o, d in moves:
            o.location -= d

    if not only or "steps" in only:
        render_steps(scene, M, parts)

    # See-through printed parts with the cover off: electronics, cells and lead routing.
    if not only or "06_internals" in only:
        for o in parts["covers"]:
            o.hide_render = True
        for o in parts["handles"] + parts["trays"] + parts["pistons"] + parts["knuckles"]:
            for i in range(len(o.data.materials)):
                o.data.materials[i] = M["glass"]
        for o in hidden:
            o.hide_render = False
        render(scene, camera(scene, "Cam internals", (0.05, 0.60, 0.50), (0.0, 0.06, -0.04), lens=40), "06_internals.png")
        render(scene, camera(scene, "Cam lead", (0.5, 0.09, -0.03), (0.178, 0.09, -0.03), lens=45), "07_lead_side.png")


main()
