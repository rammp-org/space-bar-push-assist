# Review a7 notes (reviewer)
- copies: /tmp/a7rev/check_copy.blend, /tmp/a7rev/mov_copy.blend, /tmp/a7rev/mov2.blend
- skills repo on branch `next`, used as is.

## Checks re-run
- main: `cad check /tmp/a7rev/check_copy.blend checks.json a7/cadcheck.json --only parts,...,cables` -> PASS 0 fail, 51 warn (0 untriaged, 51 accepted). warn_list identical to designer cadcheck_a7.json (diff empty both ways). unbounded_allows {}, poses_past_limits [], stale_accepts []. 123 objects, 61 screws / 24 nuts, 19 steps, 0 in no step, 35 stacks, 6 flexures.
- moving: `cad check /tmp/a7rev/mov_copy.blend checks_moving.json a7/cadcheck_movlink.json --only slide,distances,sightlines` -> PASS 0/0 (reproduces).
- a6 review rows verbatim (`--overlay a6/review_rows.json --only stacks --overlay-only` on mov2.blend -> a7/cadcheck_a6rows.json):
  plug lip 1.2 FS 7.24 MPa PASS (a6 17.23); 1.5 FS 9.05 PASS (a6 21.54). Crosstalk rows FAIL 15.63 / 11.18 but both are stale: row 3 hard-codes the a6 leaf-top offset 15 and 2*cart_hw (a7 strips are 25 wide, leaf tops 13.5 above the cell -> 0 by the same formula); row 4 is the constant 254 x 0.044 (README now rejects > 1 %).
- printcheck on cad/print/stl (--out a7/printcheck.json --render a7/printcheck): PASS 18 parts, 0 fail, 20 warn. cartridge bridges 26.7 x 2 per part (anchored 0.97, extent 26.6 x 4.7), fins 98.1/59.9 + 43.3 (region lengths; layer_ascii at z 20.1: actual spans are a 6-8 mm strip and a 10 mm band, as a5/a6), tray 1.8 mm cantilever 0.4 mm2.
- overhang_gt_45 (cadcheck parts): cartridge 161, cradle 472.6, fin_in 142, fin_out 98.9, cover 0.1, hanger/plug/piston 0.
  On STLs (scripts/steep_strip.py): cartridge 685 (flat ledges <= 1.0 mm per printcheck: link top edge steps at print z 2.7/5.3, stop-slot roofs, strip bridge), cradle 551 (hang lug 45-46 deg 194 mm2, teardrops 52-60 deg, lead-notch roofs), fin 3991 (pocket roofs), tray 843 (bed-edge chamfers z 0-5), cover/plug/piston/hanger 0.

## Head re-derivation (scripts/head_a7.py, from manifest params; no head_calc import)
- Crosstalk: leaf tops at z -15, cell axis -28.5, L 27 -> shear 12EI/L^3*a - 6EI/L^2 = 0 at a = L/2. 0.000 %; 0.041 % / 0.102 % for a 0.2 / 0.5 mm offset. AGREE (fillets are symmetric, so Le = 25 doesn't move the mid-height).
- Catch contact (rear leaf axial compression 3.17 x lean + link pitch + piston cantilever): 130 N (E2500) - 183 N (E3500). Designer 147-206 (pivots about the leaf centroid, drops the link's net vertical translation ~0.011 mm at 150 N). With c printed 0.2: 261-365 N.
- Past contact, rigid link on three axial supports (front leaf 6944 N/mm, rear leaf 6944, catch legs 7100-9900 at full axial stiffness): per extra N front -1.86, rear +1.02, catch +1.84. With legs+saddle+contact at 1/3: rear +1.94, catch +1.06. Rigid catch: rear -0.24, catch 2.93. Designer: catch 4.0 x, strips stop loading. At 600 N: rear strips 929-1416 N (designer 470-650), buckling 4407 (E2500) -> x3.1-4.7 (designer x9.4). Catch 418-1325 N (designer 1815, conservative for the legs).
- Friction shunt: legs 2 x 12.5 x 2.5, 22 tall; contact at piston bottom z -11.1 is 8.9 above the leg tops. k pair: free saddle with offset 10.2 N/mm, 3EI/L^3 27.5 (designer's 'stiff bound'), fixed-guided 110.1. Holding the saddle square at 0.12 mm needs 145 N.mm = 116 N normal on the 2.5 mm face -> reached ~60 N past contact. Shunt 13.2 N (0.12 mm) / 33.0 N (0.30 mm). Rows FAIL vs 10.
- Piston: 52.3 MPa at 600 N on the catch (agree), 26.2 at 300. Bambu PLA Basic bending strength ~76 -> x1.45. (lip at 150: 40.3)
- Push couple: +-373 N at 589 N, +-380 at 600 (README 'about +-360').
- Side load: kx per leaf 2030 N/mm, k_yaw 2.06e6; 20 N -> 0.0174 mm = 0.17 FS (designer row 0.185 limit 0.2). AGREE.
- Stops: per-pair 7.2-7.5 kN/mm accepted (head_calc 3d terms plausible: M3 shank 23 mm 44 kN/mm; head annulus 13 mm2 on PLA ~14). 50 kg cell 1.19 x FS at 600 N; 20 kg dFS 0.10: engage at 253 N grip, 20 % of the extra -> 1.56 x FS. AGREE.
- Printed washers over the 5.5 slot (estimate): 145 N of nut load over the slot, clamped strip 4.45 wide x 1.6 -> 35 MPa at 1.2 x FS pull. Row FAIL vs 20.

## BLOCKER: the cell cannot be fitted (stud slots and nut channel end inside the cartridge)
- build_concept.stud_slot(): d = (cart_hw + 8)/sqrt(2) = 19.8 is used as BOTH the x and z offset of the far end, so the slot centreline ends at x = X - 19.8 = 158.0, 0.2 inside the inboard face (157.8), and its end edge (perpendicular to the slot) leaves a wedge of material over the upper half of the exit.
- cad q inside on check2.blend at x 158.3 (0.5 in from the inboard face): y 44 (block, front stud slot) void only z -12.6..-8.6, solid at -13 and -8; y 62.5 (drop wall) the same; y 67 (nut channel) void z -18..-9, solid at -8, -6, -4. Along the channel centre: s = 28 mm (158.0, 67, -8.7) SOLID in PRT_cartridge_R.
- Window across the 45 deg motion: stud slots (-8.4 - -12.9) x cos45 = 3.2 mm < M5 stud 4.9; nut channel ~6.7 mm < M5 nut 9.24 AC / Ø13 washer.
- STL confirms (scripts/stl_inside.py on print/stl/cartridge_R.stl at print z 0.5, y -40 block): void x -8.5..-4.6, solid at -9.5 and -4.0 (~4.2 mm in the face, 3 mm across the motion).
- Row: a7R rear nut + washer up-inboard 45 deg -> blocked by PRT_cartridge_R at 24 mm (cadcheck_review.json). The cell row itself can't see the cartridge: checks.json allows PRT_cartridge_*>BUY_load_cell_* (max 3 mm3), so its slide returns no closest object.
- Also: with the stop screws in (checks.json step text order), the cell is blocked by FST_Stop_screw_push_R_in at 4 mm (0.72 to the other push screw). README's cell-first order is required.

## Other
- Qwiic Scale: sparkfun.com/products/15242: solderless 4-pin spring terminal, 2 Qwiic, fixed 0x2A. Footprint: only the SparkFun forum (Eagle import: 1000 x 1400 mil, holes 800 x 1200 mil) - same source as the designer; no official drawing found. Unverified.
- Two I2C ports: ESP32-P4 has two HP I2C controllers + LP I2C, any GPIO via the matrix: valid. Female-socket Qwiic cable needs male pins on the Waveshare board: not verified.
- Firmware: m refused unless massCheck > 0 (356-361), m! override; c stores -net/val (311); f/r/c reset massCheck (289, 299, 314); PASS 0.88-1.03; COUNTS_PER_MV_PER_V = 2^24 x 128 / 1000 (consistent with NAU7802 ±0.5 VREF/gain, ratiometric).
- cad bom PASS 13 rows. Print: 18 printed parts, 26.4 h, 4 plates (2 H2D, 2 P1S), 0 supports.
- Renders viewed: 01, 03, 08, step1, step4 (coupler now above the floor: a6 #6 FIXED), step5. Exterior unchanged from a6.
