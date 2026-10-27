# Review: space-bar push assist, attempt 8

Checks re-run (copies in /tmp/a8rev):
- Main check: CADCHECK PASS, 0 fail, 51 warn (0 untriaged). The warn set is identical to `cadcheck_a8.json`. No unbounded allows and no stale accepts.
  - Coverage: 123 objects in all four collections, 61 screws / 24 nuts, 25 steps (0 parts in no step), 19 slides, 43 stacks, 6 flexures, 5 cables.
  - Not checked: pilot/clearance diameters, wrench access to nuts, non-straight insertion paths, cable slack.
- Moving rows: PASS, 0/0.
- a7 review rows, verbatim (`cadcheck_a7rows.json`):
  - Both cell-path rows pass, and they now see the cartridge.
  - The stops-first row is blocked at 4 mm. That is the expected end stop.
  - Three rows fail, all stale or superseded: the two guided-bound shunt rows (the crown removes that bound) and the 1.6 mm washer row.
- `cad printcheck` on `cad/print/stl`: PASS, 18 parts, 0 fail, 20 warn.
- `cad bom`: PASS, 13 rows.
- My rows (`review_rows.json` -> `cadcheck_review.json`): 2 slides pass, 5 stacks fail, 1 warn.

| Metric | Score | Anchor matched | One-line reason |
|---|---|---|---|
| Functionality | 8 | 8: works, ≤2 majors with a fix under 1 h | The cell now fits (also proven on the STLs), crosstalk is 0 and the stops and catch re-derive. No print settings are given, though: at slicer defaults the piston is overstressed at a 226 N lean |
| Manufacturability | 8 | 8: 0 fails, 2 majors | No supports, 26.5 h, everything fits the beds. The two majors: no print spec, and the right amp's jumper tethers the tray halves (7 mm slack) before they are hung separately |
| Aesthetics | 9 | 9: every item holds | Clean exterior. The cover heads now read as aligned Phillips pan heads in chamfered counterbores. No exposed wires |

## Previous issues
| a7 issue | Status | New number |
|---|---|---|
| 1 cell cannot be fitted (blocker) | FIXED | Slide rows pass with the cartridge seen. My STL sweep over 0-60 mm puts 0 points of the cell, studs, washer or nut inside `cartridge_R`/`_L.stl`, and the reverse test is clean (`scripts/stl_cell_path.py`) |
| 2 friction shunt 13-33 N | PARTIAL | 1.1-3.9 N with a free saddle; 4.0-7.4 N on a 300 N lean after flattening; 11.9-19.6 N during a 600 N lean |
| 3 past-contact model | FIXED | Rear strips 1043-1538 N; ×3.05 to buckling (×2.42 with a 1.2 FS push on top) |
| 4 washers over the slot | PARTIAL | 2.4 mm now, but the Ø13 ring is only 3.85 wide: 20.4-30.7 MPa at 1.2 FS (row 20.46 > 20) |
| 5 catch gap | FIXED | Gap 0.15; pull + lean margin 85-165 N. The README's "100 N" fails at a consistent E 2500 (warn row) |
| 6 piston stress | PARTIAL | 45.6 MPa nominal (agree). The step's Kt brings it to 59-68 MPa. No infill spec |
| 7 assembly_order text | FIXED | Cell first. The stops-first row is blocked at 4 mm, as intended |
| 8 purchased parts unverified | PARTIAL | Still unverified, but now flagged, and the amp pads are drill-to-fit |
| 9 cover heads as black holes | FIXED | Renders 03, 04 and 08 |

## Measurements
All in `head_a8.txt` unless noted. My script imports nothing from `head_calc.py`.

| Item | Value | Source |
|---|---|---|
| Cell path on the STLs | 0 / 0 points inside (both cartridges); world-to-print transform matched at 0.000 mm | `scripts/stl_cell_path.py`, `dump_verts.py` |
| Lean crosstalk | 0.000 %; 0.04 / 0.10 % at a 0.2 / 0.5 mm height error (L27 and Le25) | `head_a8.py` 1 |
| Catch contact | 200 / 240 / 280 N at E 2500 / 3000 / 3500; 133-187 N if the gap prints 0.10 | 2 |
| Pull pitch at the catch, and pull + lean margin | 0.086 / 0.072 / 0.061 mm; 85 / 125 / 165 N (designer 104.6, mixing E values) | 2 |
| Three supports at 600 N | Rear strips 1043-1447 N (E 2500), 1215-1538 N (E 3500); catch 313-738 N | 3 |
| Rear-strip buckling | 4407 N (E 2500, L27) -> ×3.05; ×2.42 with a 1.2 FS push couple | 3 |
| Catch-leg buckling | 2181 N pinned at the contact (agree); sway if friction slips about 250 N (friction μN ≈ 220 N holds) | 4 |
| Shunt, free saddle | 1.12-1.57 N (0.12 mm), 2.8-3.9 N (0.30 mm) | 5 |
| Crown land after 738 N | 15-18 mm around the bore × 0.52-0.64 mm along y (designer 10 × 0.92) | 5 |
| Shunt, flattened crown | 4.0-7.4 N (later 300 N lean); 11.9-19.6 N (during 600 N) | 5 |
| Saddle across layers at 738 N | 14.2 MPa (point, clamped, solid); 9.5 (distributed load); 19.7 at default infill | 6 |
| Piston at 600 N | Mouth 45.2 (41.6 with catch relief), catch 42.3, step 45.6 nominal, 59-68 MPa with Kt | 7 |
| Piston at slicer defaults | I_eff 5224 vs 15358; 133 MPa at 600 N; walls reach 50 MPa at 226 N | 7 |
| Stop stiffness | Mine about 13.4 kN/mm per pair (solid); the designer's 6-7.6 is the conservative side | 8 |
| Cell at a 600 N shove | 50 kg: 1.15-1.20 × FS (stops barely engage). 20 kg: 1.33-1.91 × FS | 8 |
| Washers at 1.2 FS pull | Rear Ø13: 20.4-30.7 MPa; front Ø15: 16.2-24.3 MPa; 7-10 MPa sustained from the clamp | 9 |
| Overhangs on the STLs | Cartridge 793 mm² (8.9 mm socket bridge, 27.2 strip bridges, 22 mm catch-leg bridge, small-hole tops). Cradle 551 (lug at 46°, round Ø16 hole, corner-up pockets). Fin 4070-4237 (pocket roofs, spans up to about 23 mm). Tray 846-877 (bed-edge strips) | `overhang_locate.py`, `roof_span.py` |
| R amp jumper | 142.8 of 150 mm | `cables` row |
| Print | 18 parts, 26.5 h, 4 plates (2 H2D, 2 P1S), 0 supports | BOM, `plates.txt` |

## Issues
1. **Major (F, M): no print settings are given for the load-path parts.**
   - Evidence:
     - The README, BOM, `plates.txt` and `export_prints.py` say nothing about infill or walls, and the 3MFs carry no settings.
     - At slicer defaults (2 walls, 15 %), the piston mouth sees 133 MPa at a 600 N lean, and the walls reach 50 MPa at 226 N.
     - The saddle sees 19.7 MPa across layers, against its limit of 15.
     - The a8R rows fail.
   - Fix:
     - Piston, cartridge, washers and setting plug: 100 % infill, as per-object settings in the 3MFs and a BOM column.
     - Fins and trays: 4 walls, 25 %.
2. **Major (M): the right amp's Qwiic jumper (142.8 of 150 mm) is plugged at step 6, but the halves are hung separately at step 10.**
   - Fix: plug it in a new step 10b, before the cover. Buy a 200 mm cable, or move amp R 40 mm inboard. Add the step to `assembly_order`.
3. **Minor: the shunt reaches 12-20 N while 600 N rests on one grip.**
   - Fix: a lean-aware dead band in firmware, or a smaller crown. Bench-test with 30 kg hung on one grip.
4. **Minor: the piston's 45° step reaches 59-68 MPa.**
   - Fix: an R4 fillet, and move the step to y 147. That gives 42 MPa nominal, about 48 with Kt.
5. **Minor: the Ø13 washer is 20-31 MPa.**
   - Fix: a 3.0 mm rear washer (13-20 MPa; the stud has 1.05 mm to spare), or a D-shaped washer. Correct the row's strip width.
6. **Minor: the README's "pull + 100 N lean" claim fails at a consistent modulus (0.161 > 0.15).**
   - Fix: quote 85 N, or open catch_c to 0.18 (125 N).
7. **Minor: the M4 × 20 fin-to-tray screws need a 3 mm L-key (access row: L-key only).**
   - Fix: add the key to the tools and to step 7.
   - The handle comes off outboard only (my rows: clear over 250 mm in +x; blocked in +z by the plate). Say so in the service text.
8. **Minor: the fin pocket roofs span up to about 23 mm, not 9-18** (`roof_span.py`).
   - Fix: accept, or add a 1.5 mm rib. Correct the accept text.
9. **Minor: the cradle's corner-up M4 pockets and its round Ø16 hole print worse than they need to.**
   - Fix: flat-up pockets and a teardrop hole.
10. **Minor: the purchased parts are still unverified.**
    - Fix: measure a board and the header before the print run.

## Check-config audit
- **Allows.** All 5 agreed: cell × nuts, piston × grip, and the two stand-in screw allows. None blinds a slide or insertion row. The cell × cartridge allow is gone, so the cell rows see the cartridge.
- **Slide-row ignores.** They drop only later-step parts: agreed.
- **Disputed rows:**
  - The washer row: its strip (6.05) is wider than the washer's ring (3.85).
  - The `catch_pull_lean_margin` row mixes E 3000 and E 2500.
  - The piston rows check nominal stress only, with no Kt and no infill assumption.
- **Missing service slide.** No slide row covered "fin off the tray". I added one: outboard is clear.
- **Missing step.** `assembly_order` has no step that plugs the right jumper after the halves are hung (issue 2).
- **Drop and stability.** Not applicable (a force sensor bolted to a chair).
- **Accepted warns.** All 51 are explained. The fin C-roof span text is understated (issue 8).

## What is good
- **The cell fits.** It is proven three ways: rows that nothing blinds, the insertion check, and an STL sweep in both directions.
- **The head design is sound.** Crosstalk is 0 by geometry; the crowned catch keeps the shunt small for normal leans; and the 50 kg cell stays at 1.2 × FS on a 600 N shove.
- **The designer's numbers re-derive within a few percent once a consistent modulus is used.** That covers contact load, three-support sharing, leg buckling, the shunt and the stops.
- **Manufacturing is clean.** 0 fails, 0 supports, every part fits the H2D or P1S, 26.5 h of printing, no soldering iron, and only kit hardware (BOM PASS).
- **The exterior is unified.** One wedge form, one reveal, a two-colour cover/body split, and aligned, counterbored cover heads.
