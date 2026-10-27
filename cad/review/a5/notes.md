# Review a5 notes (reviewer)
- copies: /tmp/a5rev/check_copy.blend, /tmp/a5rev/check_moving_copy.blend
- `cad bom cad/BOM.md manifest.json` -> PASS 14 rows, 0 disagree, 0 modelled screws in no row.

## Checks re-run
- main: `cad check /tmp/a5rev/check_copy.blend checks.json a5/cadcheck.json --only parts,...,cables` -> PASS 0 fail, 47 warn (0 untriaged, 47 accepted); warn set identical to designer cadcheck_a5.json (set diff empty both ways). unbounded_allows {}, poses_past_limits [].
- moving: `cad check /tmp/a5rev/check_moving_copy.blend checks_moving.json a5/cadcheck_movlink.json --only slide,distances,sightlines` -> PASS 0/0 (designer's claim reproduces).
- printcheck: `cad printcheck cad/print/stl --manifest ... --out a5/printcheck.json --render a5/printcheck` -> PASS 17 parts, 0 fail, 16 warn. Used --out: cad/print/stl/printcheck.json and stl_cc/printcheck.json md5 unchanged. git status unchanged apart from cad/review/a5/. No cad tool rewrote a file outside a5/.
- cad bom PASS 14 rows.
- a4 review_rows verbatim on the moving blend: 4 slide FAIL (step-14 nuts blocked by piston at 3 mm and by the fin at 1 mm: the step is deleted, re-snug moved to the bench) + 2 config FAIL (stop_z param no longer exists). With --only slide,stacks cadcheck crashed (TypeError in check_stacks on a None tol: tool bug, the --only slide run reports it as a config fail instead).
- designer's adapted rows: jack couple 0.083 (same claim, rigid cradle assumed), lean 0 (same claim; push contacts on the axis, cell holds y at z 0: agree), bench re-snug slide rows pass (different claim, appropriate since the step moved), +-z rows now stop on the lip at 0.75 (translation stands in for pitch; agree within the check-split caveat).

## Printability (own)
- overhang_gt_45: cartridge 159, cradle 153.5, fins 97-138, trays 824-875, cover 0.1, pistons/plug/washers 0.
- scripts/layer_ascii.py (own slicer): fin_R_inboard at z 18.2: L roof = a 7 mm column (x -4..+3) between solid on both sides for y -6..+31 and -15..-26, bottom arm 10.7 tall between solid rows; at z 19.2 the C roof is a 16 mm bridge (x 38..54) between solid columns + 7 mm arms. Tool's "59.9/76.5/32.1 mm bridge" is the length of the strip, spans are 7-16 mm, all anchored both sides. Agree no supports.
- cradle: z 26 = 4.5 mm roof of the M4 lip-screw holes; z 60 = 0.5 mm ledges. cartridge flat roofs at z 30-35 (tool max bridge 5.7). tray: steep strips at print z 0-5 off the bed (steep_strip.py). No supports needed anywhere.

## Calcs: scripts/head_check_a5.py -> head_check_a5.txt
- stop stiffness: per screw 5.9 kN/mm (punch on PLA head 15.3, nut 16.0, shank 45.9, thread 50); pair with the shared 12.1 PLA path in series 6.0 (designer 7.6). 20 kg at 600 N: 1.44-1.92 x FS (k 6.0) / 1.40-1.82 (7.6). 50 kg: engages at 588 N, 1.18-1.21 x FS at 600 N.
- side load: 20/50/100 N -> 0.17/0.42/0.83 FS early at dFS 0.1 (free). 20 kg push stop on one side at 154 N with 50 N side load; 50 kg at 384 N.
- leaves: buckle 3249-4549 N (L 27, fixed-fixed, sway held by the cell) = 970-1357 N per grip; root bending 4.7/9.3/11.7 MPa (Kt) at 0.12/0.24/0.30 mm.
- lip: designer levers the link pitch about the cell centre (96 mm to the lip); about the leaf centroid it is 64.5 mm. Contact 181-254 N (designer 158-221), link-only 596-835 N; rear leaf at contact 608-851 N, x5.3 to buckling. Push-head lift at contact 0.13 mm vs 0.5 radial.
- piston D-section I 11456: 20 MPa at 300 N, 40 MPa at 600 N, 54 MPa at 800 N (at the lip); lip reaction 2.74 x lean (1642 N at 600 N).
- NEW crosstalk: leaf tops 15 mm below the cell axis -> 3.8 % of a downward grip load appears as axial cell force (5.7 N at 150 N lean). Zero if the leaf mid-length sits on the cell axis.
- NEW cradle: rear upright is a free-standing 50 x 8 plate (slices print z 9-50: only y 41..48 solid at that end; side walls stop at y -2). Jack axis 49.1 above the base top. 50 kg at 1.2 FS: 54 MPa across layers at the root, 56 MPa in the 7.9 base, tip 3.6-4.4 mm, jack tilts 6.4-7.6 deg. Head stands 3.0 off the upright -> the stroke runs out (row 4.47 > 3.0). 20 kg at 1.2 FS: 22 MPa, 1.45-1.74 mm, 2.5-3.0 deg; at 1.5 FS (README step 7 "on past 120 %") 27 MPa.
- creep: preload 100-200 N stretches the stud 0.4-0.8 um; 6 um of creep removes it over life; harmless (leaves take 0.7 N across the gap).
- sketch: ratedMvV defaults to 1.0 and README step 4 only says `f 20`, `t`; a 1.5 / 2.0 mV/V cell sets the stops at 80 % / 60 % of true FS.

## Review rows (a5/review_rows.json -> a5/cadcheck_review.json, moving blend, --only stacks --overlay-only)
- 2 FAIL: cradle upright 54.2 MPa > 25 (50 kg); jack stroke 4.47 > 3.0 (50 kg). Pass: 20 kg upright 21.7 < 25; crosstalk 5.7 N < 10 N.

## Renders viewed (once each)
01 hero, 02 side, 03 closeup, 04 top, 05 exploded, 06 internals, 07 lead side, 08 head open, step1-5. Tray centre V reveal visible and reads as intended (01); RJ45 coupler now inside the tray (cad q: z -63..-27, floor -67); cover 8 counterbored pan heads on a 2x4 grid (accepted); grips are stand-ins. step5: rear upright is a bare plate, side walls stop short of it.
