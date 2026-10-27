# Review a3 notes (reviewer)
- copy of check.blend at /tmp/a3_check.blend

## Checks re-run
- `cad check /tmp/a3_check.blend checks.json a3/cadcheck.json --only parts,...,cables` -> PASS 0 fail, 23 warn (0 untriaged, 23 accepted). Identical to designer's cadcheck_a3.json.
- a2 review_rows.json verbatim overlay (a3/cadcheck_a2rows.json): 3 FAIL (piston->pin slide stopped by cartridge at 0.05; pin "held by fin" slides 2 mm because it overlaps the cartridge at rest; piston-to-cell 0.85), passes: stop nut to piston 9.675, piston to fin 1.093/1.086, cover lifts.
- Designer's a3_designer/a2_review_rows_verbatim.json is a cadcheck REPORT, not the rows file.

## Moving link (reviewer split, scripts/split_moving_link.py -> /tmp/a3_moving.blend, PRT_movlink_R/L check-only)
- overlay review_rows.json (a3/cadcheck_review.json): moving link + piston + grip slides: -y 0.35, +y 0.35, -z 0.35, +z 0.40 all blocked by FST_Stop_pin (nearest pin gap 0.25; slide detection lags ~0.1 on the faceted pin) ; sideways +-x 1.05 blocked by fin halves. Nearest moving link to fin = 1.0 (both halves, both sides).
- a2 "pin held by fin" adapted: cartridge ground + pin slid +y/-y blocked by fin at 0.15 (0.1 fit + step).
- => cad check CAN test the moving link with a check-only split object; designer's "cadcheck cannot sweep it" overclaims.

## Geometry (build_concept.py build_cartridge, lines 812-856)
- leaves: x +-18 (36 wide), y 61-62.5 and 108.5-110 (1.5 t, 47.5 pitch), z from -42.5 (ground bar top -42) to -6, joined to top link octagon (bottom z -15 for |x'|<10, 45 deg chamfer 8 to z -7 at |x'|=18) => free length 27 at centre, 35 at the edges. Sharp (unfilleted) roots at both ends (box unions, no fillet).
- tongue: V prism x' +-10 at z -12..-15, tip z -25, y 84-96; stop hole O4.5 at z -21: V-edge wall below hole = 4/sqrt2 - 2.25 = 0.58 mm (cadcheck min wall 1.19 accepted warn).
- post: y 83-97, pin O4.05 at z -21, 21.5 above ground bar top.
- print: cartridge build dir = world x (print_rot row3 [1,0,0]); leaf length z and thickness y in the layer plane (flexures row angle 0). Sideways x load on the grip = interlayer shear in the leaves.
- cell face contact: cell front face full O25.4 on 3 mm PLA front plate (+3.4 fin floor), rear face full O25.4 on top-link front wall; studs clamped by nuts both sides => cell is a rigid parallel path for moment/shear.
- review_rows.json slide windows widened to [0.15,0.45] (pin is faceted; nearest gap 0.25); re-run: PASS 0 fail.

## Flexure hand calcs (scripts/flexure_calc.py -> flexure_calc.txt)
- leaf pair stiffness 31-43 N/mm (E 2.5-3.5 GPa); rear-leaf buckling 1.1-1.9 kN (t 1.4-1.5)
- root stress at stop: 4.6 MPa nominal at 0.25, 8.8 at worst-case 0.475; x2.0-2.5 for sharp roots -> 9-12 / 18-22 MPa
- stop engagement vs 20 kg FS 196 N: dFS 0.05 -> 5.1xFS (9.6x worst); 0.10 -> 2.6x (4.9x); 0.15 -> 1.7x (3.3x); 0.20 -> 1.3x (2.5x)
- moment share: leaves 6.8e6 N.mm/rad vs full-face clamped cell 5.9e6 -> cell takes ~47 %; 50 N down at grip = 3.9 N.m through the cell (edge-load equiv 304 N = 1.6xFS); 150 N -> 11.6 N.m (4.7xFS). With O8 seat bosses -> 0.8 %.
- sideways 150 N: 11.8 MPa interlayer shear in leaves (layers stacked along x).
- tongue wall under O4.5 hole 0.58 mm (loaded only by +z lift overload).

## Other measurements
- printcheck (a3/printcheck.json): PASS 11 parts, 0 fail, 8 warn (67 mm E-roof = anchored arms, layer map fin_R_inboard_z018.0_bridge.png agreed; 1.1 mm ledges).
- own overhang map (scripts/overhang_map.py), faces >46 deg from vertical: cartridge 30 mm2 (O5.5 stud hole crowns, z 20); piston 0; cover 0; fin_in 147, fin_out 225 (167 at z<0.5: bed-face recesses = M4 nut slot 0.5 into outboard half, short bridges); tray_L 704 (345 at z<3 = O14 bit hole crown; 78 at z 10-16 = lower M5 hole/cbore crowns; 63 at z 71-76 = upper M5 crowns). Designer's tray explanation omits the M5 hole crowns. All short spans: no supports.
- lip: inside 192.8/162.8,148,0 -> fin solid (round bore last 4 mm); y144 void (teardrop). Skin over teardrop tip 7.7 mm.
- cad bom PASS 10 rows. slicer unusable (bambustudio segfault, known).
- distances: cell to fin 0.2 (front rim), cartridge to fin 0.1 (fit), lead to fin 0.69, piston screw head to fin 1.2.
- patch cable path 149.97 vs 150 nominal (row lead 155 = +5): 0.03-5 mm slack.
- stale files in cad/print (gitignored): plate_1_fins, plate_2_trays, plate_3_covers_pistons, plate_H2D_2_tray_R_covers, tonight_*.3mf, stl/cover_L/R, stl/*_standing (Oct 26 22:13-22:44, previous attempts).
- hardware outside the user's list: M5 washer O15 (x2). Tools: 150 mm 1/4 in extension, 4.0 drill as reamer.
- cell swap: cover 8 + M4 3 + clamshell 6 + front nut 1 + piston screws 2 + rear nut 1 = 21 fastener ops + break superglue on both stud threads.
