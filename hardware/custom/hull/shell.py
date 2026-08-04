"""Wall-A body shell v0.6 — the Wall-E torso + head that drops over the
v0.5 shelf stack. Two pieces, both support-free:

  shell_sleeve  open-ended wall ring (prints upside-down, rim up):
                registration ribs hug the pi_shelf and batt_deck edges,
                4x M3x12 horizontal into the pi_shelf's new edge holes,
                interior corner posts (upper half only — clear of the
                deck) with cross-nut slots for the roof.
  shell_roof    flat roof + the two-eye head (standard Camera Module 3
                behind the left eye, Ø12 window), ribbon slot, 4x M3x12
                down into the sleeve post cross-nuts.

Openings: front Pi-port window, +W USB-C/HDMI window, -W vent slots, and
an open rear service bay (motor terminals, pack ends, tunnel access).

Axes/frames identical to hull.py. Run:  python shell.py
"""
from pathlib import Path
import sys

from build123d import (Align, Box, BuildPart, BuildSketch, Compound,
                       Cylinder, Locations, Mode, Plane, RegularPolygon,
                       Rot, extrude, export_step, export_stl, Location)

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import hull as H

# ------------------------------------------------------------ envelope
WALL = 2.4
INT_W = 84.0                  # clears the tower cross-nut corners (±41.4)
INT_L0, INT_L1 = -86.0, 55.0  # deck (-85..54) + 1 per side
EXT_W = INT_W + 2 * WALL
SLEEVE_Z0 = 79.0              # hull z; chassis 73.9 — skirts the deck
ROOF_Z = 138.6                # roof underside; 2.3 over the Pi's top
ROOF_T = 3.0
SLEEVE_H = ROOF_Z - SLEEVE_Z0
CTR_L = (INT_L0 + INT_L1) / 2

# registration ribs (0.7 proud strips hugging the plates' edges)
RIB_P = 0.7
DECK_BAND = (H.BATT_DECK_Z - 0.5, H.BATT_DECK_Z + H.PLATE_T + 2.0)
PI_BAND = (H.PI_PLATE_Z - 0.5, H.PI_PLATE_Z + H.PLATE_T + 2.0)

# side screws into the pi_shelf edge (holes added in hull.py)
SIDE_SCREWS_L = (-40.0, 20.0)
SIDE_SCREW_Z = H.PI_PLATE_Z + H.PLATE_T / 2

# interior corner posts: only above the WIDE pack (sim: posts at the
# corners ran straight through the 135mm battery)
POST = 8.0
POST_Z0 = H.BATT_DECK_Z + H.PLATE_T + H.BATT2_H + 1.0
POST_CENTERS = [(sx * (INT_W / 2 - POST / 2), ly)
                for sx in (-1, 1)
                for ly in (INT_L0 + POST / 2 + 1, INT_L1 - POST / 2 - 1)]
NUT_SLOT_BELOW = 5.8          # cross-nut slot center below the post top

# openings
FRONT_PORT_W = 56.0           # Pi USB-A / Ethernet window
FRONT_PORT_Z = (H.PI_BOARD_Z - 3.0, H.PI_BOARD_Z + 21.0)
# USB-C/HDMI cluster: center 60.4 behind the board's port-end edge,
# 35.8 span (measured from the reference Pi STL)
_uc = (H.PI_BOARD_REAR + H.PI_L) - 60.4
SIDE_CUT_L = (_uc - 24.0, _uc + 24.0)
SIDE_CUT_Z = (H.PI_BOARD_Z - 4.0, H.PI_BOARD_Z + 14.0)
REAR_BAY_W, REAR_BAY_Z1 = 60.0, 122.0          # open service bay
UNO_USB_W = (-26.0, -6.0)     # Uno USB-B window, front wall
UNO_USB_Z = (H.UNO_BOARD_Z - 3, H.UNO_BOARD_Z + 16)

# head (archived v0.4 geometry, standard Camera Module 3)
HEAD_W, HEAD_D, HEAD_H = 46.0, 40.0, 30.0
HEAD_WALL = 2.4
EYE_SPACING, EYE_Z = 23.0, 15.0
CAM_HOLE_DX, CAM_HOLE_DY = 21.0, 12.5
CAM_SCREW_D, CAM_LENS_D = 2.2, 12.0
CAM_RECESS_D, CAM_RECESS_DEPTH = 20.0, 1.2

OUT = HERE
(OUT / "stl").mkdir(exist_ok=True)
(OUT / "step").mkdir(exist_ok=True)

# ================================================================ sleeve
with BuildPart() as sleeve:
    with Locations((0, CTR_L, SLEEVE_Z0)):
        Box(EXT_W, INT_L1 - INT_L0 + 2 * WALL, SLEEVE_H,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
        Box(INT_W, INT_L1 - INT_L0, SLEEVE_H,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
            mode=Mode.SUBTRACT)

    # registration ribs: wall-to-(plate edge + 0.3) infill strips.
    # PI-band ribs are segmented to dodge the seat-screw heads at l -45/+14.
    for band_z0, band_z1, half_w, segs in (
            (*DECK_BAND, H.BATT_SHELF_W / 2 + 0.3, [(-80.0, 49.0)]),
            (*PI_BAND, H.PI_SHELF_W / 2 + 0.3,
             [(-58.0, -53.0), (-37.0, 6.0), (22.0, 38.0)])):
        rib_w = INT_W / 2 - half_w
        for sx in (-1, 1):
            for s0, s1 in segs:
                with Locations((sx * (half_w + rib_w / 2),
                                (s0 + s1) / 2, band_z0)):
                    Box(rib_w, s1 - s0, band_z1 - band_z0,
                        align=(Align.CENTER, Align.CENTER, Align.MIN))

    # interior corner posts (upper zone) + cross-nut slots
    for cx, cy in POST_CENTERS:
        with Locations((cx, cy, POST_Z0)):
            Box(POST, POST, ROOF_Z - POST_Z0,
                align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((cx, cy, ROOF_Z)):
            Cylinder(H.HOLE_D / 2, 12,
                     align=(Align.CENTER, Align.CENTER, Align.MAX),
                     mode=Mode.SUBTRACT)
        with Locations((cx, cy, ROOF_Z - NUT_SLOT_BELOW)):
            Box(POST * 3, 5.9, 2.7, mode=Mode.SUBTRACT)

    # side screw holes into the pi_shelf edge
    rot_x = Rot(0, 90, 0)
    for sx in (-1, 1):
        for sl in SIDE_SCREWS_L:
            with Locations((sx * (INT_W / 2 + WALL / 2), sl, SIDE_SCREW_Z)):
                with Locations(rot_x):
                    Cylinder(H.HOLE_D / 2, WALL * 3, mode=Mode.SUBTRACT)

    # front window: Pi USB-A / Ethernet
    with Locations((0, INT_L1 + WALL / 2,
                    (FRONT_PORT_Z[0] + FRONT_PORT_Z[1]) / 2)):
        Box(FRONT_PORT_W, WALL * 3, FRONT_PORT_Z[1] - FRONT_PORT_Z[0],
            mode=Mode.SUBTRACT)
    # front window: Uno USB-B (the shell skirts down over it)
    with Locations(((UNO_USB_W[0] + UNO_USB_W[1]) / 2, INT_L1 + WALL / 2,
                    (UNO_USB_Z[0] + UNO_USB_Z[1]) / 2)):
        Box(UNO_USB_W[1] - UNO_USB_W[0], WALL * 3,
            UNO_USB_Z[1] - UNO_USB_Z[0], mode=Mode.SUBTRACT)
    # +W window: USB-C / HDMI
    with Locations((INT_W / 2 + WALL / 2,
                    (SIDE_CUT_L[0] + SIDE_CUT_L[1]) / 2,
                    (SIDE_CUT_Z[0] + SIDE_CUT_Z[1]) / 2)):
        Box(WALL * 3, SIDE_CUT_L[1] - SIDE_CUT_L[0],
            SIDE_CUT_Z[1] - SIDE_CUT_Z[0], mode=Mode.SUBTRACT)
    # -W vents
    for i in range(-3, 4):
        with Locations((-(INT_W / 2 + WALL / 2), i * 12.0 + CTR_L, 122.0)):
            Box(WALL * 3, 4.0, 22.0, mode=Mode.SUBTRACT)
    # rear service bay (open)
    with Locations((0, INT_L0 - WALL / 2,
                    (SLEEVE_Z0 + REAR_BAY_Z1) / 2)):
        Box(REAR_BAY_W, WALL * 3, REAR_BAY_Z1 - SLEEVE_Z0,
            mode=Mode.SUBTRACT)

# ================================================================ roof
HEAD_CTR_L = INT_L1 + WALL - HEAD_D / 2   # head front flush with the shell

with BuildPart() as roof:
    with Locations((0, CTR_L, ROOF_Z)):
        Box(EXT_W, INT_L1 - INT_L0 + 2 * WALL, ROOF_T,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    for cx, cy in POST_CENTERS:
        with Locations((cx, cy, ROOF_Z)):
            Cylinder(H.HOLE_D / 2, ROOF_T,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

    # head
    head_z = ROOF_Z + ROOF_T
    front = INT_L1 + WALL
    with Locations((0, HEAD_CTR_L, head_z)):
        Box(HEAD_W, HEAD_D, HEAD_H,
            align=(Align.CENTER, Align.CENTER, Align.MIN))
    with Locations((0, HEAD_CTR_L - HEAD_WALL / 2, head_z)):
        Box(HEAD_W - 2 * HEAD_WALL, HEAD_D - HEAD_WALL, HEAD_H - HEAD_WALL,
            align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
    with Locations((0, HEAD_CTR_L - HEAD_D / 2, head_z)):
        Box(HEAD_W - 2 * HEAD_WALL, HEAD_D, HEAD_H - HEAD_WALL,
            align=(Align.CENTER, Align.MAX, Align.MIN), mode=Mode.SUBTRACT)
    eye_rot = Rot(90, 0, 0)
    for side, is_cam in ((1, True), (-1, False)):
        ew = side * EYE_SPACING / 2
        with Locations((ew, front, head_z + EYE_Z)):
            with Locations(eye_rot):
                Cylinder(CAM_RECESS_D / 2, CAM_RECESS_DEPTH * 2,
                         mode=Mode.SUBTRACT)
        if is_cam:
            with Locations((ew, front - HEAD_WALL / 2, head_z + EYE_Z)):
                with Locations(eye_rot):
                    Cylinder(CAM_LENS_D / 2, HEAD_WALL * 3, mode=Mode.SUBTRACT)
            for sw in (-1, 1):
                for sz in (-1, 1):
                    with Locations((ew + sw * CAM_HOLE_DX / 2,
                                    front - HEAD_WALL / 2,
                                    head_z + EYE_Z + sz * CAM_HOLE_DY / 2)):
                        with Locations(eye_rot):
                            Cylinder(CAM_SCREW_D / 2, HEAD_WALL * 3,
                                     mode=Mode.SUBTRACT)
    # ribbon slot through the roof behind the head interior
    with Locations((0, HEAD_CTR_L - 10, ROOF_Z - 1)):
        Box(18, 4, ROOF_T + 2,
            align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)

# ================================================================ export
for name, bp in (("shell_sleeve", sleeve), ("shell_roof", roof)):
    export_stl(bp.part, str(OUT / "stl" / f"{name}.stl"))
    export_step(bp.part, str(OUT / "step" / f"{name}.step"))

print(f"sleeve: hull z {SLEEVE_Z0}..{ROOF_Z} ({SLEEVE_H} tall), ext "
      f"{EXT_W} x {INT_L1 - INT_L0 + 2 * WALL}")
print(f"roof+head: z {ROOF_Z}..{ROOF_Z + ROOF_T + HEAD_H} "
      f"(chassis top {ROOF_Z + ROOF_T + HEAD_H - 5.1:.1f})")
print("exported: stl/{shell_sleeve,shell_roof}.stl (+ STEP)")
