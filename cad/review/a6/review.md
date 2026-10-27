# Review: space-bar-push-assist, attempt 6
Checks re-run: `cad check` main PASS, 0 fail, 47 warn (0 untriaged; accepted set identical to cadcheck_a6.json). Moving/bench rows PASS 0/0. printcheck PASS (17 parts, 0 fail, 16 warn). cad bom PASS (13 rows).
Coverage: parts, interference over 114 objects in all four collections, 53 screws / 24 nuts over 19 steps, 3 service ops, 13 slides, 36 insertions, 22 stacks, 4 flexures, 5 cables.
Not checked by the tool: hole diameters, wrench access to nuts, multi-segment insertion paths, teardown count, aesthetics, BOM correctness. Stability was skipped (the unit bolts to a chair).

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 8 | Works, at most 2 majors with a quick fix | Cradle fixed and re-derived. The plug's 2.1 mm lip is a weak link in the pull step. Crosstalk is only handled in firmware, with 0.36 N of margin at lip contact |
| Manufacturability | 8 | 2 majors, each under 1 h, no big reprint | 0 fails and no supports, 24.9 h. A soldering iron is still needed for the HX711 header, and the plug lip can shear |
| Aesthetics | 9 | Every rubric item holds | Same unit as a5. Polish only |

## Previous issues
| a5 issue | Status | New number |
|---|---|---|
| 1 Cradle cannot set the 50 kg cell | FIXED | Free-cantilever bound 17.69 MPa (a5 54.19), stroke 0.93 mm (a5 4.47). My frame derivation: 2.03 MPa in plane, 1.19 across layers, 0.16 deg tilt, 0.41 of 7.0 mm stroke |
| 2 mV/V never set | FIXED | `m` is refused without f, r or c, and t. `k` check 0.90-1.03. Caveat: a FAILed `k` still lets `m` mark (issue 4) |
| 3 20 kg overload | FIXED (by cell choice) | 50 kg: 1.18-1.21 x FS at 600 N. 20 kg documented as a fallback |
| 4 Lean crosstalk | PARTIAL | 5.69 N at 150 N (unchanged). 9.64 N at lip contact vs the 10 N band |
| 5 Lip lever | FIXED | Contact at 182-254 N. The text says x1.6 in head_calc and x5.3 in README |
| 6 Soldering | PARTIAL | Cell to screw terminal; the logic header still needs an iron |
| 7 Lip friction | NOT FIXED (accepted) | 150 N limit is in the README only |
| 8 Stale text | FIXED | 0 hits for "R1.5" |

## Measurements
| Item | Value | Source |
|---|---|---|
| Cradle U section | A 1116 mm2, centroid z -31.08, I 514,134 mm4, 2.03 MPa | hand calc, notes.md |
| Upright between the walls / across layers | 6.1 / 1.19 MPa (5.2 % share) | hand calc |
| Jack tilt / stroke | 0.16 deg / 0.41 of 7.0 mm | hand calc |
| Upright nut skin (push) | 29 MPa bearing (in plane), 3.6 MPa shear | scripts/jack_local.py |
| Plug T-slot lip (pull) | 2.1 mm thick, 20 mm2 contact, peak shear 17.2 / 21.5 MPa at 589 / 736 N | jack_local.py, rows a6R plug lip (FAIL) |
| Crosstalk | 5.69 N at 150 N; 9.64 N at 254 N; 11.18 N for a 4.4 % unit | a5R row, a6R rows |
| Overhang > 45 deg | cartridge 159, cradle 153.5, fins 97-138, trays 824-875 mm2. All located (lead-notch roofs 4.4, key-window tops <= 8, teardrops, tray chamfers off the bed) | steep_strip.py, layer_ascii.py |
| Print | 17 parts, 1,247 g, 24.9 h, 2 H2D + 2 P1S plates, 0 supports | BOM, plates.txt |
| Hardware | 53 screws, 24 nuts, 6 T-nuts. All ISO 4762 M3-M5 caps or M3 pan self-tappers | cad bom |
| Reach | M5 lower bolts 98 mm, ESP32 screws 104 mm, both under the 150 mm extension | cadcheck warns |

## Issues
1. **Major (M, F): the setting plug's T-slot lip is 2.1 mm thick and takes the full pull load.** Peak shear is 17.2 MPa at 1.2 x FS and 21.5 MPa at the 1.5 x FS that step 7 reaches. On the D-flat (print-down) side the shear plane is a layer plane. Rows a6R FAIL against 12 MPa. Fix: make the lip 5.0 mm (move the pocket 2.9 mm forward, lengthen the plug), which gives 6.0 MPa. Cap step 7 at 125 %.
2. **Major (M): a soldering iron is still needed.** The Adafruit 5974 logic header ships loose. Fix: a press-fit (hammer-in) 2.54 mm header, or a module sold with its header fitted. Add a 2 mm slotted bit to the tool list.
3. **Minor (F): the dead band is sized for the 150 N limit, but leans are only stopped at the lip (182-254 N).** At 254 N the nominal crosstalk reads 9.64 N against the 10 N band; a 4.4 % unit reads 11.18 N against its prescribed 10 N. Fix: max(12 N, 260 N x c x 1.2), and record the sign in step 12.
4. **Minor (F): the sketch's known-mass check is advisory, and `c` in pull flips the push sign against README step 5.** Fix: refuse `m` when massCheck <= 0 unless `m!` is typed. Store pull calibrations as negative. Reset massCheck in `f`. Set the PASS floor to 0.88.
5. **Minor (F): lip friction past contact and the 150 N lean limit** (carried from a5).
6. **Minor (M, A): documentation inconsistencies.** The step 4 render shows the coupler below the floor (insertion is +Z). The leaf margin is x1.6 in head_calc and x5.3 in README.
7. **Minor (M): the known-mass rig is improvised** (two books, cord in a 3 mm gap). Fix: an 8 g printed hanger held under the jack head, and feet on the upright's rear face.

## Check-config audit
- Main accepts: all 47 are the same as a5 and still agreed. The jack standoff warn (7.0 mm) is intended.
- a6 cradle stack rows: agreed. They reproduce by hand. They cover the frame, not the local load path; the plug-lip rows in review_rows.json fill that gap.
- No row covers the known-mass setup, and no row covers the firmware dead band against the lip-contact lean. Both are in review_rows.json or issues 3 and 7.

## What is good
The cradle is now a real closed frame and its numbers stand up to an independent derivation. The stop-setting procedure gates on scale and tare. The BOM commits to one cell, and the 20 kg fallback has honest limits. The lead goes into a screw terminal. 0 fails across cad check, printcheck and cad bom, with no supports. The unit's form is unchanged and coherent.
