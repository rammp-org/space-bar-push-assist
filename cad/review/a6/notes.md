# Review a6 notes (reviewer)
- copies: /tmp/a6rev/check_copy.blend, /tmp/a6rev/check_moving_copy.blend, /tmp/a6rev/mov2.blend
- skills repo on branch `next`, used as is.

## Checks re-run
- moving: `cad check /tmp/a6rev/check_moving_copy.blend checks_moving.json a6/cadcheck_movlink.json --only slide,distances,sightlines` -> PASS 0 fail 0 warn (designer claim reproduces).
- a5 review_rows verbatim: `cad check /tmp/a6rev/mov2.blend checks_moving.json a6/cadcheck_a5rows.json --overlay a5/review_rows.json --only stacks --overlay-only` -> PASS: cradle 50 kg 17.69 MPa (a5 54.19), 20 kg 7.08 (a5 21.7), jack stroke 0.93 (a5 4.47), crosstalk 5.69 N (unchanged; it is a property of the cartridge).
  Note: rows still model a free cantilever, now with t = 14 (bench_up1-bench_up0). Bound, not the real frame.
- main: `cad check /tmp/a6rev/check_copy.blend checks.json a6/cadcheck.json --only parts,...,cables` -> PASS 0 fail, 47 warn (0 untriaged, 47 accepted). Accepted-warn set identical to designer cadcheck_a6.json (diff empty both ways); vs a5 only the jack standoff (3.0 -> 7.0) and HX711 cable overlap (4.9 -> 4.8) changed. unbounded_allows {}, poses_past_limits [], stale_accepts [].
- printcheck: `cad printcheck cad/print/stl --manifest ... --out a6/printcheck.json --render a6/printcheck` -> PASS 17 parts, 0 fail, 16 warn (same fin roof strips as a5).
- `cad bom cad/BOM.md manifest.json` -> PASS 13 rows.

## Overhangs (own, scripts/steep_strip.py + layer_ascii.py)
- overhang_gt_45_mm2: cartridge 159.4, cradle 153.5, fins 96.7/137.6, trays 824/875, cover 0.1, others 0.
- cradle (new frame): slices at print z 26/30/45 show both 6 mm walls continuous to the upright (closed frame confirmed). Flat down faces: z 26.0 (52.8 mm2) = 4.4 mm roof of the lead notch through each wall; z 60.4-60.5 (53 mm2) = tops of the key windows / nut-driver hole in the front wall (<= 8 mm spans); 60 deg flanks at z 35-45 = lip-screw teardrops. No supports needed. Agree.

## Cradle re-derivation (by hand, manifest params)
- U section: base 50 x 7.9 (z -57..-49.1) + walls 2 x 6 x 60.1: A 1116 mm2, centroid z -31.08, I 514,134 mm4. M = 589 x 31.08 = 18.3 N.m. sigma = 0.53 + 1.50 = 2.03 MPa (layer plane). Agrees with 2.02.
- Upright beam between walls (span 38, band 14x14): 6.1 MPa in plane. Cantilever share: k_cant 550 N/mm vs k_beam(bend+shear) ~10,100 -> 5.2 %, 1.19 MPa across layers. Agrees.
- Tilt: frame 0.066 deg + cantilever slope 0.095 deg = 0.16 deg. Stroke 0.017+0.036 (frame) + 0.058 + 0.30 = 0.41 mm vs 7 mm standoff. Agrees.
- NOT in the designer calc: local jack path. scripts/jack_local.py -> jack_local.txt:
  - upright nut-pocket skin (push): bearing 20.4 mm2 -> 29 MPa (36 at 1.5 FS) in plane; skin shear 3.6-4.5 MPa. OK.
  - setting plug T-slot rear lip (pull): lip only 2.1 thick (plug1 115 - (jack_tip 108 - 0.1 + 5)). Nut contact 20 mm2 (29 MPa bearing). Shear on 24.4 mm support perimeter: 11.5 MPa mean / 17.2 peak at 589 N, 14.3 / 21.5 at 736 N (1.5 FS, README step 7). Plug prints D-flat down, so at x -4.85 the shear plane is a layer plane. Plate bending bound 36-45 MPa. Lip 5 mm: 6.0 MPa shear, 7.9 bending at 736 N.

## Firmware (firmware/bench_hx711.ino)
- 'm' refused only without f, r/c, t (line 363). massCheck 0 -> "Note", -1 (FAIL) -> "Warning", but marks anyway (lines 368-369). The known-mass check is advisory, not a gate.
- 'c' keeps sign (line 331): calibrated in pull (README step 4 hangs the mass = pull), pull reads +, so the push direction then reads negative, opposite to README step 5 "+120 %". The TOUCH logic works with either sign.
- 'f' after 'k' does not reset massCheck though netToKg (mV/V path) depends on fsKg.
- head_calc 10: a correct 20 kg cell at dFS 0.2 reads 0.889 < PASS floor 0.90 -> FAIL -> 'c' path (safe, but a false FAIL).

## Other
- Adafruit 5974 (WebFetch adafruit.com/product/5974): 6-port terminal pre-soldered; the 6-pin logic header is shown beside the board (ships loose). One solder joint per board (and the bench board) unless a press-fit header is used.
- head_calc 4 says rear leaf at contact 1998 N, x1.6 to buckling (link-only contact 596 N); README says x5.3 (contact 182 N with piston bending). Doc inconsistency; the x5.3 figure matches my a5 calc.
- step4_electronics.png explodes BUY_rj45_coupler 60 mm BELOW the floor (build_concept.py 1902 rj_down), but insertion row says free_dir +Z and README says "on its pad ... from above". Render contradicts the step.
- checks.json flexures text now "r = leaf_r" (0 hits for R1.5): stale text fixed.

## Review rows (a6/review_rows.json -> a6/cadcheck_review.json, moving blend, --only stacks --overlay-only)
- FAIL plug lip 1.2 FS 17.23 > 12; FAIL plug lip 1.5 FS 21.54 > 12; PASS crosstalk at lip contact 254 N nominal 9.64 < 10 (0.36 N margin); FAIL crosstalk 4.4 % unit at 254 N 11.18 > 10.

## Renders viewed once each
01 hero, 02 side, 03 closeup, 04 top, 05 exploded, 06 internals, 07 lead side, 08 head open, step1-5. Unit unchanged in look from a5 (9). step5: closed frame visible, cradle a plain block (bench tool). step4: coupler drawn under the floor.
