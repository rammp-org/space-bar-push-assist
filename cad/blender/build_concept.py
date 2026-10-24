"""Push-assist handle concept: builds the printable parts in Blender and renders review images.

Run:  /Applications/Blender.app/Contents/MacOS/Blender -b -P cad/blender/build_concept.py
Out:  cad/blender/push_assist_concept.blend and cad/blender/renders/*.png

Reference parts (load cell, boards, RJ45, grip) are STLs exported from Onshape by
export_parts.mjs, so they match the CAD. Printed parts (handle halves, pistons, tray halves,
covers) are built with SDF nodes so fillets and cut-outs stay robust; print_check reports
each one's size in its print orientation against the H2D bed.

Axes (mm): X across the chair, Y rearward toward the attendant, Z up.
The 4040 runs along X, centred on the origin.
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
    extrusion_length=385,    # 4040 spine; ends hidden inside the fins (chair mount is TBD)
    handle_spacing=355.6,    # 14 in, handle centre to handle centre

    # Box between the fins. The fins are the box's end caps, flush front, back and sides.
    box_front_y=-30,
    box_rear_y=60,
    box_bottom_z=-100,
    box_top_z=20,            # cover sits on top; the 4040 runs y -20..20, z -20..20 inside
    partition_y=20,          # wall behind the 4040 separating it from the boards bay
    wall=3,
    cover_t=5,
    crown_h=3,               # cover crown height (subtle shoulder line at the rear seam)
    box_r=12,                # bottom edge radius of the box

    # Fin (one per handle, printed as two halves split on its centre plane).
    fin_t=36,                # X thickness of the fin plate
    fin_top_front=(40, 222), # (y, z) top-front corner of the fin
    fin_top_rear=(130, 185), # (y, z) top-rear corner, where the grip emerges
    fin_r=25,                # corner radius at the fin's top corners
    window=((40, 45), (82, 45), (100, 160)),   # lightening window (y, z) triangle, R8 corners
    window_r=8,
    panel=(36, 36, 1.5),     # recessed panel on the outer face over the 4040 bolt (w, h, depth)
    open_r=6,                # every convex edge of the fin and box ends is R6

    # Grip and sensor head (barrel along Y at z = arm_z, lip at the fin's top-rear corner).
    arm_z=195,
    lip_y=128,
    barrel_d=50,
    floor_t=6,
    void_len=14,
    piston_d=33,             # = the MTB grip flange
    sleeve=45,
    piston_show=12,
    spigot_length=130,
    spigot_bore=16,

    # Load-cell lead: 4 mm OD, 1/2 in straight off the sensor's side, R13 bends.
    lead_d=4.0,
    lead_straight=12.7,
    lead_bend_r=13.0,
    channel_d=5.5,
    wire_hole_z=-30,

    fillet_r=12,             # concave blends (barrel into fin)
    edge_r=4,                # small edges (cover)
    groove=(2.0, 1.5),       # parting groove along the fin split (width, depth)
    voxel=0.6,
)
P["voxel"] = float(os.environ.get("PA_VOXEL", P["voxel"]))   # coarser for quick checks

HX = P["handle_spacing"] / 2

# Fasteners. Every bolt is countersunk and ends in a nut: a captive hex nut or a 4040 T-nut.
M3 = dict(hole=3.4, head=6.7, nut_af=5.6, nut_t=2.6)
M4 = dict(hole=4.5, head=8.8, nut_af=7.1, nut_t=3.4)
M5 = dict(hole=5.5, head=10.4, nut_af=8.1, nut_t=4.2)

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
             windows=(), open_r=0.0):
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

# ------------------------------------------------------------------ fin (handle + box end cap)

def handle_frame():
    """Shared head numbers (right fin, centred on x = HX)."""
    lip = P["lip_y"]
    pr = lip - P["sleeve"]                                  # piston rear face
    cr = pr - 0.4                                           # cell rear face
    ye = cr - 12.6                                          # cell front face / floor
    return dict(az=P["arm_z"], lip=lip, pr=pr, cell_rear=cr, ye=ye,
                box_end=HX - P["fin_t"] / 2)                # x of the box end / fin inner face


def fin_profile():
    """Side outline (y, z) of the fin, CCW: box front-bottom, rear-bottom, diagonal rear edge up
    to the grip, top edge, leaning front edge down to the box front."""
    fy, ry, zb, zt = P["box_front_y"], P["box_rear_y"], P["box_bottom_z"], P["box_top_z"]
    tf, tr, r = P["fin_top_front"], P["fin_top_rear"], P["fin_r"]
    pts = [(fy, zb), (ry, zb), tr, tf, (fy, zt)]
    return round_corners(pts, [P["box_r"], 20, r, r, 10], segs=10)


def lead_path(sign):
    """Lead: straight down off the boss, forward along the fin's front margin, down that edge,
    back into the boards bay, then inboard through the fin's inner face into the box."""
    F = handle_frame()
    Rb, x = P["lead_bend_r"], sign * HX
    fy, zt = P["box_front_y"], P["box_top_z"]
    tf = P["fin_top_front"]
    lean = math.atan2(tf[0] - fy, tf[1] - zt)                 # front edge lean from vertical
    t = Turtle((x, F["ye"] + 3.5, F["az"] - 15), (0, 0, -1))
    t.line(12.7 + P["lead_straight"] - 15)                    # 1/2 in off the sensor's side
    t.arc(Rb, -90, "X")                                       # forward
    z_run = t.p.z
    y_edge = fy + (z_run - zt) * math.tan(lean)               # front edge at this height
    t.line_to("y", y_edge + 14 + Rb * (1 - math.cos(lean)) + Rb * math.sin(lean))
    t.arc(Rb, 90 - math.degrees(lean), "X")                   # down, parallel to the front edge
    t.line_to("z", zt + 30 + Rb)
    t.arc(Rb, math.degrees(lean) + 90, "X")                   # rearward, over the 4040
    t.line_to("y", P["partition_y"] + 14 - Rb)
    t.arc(Rb, -90, "X")                                       # down into the boards bay
    t.line_to("z", P["wire_hole_z"] + Rb)
    t.arc(Rb, 90 * sign, "Y")                                 # inboard
    t.line_to("x", sign * (F["box_end"] - 1))
    handle_part = list(t.pts) + [t.p - Vector((sign * 6, 0, 0))]
    return t, handle_part


def clamshell_bolts():
    """(y, z, half thickness) of the M3 bolts through the fin: two in the box end, one under the
    window, two under the bore, one in the top-front corner."""
    F = handle_frame()
    ht = P["fin_t"] / 2
    az, ye, lip = F["az"], F["ye"], F["lip"]
    return [(-5, -60, ht), (45, -60, ht), (62, 28, ht), (40, 190, ht),
            (ye + 14, az - 21, ht), (lip - 8, az - 21, ht)]


def box_bolts():
    """(y, z) of the M4s from inside the tray through its end wall into nuts in the fin."""
    return [(40, -75), (40, 0)]


def build_fin(M):
    """Right fin as two printed halves (-X = inboard, +X = outboard), plus its hardware.

    Load path: grip -> piston (Ø33, 45 mm sleeve in the barrel bore carries bending; key rib
    carries torque) -> piston face clamped between the cell's rear face and an M5 nut -> cell ->
    front stud -> 6 mm floor clamped between the cell's front face and an M5 nut + Ø15 washer.
    """
    F = handle_frame()
    x, az, ye, cr, pr, lip = HX, F["az"], F["ye"], F["cell_rear"], F["pr"], F["lip"]
    ht, ft, vl = P["fin_t"] / 2, P["floor_t"], P["void_len"]
    bore = P["piston_d"] + 0.6
    bd = P["barrel_d"]

    sources = [prism("fin plate", fin_profile(), "X", x - ht, x + ht, coll="Part sources"),
               cylinder("barrel", (x, ye - ft - vl - 4, az), (x, lip, az), bd, coll="Part sources")]
    w = P["window"]
    windows = [prism("window", round_corners(list(w), [P["window_r"]] * 3, segs=10), "X", x - ht - 2, x + ht + 2, coll="Part sources")]
    pw, ph, pd = P["panel"]
    windows.append(box("panel recess", (x + ht - pd, -pw / 2, -ph / 2), (x + ht + 2, pw / 2, ph / 2)))

    cuts = []
    _, lead = lead_path(1)
    cuts.append(tube("lead channel", lead, P["channel_d"], coll="Part sources"))
    cuts.append(cylinder("cell pocket", (x, ye - 0.2, az), (x, pr + 0.5, az), 26.2, coll="Part sources"))
    cuts.append(box("boss pocket", (x - 3.2, ye + 0.4, az - 20), (x + 3.2, ye + 6.6, az)))
    cuts.append(cylinder("floor hole", (x, ye - ft - 0.5, az), (x, ye + 0.5, az), M5["hole"], coll="Part sources"))
    cuts.append(box("nut void", (x - 11, ye - ft - vl, az - 10), (x + 11, ye - ft, az + 10)))
    cuts.append(cylinder("sleeve bore", (x, pr - 0.5, az), (x, lip + 1, az), bore, coll="Part sources"))
    cuts.append(box("key slot", (x - 2.2, pr - 1, az + bore / 2 - 0.5), (x + 2.2, lip + 1, az + bore / 2 + 3.4)))
    # 4040 pocket and its M8 (into the extrusion's centre bore), under the panel recess.
    cuts.append(box("4040 pocket", (x - ht - 1, -20.3, -20.3), (x + ht - 3, 20.3, 20.3)))
    cuts.append(cylinder("m8 hole", (x + ht - 4, 0, 0), (x + ht + 1, 0, 0), 8.5, coll="Part sources"))
    cuts.append(cylinder("m8 counterbore", (x + ht - pd - 8, 0, 0), (x + ht + 1, 0, 0), 14.0, coll="Part sources"))
    # Clamshell bolts: countersunk on the outboard face, captive nut on the inboard face.
    heads = []
    for i, (y, z, hw) in enumerate(clamshell_bolts()):
        cuts.append(cylinder(f"m3 hole {i}", (x - hw - 2, y, z), (x + hw + 2, y, z), M3["hole"], coll="Part sources"))
        cuts.append(cone(f"m3 csk {i}", (x + hw - 1.8, y, z), (x + hw + 1, y, z), M3["hole"], M3["head"] + 2.6, coll="Part sources"))
        cuts.append(hex_prism(f"m3 nut {i}", (0, y, z), "X", M3["nut_af"], x - hw - 1, x - hw + 3.2, coll="Part sources"))
        heads.append(((x + hw - 0.6, y, z), (1, 0, 0), M3["head"]))
    # Box bolts: M4 from inside the tray through its end wall into nuts dropped into slots from
    # the split plane (slots open toward the inner face only through the bolt hole).
    for i, (y, z) in enumerate(box_bolts()):
        cuts.append(cylinder(f"m4 hole {i}", (x - ht - 1, y, z), (x - ht + 10.5, y, z), M4["hole"], coll="Part sources"))
        cuts.append(box(f"m4 nut slot {i}", (x - ht + 6, y - 3.7, z - 3.7), (x - ht + 6 + M4["nut_t"] + 0.8, y + 3.7, z + 30)))

    inboard, outboard = sdf_part("Fin R", sources, M["printed"], fillet_r=P["fillet_r"], windows=windows, open_r=P["open_r"],
                                 subtract=cuts, split_x=x, groove=P["groove"], groove_ymax=lip - 4)
    inboard.name, outboard.name = "Fin R inboard half", "Fin R outboard half"
    hw = [cylinder(f"Fin R bolt {i}", Vector(p) - Vector(n) * 0.25, Vector(p) + Vector(n) * 0.25, d, M["steel"], coll="Hardware")
          for i, (p, n, d) in enumerate(heads)]

    # Piston + grip spigot (unchanged): printed standing on its rear face.
    p1 = lip + P["piston_show"]
    rib = az + bore / 2 - 0.3
    sb = P["spigot_bore"]
    piston = sdf_part("Piston R", [cylinder("piston", (x, pr, az), (x, p1, az), P["piston_d"], coll="Part sources"),
                                  cylinder("spigot", (x, p1 - 1, az), (x, p1 + P["spigot_length"], az), 22.2, coll="Part sources"),
                                  box("key rib", (x - 2, pr + 0.5, rib - 0.5), (x + 2, lip - 2, rib + 3.0))],
                      M["printed"], fillet_r=2.0,
                      subtract=[cylinder("stud hole", (x, pr - 1, az), (x, pr + 7, az), M5["hole"], coll="Part sources"),
                                cylinder("spigot bore", (x, pr + 6, az), (x, p1 + P["spigot_length"] + 1, az), sb, coll="Part sources")])[0]
    grip = import_stl("MTB grip R", "mtb_grip.stl", Matrix.Translation((x, p1, az)) @ rot("Z", 90), M["rubber"], coll="Hardware")
    cell = import_stl("Load cell R", "load_cell.stl", Matrix.Translation((x, ye + 6.3, az)) @ rot("Y", 180), M["steel"], coll="Hardware")
    fw = cylinder("Front washer R", (x, ye - ft - 1.2, az), (x, ye - ft, az), 15.0, M["steel"], coll="Hardware")
    fn = hex_prism("Front nut R", (x, 0, az), "Y", 8.0, ye - ft - 1.2 - M5["nut_t"], ye - ft - 1.2, mat=M["steel"], coll="Hardware")
    rw = cylinder("Rear washer R", (x, pr + 6, az), (x, pr + 7, az), 10.0, M["steel"], coll="Hardware")
    rn = hex_prism("Rear nut R", (x, 0, az), "Y", 8.0, pr + 7, pr + 7 + M5["nut_t"], mat=M["steel"], coll="Hardware")
    return dict(inboard=inboard, outboard=outboard, piston=piston,
                other=hw + [grip, cell, fw, fn, rw, rn], cell=cell)

# ------------------------------------------------------------------ box: tray and cover

def tray_features(sign):
    """Positions (x) of the tray's bosses and bolts for the half on side `sign`."""
    return dict(cover_rear=[sign * v for v in (25, 75, 125)], cover_front=[sign * v for v in (25, 75, 125)],
                t_nut=[sign * v for v in (50, 140)], cover_t_nut=sign * 75)


def box_section(inset=0.0, z_top=None):
    fy, ry, zb, zt = P["box_front_y"], P["box_rear_y"], P["box_bottom_z"], P["box_top_z"]
    z_top = zt if z_top is None else z_top
    r = max(1.0, P["box_r"] - inset)
    return round_corners([(fy + inset, zb + inset), (ry - inset, zb + inset), (ry - inset, z_top), (fy + inset, z_top)],
                         [r, r, 1.0, 1.0], segs=10)


def crown_z(y):
    fy, ry = P["box_front_y"], P["box_rear_y"]
    mid, half = (fy + ry) / 2, (ry - fy) / 2
    return P["box_top_z"] + P["cover_t"] + P["crown_h"] * max(0.0, 1 - ((y - mid) / half) ** 2)


def build_tray_half(sign, M, electronics=None):
    F = handle_frame()
    fy, ry, w = P["box_front_y"], P["box_rear_y"], P["wall"]
    zb, tz = P["box_bottom_z"], P["box_top_z"]
    py = P["partition_y"]
    ex = F["box_end"]
    x0, x1 = sorted((0, sign * ex))
    side = "L" if sign < 0 else "R"
    f = tray_features(sign)

    src = [prism("box", box_section(), "X", x0, x1, coll="Part sources")]
    xi0, xi1 = sorted((0, sign * (ex - w)))
    cut = [prism("bay 4040", round_corners([(fy + w, zb + w), (py, zb + w), (py, tz + 20), (fy + w, tz + 20)], [9, 1, 1, 1], segs=10),
                 "X", xi0, xi1, coll="Part sources"),
           prism("bay boards", round_corners([(py + w, zb + w), (ry - w, zb + w), (ry - w, tz + 20), (py + w, tz + 20)], [1, 9, 1, 1], segs=10),
                 "X", xi0, xi1, coll="Part sources")]
    # Lead from the fin enters the boards bay through the end wall.
    t_lead, _ = lead_path(sign)
    cut.append(cylinder("lead hole", (sign * (ex - w - 1), t_lead.p.y, t_lead.p.z), (sign * (ex + 1), t_lead.p.y, t_lead.p.z),
                        P["channel_d"] + 1, coll="Part sources"))
    # Fin bolts: M4 countersunk from inside through the end wall into nuts in the fin.
    for y, z in box_bolts():
        cut.append(cylinder("fin bolt hole", (sign * (ex - w - 8), y, z), (sign * (ex + 1), y, z), M4["hole"], coll="Part sources"))
        cut.append(cone("fin bolt csk", (sign * (ex - w - 9), y, z), (sign * (ex - w - 8 + 2.3), y, z),
                        M4["head"] + 2.2, M4["hole"], coll="Part sources"))
        src.append(box("fin bolt boss", (min(sign * (ex - w - 8), sign * (ex - w + 0.5)), y - 7, z - 7),
                       (max(sign * (ex - w - 8), sign * (ex - w + 0.5)), y + 7, z + 7)))
    # Cover bosses with side-entry M3 nut slots.
    for x in f["cover_rear"] + f["cover_front"]:
        rear = x in f["cover_rear"]
        y_in, y_c = (ry - w, ry - w - 3.8) if rear else (py + w, py + w + 3.8)
        src.append(box("cover boss", (x - 5, min(y_in, y_in + (-8 if rear else 8)), tz - 14), (x + 5, max(y_in, y_in + (-8 if rear else 8)), tz)))
        cut.append(cylinder("cover hole", (x, y_c, tz - 15), (x, y_c, tz + 1), M3["hole"], coll="Part sources"))
        slot_y = (y_c - 9, y_c + 3.0) if rear else (y_c - 3.0, y_c + 9)
        cut.append(box("cover nut slot", (x - M3["nut_af"] / 2 - 0.1, slot_y[0], tz - 8), (x + M3["nut_af"] / 2 + 0.1, slot_y[1], tz - 8 + M3["nut_t"] + 0.3)))
    # 4040 bolts: M5 countersunk from the boards bay through the partition into T-nuts in the rear slot.
    for x in f["t_nut"]:
        src.append(box("t-nut boss", (x - 8, py + w - 0.5, -8), (x + 8, py + w + 4, 8)))
        cut.append(cylinder("t-nut hole", (x, py - 1, 0), (x, py + w + 5, 0), M5["hole"], coll="Part sources"))
        cut.append(cone("t-nut csk", (x, py + w + 4 - 2.9, 0), (x, py + w + 5, 0), M5["hole"], M5["head"] + 2.0, coll="Part sources"))

    if electronics:
        for kind, holes, standoff in electronics["boards"]:
            for (hx_, hz_) in holes:
                src.append(cylinder("standoff", (hx_, py + w - 0.5, hz_), (hx_, py + w + standoff, hz_), 6.5, coll="Part sources"))
                cut.append(cylinder("standoff hole", (hx_, py - 1, hz_), (hx_, py + w + standoff + 1, hz_), M3["hole"], coll="Part sources"))
                cut.append(cone("standoff csk", (hx_, py - 1, hz_), (hx_, py + 1.9, hz_), M3["head"] + 2.0, M3["hole"], coll="Part sources"))
        rx = electronics["rj45_x"]
        ym = (py + ry) / 2
        src.append(box("rj45 pad", (rx - 22, py + w - 0.5, zb + w - 0.5), (rx + 22, ry - w + 0.5, zb + w + 3)))
        cut.append(cylinder("rj45 hole", (rx, ym, zb - 1), (rx, ym, zb + w + 4), 24.0, coll="Part sources"))
        for dx in (-15.3, 15.3):
            cut.append(cylinder("rj45 screw", (rx + dx, ym, zb - 1), (rx + dx, ym, zb + w + 4), M3["hole"], coll="Part sources"))
            cut.append(hex_prism("rj45 nut", (rx + dx, ym, 0), "Z", M3["nut_af"], zb + w + 3 - M3["nut_t"] - 0.3, zb + w + 3.1, coll="Part sources"))

    return sdf_part(f"Tray {side}", src, M["printed"], fillet_r=1.0, subtract=cut)[0]


def build_cover_half(sign, M):
    F = handle_frame()
    fy, ry, w, tz, ct = P["box_front_y"], P["box_rear_y"], P["wall"], P["box_top_z"], P["cover_t"]
    py = P["partition_y"]
    ex = F["box_end"]
    x0, x1 = sorted((0, sign * ex))
    side = "L" if sign < 0 else "R"
    f = tray_features(sign)
    n = 14
    crown = [(ry + (fy - ry) * i / (n + 1), crown_z(ry + (fy - ry) * i / (n + 1))) for i in range(1, n + 1)]
    prof = round_corners([(fy, tz), (ry, tz), (ry, tz + ct)] + crown + [(fy, tz + ct)],
                         [1.0, 1.0, 1.5] + [0] * n + [P["edge_r"]], segs=8)
    src = [prism("cover plate", prof, "X", x0, x1, coll="Part sources"),
           prism("cover key", [(-3.9, tz - 4.5), (3.9, tz - 4.5), (3.9, tz + 0.5), (-3.9, tz + 0.5)], "X", x0 + 8, x1 - 8, coll="Part sources")]
    cut = []
    for x in f["cover_rear"] + f["cover_front"]:
        y_c = ry - w - 3.8 if x in f["cover_rear"] else py + w + 3.8
        ztop = crown_z(y_c)
        cut.append(cylinder("cover hole", (x, y_c, tz - 1), (x, y_c, ztop + 1), M3["hole"], coll="Part sources"))
        cut.append(cone("cover csk", (x, y_c, ztop - 1.9), (x, y_c, ztop + 1), M3["hole"], M3["head"] + 2.6, coll="Part sources"))
    x = f["cover_t_nut"]
    ztop = crown_z(0)
    cut.append(cylinder("4040 hole", (x, 0, tz - 6), (x, 0, ztop + 1), M5["hole"], coll="Part sources"))
    cut.append(cone("4040 csk", (x, 0, ztop - 2.9), (x, 0, ztop + 1), M5["hole"], M5["head"] + 2.0, coll="Part sources"))
    cut.append(box("key gap at bolt", (x - 6, -5, tz - 6), (x + 6, 5, tz)))
    return sdf_part(f"Cover {side}", src, M["light"], fillet_r=1.0, subtract=cut)[0]

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

    # --- chair posts and 4040 -----------------------------------------------------
    L = P["extrusion_length"]
    profile = round_corners([(-20, -20), (20, -20), (20, 20), (-20, 20)], 1.5, segs=4)
    alu = prism("4040 extrusion", profile, "X", -L / 2, L / 2, M["alu"], coll="Frame")
    for s in range(4):
        pts = [(-4.1, 21), (-4.1, 18), (-8, 18), (-8, 13.5), (8, 13.5), (8, 18), (4.1, 18), (4.1, 21)]
        c, si = math.cos(s * math.pi / 2), math.sin(s * math.pi / 2)
        cut(alu, prism(f"tslot{s}", [(u * c - v * si, u * si + v * c) for u, v in pts], "X", -L / 2 - 1, L / 2 + 1, coll="Frame"))
    cut(alu, cylinder("4040 bore", (-L / 2 - 1, 0, 0), (L / 2 + 1, 0, 0), 6.8, coll="Frame"))
    print(f"  [{time.time() - t0:6.1f} s] frame")

    # --- handles: build the right one, mirror for the left ---------------------------
    H = build_fin(M)
    left = dict(inboard=mirror_x(H["inboard"], "Fin L inboard half"),
                outboard=mirror_x(H["outboard"], "Fin L outboard half"),
                piston=mirror_x(H["piston"], "Piston L"))
    for o in H["other"]:
        if o.type == "MESH":
            m = mirror_x(o, o.name.replace(" R", " L"))
            m.data.materials.clear()
            m.data.materials.append(o.data.materials[0])
            for c in m.users_collection:
                c.objects.unlink(m)
            collection("Hardware").objects.link(m)
    print(f"  [{time.time() - t0:6.1f} s] handles")

    # --- electronics (left half): ESP32 between the two amps -------------------------
    wall_y = P["partition_y"] + P["wall"]
    esp_m = place_board((27.5, 34, 0), BOARD_TO_WALL, (-75, wall_y + 5, -28))
    import_stl("ESP32-P4 PoE", "esp32_p4.stl", esp_m, M["pcb_dark"], coll="Electronics")
    esp_holes = [(esp_m @ Vector((hx_, hy_, 0))) for hx_, hy_ in ((3.5, 25.75), (51.5, 25.75), (3.5, 58.75), (51.5, 58.75))]
    amps = {}
    for side, cx, R in (("L", -135, rot("Y", 180) @ BOARD_TO_WALL), ("R", -26, BOARD_TO_WALL)):
        amp_m = place_board((15.24, 11.43, 0), R, (cx, wall_y + 4, -30))
        import_stl(f"HX711 {side}", "hx711.stl", amp_m, M["pcb_red"], coll="Electronics")
        amps[side] = amp_m
    boards = [("esp", [(p.x, p.z) for p in esp_holes], 5)]
    for side, amp_m in amps.items():
        boards.append(("amp", [((amp_m @ Vector((hx_, hy_, 0))).x, (amp_m @ Vector((hx_, hy_, 0))).z)
                               for hx_, hy_ in ((2.54, 2.54), (27.94, 2.54), (2.54, 20.32), (27.94, 20.32))], 4))
    rj_x = -125
    trays = [build_tray_half(-1, M, dict(boards=boards, rj45_x=rj_x)), build_tray_half(1, M)]
    covers = [build_cover_half(-1, M), build_cover_half(1, M)]
    print(f"  [{time.time() - t0:6.1f} s] trays + covers")

    fy, ry = P["partition_y"], P["box_rear_y"]
    import_stl("RJ45 panel coupler", "rj45_coupler.stl",
               Matrix.Translation((rj_x, (fy + ry) / 2, P["box_bottom_z"])) @ rot("Z", 90) @ rot("X", 180), M["nickel"], coll="Electronics")
    jack = esp_m @ Vector((29.93, -1.5, 7))
    ym, bz = (fy + ry) / 2, P["box_bottom_z"]
    plug_top = bz + 27 + 18
    box("Patch plug (coupler)", (rj_x - 6, ym - 7, bz + 27), (rj_x + 6, ym + 7, plug_top), M["patch"], coll="Electronics")
    box("Patch plug (board)", (jack.x - 6, jack.y - 7, jack.z - 18), (jack.x + 6, jack.y + 7, jack.z), M["patch"], coll="Electronics")
    cable("Patch cable", [(rj_x, ym, plug_top), (rj_x + 4, 48, plug_top + 6), (rj_x + 22, 50, plug_top - 4),
                          (jack.x - 14, 47, bz + 10), (jack.x, jack.y + 2, jack.z - 30), (jack.x, jack.y, jack.z - 18)], 5, M["patch"])

    # --- wiring ------------------------------------------------------------------------
    leads = []
    for sign, side in ((-1, "L"), (1, "R")):
        t, _ = lead_path(sign)
        jp4 = amps[side] @ Vector((1.27, 6.35, 8.5))
        stop = jp4.x - 15 * (1 if side == "L" else -1)            # jacket ends 15 mm short; conductors fan out to JP4
        if (stop - t.p.x) * t.h.x > 0:
            t.line_to("x", stop)
        leads.append(poly_cable(f"Load cell lead {side}", t.pts, P["lead_d"], M["wire"]))
        j1 = amps[side] @ Vector((29.2, 16.5, 8.5))
        hdr = esp_m @ Vector((27.5 + (18 if side == "L" else -18), 64.8, 8.5))
        cable(f"HX711 to ESP32 {side}", [j1, (j1.x + (6 if side == "L" else -6), j1.y + 3, j1.z + 10),
                                         (hdr.x, hdr.y + 4, hdr.z + 8), hdr], 2.0, M["wire_red"])

    for k in ("lead_d", "lead_straight", "lead_bend_r"):
        scene[k] = P[k]                                           # read by check_wires.py
    print(f"  [{time.time() - t0:6.1f} s] done")
    parts = dict(handles=[H["inboard"], H["outboard"], left["inboard"], left["outboard"]],
                 pistons=[H["piston"], left["piston"]], trays=trays, covers=covers, knuckles=[])
    return scene, M, parts, leads


def print_check(parts):
    """Bounding box of each printed part in its print orientation vs the H2D's single-nozzle volume."""
    bed = (325, 320, 325)
    rows = []
    for o in parts["handles"] + parts["pistons"] + parts["trays"] + parts["covers"] + parts["knuckles"]:
        vs = [v.co for v in o.data.vertices]
        ext = [max(v[i] for v in vs) - min(v[i] for v in vs) for i in range(3)]
        if o in parts["handles"]:
            plate, h, how = (ext[1], ext[2]), ext[0], "split face down"
        elif o in parts["pistons"]:
            plate, h, how = (ext[0], ext[2]), ext[1], "standing on its front face"
        elif o in parts["trays"]:
            plate, h, how = (ext[0], ext[1]), ext[2], "bottom down, open top up"
        elif o in parts["covers"]:
            plate, h, how = (ext[0], ext[1]), ext[2], "crown up, supported under"
        else:
            plate, h, how = (ext[0], ext[1]), ext[2], "post bore vertical"
        a, b = sorted(plate, reverse=True)
        fits = a <= bed[0] and b <= bed[1] and h <= bed[2]
        rows.append(f"{o.name:28s} {a:6.1f} x {b:6.1f} x {h:6.1f} mm  {how:28s} {'fits' if fits else 'DOES NOT FIT'}")
    text = "Print check (H2D single nozzle 325 x 320 x 325 mm)\n" + "\n".join(rows)
    print(text)
    with open(os.path.join(RENDERS, "print_check.txt"), "w") as fh:
        fh.write(text + "\n")

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
        "01_hero": camera(scene, "Cam hero", (0.55, 0.85, 0.40), (0.0, 0.06, 0.04), lens=50),
        "02_side": camera(scene, "Cam side", (1.5, 0.06, 0.05), (0.0, 0.06, 0.05), ortho=0.50),
        "03_handle_closeup": camera(scene, "Cam handle", (0.5, 0.40, 0.34), (0.17, 0.10, 0.12), lens=50),
        "04_top": camera(scene, "Cam top", (0.0, 0.06, 1.5), (0.0, 0.06, 0.0), ortho=0.62),
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
        moves += [(o, lift + Vector((45, 0, 0))) for o in bpy.data.objects if o.name.startswith("Fin R outboard")
                  or (o.name.startswith("Fin R bolt"))]
        moves += [(o, lift) for o in bpy.data.objects if o.name.startswith("Fin R inboard")]
        moves += [(o, lift) for o in bpy.data.objects if o.name in ("Load cell R", "Front washer R", "Front nut R")]
        moves += [(o, lift + Vector((0, 60, 0))) for o in bpy.data.objects if o.name in ("Piston R", "MTB grip R", "Rear washer R", "Rear nut R")]
        for o, d in moves:
            o.location += d
        cell = bpy.data.objects["Load cell R"]
        cell.hide_render = False
        render(scene, camera(scene, "Cam exploded", (0.75, 0.62, 0.38), (0.16, 0.1, 0.06), lens=45), "05_exploded.png")
        cell.hide_render = True
        for o, d in moves:
            o.location -= d

    # Head with the outboard half off and the piston drawn back: cell, couplers, sleeve, key.
    if not only or "08_head_open" in only:
        out = bpy.data.objects["Fin R outboard half"]
        out.hide_render = True
        moves = [(bpy.data.objects[n], Vector((0, 55, 0))) for n in ("Piston R", "MTB grip R", "Rear washer R", "Rear nut R")]
        for o, d in moves:
            o.location += d
        cell = bpy.data.objects["Load cell R"]
        cell.hide_render = False
        F = handle_frame()
        tgt = (HX / 1000 - 0.005, (F["ye"] + 22) / 1000, F["az"] / 1000 - 0.012)
        render(scene, camera(scene, "Cam head", (tgt[0] + 0.19, tgt[1] - 0.10, tgt[2] + 0.12), tgt, lens=60), "08_head_open.png")
        cell.hide_render = True
        out.hide_render = False
        for o, d in moves:
            o.location -= d

    # See-through printed parts with the cover off: electronics, cells and lead routing.
    if not only or "06_internals" in only:
        for o in parts["covers"]:
            o.hide_render = True
        for o in parts["handles"] + parts["trays"] + parts["pistons"] + parts["knuckles"]:
            for i in range(len(o.data.materials)):
                o.data.materials[i] = M["glass"]
        for o in hidden:
            o.hide_render = False
        render(scene, camera(scene, "Cam internals", (0.1, 0.62, 0.45), (-0.03, 0.04, -0.03), lens=40), "06_internals.png")
        render(scene, camera(scene, "Cam lead", (0.5, 0.11, 0.12), (0.178, 0.11, 0.12), lens=45), "07_lead_side.png")


main()
