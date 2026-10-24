FeatureScript 3070;
import(path : "onshape/std/geometry.fs", version : "3070.0");

/**
 * T-slot aluminium extrusion generator.
 *
 * Builds a length of T-slot ("80/20 style") extrusion from a chosen profile series.
 * The cross section is generated as: a rounded outer rectangle, minus one T-slot
 * cavity per cell per face, minus one centre bore per cell. The diagonal ribs of a
 * real extrusion fall out of that as the material left between adjacent cavities.
 *
 * Each cavity is clipped to stay half a rib thickness clear of the 45 degree diagonal
 * running from the cell corner to the centre. Without that clip, adjacent channels
 * overlap at the corners and the bar falls apart into four disconnected corner pieces,
 * so `channelWidth` acts as an upper bound that the rib clip may reduce.
 *
 * Preset dimensions are the common generic values for each metric series and are close
 * to, but not guaranteed identical to, any single manufacturer's catalogue. Pick
 * `Custom` to enter exact numbers from a datasheet.
 */

// ------------------------------------------------------------------ constants

const EXTRUSION_LENGTH_BOUNDS =
{
    (meter)      : [1e-5, 0.25, 100],
    (centimeter) : 25.0,
    (millimeter) : 250.0,
    (inch)       : 10.0,
    (foot)       : 1.0
} as LengthBoundSpec;

// Each custom dimension needs its own default, otherwise picking `Custom` starts from a
// cross section that cannot be built (every value landing on the same number).
const CELL_SIZE_BOUNDS =
{
    (meter)      : [1e-5, 0.02, 1],
    (centimeter) : 2.0,
    (millimeter) : 20.0,
    (inch)       : 0.75
} as LengthBoundSpec;

const SLOT_OPENING_BOUNDS =
{
    (meter)      : [1e-5, 0.006, 0.5],
    (centimeter) : 0.6,
    (millimeter) : 6.0,
    (inch)       : 0.25
} as LengthBoundSpec;

const LIP_DEPTH_BOUNDS =
{
    (meter)      : [1e-5, 0.002, 0.5],
    (centimeter) : 0.2,
    (millimeter) : 2.0,
    (inch)       : 0.08
} as LengthBoundSpec;

const CHANNEL_WIDTH_BOUNDS =
{
    (meter)      : [1e-5, 0.011, 0.5],
    (centimeter) : 1.1,
    (millimeter) : 11.0,
    (inch)       : 0.43
} as LengthBoundSpec;

const CHANNEL_DEPTH_BOUNDS =
{
    (meter)      : [1e-5, 0.006, 0.5],
    (centimeter) : 0.6,
    (millimeter) : 6.0,
    (inch)       : 0.25
} as LengthBoundSpec;

const BORE_DIAMETER_BOUNDS =
{
    (meter)      : [0, 0.0042, 0.5],
    (centimeter) : 0.42,
    (millimeter) : 4.2,
    (inch)       : 0.166
} as LengthBoundSpec;

// std's POSITIVE_COUNT_BOUNDS defaults to 2, which would start Custom on a 2 x 2 grid.
const CELL_COUNT_BOUNDS =
{
    (unitless) : [1, 1, 20]
} as IntegerBoundSpec;

const RIB_THICKNESS_BOUNDS =
{
    (meter)      : [1e-5, 0.0018, 0.05],
    (centimeter) : 0.18,
    (millimeter) : 1.8,
    (inch)       : 0.07
} as LengthBoundSpec;

const CORNER_RADIUS_BOUNDS =
{
    (meter)      : [0, 0.0015, 0.05],
    (centimeter) : 0.15,
    (millimeter) : 1.5,
    (inch)       : 0.0625
} as LengthBoundSpec;

// How far the cutting bodies run past each end of the bar, so the boolean never has to
// resolve coincident end caps.
const CUT_OVERSHOOT = 1 * millimeter;

// ------------------------------------------------------------------- profiles

export enum ExtrusionProfile
{
    annotation { "Name" : "20 x 20 mm (6 mm slot)" }
    S20X20,
    annotation { "Name" : "20 x 40 mm (6 mm slot)" }
    S20X40,
    annotation { "Name" : "30 x 30 mm (8 mm slot)" }
    S30X30,
    annotation { "Name" : "30 x 60 mm (8 mm slot)" }
    S30X60,
    annotation { "Name" : "40 x 40 mm (8 mm slot)" }
    S40X40,
    annotation { "Name" : "40 x 80 mm (8 mm slot)" }
    S40X80,
    annotation { "Name" : "Custom" }
    CUSTOM
}

/**
 * Nominal cross-section dimensions for one cell of each metric series.
 *
 * `slotOpening`  width of the gap at the outer face
 * `lipDepth`     how far in the parallel-sided part of the opening runs
 * `channelWidth` width of the undercut channel behind the lip
 * `channelDepth` distance from the outer face to the bottom of the channel
 * `boreDiameter` central hole, tapped for the series' fastener
 * `cornerRadius` rounding on the four outer corners
 * `ribThickness` material left on the diagonal between two adjacent channels
 */
function seriesDimensions(series is number) returns map
{
    if (series == 20)
    {
        return {
                "cellSize" : 20 * millimeter,
                "slotOpening" : 6 * millimeter,
                "lipDepth" : 2 * millimeter,
                "channelWidth" : 11 * millimeter,
                "channelDepth" : 6 * millimeter,
                "boreDiameter" : 4.2 * millimeter,
                "cornerRadius" : 1.5 * millimeter,
                "ribThickness" : 1.8 * millimeter
            };
    }
    if (series == 30)
    {
        return {
                "cellSize" : 30 * millimeter,
                "slotOpening" : 8 * millimeter,
                "lipDepth" : 2.5 * millimeter,
                "channelWidth" : 16.5 * millimeter,
                "channelDepth" : 8.5 * millimeter,
                "boreDiameter" : 6.8 * millimeter,
                "cornerRadius" : 2 * millimeter,
                "ribThickness" : 2.5 * millimeter
            };
    }
    return {
            "cellSize" : 40 * millimeter,
            "slotOpening" : 8 * millimeter,
            "lipDepth" : 2.7 * millimeter,
            "channelWidth" : 16.5 * millimeter,
            "channelDepth" : 10.5 * millimeter,
            "boreDiameter" : 10.2 * millimeter,
            "cornerRadius" : 2 * millimeter,
            "ribThickness" : 3 * millimeter
        };
}

/** Resolve the feature parameters into a single cross-section dimension map. */
function profileDimensions(definition is map) returns map
{
    if (definition.profile == ExtrusionProfile.CUSTOM)
    {
        return {
                "cellSize" : definition.cellSize,
                "cellsX" : definition.cellsX,
                "cellsY" : definition.cellsY,
                "slotOpening" : definition.slotOpening,
                "lipDepth" : definition.lipDepth,
                "channelWidth" : definition.channelWidth,
                "channelDepth" : definition.channelDepth,
                "boreDiameter" : definition.boreDiameter,
                "cornerRadius" : definition.cornerRadius,
                "ribThickness" : definition.ribThickness
            };
    }

    var series = 40;
    var cellsX = 1;
    if (definition.profile == ExtrusionProfile.S20X20)
    {
        series = 20;
    }
    else if (definition.profile == ExtrusionProfile.S20X40)
    {
        series = 20;
        cellsX = 2;
    }
    else if (definition.profile == ExtrusionProfile.S30X30)
    {
        series = 30;
    }
    else if (definition.profile == ExtrusionProfile.S30X60)
    {
        series = 30;
        cellsX = 2;
    }
    else if (definition.profile == ExtrusionProfile.S40X80)
    {
        cellsX = 2;
    }

    return mergeMaps(seriesDimensions(series), { "cellsX" : cellsX, "cellsY" : 1 });
}

/**
 * Derive the actual cavity outline from the nominal dimensions.
 *
 * `ribLimit` is the largest value of (offset along the face + depth) a cavity may reach:
 * it holds every cavity half a rib clear of the 45 degree diagonal to the cell corner,
 * which is what leaves the diagonal ribs of a real extrusion in place.
 */
function slotGeometry(dims is map) returns map
{
    const cellHalf = dims.cellSize / 2;
    const halfOpening = dims.slotOpening / 2;
    const ribLimit = cellHalf - dims.ribThickness / sqrt(2);

    if (dims.slotOpening >= dims.cellSize - 2 * dims.cornerRadius)
    {
        throw regenError("Slot opening is too wide for the cell size.", ["slotOpening", "cellSize"]);
    }
    if (dims.channelWidth < dims.slotOpening)
    {
        throw regenError("Channel width must be at least the slot opening.", ["channelWidth", "slotOpening"]);
    }
    if (ribLimit <= halfOpening + dims.lipDepth)
    {
        throw regenError("Rib thickness leaves no room for the slot.", ["ribThickness", "cellSize"]);
    }

    // Widest half-width the rib clip allows, given that the flare runs out at 45 degrees.
    const halfChannelCap = (ribLimit - dims.lipDepth + halfOpening) / 2;
    const halfChannel = dims.channelWidth / 2 < halfChannelCap ? dims.channelWidth / 2 : halfChannelCap;
    const flareDepth = dims.lipDepth + (halfChannel - halfOpening);

    if (dims.channelDepth <= flareDepth)
    {
        throw regenError("Channel depth must exceed the lip depth plus the flare.",
                ["channelDepth", "lipDepth"]);
    }
    if (dims.channelDepth >= ribLimit)
    {
        throw regenError("Channel depth is too deep for this cell size and rib thickness.",
                ["channelDepth", "ribThickness"]);
    }
    if (dims.channelDepth + dims.boreDiameter / 2 >= cellHalf)
    {
        throw regenError("Channel depth and bore diameter overlap at the centre of the cell.",
                ["channelDepth", "boreDiameter"]);
    }

    const bottomCap = ribLimit - dims.channelDepth;
    return {
            "halfOpening" : halfOpening,
            "lipDepth" : dims.lipDepth,
            "halfChannel" : halfChannel,
            "flareDepth" : flareDepth,
            "halfBottom" : halfChannel < bottomCap ? halfChannel : bottomCap,
            "channelDepth" : dims.channelDepth
        };
}

// -------------------------------------------------------------- profile shape

/**
 * Closed point loop for one T-slot cavity, in sketch coordinates.
 *
 * @param faceCenter : Midpoint of this slot on the outer face.
 * @param inward : Unitless 2d direction pointing from that face into the material.
 */
function slotCavityPoints(faceCenter is Vector, inward is Vector, geom is map) returns array
{
    const along = vector(-inward[1], inward[0]); // 90 degrees from `inward`, along the face

    // (offset along the face, depth into the material); negative depth pokes out through
    // the face so the cavity always breaks the surface cleanly.
    const profile = [
            [-geom.halfOpening, -CUT_OVERSHOOT],
            [-geom.halfOpening, geom.lipDepth],
            [-geom.halfChannel, geom.flareDepth],
            [-geom.halfBottom, geom.channelDepth],
            [geom.halfBottom, geom.channelDepth],
            [geom.halfChannel, geom.flareDepth],
            [geom.halfOpening, geom.lipDepth],
            [geom.halfOpening, -CUT_OVERSHOOT]
        ];

    var points = [];
    for (var uv in profile)
    {
        points = append(points, faceCenter + along * uv[0] + inward * uv[1]);
    }
    return append(points, points[0]); // close the loop
}

/** Draw the outer boundary: a rectangle with the four corners rounded. */
function addOuterBoundary(sketch is Sketch, halfWidth is ValueWithUnits, halfHeight is ValueWithUnits,
    radius is ValueWithUnits)
{
    const a = halfWidth;
    const b = halfHeight;

    if (radius <= TOLERANCE.zeroLength * meter)
    {
        skRectangle(sketch, "outer", { "firstCorner" : vector(-a, -b), "secondCorner" : vector(a, b) });
        return;
    }

    const r = radius;
    const diag = r / sqrt(2);

    // Straight runs between the corner arcs.
    skLineSegment(sketch, "outerBottom", { "start" : vector(-a + r, -b), "end" : vector(a - r, -b) });
    skLineSegment(sketch, "outerRight", { "start" : vector(a, -b + r), "end" : vector(a, b - r) });
    skLineSegment(sketch, "outerTop", { "start" : vector(a - r, b), "end" : vector(-a + r, b) });
    skLineSegment(sketch, "outerLeft", { "start" : vector(-a, b - r), "end" : vector(-a, -b + r) });

    // Corner arcs, each given by start / midpoint / end.
    const corners = [
            [vector(a - r, -b + r), vector(1, -1), vector(a - r, -b), vector(a, -b + r)],
            [vector(a - r, b - r), vector(1, 1), vector(a, b - r), vector(a - r, b)],
            [vector(-a + r, b - r), vector(-1, 1), vector(-a + r, b), vector(-a, b - r)],
            [vector(-a + r, -b + r), vector(-1, -1), vector(-a, -b + r), vector(-a + r, -b)]
        ];

    for (var i = 0; i < size(corners); i += 1)
    {
        const corner = corners[i];
        skArc(sketch, "outerArc" ~ i, {
                    "start" : corner[2],
                    "mid" : corner[0] + corner[1] * diag,
                    "end" : corner[3]
                });
    }
}

/** Add every T-slot cavity and centre bore for the given cell grid. */
function addCavities(sketch is Sketch, dims is map, geom is map)
{
    const s = dims.cellSize;
    const nx = dims.cellsX;
    const ny = dims.cellsY;
    const halfWidth = nx * s / 2;
    const halfHeight = ny * s / 2;

    var slotIndex = 0;
    for (var i = 0; i < nx; i += 1)
    {
        const cx = -halfWidth + s * (i + 0.5);
        // Top and bottom faces get one slot per column.
        for (var side in [1, -1])
        {
            const faceCenter = vector(cx, halfHeight * side);
            const inward = vector(0, -side);
            skPolyline(sketch, "slot" ~ slotIndex, { "points" : slotCavityPoints(faceCenter, inward, geom) });
            slotIndex += 1;
        }
    }

    for (var j = 0; j < ny; j += 1)
    {
        const cy = -halfHeight + s * (j + 0.5);
        // Left and right faces get one slot per row.
        for (var side in [1, -1])
        {
            const faceCenter = vector(halfWidth * side, cy);
            const inward = vector(-side, 0);
            skPolyline(sketch, "slot" ~ slotIndex, { "points" : slotCavityPoints(faceCenter, inward, geom) });
            slotIndex += 1;
        }
    }

    if (dims.boreDiameter > TOLERANCE.zeroLength * meter)
    {
        var boreIndex = 0;
        for (var i = 0; i < nx; i += 1)
        {
            for (var j = 0; j < ny; j += 1)
            {
                skCircle(sketch, "bore" ~ boreIndex, {
                            "center" : vector(-halfWidth + s * (i + 0.5), -halfHeight + s * (j + 0.5)),
                            "radius" : dims.boreDiameter / 2
                        });
                boreIndex += 1;
            }
        }
    }
}

// ------------------------------------------------------------------ placement

/** The plane the bar starts from: a selected plane, face, or mate connector; else the origin. */
function resolveStartPlane(context is Context, definition is map) returns Plane
{
    if (isQueryEmpty(context, definition.startPlane))
    {
        return XY_PLANE;
    }

    const asPlane = try silent(evPlane(context, { "face" : definition.startPlane }));
    if (asPlane != undefined)
    {
        return asPlane;
    }

    const asMateConnector = try silent(evMateConnector(context, { "mateConnector" : definition.startPlane }));
    if (asMateConnector != undefined)
    {
        return plane(asMateConnector);
    }

    throw regenError("Select a plane, a planar face, or a mate connector.", ["startPlane"]);
}

// -------------------------------------------------------------------- feature

annotation { "Feature Type Name" : "Aluminum extrusion" }
export const aluminumExtrusion = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Profile" }
        definition.profile is ExtrusionProfile;

        if (definition.profile == ExtrusionProfile.CUSTOM)
        {
            annotation { "Name" : "Cell size" }
            isLength(definition.cellSize, CELL_SIZE_BOUNDS);

            annotation { "Name" : "Cells across" }
            isInteger(definition.cellsX, CELL_COUNT_BOUNDS);

            annotation { "Name" : "Cells up" }
            isInteger(definition.cellsY, CELL_COUNT_BOUNDS);

            annotation { "Name" : "Slot opening" }
            isLength(definition.slotOpening, SLOT_OPENING_BOUNDS);

            annotation { "Name" : "Lip depth" }
            isLength(definition.lipDepth, LIP_DEPTH_BOUNDS);

            annotation { "Name" : "Channel width" }
            isLength(definition.channelWidth, CHANNEL_WIDTH_BOUNDS);

            annotation { "Name" : "Channel depth" }
            isLength(definition.channelDepth, CHANNEL_DEPTH_BOUNDS);

            annotation { "Name" : "Centre bore diameter" }
            isLength(definition.boreDiameter, BORE_DIAMETER_BOUNDS);

            annotation { "Name" : "Diagonal rib thickness" }
            isLength(definition.ribThickness, RIB_THICKNESS_BOUNDS);

            annotation { "Name" : "Corner radius" }
            isLength(definition.cornerRadius, CORNER_RADIUS_BOUNDS);
        }

        annotation { "Name" : "Length" }
        isLength(definition.length, EXTRUSION_LENGTH_BOUNDS);

        annotation { "Name" : "Start plane or mate connector",
                     "Filter" : GeometryType.PLANE || BodyType.MATE_CONNECTOR,
                     "MaxNumberOfPicks" : 1 }
        definition.startPlane is Query;

        annotation { "Name" : "Symmetric about plane" }
        definition.symmetric is boolean;

        annotation { "Name" : "Opposite direction", "UIHint" : UIHint.OPPOSITE_DIRECTION }
        definition.flipDirection is boolean;
    }
    {
        const dims = profileDimensions(definition);
        const geom = slotGeometry(dims);

        const halfWidth = dims.cellsX * dims.cellSize / 2;
        const halfHeight = dims.cellsY * dims.cellSize / 2;

        const startPlane = resolveStartPlane(context, definition);
        const direction = definition.flipDirection ? -startPlane.normal : startPlane.normal;

        const endDepth = definition.symmetric ? definition.length / 2 : definition.length;
        const startDepth = definition.symmetric ? definition.length / 2 : 0 * meter;

        // 1. The solid bar.
        var barSketch = newSketchOnPlane(context, id + "barSketch", { "sketchPlane" : startPlane });
        addOuterBoundary(barSketch, halfWidth, halfHeight, dims.cornerRadius);
        skSolve(barSketch);

        var barExtrude = {
            "entities" : qSketchRegion(id + "barSketch"),
            "direction" : direction,
            "endBound" : BoundingType.BLIND,
            "endDepth" : endDepth
        };
        if (definition.symmetric)
        {
            barExtrude.startBound = BoundingType.BLIND;
            barExtrude.startDepth = startDepth;
        }
        opExtrude(context, id + "barExtrude", barExtrude);

        // 2. The slots and bores, run long at both ends so the boolean stays clean.
        var cutSketch = newSketchOnPlane(context, id + "cutSketch", { "sketchPlane" : startPlane });
        addCavities(cutSketch, dims, geom);
        skSolve(cutSketch);

        opExtrude(context, id + "cutExtrude", {
                    "entities" : qSketchRegion(id + "cutSketch"),
                    "direction" : direction,
                    "endBound" : BoundingType.BLIND,
                    "endDepth" : endDepth + CUT_OVERSHOOT,
                    "startBound" : BoundingType.BLIND,
                    "startDepth" : startDepth + CUT_OVERSHOOT
                });

        opBoolean(context, id + "subtractCavities", {
                    "tools" : qCreatedBy(id + "cutExtrude", EntityType.BODY),
                    "targets" : qCreatedBy(id + "barExtrude", EntityType.BODY),
                    "operationType" : BooleanOperationType.SUBTRACTION
                });

        // 3. Tidy up the construction sketches.
        opDeleteBodies(context, id + "deleteSketches", {
                    "entities" : qUnion([
                                qCreatedBy(id + "barSketch", EntityType.BODY),
                                qCreatedBy(id + "cutSketch", EntityType.BODY)
                            ])
                });

        setProperty(context, {
                    "entities" : qCreatedBy(id + "barExtrude", EntityType.BODY),
                    "propertyType" : PropertyType.NAME,
                    "value" : "Extrusion " ~ round(dims.cellsX * dims.cellSize / millimeter) ~ "x" ~
                    round(dims.cellsY * dims.cellSize / millimeter) ~ " - " ~
                    round(definition.length / millimeter) ~ "mm"
                });
    });
