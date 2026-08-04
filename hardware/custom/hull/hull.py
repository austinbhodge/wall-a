"""Wall-A electronics shelves v0.5 — two printed shelves that use the MR6
chassis's OWN shelf system (Thingiverse thing:2753227): the Arduino rides a
middle-shelf replacement, the Pi rides a top-shelf replacement on the stock
30mm standoffs. No base plate, no walls — open-air, maximum access. A body
shell + Wall-E head can drop over this stack later.

  uno_shelf   middle-shelf position: 73.8 x 75 x 3, slides into the middle
              rails (chassis z 18.5..21.5, insert from the front), fastened
              at the stock 4 holes — chassis (x -94.5|-27.5, y 27.5|56.9) —
              with M3 nuts below and the 30mm standoffs screwed down
              through the plate. Arduino Uno + OSEPP shield on 4mm bosses,
              USB-B overhanging the front edge, M3/M4 motor terminals
              hanging over the open rear edge (motor leads rise right
              there from the gearbox).
  pi_shelf    top-shelf position: 74 x 99.5 x 3 resting on the standoff
              tops (underside chassis z 51.5), same 4-hole pattern, M3
              screws or nuts on top. Pi 5 on 5mm bosses, USB-A/Ethernet
              flush with the front edge, USB-C/HDMI at the open +W edge.

Height chain (chassis z), driven by the caliper-measured stack:
  21.5 shelf top + 4.0 boss + 23.5 Uno+shield (measured 2026-07-22)
     = 49.0 stack top  vs  51.5 pi_shelf underside  ->  2.5 mm clear.

Both shelves carry a 10mm-pitch Ø3.2 prototyping grid (MR6 idiom) for
zip-ties, sensors, and whatever comes next.

Axes: origin chassis (x -61, y 57.5); hull z = chassis z + 5.1 (kept from
v0.3/v0.4 so the chassis_fit transform stays (w-61, l+57.5, z-5.1)).
+L = front. Parts export in assembled position; lay flat to print.

Run:  python hull.py   -> STL + STEP into ./stl and ./step
"""

from pathlib import Path
from build123d import *

# ------------------------------------------------------------ MR6 interface
Z0 = 5.1                      # hull z of chassis z=0
MID_RAIL_TOP = 18.5 + Z0      # 23.6 — uno_shelf underside
TOP_SHELF_Z = 51.5 + Z0       # 56.6 — pi_shelf underside (30mm standoffs)
PLATE_T = 3.0
STANDOFF_HOLES = [(sx * 33.48, cy - 57.5)
                  for sx in (-1, 1) for cy in (27.5, 56.9)]
HOLE_D = 3.4                  # M3 clearance for screws / standoff studs

UNO_SHELF_W = 73.8            # middle-rail slot takes 74.0; 0.2 tolerance
UNO_SHELF_REAR, UNO_SHELF_FRONT = -40.0, 35.0    # chassis y 17.5..92.5

# ---- battery bridge (between the Uno stack and the Pi) -------------------
# TWO batteries, both measured by the user, STACKED on one deck:
#   motor pack:      65.4 wide x 117.4 long x  7.2 tall (rides on top)
#   pi/arduino pack: 71.7 wide x ~135  long x 15.8 tall (bottom — heavier,
#                    and too wide for the old 74 deck, hence 80mm deck)
# The user needs 28.5mm of open air above the Uno+shield stack to plug
# jumper wires into the headers, so the deck rides a BRIDGE: two side
# brackets (_| profile, feet on the 30mm standoffs) carry it.
BATT_W, BATT_L, BATT_H = 65.4, 117.4, 7.2         # motor pack (top)
BATT2_W, BATT2_L, BATT2_H = 71.7, 135.0, 15.8     # pi/arduino pack (bottom)
BATT_STACK_H = BATT_H + BATT2_H                   # 23.0
WIRE_CLEAR = 28.5             # measured need: stack top -> deck underside

# the bracket is longer than its foot: the flange segments sit BEYOND the
# foot ends, so every foot screw has wide-open vertical driver access and
# the deck screws have nothing underneath them (driven from below, nuts in
# hex pockets on the deck top). All fasteners are through-bolted — the
# user's kit is M2-M5 button-heads + nuts, printing in PETG.
# asymmetric: the front flange reaches past the shield so its bolt's
# below-driver path is clear (sim). Print the second bracket MIRRORED
# in the slicer.
BRACKET_L0, BRACKET_L1 = -57.0, 39.0
FOOT_L0, FOOT_L1 = -40.0, 10.0         # foot span (standoff holes within)
FOOT_W = 8.0
LEG_T = 3.5                   # vertical web, outboard of the shield
FLANGE_T = 6.0                # top flange segments at the bracket ends
FLANGE_SEG = 6.0
# bolt line inboard of the leg (sim: heads/drivers collide at ±33.48)
DECK_SCREWS = [(sx * 29.6, ly) for sx in (-1, 1) for ly in (-54.0, 37.0)]
FLANGE_W = 10.0               # flange widened inboard to carry the bolts
NUT_AF = 5.9                  # M3 nut pocket, across flats + clearance

BATT_SHELF_W = 80.0           # sized for the 71.7 pack + rails
BATT_SHELF_REAR, BATT_SHELF_FRONT = -85.0, 54.0  # chassis y -27.5..111.5
BATT_CTR_L = (BATT_SHELF_REAR + BATT_SHELF_FRONT) / 2
RAIL_T, RAIL_H = 2.4, 12.0    # side rails contain the lower (thick) pack
TOWER_T, TOWER_L = 3.5, 12.0  # towers at the 80mm deck edges
TOWER_W_CTR = BATT_SHELF_W / 2 - TOWER_T / 2     # ±38.25
PI_SEATS = [(sx * TOWER_W_CTR, ly) for sx in (-1, 1) for ly in (-45.0, 14.0)]

PI_SHELF_W = 80.0             # widened to reach the new seat line
PI_SHELF_REAR, PI_SHELF_FRONT = -60.0, 39.5      # chassis y -2.5..97
# (BATT_DECK_Z / BATT_STACK_TOP / TOWER_TOP / PI_PLATE_Z derived below,
#  after the measured Uno stack height)

GRID_PITCH, GRID_D = 10.0, 3.2

# ------------------------------------------------------------ electronics
# measured on the real hardware with calipers (2026-07-22):
UNO_STACK_H = 23.5            # Uno PCB bottom -> top of stacked OSEPP shield
# Arduino Uno R3; hole coords split the 0.3-0.6mm difference between the
# official drawing and hardware/reference/arduino_uno.stl. Ports face
# FRONT: hx from the USB corner, hy from the digital-pin edge (facing -W).
UNO_L, UNO_W = 68.6, 53.4
UNO_HOLES = [(14.0, 2.5), (15.25, 50.9), (66.0, 7.6), (66.05, 35.2)]
# through-bolted: M3x12 from the top, M3 nut under the shelf
UNO_BOSS_D, UNO_BOSS_H, UNO_PILOT_D = 7.0, 4.0, 3.4
UNO_BOARD_FRONT = 32.6        # USB tip ~36.8, pokes past the shelf edge
UNO_BOARD_Z = MID_RAIL_TOP + PLATE_T + UNO_BOSS_H
UNO_STACK_TOP = UNO_BOARD_Z + UNO_STACK_H

# battery-bridge height chain (depends on the measured stack)
BATT_DECK_Z = UNO_STACK_TOP + WIRE_CLEAR         # deck underside (hull z)
BATT_STACK_TOP = BATT_DECK_Z + PLATE_T + BATT_STACK_H
TOWER_TOP = BATT_STACK_TOP + 1.0   # pi seat plane, 1.0 over the batteries
PI_PLATE_Z = TOWER_TOP        # plain plate on the deck towers

# Raspberry Pi 5 (verified against hardware/reference STL), ports FRONT;
# hx measured from the far-from-ports edge
PI_L, PI_W = 85.0, 56.0
PI_HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
PI_BOSS_D, PI_BOSS_H, PI_PILOT_D = 6.0, 5.0, 2.4   # through-bolted:
# M2x12 + nut under the plate (the kit has M2, and it passes the Pi's
# Ø2.7 board holes; add an M2 washer under the nut)
PI_PORT_OVERHANG = 3.9
PI_COMP_H = 18.7              # tallest component per the reference STL
PI_BOARD_FRONT = 35.4         # port faces ~flush with the shelf front edge
PI_BOARD_REAR = PI_BOARD_FRONT - PI_L
PI_CTR_L = PI_BOARD_REAR + PI_L / 2
PI_BOARD_Z = PI_PLATE_Z + PLATE_T + PI_BOSS_H

assert TOP_SHELF_Z - UNO_STACK_TOP >= 2.0, (
    f"Uno+shield stack top {UNO_STACK_TOP} too close to pi_shelf "
    f"underside {TOP_SHELF_Z}")

OUT = Path(__file__).parent
(OUT / "stl").mkdir(exist_ok=True)
(OUT / "step").mkdir(exist_ok=True)
for stale in ("hull_base", "uno_deck", "pi_tray", "base_bay", "uno_level",
              "pi_level", "lid", "batt_shelf"):
    for ext, sub in ((".stl", "stl"), (".step", "step")):
        p = OUT / sub / f"{stale}{ext}"
        if p.exists():
            p.unlink()


def keepout(px, py, centers, r):
    return any((px - cx) ** 2 + (py - cy) ** 2 < r * r for cx, cy in centers)


def build_shelf(width, l_rear, l_front, bosses, boss_d, boss_h, pilot_d,
                grid_avoid, lift=0.0):
    """Plate + electronics bosses + standoff holes + prototyping grid.
    `lift` adds underside bosses at the standoff holes (needs slicer
    supports under just those bosses). Called inside a BuildPart context."""
    ctr_l = (l_rear + l_front) / 2
    with Locations((0, ctr_l, 0)):
        Box(width, l_front - l_rear, PLATE_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    if lift:
        for hw, hl in STANDOFF_HOLES:
            with Locations((hw, hl, 0)):
                Cylinder(LIFT_BOSS_D / 2, lift,
                         align=(Align.CENTER, Align.CENTER, Align.MAX))
                Cylinder(HOLE_D / 2, lift,
                         align=(Align.CENTER, Align.CENTER, Align.MAX),
                         mode=Mode.SUBTRACT)
        # trim the bosses flush with the plate outline — the Ø9 bulge
        # would otherwise poke ~1mm past the side edges
        for sx in (-1, 1):
            with Locations((sx * (width / 2 + 5), ctr_l, -lift)):
                Box(10, l_front - l_rear, lift,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                    mode=Mode.SUBTRACT)
    # bosses are through-drilled: machine screw from the top, nut below
    # the plate (user's kit: button-heads + nuts; PETG)
    for pw, pl in bosses:
        with Locations((pw, pl, PLATE_T)):
            Cylinder(boss_d / 2, boss_h,
                     align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((pw, pl, PLATE_T + boss_h)):
            Cylinder(pilot_d / 2, boss_h + PLATE_T,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)
    for hw, hl in STANDOFF_HOLES:
        with Locations((hw, hl, 0)):
            Cylinder(HOLE_D / 2, PLATE_T,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
    # prototyping grid, skipping bosses and standoff holes
    nw = int((width / 2 - 5) // GRID_PITCH)
    for i in range(-nw, nw + 1):
        gx = i * GRID_PITCH
        gl = l_rear + 7.5
        while gl < l_front - 5:
            if not keepout(gx, gl, bosses, 6.5) and \
               not keepout(gx, gl, STANDOFF_HOLES, 6.0) and \
               not keepout(gx, gl, grid_avoid, 6.5):
                with Locations((gx, gl, 0)):
                    Cylinder(GRID_D / 2, PLATE_T,
                             align=(Align.CENTER, Align.CENTER, Align.MIN),
                             mode=Mode.SUBTRACT)
            gl += GRID_PITCH


UNO_BOSSES = [(hy - UNO_W / 2, UNO_BOARD_FRONT - hx) for hx, hy in UNO_HOLES]
PI_BOSSES = [(-PI_W / 2 + hy, PI_BOARD_REAR + hx) for hx, hy in PI_HOLES]

with BuildPart() as uno_shelf:
    build_shelf(UNO_SHELF_W, UNO_SHELF_REAR, UNO_SHELF_FRONT,
                UNO_BOSSES, UNO_BOSS_D, UNO_BOSS_H, UNO_PILOT_D,
                grid_avoid=[])
    uno_shelf.part = uno_shelf.part.moved(Location((0, 0, MID_RAIL_TOP)))

# one bracket STL, printed twice (symmetric about its l-center, so the
# same part serves both sides rotated 180°). Modeled at the +W side.
with BuildPart() as batt_bracket:
    bl_ctr = (BRACKET_L0 + BRACKET_L1) / 2
    # foot on the standoff tops, holes at the standoff line — no flange
    # overhead anywhere along the foot: straight-down driver access
    with Locations((33.0, (FOOT_L0 + FOOT_L1) / 2, TOP_SHELF_Z)):
        Box(FOOT_W, FOOT_L1 - FOOT_L0, PLATE_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    for hl in (-30.0, -0.6):
        with Locations((33.48, hl, TOP_SHELF_Z)):
            Cylinder(HOLE_D / 2, PLATE_T,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
    # leg web, outboard of the shield stack, full bracket length
    with Locations((35.25, bl_ctr, TOP_SHELF_Z + PLATE_T)):
        Box(LEG_T, BRACKET_L1 - BRACKET_L0,
            (BATT_DECK_Z - FLANGE_T) - (TOP_SHELF_Z + PLATE_T),
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    # FULL-HEIGHT access windows above each foot screw (sim: a partial
    # window left the top chord blocking a straight driver). The leg
    # becomes three columns tied by the foot and the deck above.
    for hl in (-30.0, -0.6):
        with Locations((35.25, hl, TOP_SHELF_Z + PLATE_T)):
            Box(LEG_T * 3, 14.0,
                (BATT_DECK_Z - FLANGE_T) - (TOP_SHELF_Z + PLATE_T),
                align=(Align.CENTER, Align.CENTER, Align.MIN),
                mode=Mode.SUBTRACT)
    # leg extensions drop to foot level beyond the foot ends
    for e0, e1 in ((BRACKET_L0, FOOT_L0), (FOOT_L1, BRACKET_L1)):
        with Locations((35.25, (e0 + e1) / 2, TOP_SHELF_Z)):
            Box(LEG_T, e1 - e0, PLATE_T,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    # flange segments at the bracket ends, through-drilled Ø3.4:
    # M3x12 comes UP from below (open air underneath), nut in the deck's
    # hex pocket on top
    for fl in (BRACKET_L0 + FLANGE_SEG / 2, BRACKET_L1 - FLANGE_SEG / 2):
        with Locations((37.0 - FLANGE_W / 2, fl, BATT_DECK_Z - FLANGE_T)):
            Box(FLANGE_W, FLANGE_SEG, FLANGE_T,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    for hw, hl in DECK_SCREWS:
        if hw > 0:
            with Locations((hw, hl, BATT_DECK_Z - FLANGE_T)):
                Cylinder(HOLE_D / 2, FLANGE_T,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)

# flat battery deck: prints support-free (towers and rails point up)
with BuildPart() as batt_deck:
    build_shelf(BATT_SHELF_W, BATT_SHELF_REAR, BATT_SHELF_FRONT,
                [], 0, 0, 0, grid_avoid=PI_SEATS + DECK_SCREWS)
    # deck-to-flange bolts come up from below; their nuts sit flush in
    # hex pockets on the deck top (under the battery)
    for hw, hl in DECK_SCREWS:
        with Locations((hw, hl, 0)):
            Cylinder(HOLE_D / 2, PLATE_T,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(PLATE_T)):
            with Locations((hw, hl)):
                RegularPolygon(NUT_AF / 2 / 0.8660254, 6)
        extrude(amount=-2.5, mode=Mode.SUBTRACT)
    # side rails for the lower (71.7-wide) pack
    for sx in (-1, 1):
        with Locations((sx * (BATT2_W / 2 + 0.4 + RAIL_T / 2), -15.0,
                        PLATE_T)):
            Box(RAIL_T, 90.0, RAIL_H,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
    # pi_shelf seat towers at the 80mm deck edges, clear of both packs.
    # Screws: M3x12 from the pi_shelf top into a nut captured in a
    # cross-slot near each tower top (towers are too tall to through-bolt
    # with the kit's 16mm max).
    tower_h = TOWER_TOP - (BATT_DECK_Z + PLATE_T)
    for tw, tl in PI_SEATS:
        sx = 1 if tw > 0 else -1
        with Locations((sx * TOWER_W_CTR, tl, PLATE_T)):
            Box(TOWER_T, TOWER_L, tower_h,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((tw, tl, PLATE_T + tower_h)):
            Cylinder(HOLE_D / 2, 12,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)
        # nut cross-slot, open through the tower thickness — raised above
        # the wide pack's top edge (sim: nut corners clipped the battery)
        with Locations((sx * TOWER_W_CTR, tl, PLATE_T + tower_h - 5.8)):
            Box(TOWER_T * 3, 5.9, 2.7, mode=Mode.SUBTRACT)
    batt_deck.part = batt_deck.part.moved(Location((0, 0, BATT_DECK_Z)))

with BuildPart() as pi_shelf:
    build_shelf(PI_SHELF_W, PI_SHELF_REAR, PI_SHELF_FRONT,
                PI_BOSSES, PI_BOSS_D, PI_BOSS_H, PI_PILOT_D,
                grid_avoid=PI_SEATS)
    # seat holes down into the battery shelf's towers
    for hw, hl in PI_SEATS:
        with Locations((hw, hl, 0)):
            Cylinder(HOLE_D / 2, PLATE_T,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)
    # horizontal edge holes for the body shell's side screws (shell.py):
    # Ø2.7 in the plate edge, M3 self-taps in-plane — cosmetic-load only
    for sx in (-1, 1):
        for sl in (-40.0, 20.0):
            with Locations((sx * (PI_SHELF_W / 2 - 4), sl, PLATE_T / 2)):
                with Locations(Rot(0, 90, 0)):
                    Cylinder(2.7 / 2, 8.0, mode=Mode.SUBTRACT)
    # underside hex pockets so the Pi's M2 nuts sit flush — the motor pack
    # is only 1.0 below the plate (sim caught the nuts hitting it)
    for hw, hl in PI_BOSSES:
        with BuildSketch(Plane.XY.offset(1.8)):
            with Locations((hw, hl)):
                RegularPolygon(4.3 / 2 / 0.8660254, 6)
        extrude(amount=-1.8, mode=Mode.SUBTRACT)
    pi_shelf.part = pi_shelf.part.moved(Location((0, 0, PI_PLATE_Z)))

# ================================================================ export
PARTS = {"uno_shelf": uno_shelf, "batt_bracket": batt_bracket,
         "batt_deck": batt_deck, "pi_shelf": pi_shelf}
for name, bp in PARTS.items():
    export_stl(bp.part, str(OUT / "stl" / f"{name}.stl"))
    export_step(bp.part, str(OUT / "step" / f"{name}.step"))
export_step(Compound(children=[bp.part for bp in PARTS.values()]),
            str(OUT / "step" / "hull_assembly.step"))

print(f"uno_shelf:    chassis z 18.5..21.5, board z {UNO_BOARD_Z - Z0:.1f}, "
      f"stack top {UNO_STACK_TOP - Z0:.1f}")
print(f"batt_bridge:  feet on standoffs at {TOP_SHELF_Z - Z0:.1f}; deck "
      f"chassis z {BATT_DECK_Z - Z0:.1f}..{BATT_DECK_Z + PLATE_T - Z0:.1f}; "
      f"battery stack top {BATT_STACK_TOP - Z0:.1f}; towers to "
      f"{TOWER_TOP - Z0:.1f}")
print(f"pi_shelf:     plain plate on the towers, chassis z "
      f"{PI_PLATE_Z - Z0:.1f}..{PI_PLATE_Z + PLATE_T - Z0:.1f}, board z "
      f"{PI_BOARD_Z - Z0:.1f}, top {PI_BOARD_Z + PI_COMP_H - Z0:.1f}")
print(f"WIRE TUNNEL over the shield stack: "
      f"{BATT_DECK_Z - UNO_STACK_TOP:.1f} mm (need {WIRE_CLEAR})")
print("exported: stl/{uno_shelf,batt_bracket,batt_deck,pi_shelf}.stl "
      "(+ STEP; print batt_bracket TWICE)")
