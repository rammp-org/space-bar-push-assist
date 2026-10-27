# Review: space-bar push assist (round 6 wedge unit), attempt 1

Checks re-run: `CADCHECK FAIL: 1 fail, 65 warn (65 untriaged)`. The one fail is stability (-20.6 deg), which doesn't apply to a bolted unit. Coverage: parts, interference (84 objects, all four collections), fasteners (40 screws, 10 nuts), assembly (8 steps, 0 unplaced), insertion, cables (5 routes), stability. Not checked: service access, hole diameters and wrench access, drop, payload, flexures, cable lead lengths, BOM. Printcheck (stl_cc and the standing fin STLs): PASS, 0 fail. Reviewer rows (`review_rows.json`): 7 fail, 1 warn.

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 5 | Blocker in the core function | The mount, fin-joint, cover and board bosses were all cut away by the tray cavity. The whole unit hangs on four M5 heads through a 3 mm wall, 20 mm from the pivot. The sensor has no overload stop and has sleeve friction. |
| Manufacturability | 5 | Two blockers | 18 of 40 screws can't grip (10 cover, 8 board). The README hardware and steps disagree with the model on every fastener, and with the lab's stock (M8, countersunk). |
| Aesthetics | 7 | 10 minus 1 per failed item, rounded down | No single radius family. 10 counterbored cover holes in an irregular pattern, with nothing behind them. Otherwise one clean, two-tone form. |

## Previous issues
None. This is attempt 1.

## Measurements
| Item | Value | Source |
|---|---|---|
| Land under the M5 heads | 3.0 mm wall. Head stands 6.0 mm off; designed 9 mm boss absent | `cad q ray 126,29.536,-1.828 0,-0.966,0.259`; fasteners warn |
| Tray end wall under the M4 heads | 3.0 mm (x 149.8 to 152.8); boss absent | `ray 130,35,0 1,0,0`; warn "head stands 4.0 mm off" |
| Cover screw bosses | none (ray reaches the floor at z -64) | `ray 74,12.265,15 0,0,-1`; 10 warns "no material grips" |
| Board standoffs | none. ESP32 1.21 mm and HX711 4.0 mm above the floor; screws get 1-2 mm of thread | `dist BUY_esp32_p4 PRT_tray_L`; fasteners warns |
| RJ45 pad | none | `ray -40,85,-50 0,0,-1` |
| Mount lever (land knee to bolt row) | 20 mm. Grip centre is ~230 mm behind the plate | build P land=40; section sec_x125_tray.png |
| Front-face gap to plate below the land | 4.4 mm at z -30, ~27 mm at z -115 | `ray 100,5,-30 0,-1,0` + plate tilt |
| Overload stop (piston to bore step) | 0.50 mm push, none in pull | review row `distances` FAIL; slide_out stops at 0.55 |
| Piston to fin running clearance | 0.007 mm (inboard), -0.496 mm³ overlap (outboard) along y 106-147 | `cad q dist`; review rows FAIL |
| Sleeve radial clearance | 0.32 mm | `ray 194.5,130,0 -1,0,0` |
| Sleeve length vs grip lever | 45 mm vs 80 mm to the grip centre. Friction is 0.46-1.4 x the vertical hand load | hand calc from the manifest bboxes |
| Spigot bending, printed standing | 13 MPa at 150 N, 26 MPa at 300 N (Z = 784 mm³, 68 mm arm) vs 15 MPa interlayer | hand calc; print_rot standing |
| Rear M5 nut depth | 180 mm reach needed vs ~175 (150 mm extension + socket) | piston bbox y292, rear nut y116.2 |
| Cover removal | Straight up is blocked by the plate at 2 mm. It comes off along the plate face | review slide rows |
| Print | 10 parts, 18.9 h, 1061 g, 0 supports. Fins flat use 288 x 315 of the H2D bed | cadcheck parts est_h/est_g; plates.txt |
| Cables | 5 routes, no lead lengths declared. Patch cable kink R2.8 for OD 5 | cables warns |

## Issues (ranked)

1. **Blocker (F, M). Every internal boss on the trays is cut away.** `build_tray_half` adds the land, fin-bolt, cover, standoff and RJ45 bosses to `src`, then subtracts the `bay` cavity, which removes them. The result:
   - the M5 mount heads bear on a 3 mm wall (6.0 mm stand-off);
   - the M4 fin bolts clamp a 3 mm end wall (4.0 mm stand-off);
   - all 10 cover screws float, so the cover doesn't close the torsion box;
   - the 8 board screws get 1-2 mm of thread (needs 6), and there are no standoffs or RJ45 pad.

   Evidence: fasteners warns, the rays above, `sec_x125_tray.png`.
   **Fix:** union the bosses after the bay cut (`sdf_part(..., add=bosses)`, or subtract `bay` from `src[0]` first), then re-run `cad check --only fasteners`. Target sizes:
   - land bosses 22 x 22 x 9 mm (n 0..9);
   - M4 bosses 14 x 14 x 8 mm;
   - cover bosses 10 x 10 x 14 mm with a Ø2.5 pilot at least 10 deep;
   - standoffs Ø6.5 x 5 mm with Ø2.5 pilots at least 6 deep.

   Turn the four `head stands off` and `no material grips` warns into 0.
2. **Blocker (F). The mount has a 20 mm lever against a ~230 mm handle.** Below the 40 mm land, the front face leaves the plate (27 mm gap at the fin bottom), so a downward hand load pivots the unit about the knee. 150 N on one grip gives about 1.7 kN in that half's two M5s, through a 3 mm PLA wall (80 mm² punch perimeter). Tipping or leaning on push handles routinely exceeds 150 N.
   **Fix:** keep the front face on the plate (bevel 0) down to the bridge floor, and add a second M5 row on the lower land at u ≈ -55 (about 70 mm below the top row). That gives a lever of about 75 mm, so bolt load drops about 3.7x. Alternatively, add 15°-wedge spacer pads 22 x 22 mm at the fin bottoms with a M5 each. Restore the 9 mm land bosses (issue 1).
3. **Major (F). There is no overload protection on a 20 kg cell.** The bore step stop is 0.50 mm away in push (the cell's full-scale deflection is about 0.1-0.2 mm). Nothing stops it in pull, so the cell takes any hard pull or shove directly.
   **Fix:** per piston, add an M4 hex-head stop screw in a captive nut in each fin half, bearing on the piston's rear shoulder for push and on a 3 mm lug for pull. Set each with a 0.10 mm feeler and superglue it. Or move to a 50 kg cell (about 490 N) and keep a 0.3 mm printed stop. Add `distances` rows with max 0.15 (already in `review_rows.json`).
4. **Major (F). Sleeve friction and the key rib cause hysteresis.** The 45 mm sleeve carries an 80 mm overhang, so axial friction is 0.46-1.4 x the vertical hand load (mu 0.1-0.3). The key-rib root fillet touches or overlaps the slot edge along the full 41 mm (0.00/0.01 mm; -0.496 mm³). Proportional sum/difference steering needs better than "push/no-push" (HANDOFF's own words).
   **Fix:**
   - Remove the rib root fillet, or chamfer the slot edges 1.0 mm. Rib 4.0 in a 4.8 slot gives 0.4 per side.
   - Make the sleeve at least 90 mm by moving the cell forward 45 mm. Or replace it with the HANDOFF's two 1.2 mm PLA leaf flexures (axial stiffness about 1/50 of the cell's).
   - Add a prismatic joint for the piston (±0.5 mm) and `fits` min 0.2.
5. **Major (M). The README hardware and steps don't match the model or the lab's stock.**
   - Mount: README says M8 button heads; the model has M5 caps in Ø5.5 holes.
   - Fin bolts: README says M4x20 countersunk; the model has M4 cap x16 in Ø8 counterbores. An M4 hex head (8.1 across corners) doesn't fit those counterbores.
   - Fin halves: README says M3x35 countersunk from outboard into nuts in hex pockets; the model has self-tappers from inboard and no hex pockets.
   - Boards: README says 12 screws + nuts from under; the model has 8 self-tappers from above.
   - Covers: README lists no screws; the model has 10 self-tappers.

   README steps 1, 5, 8 and 11-12 can't be done as written. The model also breaks HANDOFF's "never thread into plastic" rule (30 self-tappers). M8, DIN 7991 and the Ø15 fender washer aren't in the lab's M3-M5 hex-head stock.
   **Fix:** pick one fastener scheme from the lab's stock and regenerate README from the manifest: M5 hex-head x16 for the mount, M4 hex-head x20 with Ø9.5 counterbores, M3 self-tap x30 for the fin halves (or M3 hex x35 + nuts in 5.6 AF pockets). Then run `cad bom` against a BOM table it can parse.
6. **Major (F/M). The grip spigot is printed with its layers across the bending axis.** It's a Ø22.2/16 tube with a 68 mm arm to the hand: 13 MPa at 150 N and 26 MPa at 300 N, against the 15 MPa interlayer limit. It snaps at the spigot root.
   **Fix:** print the piston lying on its side with a 1.5 mm flat under the spigot (the grip hides it) and the key rib up. Or shrink the bore to Ø12 by moving the rear-nut access to a side window, which raises Z to about 1000 mm³. Add a `flexures` row (interlayer 15 MPa).
7. **Major (M). The rear M5 nut needs a 180 mm reach down a Ø16 bore.** It's tightened with a 1/4 in 8 mm socket; the README's ~150 mm extension plus socket gives about 175 mm, and a spanner plus a socket set isn't in the lab's tool list.
   **Fix:** shorten the spigot bore reach to 140 mm or less by moving the piston face forward, or capture the rear nut in a hex pocket in the piston (8.1 AF x 4.5) so the cell stud screws in by turning the piston. In both cases the only tool is a hex bit.
8. **Minor (M). The lid lifts off only along the plate face.** Straight up is blocked by the leaning plate at 2 mm, and removal clears the tray by 0.00 mm. Service of the cell takes about 22 fastener operations: 10 cover, 3 M4, 6 M3 (reachable only with the fin off), 2 nuts, and the grip.
   **Fix:** set the cover front edge 3 mm behind the plate line. Move the clamshell M3 heads to the outboard face in 6.5 mm counterbores with plugs, so the fin can be opened in place.
9. **Minor (F). Cable lead lengths aren't declared, and the patch cable kinks at R2.8 (OD 5).** A real 6 in patch cable plus boots needs about R20 and about 60 mm of plug length above the coupler.
   **Fix:** add `cable_leads` (cell lead length, 150 mm patch). Mount the coupler horizontal on the rear wall at z ≈ -40 so the patch is a straight 40 mm run to the ESP32 jack.
10. **Minor (A). There's no single radius family.** The fins use R4/R6/R10/R12, the tray R0.5/1/2/4 and the cover R0.5/1/1.5/4; the declared `edge_r=4` is used once. The cover screws form an irregular pattern (front x ±70/145, rear ±25/75/125), with empty holes in the hero view.
    **Fix:** use R6 for the convex edges of all exterior parts and R1 for the internal ones. Put the cover screws on one 3 x 2 grid per half (x ±30/±75/±120, both rows).
11. **Minor (process).** Renders 02-08 are dated Oct 23, older than the Oct 26 build, so they're stale. FST_Board_screw_6/7 carry host "Tray L" but sit in tray R. All 65 warns are untriaged.

## Check-config audit
- `--only` without stability: **agreed**. The unit is bolted. A mount-moment check (issue 2) should replace it, but cadcheck has no such row, so it's hand-calculated here.
- All 7 `allow` entries: **agreed**. Cell to fin measures 0.027 mm (no real overlap); the grip clamp, stud hardware and ESP32 stand-in holes are physical.
- Missing: a prismatic piston joint; `fits` for the sleeve and key rib; `distances` for the overload stops; `service` rows (added in review_rows.json, which pass with covers off); `cable_leads`; a `flexures`/interlayer row for the spigot. `fasteners.max_standoff` warns should have been triaged as fails.
- `assembly_order` places `CAB_*` (including the load-cell leads) at "electronics into the trays", before the handles exist. README's order (handles, then electronics, then fin to tray, then mount) differs from checks.json (T-nuts, electronics, handles, fin to tray, mount). Make one match the other.

## What is good
- Printing: 10 parts, no supports anywhere (printcheck PASS for both flat and standing fins), 18.9 h and about 1.06 kg total. Every part fits the P1S.
- The load path concept is sound: the cell sees only axial load, the sleeve takes bending, the boss slot clocks the cell, and the key rib stops rotation.
- Clean unified wedge form, flush cover, light upper / dark lower, no visible wires, and a clean outboard face on the fins (`r_left_fin_outboard.png`).
- Handles at exactly 355.6 mm (14 in). The lead route uses R13 bends with 0.67-1.2 mm clearance to the walls.
