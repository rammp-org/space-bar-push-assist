FeatureScript 3070;
import(path : "onshape/std/geometry.fs", version : "3070.0");

// Reference envelopes for the bought-in parts of the push-assist handle.
// These are keep-out models for packaging, not detailed replicas. Every dimension
// is in millimetres and noted with its source; "est." means scaled off a vendor
// drawing or assumed from a typical part, so measure before cutting anything tight.

// ------------------------------------------------------------------ helpers

function mm(x is number) returns ValueWithUnits
{
    return x * millimeter;
}

function pt(x is number, y is number, z is number) returns Vector
{
    return vector(x, y, z) * millimeter;
}

/** Axis-aligned block from two corners in mm. */
function block(context is Context, id is Id, x0 is number, y0 is number, z0 is number,
    x1 is number, y1 is number, z1 is number)
{
    fCuboid(context, id, { "corner1" : pt(x0, y0, z0), "corner2" : pt(x1, y1, z1) });
}

/** Cylinder between two centre points in mm. */
function rod(context is Context, id is Id, a is Vector, b is Vector, diameter is number)
{
    fCylinder(context, id, { "bottomCenter" : a * millimeter, "topCenter" : b * millimeter, "radius" : mm(diameter / 2) });
}

/** Union everything this feature made into one part, drill it, then name and colour it. */
function finishPart(context is Context, id is Id, holeIds is array, name is string, colour is Color)
{
    var holeQueries = [];
    for (var h in holeIds)
    {
        holeQueries = append(holeQueries, qCreatedBy(h, EntityType.BODY));
    }
    const holes = qUnion(holeQueries);
    const solids = qSubtraction(qBodyType(qCreatedBy(id, EntityType.BODY), BodyType.SOLID), holes);

    if (size(evaluateQuery(context, solids)) > 1)
    {
        opBoolean(context, id + "union", {
                    "tools" : solids,
                    "operationType" : BooleanOperationType.UNION
                });
    }
    if (size(holeIds) > 0)
    {
        opBoolean(context, id + "drill", {
                    "tools" : holes,
                    "targets" : qSubtraction(qBodyType(qCreatedBy(id, EntityType.BODY), BodyType.SOLID), holes),
                    "operationType" : BooleanOperationType.SUBTRACTION
                });
    }
    const part = qBodyType(qCreatedBy(id, EntityType.BODY), BodyType.SOLID);
    setProperty(context, { "entities" : part, "propertyType" : PropertyType.NAME, "value" : name });
    setProperty(context, { "entities" : part, "propertyType" : PropertyType.APPEARANCE, "value" : colour });
}

// ------------------------------------------------------------------ HX711

// SparkFun SEN-13879 (HX711 v1.1). Outline, holes and headers from the Eagle .brd.
// Origin: board corner, PCB top face at z = 1.6, components up.
annotation { "Feature Type Name" : "HX711 board (SparkFun)" }
export const hx711Board = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Include pin headers" }
        definition.headers is boolean;
    }
    {
        const t = 1.6;
        block(context, id + "pcb", 0, 0, 0, 30.48, 22.86, t);
        // HX711 SO16, rotated so its long side runs along Y.
        block(context, id + "ic", 15.24 - 2, 11.43 - 5, t, 15.24 + 2, 11.43 + 5, t + 1.75);
        if (definition.headers)
        {
            // JP4: load cell side (E+, E-, A-, A+, shield). J1: MCU side (GND, DAT, CLK, VCC, VDD).
            // Straight 0.1" male headers, 2.5 mm body + 6 mm pins.
            block(context, id + "jp4", 0, 6.35 - 6.35, t, 2.54, 6.35 + 6.35, t + 8.5);
            block(context, id + "j1", 27.94, 16.51 - 6.35, t, 30.48, 16.51 + 6.35, t + 8.5);
        }
        var holeIds = [];
        var i = 0;
        for (var p in [[2.54, 2.54], [27.94, 2.54], [2.54, 20.32], [27.94, 20.32]])
        {
            rod(context, id + ("hole" ~ i), vector(p[0], p[1], -1), vector(p[0], p[1], t + 1), 3.302);
            holeIds = append(holeIds, id + ("hole" ~ i));
            i += 1;
        }
        finishPart(context, id, holeIds, "HX711 (SparkFun SEN-13879)", color(0.75, 0.1, 0.1));
    });

// ------------------------------------------------------------------ ESP32-P4

// Waveshare ESP32-P4-WIFI6-POE-ETH. Outline 55 x 68 and the 48 x 33 hole pattern are from
// the vendor drawing. Holes (3 mm, 9.25 mm from the GPIO edge) and the RJ45 / USB heights
// are measured. Other component positions are scaled off the drawing (est.).
// Origin: board corner, RJ45 edge along y = 0, GPIO header along y = 68, PCB top at z = 1.6.
annotation { "Feature Type Name" : "ESP32-P4 PoE board (Waveshare)" }
export const esp32P4PoeBoard = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Include underside keep-out" }
        definition.underside is boolean;
    }
    {
        const t = 1.6;
        block(context, id + "pcb", 0, 0, 0, 55, 68, t);

        block(context, id + "gpio", 27.5 - 25.4, 62.2, t, 27.5 + 25.4, 67.3, t + 8.5);       // 2x20 male header
        block(context, id + "rj45", 29.93 - 8, -1.5, t, 29.93 + 8, 19.8, t + 13.5);         // PoE magjack, measured height
        block(context, id + "usb", 12 - 7, -1.5, t, 12 + 7, 16.3, t + 16.75);               // USB-A over USB-C stack, measured height
        block(context, id + "tf", 38.8, 1, t, 51.5, 12.8, t + 1.9);                        // microSD
        block(context, id + "core", 14.8, 38.4, t, 32, 59.7, t + 3.2);                     // ESP32-P4 core module
        block(context, id + "c6", 18.3, 25.4, t, 31.4, 37.6, t + 2.6);                     // ESP32-C6 WiFi module
        block(context, id + "xfmr", 33.7, 30.1, t, 45.6, 44.3, t + 10);                    // PoE transformer, est.
        block(context, id + "ffc", 1.5, 32, t, 13.5, 51, t + 2.5);                         // LCD + CAM FPC sockets
        rod(context, id + "cap1", vector(50.9, 42, t), vector(50.9, 42, t + 8), 6.3);      // 220 uF 16 V
        rod(context, id + "cap2", vector(50.9, 33.7, t), vector(50.9, 33.7, t + 8), 6.3);  // 220 uF 16 V
        rod(context, id + "cap3", vector(41.4, 22.3, t), vector(41.4, 22.3, t + 10), 8);   // 22 uF 100 V
        if (definition.underside)
        {
            // Covers the 2-pin speaker JST (3.75 mm, measured) plus through-hole legs. Position of
            // the JST is not modelled, so the whole underside is kept clear to that depth.
            block(context, id + "under", 1, 1, -3.75, 54, 67, 0);
        }

        var holeIds = [];
        var i = 0;
        for (var p in [[3.5, 68 - 9.25 - 33], [51.5, 68 - 9.25 - 33], [3.5, 68 - 9.25], [51.5, 68 - 9.25]])
        {
            rod(context, id + ("hole" ~ i), vector(p[0], p[1], -3), vector(p[0], p[1], t + 1), 3);
            holeIds = append(holeIds, id + ("hole" ~ i));
            i += 1;
        }
        finishPart(context, id, holeIds, "ESP32-P4-WIFI6-POE-ETH (Waveshare)", color(0.12, 0.12, 0.12));
    });

// ------------------------------------------------------------------ RJ45 panel coupler

// ANMBEST shielded waterproof RJ45 panel coupler. Listing gives a 20.8 mm panel hole,
// ~36 mm overall length and a 1.5-10 mm panel. Flange, cap and nut sizes are est.
// Origin: centre of the panel hole on the panel's outside face; +Z points out of the box.
annotation { "Feature Type Name" : "RJ45 panel coupler (ANMBEST)" }
export const rj45PanelCoupler = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Panel thickness" }
        isLength(definition.panelThickness, { (millimeter) : [1.5, 3, 10] } as LengthBoundSpec);
    }
    {
        const panel = definition.panelThickness / millimeter;
        block(context, id + "flange", -13, -13, 0, 13, 13, 3);                              // square flange, est.
        rod(context, id + "cap", vector(0, 0, 3), vector(0, 0, 9), 24);                     // dust-cap thread, est.
        rod(context, id + "body", vector(0, 0, -27), vector(0, 0, 0), 20.5);                // threaded barrel
        // Hex nut, 27 mm across flats, clamped to the inside of the panel.
        var nut = newSketchOnPlane(context, id + "nutSketch", { "sketchPlane" : plane(pt(0, 0, -panel), vector(0, 0, 1)) });
        skRegularPolygon(nut, "hex", { "center" : vector(0, 0) * millimeter, "firstVertex" : vector(27 / sqrt(3), 0) * millimeter, "sides" : 6 });
        skSolve(nut);
        opExtrude(context, id + "nut", {
                    "entities" : qSketchRegion(id + "nutSketch"),
                    "direction" : vector(0, 0, -1),
                    "endBound" : BoundingType.BLIND,
                    "endDepth" : mm(4)
                });
        opDeleteBodies(context, id + "deleteSketch", { "entities" : qCreatedBy(id + "nutSketch", EntityType.BODY) });
        // Plug openings, so the model shows which way the cables go in.
        block(context, id + "plugOut", -6, -4.5, -28, 6, 4.5, -10);
        block(context, id + "plugIn", -6, -4.5, 5, 6, 4.5, 10);
        finishPart(context, id, [id + "plugOut", id + "plugIn"], "RJ45 panel coupler (ANMBEST)", color(0.6, 0.6, 0.62));
    });

// ------------------------------------------------------------------ MTB grip

// Standard lock-on mountain bike grip: fits a 22.2 mm (7/8") bar. Length and OD vary by
// grip; 135 x 32 mm is typical. Origin: bar axis at the inboard end, grip runs along +X.
// The 22.2 mm bore is the dimension that matters: the handle tube we design must match it.
annotation { "Feature Type Name" : "MTB lock-on grip" }
export const mtbGrip = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Grip length" }
        isLength(definition.length, { (millimeter) : [80, 135, 200] } as LengthBoundSpec);

        annotation { "Name" : "Grip outer diameter" }
        isLength(definition.outerDiameter, { (millimeter) : [26, 32, 40] } as LengthBoundSpec);

        annotation { "Name" : "Bar diameter" }
        isLength(definition.barDiameter, { (millimeter) : [19, 22.2, 25.4] } as LengthBoundSpec);
    }
    {
        const len = definition.length / millimeter;
        const od = definition.outerDiameter / millimeter;
        const bar = definition.barDiameter / millimeter;
        rod(context, id + "collar", vector(0, 0, 0), vector(8, 0, 0), od + 1);              // lock-on clamp, est.
        rod(context, id + "rubber", vector(8, 0, 0), vector(len, 0, 0), od);
        rod(context, id + "bore", vector(-1, 0, 0), vector(len - 3, 0, 0), bar);             // closed outer end
        finishPart(context, id, [id + "bore"], "MTB lock-on grip", color(0.08, 0.08, 0.08));
    });
