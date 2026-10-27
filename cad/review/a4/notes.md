# Review a4 notes (reviewer)
- copies: /tmp/a4r_check.blend, /tmp/a4r_moving.blend

## Checks re-run
- `cad check /tmp/a4r_check.blend checks.json a4/cadcheck.json --only (designer set)` -> PASS 0 fail, 39 warn (0 untriaged, 39 accepted); warn list identical to designer's cadcheck_a4.json (diffed sets: none only-mine, none only-designer). service: 3 ops only (cell re-seat, mount bolts) - no op for README step 14 "re-snug both cell nuts".
- designer moving rows: `cad check /tmp/a4r_moving.blend checks_moving.json a4/cadcheck_movlink.json --only slide,distances` -> PASS 0 fail 0 warn (52 s).
- a3 review_rows.json verbatim overlay on moving blend (a4/cadcheck_a3rows.json): 16 FAIL. 2 distances rows skipped (FST_Stop_pin gone); 14 slide rows stopped by PRT_washer_rear_R/L at 0.05-0.85 (the new printed washer rides on the rear stud but is not in the a3 objects list) and, for the ground rows, by the new stop nuts. Mechanical artefacts of new parts, not regressions.
- Adapted rows: push/pull rows are the same claim (pin -> screws). +-z rows CHANGED claim: a3 said the stop catches lean/lift at 0.25; a4 rows say "backstop = fin cavity at 1.0" (at_mm 0.8-1.3). Sideways rows same claim. Ground rows same claim (+stop screws/nuts moved with the ground: fair).

## Geometry (cad q list on moving blend)
- cell axis z 0 (nuts z +-4), puck y 47.3-60; rear nut y 65.6-70.3; piston y 73-282 (z +-11.1), grip y 152-287 axis z 0.
- leaves top = link bottom z -15, ground bar top z -42; leaf pitch 47.5 (y 61/110 -> centroid y 85.5).
- stop screws at z -24 (stop_z), tips y 81.35 / 89.65 on tongue y 81.5-89.5 -> stop line is 24 mm below the cell axis.
- re-snug access: ray from rear nut +y hits PRT_piston_R at 73.0 (0.5 mm behind stud end): rear nut is under the piston, inside the closed fin. Ray from front nut -y exits the land face at y 0 onto BUY_corpus_back_plate (34 mm): front nut bore is covered by the chair plate when mounted.

## Printability (re-run on exported STLs)
- `cad printcheck cad/print/stl --manifest ... --render a4/printcheck` -> PASS 15 parts, 0 fail, 24 warn (same as designer). NOTE: the tool wrote its report to cad/print/stl/printcheck.json (gitignored, same STLs); copied to a4/printcheck.json.
- overhang_gt_45_mm2 (cadcheck parts): cartridge 44, cover 0.1, fin_in 146.6, fin_out 108, piston 0, tray_L 733 / tray_R 702, washers 0.
- own map (scripts/steep_strip.py, faces < 44.5 deg from straight down): tray_R 689 mm2, of which ~110 mm2 are two full-width bed-edge strips at z 0-5 (52-54 deg from vertical, start on the bed: fine), rest = boss/hole crowns 5-9 mm2 each. fin: flat roofs at z 18-19 (the E and C bridges, 22.5 mm max span per designer; layer map fin_R_inboard_z018.0_bridge.png viewed, anchored both sides). cartridge: 9.9 mm max bridge at print z 31. No island or cantilever > 3 mm. Agree: no supports.
- est_h sum 22.43 h, 15 parts, 3 plates (2 H2D, 1 P1S). cad bom PASS 11 rows. slicer unusable (bambustudio segfault, known).

## Calcs (scripts/head_check.py -> head_check.txt)
- moment share: designer column model 1.9 %; boss + half-space 2.9-3.4 %; + M5 stud bending path in parallel 5.7-6.7 % (1.4-1.7 N.m in the cell at 150 N down). Still >7x better than a3's 47 %.
- stop set by jacking the tongue at z -24 (24 mm below the cell axis): the couple turns the link on the leaves, adding 1.2FS*24^2/k_rot = 0.017-0.024 mm to the set gap. In use the grip pushes on the axis, so the stop engages at 1.40 x FS (dFS 0.1), 1.60 (dFS 0.05), 1.33 (0.15). Designer push stack worst case 0.163 + 0.20 = 0.36 > 0.3 limit (review row: worst 0.363, rss 0.258).
- lean: grip load down turns the link about the cell attachment; tongue moves 24*theta toward the push screw: 0.024 / 0.048 / 0.071 mm at 50/100/150 N down. Push clips at 0.93 FS (dFS 0.1) / 0.65 FS (dFS 0.05) at 100 N down; 0.69 / 0.18 at 150 N. Review stack row: 0.475 FS lost at 100 N (dfs_ref 0.1).
- overload past engagement (20 kg cell, stop 2.34 kN/mm in series with link rotation -> 1.95 kN/mm at the grip axis): 600 N push -> 2.55 / 2.21 / 2.00 x FS for dFS 0.05/0.10/0.15 (designer 2.35/2.03/1.85).
- rear leaf buckling: leaf load = 3.32 x downward grip load; buckles at 338-578 N down per grip (E 2500-3500, net/gross). Elastic drop at buckling 0.27 mm < the 1.0 cav backstop, so the backstop cannot save the leaf. a3 had the pin catching +-z at 0.25; a4 has no vertical stop. leaf_t 2.0 -> 1174 N per grip, k 104 N/mm, root bending 11.2 MPa at 0.30.
- boss clamp: 9.1 MPa at 0.5 N.m, 18.3 at 1.0, 27.4 at 1.5. README "0.5 N.m = drill's lowest clutch setting" is unverified; no torque tool in the kit.
- re-derived leaf bending 6.2 MPa at 0.30 (Le 25.5), axial 7.8 MPa at 150 N: designer's 19.0 MPa row reproduces.

## Review rows (a4/review_rows.json -> a4/cadcheck_review.json, --only slide,stacks --overlay-only)
- 5 fail, 1 warn: rear nuts R/L blocked by PRT_piston at 3 mm; front nuts R/L blocked by BUY_corpus_back_plate at 34 mm (README step 14 re-snug needs fin teardown + dismount); lean stack 0.475 > 0.2 FAIL; jack-couple stack worst 0.363 > 0.3 (rss 0.258 -> warn).

## Renders viewed
01 hero, 02 side, 03 closeup, 04 top, 05 exploded, 06 internals, 07 lead side, 08 head open, step1, step3. Visible: 8 M3 counterbores on the cover top (2x4 grid); tray centre seam at x 0 on the attendant-facing sloped face (step3, 01); RJ45 coupler body 9 mm below the tray floor (z -76 vs -67) reads as a grey box under the bridge in 01_hero; fin reveal + one hairline at fin/tray/cover reads clean; recessed outboard panel clean (03).
