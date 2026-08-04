# Wall-A Electronics Shelves (v0.5)

> **Before printing anything: run `python sim/simulate.py`** — the
> [digital-twin simulation](sim/README.md) checks every solid (parts,
> boards, batteries, fasteners, driver access, keep-outs) and must report
> 0 FAIL. `sim/wall_a.FCStd` is the full assembly for FreeCAD.

Two printed shelves that use the MR6 chassis's **own shelf system**
(Thingiverse thing:2753227) — no base plate, no walls, open-air access.
Parametric Python ([hull.py](hull.py), build123d); re-run `python hull.py`
to regenerate STL + STEP. Both print flat, no supports.

| Piece | Position | Carries |
|-------|----------|---------|
| `uno_shelf` | middle-shelf rails, chassis z 18.5..21.5 (slide in from the front) | Arduino Uno + OSEPP shield on 4mm bosses, ports forward. USB-B pokes 4mm past the front edge; M3/M4 motor terminals hang over the open rear edge, right above where the Tamiya leads rise. |
| `batt_bracket` ×2 | feet on the stock **30mm standoffs** (holes at the standoff line, plain M3×10), legs outboard of the shield, flange segments at the ends with deck pilots — the gaps between segments keep the foot screws driver-accessible | One STL printed **twice** (symmetric — same part both sides, printed lying flat for strength). Together the two brackets form the `_∏_` bridge over the Uno. |
| `batt_deck` | 80 × 139 flat plate on the bracket flanges, chassis z 77.5..80.5; bolts come **up from below** into nuts seated in hex pockets on the deck top | **Both batteries, stacked**: the 71.7 × 135 × 15.8 pi/arduino pack on the bed (side rails, 12 tall), the 65.4 × 117.4 × 7.2 motor pack on top of it — zip-ties/velcro through the grid hold the pair. Four edge towers (at ±38.25) with **cross-nut slots** near their tops carry the pi_shelf. Leaves the **28.5mm wire tunnel** over the shield. |
| `pi_shelf` | 80-wide flat plate on the deck towers, chassis z 104.5..107.5, M3×12 into the tower cross-nuts | Pi 5 on 5mm bosses, USB-A/Ethernet flush with the front edge, USB-C/HDMI at the open +W edge. Board at chassis z 112.5, top 131.2. |

Both shelves use the stock 4-hole pattern — chassis (x −94.5/−27.5,
y 27.5/56.9) — nuts below the `uno_shelf` (as the stock middle shelf),
standoffs through it, screws or nuts on top of the `pi_shelf` (as the
stock top shelf). A 10mm-pitch Ø3.2 prototyping grid covers both plates.

## The height chain (why this works)

Caliper-measured on the real hardware (2026-07-22): Uno PCB bottom → top
of the stacked OSEPP shield = **23.5 mm**.

```
21.5  uno_shelf top
+4.0  bosses
+23.5 Uno + shield stack        -> 49.0 stack top
51.5  standoff tops = bracket feet
77.5  deck underside            -> 28.5 mm WIRE TUNNEL (user-measured need)
80.5  battery bed
      ..96.3  pi/arduino pack (15.8, measured)
      ..103.5 motor pack on top (7.2, measured)
104.5 towers top = pi_shelf underside  -> 1.0 mm over the packs
112.5 Pi board, top of Pi 131.2
```

fit_check asserts this chain on every build, plus: single-solid STLs,
hole-to-boss alignment against the reference models (Pi 0.012mm,
Uno 0.37mm), and standoff/hardware clearance to both boards (7.5mm Uno,
5.4mm Pi).

## ⚠ Verify before printing

At the middle-shelf level the shield sits **between the mounts (60.0mm
gap)**. The OSEPP terminal blocks overhang the 53.4 board — measure the
shield's total width across the blocks: it must be **< 59.5mm** to slide
in. If it's wider, say the word and the bosses get taller (the stack can
ride above the mount tops at the cost of the 2.5mm margin — or the Pi
shelf gains taller standoffs).

## Assembly

1. Click 4 M3 nuts under the middle-rail positions (stock cages).
2. Bench-mount the Uno + shield on `uno_shelf`; slide it into the middle
   rails from the front; drop the 30mm standoffs through the 4 holes into
   the nuts.
3. Wire the motors (leads rise behind the shelf's rear edge into the
   rear-facing M3/M4 blocks) and power. Full open access.
4. Bench-mount the Pi on `pi_shelf`; set it on the standoffs; screw down.
5. Pi→Uno USB A-to-B: short loop down the open front.

## Hardware

Everything is **through-bolted with nuts** (no self-tapping anywhere) using
the user's M2–M5 button-head + nut assortment. Printed in **PETG**.

- 4× M3 nuts + 4× 30mm M3 standoffs — the stock shelf kit (middle rails)
- 4× **M3×8** — bracket feet down into the standoffs (open sky above every
  foot screw — the flanges sit beyond the foot ends)
- 4× **M3×12** — up from under the flanges into **M3 nuts seated in hex
  pockets** on the deck top (flush under the battery)
- 4× **M3×12 + nuts** — pi_shelf down into the tower **cross-nut slots**
  (slide a nut into each slot near the tower top; the screw threads into
  it — towers are too tall for through-bolts)
- 4× **M3×12 + nuts** — Uno through its bosses, nuts under the shelf
- 4× **M2×12 + nuts + washers** — Pi through its bosses (M2 passes the
  Pi's Ø2.7 board holes; washer under each nut)

## Print settings (A1 Mini, PLA/PETG)

**PETG**, 0.2mm layers, 4 walls, 15% infill (PETG: dry filament, slower
outer walls). Every part prints flat with **no supports** — including
`batt_bracket` (print it lying on its side face, twice) and `batt_deck`
(towers and rails point up).

## Roadmap

- [ ] Body shell + Wall-E head (Camera Module 3 eye) that drops over the
      shelf stack — the previous head/eye geometry lives in git history
- [ ] Battery placement (bottom-shelf bay or rear over the gearbox)
- [ ] Front bumper if the forward plugs prove exposed

Reference models live in `hardware/reference/` (gitignored);
[analyze_mr6.py](analyze_mr6.py) / [render_mount.py](render_mount.py)
document the measured chassis interface (`preview/mount_sections.png`).
