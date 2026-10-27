# a8 review notes (reviewer)
- blends copied to /tmp/a8rev at Tue Oct 27 07:30:23 EDT 2026

## Checks re-run
- main: `cad check /tmp/a8rev/check.blend checks.json a8/cadcheck.json --only parts,...,cables` -> PASS 0 fail, 51 warn (0 untriaged, 51 accepted), 109 s. warn_list identical to designer cadcheck_a8.json both ways. unbounded_allows {}, poses_past_limits [], stale_accepts []. 123 objects, 61 screws / 24 nuts, 25 steps, 0 in no step, 19 slides, 43 stacks, 6 flexures, 5 cables. NOTE coverage: parts layer check ran "on the model's print triangles (no stl/ on disk)".
- moving: `cad check /tmp/a8rev/check_moving.blend checks_moving.json a8/cadcheck_movlink.json --only slide,distances,sightlines` -> PASS 0/0, identical to designer.
- a7 review rows verbatim (`--overlay a7/review_rows.json --only slide,stacks --overlay-only` -> a8/cadcheck_a7rows.json): 4 FAIL, 4 PASS.
  - cell-first 45 deg slide: PASS, now closest=PRT_cartridge_R at 0.0 (the cartridge is seen: allow gone). 
  - rear nut+washer 45 deg: PASS (a7: blocked at 24 mm).
  - stops-already-in: blocked by FST_Stop_screw_push_R_in at 4 mm (expected; an end stop, README is cell-first).
  - stiff-bound shunt 33.0 / 13.2 FAIL: the guided bound; the crown is meant to remove it -> judged in head_a8.
  - rear strips 1345 < 1469 PASS.
  - washer row FAIL 35.0: stale (hard-codes 1.6 mm); a8 washers 2.4.

## STL cell path (scripts/stl_cell_path.py; world verts dumped by scripts/dump_verts.py from the check.blend copy)
- world->print transform found by matching all 48 axis maps: mean NN 0.000 mm (R: print x = -world z, y = y, z = world x - 157.8).
- cell (puck Ø25.4 with the seat faces shrunk 0.1 in y), both studs Ø4.9, rear washer Ø13, rear nut (circumscribed Ø9.24), swept 0-60 mm along (-x,0,+z)/√2 in 2 mm steps: 0 points inside the cartridge_R STL (ray parity, two ray axes must agree); reverse test (STL vertices + edge midpoints inside the moving solids, 1 mm steps): none. cartridge_L STL (mirror map): same, 0 / none.
- So the a7 blocker is FIXED on the exported STLs, not only in the model.

## Head re-derivation (scripts/head_a8.py -> a8/head_a8.txt)
- crosstalk 0.000 % (L27 and Le25 measured from the effective tops); 0.04/0.10 % at 0.2/0.5 mm height error. AGREE.
- catch contact 200 (E2500) / 240 / 280 (E3500) N at 0.15 gap; 133-187 N if the gap prints 0.10. AGREE (designer 200-280).
- pull + lean margin: 1.2FS pull lowers the catch 0.086 (E2500) / 0.072 (E3000) / 0.061 (E3500) -> 85 / 125 / 165 N. Designer 104.6 mixes E3000 pitch with E2500 lean; consistent E2500 is 85 N. Minor.
- three supports at 600 N: rear strips 1043-1447 (E2500), 1215-1538 (E3500); buckling 4407 / 6170 -> x3.05 worst at E2500; with a concurrent 1.2FS push couple (+373 N) x2.42. Strip compression 23-31 MPa. AGREE with designer x2.9 (theirs mixes the E3500 load with the E2500 buckle: conservative).
- catch legs buckling pinned at the contact 2181 N (E2500) AGREE; if the contact slips in y (friction only) a sway mode is ~250 N < 738 N; friction μN ≈ 220 N holds the bifurcation; minor caveat.
- friction shunt free 1.12-1.57 N (0.12 mm), 2.8-3.9 N (0.30) AGREE. Flattened crown: designer's N·a is an upper bound. My elliptical plastic contact land (circumferential R_eff 972, crown 1.2): half width 0.26-0.32 at 184 N, 0.52-0.64 total at 738 N. During a 600 N lean 11.9-19.6 N (> 10 N dead band, transient); later 300 N lean 4.0-7.4 N. AGREE with designer's "open".
- saddle across layers at 738 N: 14.2 MPa (point, clamped; solid); 9.5 (UDL); 28.4 if simply supported. Default print (2 walls, 15 %) x1.39 -> 19.7 MPa > 15.
- piston at 600 N: mouth 45.2 (bound) / 41.6 with catch relief, catch 42.3, step 45.6 nominal AGREE; x Kt 1.3-1.5 at the 45 deg step -> 59-68 MPa (x1.1-1.3 on 76). NEW: no infill/wall spec anywhere (README, BOM, plates.txt, 3MF has no Metadata/config). With slicer defaults (2 walls, 15 %) I_eff 5224 vs 15358 -> 133 MPa at 600 N, 67 at 300 N; walls reach 50 MPa at a 226 N lean.
- stops: my estimate 6.7 kN/mm per screw, 13.4 per pair (solid); designer 6-7.6 per pair is the soft side (conservative). 50 kg cell at 600 N: 1.15-1.20 FS (stops barely engage). 20 kg: 1.33-1.91 FS. AGREE.
- washers: rear Ø13 strip is only 3.85 wide (OD/2 - 2.65): 20.4 (clamped) - 30.7 (s.s.) MPa at 1.2 FS pull, 24-36 at 1.4 FS (bench step 7); front Ø15 16-24 MPa. Designer row 11.4 uses a 6.05 strip. Sustained clamp preload 7-10 MPa (creep). Minor.

## Printability (cad printcheck cad/print/stl --out a8/printcheck.json --render a8/printcheck): PASS 18 parts, 0 fail, 20 warn (same as designer)
- overhang_gt_45_mm2 (cadcheck parts): cartridge 161, cradle 472.6, fin_in 141, fin_out 99.5, tray 826-876, cover 0.1, others 0. STL (steep_strip): cartridge 793, cradle 551, fin 4070/4237, tray 846-877.
- scripts/overhang_locate.py (clusters, angle, what is below) + scripts/roof_span.py (true reach per roof layer):
  - cartridge: 398 mm2 flat roof at print z 33 = top of the Ø24 socket bore (flat-topped teardrop) -> bridge 8.9 mm; leaf strip first layers 27.2 mm bridges (accepted); catch-leg first layer ~22 mm bridge (not listed by printcheck); stop key/clearance hole tops (68 deg facets, Ø3.2/Ø3.4 holes) and the Ø5.5 stud hole tops: trivial; nut-slot roofs 2.6-3.2 mm bridges; seat-boss rims 1 mm ledges.
  - cradle: hang lug 46 deg (195 mm2, 1 deg past); Ø16 front-wall hole printed round (49-86 deg roof, ~6 mm final chord); M4 nut pockets corner-up give 30-deg-from-horizontal roofs (60 from vertical, reach 3.4) - flat-up would be a 4 mm bridge. Minor, bench tool.
  - fin: z 20.0 L roof is a 3-side-supported plate (free edge 13.5 mm, bridged across x), z 21 C roof: worst cell 11.4 mm from support -> real spans up to ~23 mm (designer 9-18). Hidden pocket roofs; acceptable on Bambu bridging. Agree with accept.
  - tray: bed-edge chamfer strips z 0-5 only (reach <=1 mm) + boss undersides at 46 deg; z 0.9 worst 0.7 mm. Agree.
  - piston, plug, hanger, cover, washers: 0.

## Assembly walk / config audit
- allow entries (5): cell>front/rear nut (threaded on stud; slide rows move cell+nut together, front nut ignored in the cell-first row), piston>grip, board/RJ45 screws vs stand-ins: all agreed; none blinds a slide or insertion row. Slide-row ignore lists only drop later-step parts: agreed.
- insertion: cell free only along the 45 deg insert_dir; cart group +x into the inboard half; piston +y; fin_R group onto tray -z (bench).
- CAB_Amp_to_ESP32_R path 142.8 of 150 mm; README step 6 plugs it on the bench, step 10 hangs the halves separately -> tethered halves, 7 mm slack. MAJOR (M).
- FST_M4_screw_R1/R2/L1/L2: access L-key only (lkey arc 140); horizontal along x inside a 150 mm tray: a drill + bit cannot line up for any of the three; README tools list 2.5 and 4 mm keys only, no 3 mm key for M4. Minor (user has hex keys).
- service 'cell R (fin off the tray)': no slide row; mine (review_rows) +x 250 mm clear with bench props ignored; +z blocked by the back plate at 4 mm (expected). Screws: 8 cover + 3 M4 + 6 M3x30 + 2 piston, lead out of the spring terminal, then re-set stops in the cradle.
- cad bom PASS 13 rows.
- Review rows (a8/review_rows.json -> a8/cadcheck_review.json): 2 slide PASS; 5 FAIL (washer 20.46>20, piston step Kt 63.9>47.5, piston default print 133>47.5, saddle default print 19.7>15, R jumper 142.8>130) + 1 warn (pull + 100 N lean 0.161 > 0.15).
- Print settings: grep infill/walls in README, BOM, plates.txt, export_prints.py: none; 3MF contains only 3D/3dmodel.model (no Metadata/ settings).
## Renders (all viewed except 05_junction, 07_lead_closeup): 01, 02, 03, 04, 05, 06, 07_lead_side, 08, step0-5. Exterior clean; cover heads now read as Phillips pan heads in chamfered counterbores, aligned 4x2. Cover light grey vs dark body (cover/structure). No exposed wires in 01-04.
