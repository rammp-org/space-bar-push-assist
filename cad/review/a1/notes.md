# Reviewer notes, attempt 1 (measurements as made)

Blend copy: /tmp/pa_review_copy.blend (from cad/blender/check.blend). Tools: `<pcb>/scripts/cad`.

## Check runs
- `cad check copy checks.json cad/review/a1/cadcheck.json` (all checks): 1 fail (stability -20.6 deg, not applicable: unit is bolted), 65 warns, 65 untriaged. Warn list identical to designer's cadcheck_a1.json (set difference empty).
- `cad printcheck cad/print/stl_cc --manifest manifest.json`: PASS, 10 parts, 0 fail, 12 warn (cantilevers <= 2.3 mm). -> printcheck.json, printcheck/*.png
- `cad printcheck` on the 4 `*_standing.stl` (tonight P1S plate, not in stl_cc): PASS, 14 warns <= 1.7 mm. -> printcheck_standing.json
- `cad slice --detect`: bambustudio unusable (CLI segfault), no slicer run.
- Reviewer rows `review_rows.json`, `cad check ... --only distances,service,slide --overlay review_rows.json --overlay-only` -> cadcheck_review.json: 7 fail, 1 warn (below).

## Fastener bosses missing (root cause: build_tray_half adds bosses to `src`, then the `bay` cavity cut removes them)
- Land (M5 mount): ray along FST_M5_bolt_3 axis offset 6 mm, from inside: first tray material 6.0 mm past the head -> land is the 3 mm front wall only, designed boss (n 0.05..9) absent. cadcheck: "FST_M5_bolt_* head stands 6.0 mm off the part".
- Fin bolts (M4): ray x=130->+x at (y35,z0) hits tray at x=149.8, fin at 152.8 -> 3.0 mm end wall, boss (x 141.8..150.3) absent. cadcheck: M4 heads stand 4.0 mm off; engages 2.6 of 3.2 nut as modelled.
- Cover bosses: ray (74,12.265,15) down hits tray floor at z=-64 -> no boss. cadcheck: all 10 FST_Cover_screw_* "no material grips the thread".
- Board standoffs: ray (-12.9,46.25,-63) down hits floor at -64; ESP32 underside 1.21 mm above floor (`dist BUY_esp32_p4 PRT_tray_L` = 1.208), HX711_R 4.0 mm above floor. cadcheck: board screws 1.0-2.0 mm thread (needs 6.0). FST_Board_screw_2/3 need a 106 mm bit.
- RJ45 pad: ray (-40,85,-50) down hits floor at -64 -> pad absent.
- Section render: sec_x125_tray.png (M5 cap and cover screws floating in the cavity).

## Sensor head (right; left mirrored)
- Overload stop, piston rear face to bore step along -Y at r=15: 0.49-0.50 mm (`ray 192.8,104.99,0 0,-1,0`; distances row fails max 0.15). slide_out row: piston stops at 0.55 mm. No stop at all in pull (tension).
- Piston vs fin halves nearest: inboard 0.007 mm, outboard -0.496 mm3 overlap from y106.3 to y147.5 (key-rib root fillet on the slot edge, whole sleeve length). Under vol_tol so interference check is silent. distances rows min 0.2 fail at 0.00/0.01.
- Sleeve radial clearance: bore wall x 194.6 vs piston 194.284 -> 0.32 mm radial.
- Piston to cell 0.20 mm; cell to fin inboard 0.027 mm.
- Sleeve 45 mm (y105-150); grip 162-297 (centre ~230). Two-point bushing: reactions 2.78 Fv + 1.78 Fv = 4.56 Fv; friction 0.46-1.4 Fv for mu 0.1-0.3.
- Spigot Ø22.2/Ø16 (Z = 784 mm3), printed standing (layers across the axis). Root at y162, hand at 230 -> 68 mm: 150 N -> 13 MPa, 300 N -> 26 MPa vs 15 MPa interlayer.
- Rear M5 nut: spigot mouth y292, nut top y116.2 -> 175.8 mm deep + ~4 mm engagement = 180 mm reach; README says ~150 mm extension + socket.

## Mount
- Tray/plate contact only on the 40 mm land (knee z -13.6); front face vertical below it, plate leans 15 deg: gap 4.4 mm at z -30, ~27 mm at fin bottom z -115.
- Bolts at land centre: lever from knee 20 mm. Grip centre ~230 mm behind plate. Fv=150 N per handle -> 34.5 N m -> ~1725 N in the two bolts of that half. M5 cap head Ø8.5 on a 3 mm wall: punch perimeter 80 mm2.
- M5 x16 seated on the 3 mm wall would put the tip 13 mm below the plate face (check real 4040 slot depth; stand-in slot is 32 mm deep).

## Service / slide
- Cover straight up (+Z): blocked by BUY_corpus_back_plate at 2 mm (plate leans over its front edge). Along the plate face (0,0.259,0.966): slides out, 0.00 mm to tray (warn).
- Service rows: M4 fin bolts reachable straight 10 / L-key 15.5; M5 mount bolts straight 8 with covers off. Load cell swap: cover (10 screws) + 3 M4 + 6 M3 (heads on inboard face, only reachable with fin off) + 2 M5 nuts + grip.

## Print
- est per part (cadcheck parts): fins 4 x ~2.4 h / 124 g, trays 2 x 2.65 h / 137 g, covers 2 x 1.24 h / 61 g, pistons 2 x 0.74 h / 35 g. Total 18.9 h, 1061 g, 10 parts, 0 supports.
- Plate fit: fins flat 288 x 315 on H2D (5 mm margin to 320); all parts fit P1S individually.

## BOM (README) vs model (cad bom could not parse README: 0 rows, 40 screws in no row)
- Mount: README 4 x M8x16 button + M8 T-nut; model 4 x M5 cap x16 + M5 drop-in T-nut, holes Ø5.5.
- Fin to tray: README 6 x M4x20 DIN 7991 csk; model M4 cap x16 in Ø8 counterbores.
- Fin halves: README 12 x M3x35 csk from outboard into nuts in hex pockets; model 12 x M3 self-tap pan x30 from inboard into Ø2.5 pilots, round Ø6.5 counterbores, no hex pockets.
- Boards: README 12 x M3x10 csk + nut from under; model 8 x M3 self-tap x8 from above (HX711 2 holes each). FST_Board_screw_6/7 labelled host "Tray L" but sit in tray R.
- RJ45: README 2 x M3 into captive nuts; model 2 Ø2.5 pilots, no screws.
- Covers: README none ("cosmetic"); model 10 x M3 self-tap x12.
- HANDOFF rule "never thread into plastic": model has 30 self-tappers.

## Renders
- 02_side, 03, 04, 05_exploded, 06, 07_lead_side, 08 dated Oct 23; build/manifest/hero Oct 26 -> stale. Only 01_hero and step1-4 current.
- r_left_fin_outboard.png (reviewer): outboard face clean, no holes (ray 210,40,15 -> face at 202.8).
