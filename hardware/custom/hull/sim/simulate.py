"""Wall-A digital-twin simulation.

Every physical object is modeled as a solid in the CHASSIS frame — printed
parts (exact STEP geometry), electronics envelopes (measured), both battery
packs (measured), standoffs, every screw/nut/washer, staged driver-access
volumes, and the wire-tunnel keep-out. Then:

  1. exact OCCT pairwise interference (any overlap volume = finding)
  2. printed parts vs chassis meshes (trimesh proximity)
  3. driver access per fastener, respecting ASSEMBLY STAGE
  4. keep-out volume intrusion

Outputs: sim/report.txt (+ exit 1 on FAIL), sim/manifest.json for
build_fcstd.py (FreeCAD assembly), sim/proxies/*.stl for the viewer.

Run:  python sim/simulate.py
"""
from pathlib import Path
import json
import sys

import numpy as np
import trimesh
from build123d import (Box, BuildPart, BuildSketch, Compound, Cylinder,
                       Locations, Mode, Plane, RegularPolygon, Align,
                       extrude, import_step, export_stl, Location)

HERE = Path(__file__).parent
HULL = HERE.parent
sys.path.insert(0, str(HULL))
import hull as H

MR6 = Path(r"C:\Users\austi\Documents\3dModels"
           r"\MR6 - Mini Prototyping Tank Robot - 2753227\files")
(HERE / "proxies").mkdir(exist_ok=True)

Z0 = 5.1
def C(w, l, z):
    """hull frame -> chassis frame"""
    return (w - 61.0, l + 57.5, z - Z0)

# ---------------------------------------------------------------- solids
OBJECTS = {}   # name -> dict(solid, stage, cat, color, note)

def add(name, solid, stage, cat, color, note=""):
    OBJECTS[name] = dict(solid=solid, stage=stage, cat=cat, color=color,
                         note=note)

def box_c(name, cx, cy, cz0, cz1, sx, sy, stage, cat, color, note=""):
    with BuildPart() as bp:
        with Locations((cx, cy, cz0)):
            Box(sx, sy, cz1 - cz0, align=(Align.CENTER, Align.CENTER,
                                          Align.MIN))
    add(name, bp.part, stage, cat, color, note)

def cyl_c(name, cx, cy, cz0, cz1, d, stage, cat, color, note=""):
    with BuildPart() as bp:
        with Locations((cx, cy, cz0)):
            Cylinder(d / 2, cz1 - cz0, align=(Align.CENTER, Align.CENTER,
                                              Align.MIN))
    add(name, bp.part, stage, cat, color, note)

def hex_c(name, cx, cy, cz0, cz1, af, stage, cat, color, note=""):
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(cz0)):
            with Locations((cx, cy)):
                RegularPolygon(af / 2 / 0.8660254, 6)
        extrude(amount=cz1 - cz0)
    add(name, bp.part, stage, cat, color, note)

T_CH = Location((-61.0, 57.5, -Z0))

# printed parts (exact STEP, exported in hull frame at absolute z)
PRINT_COLOR = (218, 165, 60)
for pname, stage in (("uno_shelf", 1), ("batt_deck", 3), ("pi_shelf", 4)):
    shape = import_step(str(HULL / "step" / f"{pname}.step"))
    add(pname, shape.moved(T_CH), stage, "printed", PRINT_COLOR)
br = import_step(str(HULL / "step" / "batt_bracket.step"))
add("bracket_R", br.moved(T_CH), 2, "printed", PRINT_COLOR)
add("bracket_L", br.mirror(Plane.YZ).moved(T_CH), 2, "printed", PRINT_COLOR)

# chassis meshes (trimesh only — checked by proximity, shown in FreeCAD)
CHASSIS_MESHES = {}
for n in ("LHS_Track_Frame_Mount", "RHS_Track_Frame_Mount",
          "Motor_Mount", "Back_Panel"):
    CHASSIS_MESHES[n] = trimesh.load(MR6 / f"{n}.stl")

# electronics envelopes (measured)
ub_z = H.UNO_BOARD_Z - Z0                       # Uno PCB bottom, chassis
ux, uy, _ = C(0, H.UNO_BOARD_FRONT - H.UNO_L / 2, 0)
box_c("uno_stack_env", ux, uy, ub_z, ub_z + H.UNO_STACK_H,
      59.0, H.UNO_L, 1, "electronics", (40, 160, 90),
      "Uno+OSEPP envelope incl. terminal overhang (measured 23.5 tall)")
# Uno USB-B overhang (from the reference mesh: w -23..-14.4, 6.5 past board)
usb_x0, usb_y0, _ = C(-23.0, H.UNO_BOARD_FRONT, 0)
usb_x1 = usb_x0 + 8.6
box_c("uno_usb_env", (usb_x0 + usb_x1) / 2, usb_y0 + 3.25,
      ub_z + 2.0, ub_z + 13.0, 8.6, 6.5, 1, "electronics", (40, 160, 90))

pb_z = H.PI_BOARD_Z - Z0
px, py, _ = C(0, H.PI_CTR_L, 0)
box_c("pi_env", px, py, pb_z, pb_z + H.PI_COMP_H,
      H.PI_W, H.PI_L, 4, "electronics", (40, 160, 90),
      "Pi 5 envelope (18.7 tall per reference STL)")
box_c("pi_ports_env", px, py + H.PI_L / 2 + H.PI_PORT_OVERHANG / 2,
      pb_z, pb_z + 16.0, 53.6, H.PI_PORT_OVERHANG, 4, "electronics",
      (40, 160, 90))

# batteries (measured; wide pack below, slim pack on top)
bed = H.BATT_DECK_Z + H.PLATE_T - Z0
bx, by, _ = C(0, H.BATT_CTR_L, 0)
box_c("batt_pi_arduino", bx, by, bed, bed + H.BATT2_H,
      H.BATT2_W, H.BATT2_L, 3, "battery", (90, 90, 100),
      "71.7 x 135 x 15.8 (measured)")
box_c("batt_motor", bx, by, bed + H.BATT2_H, bed + H.BATT2_H + H.BATT_H,
      H.BATT_W, H.BATT_L, 3, "battery", (120, 120, 130),
      "65.4 x 117.4 x 7.2 (measured)")

# standoffs + fasteners
STANDOFF_XY = [C(w, l, 0)[:2] for w, l in H.STANDOFF_HOLES]
shelf_top = H.MID_RAIL_TOP + H.PLATE_T - Z0     # 21.5 chassis
for i, (sx, sy) in enumerate(STANDOFF_XY):
    cyl_c(f"standoff_{i}", sx, sy, shelf_top, shelf_top + 30.0, 6.4, 1,
          "fastener", (170, 170, 175), "30mm M3 standoff")
    # stock attach: stud through shelf AND middle rail into a nut in the
    # rail's cage void below (rail spans chassis z 15..18.5 here)
    cyl_c(f"standoff_stud_{i}", sx, sy, 12.4, shelf_top, 3.0, 1,
          "fastener", (170, 170, 175))
    hex_c(f"standoff_nut_{i}", sx, sy, 12.4, 14.8, 5.5, 1, "fastener",
          (150, 150, 155), "nut in the rail cage void")

FASTENERS = []  # (name, head_top_z, drive_dir, stage, skip_driver)
def screw(name, cx, cy, head_z0, head_z1, shaft_z0, shaft_z1, stage,
          drive_dir, head_d=5.7, shaft_d=3.0):
    cyl_c(name + "_head", cx, cy, head_z0, head_z1, head_d, stage,
          "fastener", (200, 200, 205))
    cyl_c(name + "_shaft", cx, cy, shaft_z0, shaft_z1, shaft_d, stage,
          "fastener", (200, 200, 205))
    FASTENERS.append((name, cx, cy, head_z0, head_z1, drive_dir, stage))

# bracket feet -> standoff tops (M3x8, driven from above, stage 2)
foot_top = shelf_top + 30.0 + H.PLATE_T          # 54.5 chassis
for i, (fw, fl) in enumerate([(33.48, -30.0), (33.48, -0.6),
                              (-33.48, -30.0), (-33.48, -0.6)]):
    cx, cy, _ = C(fw, fl, 0)
    screw(f"foot_screw_{i}", cx, cy, foot_top, foot_top + 2.2,
          foot_top - H.PLATE_T, foot_top, 2, +1)

# deck bolts: up from under the flanges into deck-top hex-pocket nuts
for i, (dw, dl) in enumerate(H.DECK_SCREWS):
    cx, cy, _ = C(dw, dl, 0)
    fl_bot = H.BATT_DECK_Z - H.FLANGE_T - Z0
    screw(f"deck_bolt_{i}", cx, cy, fl_bot - 2.2, fl_bot,
          fl_bot, fl_bot + H.FLANGE_T + H.PLATE_T, 3, -1)
    hex_c(f"deck_nut_{i}", cx, cy, H.BATT_DECK_Z + H.PLATE_T - 2.4 - Z0,
          H.BATT_DECK_Z + H.PLATE_T - Z0, 5.5, 3, "fastener",
          (150, 150, 155), "nut in deck hex pocket")

# pi_shelf -> tower cross-nuts (M3x12 from above, stage 4)
for i, (pw, pl) in enumerate(H.PI_SEATS):
    cx, cy, _ = C(pw, pl, 0)
    top = H.PI_PLATE_Z + H.PLATE_T - Z0
    screw(f"pi_seat_screw_{i}", cx, cy, top, top + 2.2,
          top - H.PLATE_T - 8.0, top, 4, +1)
    slot_z = H.PI_PLATE_Z - 5.8 - Z0
    hex_c(f"tower_nut_{i}", cx, cy, slot_z - 1.2, slot_z + 1.2, 5.5, 3,
          "fastener", (150, 150, 155), "nut in tower cross-slot")

# Uno board screws (bench stage 0): heads over the board, nuts under shelf
for i, (bw, bl) in enumerate(H.UNO_BOSSES):
    cx, cy, _ = C(bw, bl, 0)
    shelf_bot = H.MID_RAIL_TOP - Z0
    screw(f"uno_screw_{i}", cx, cy, ub_z + 1.6, ub_z + 3.8,
          shelf_bot - 1.0, ub_z + 1.6, 0, +1)
    hex_c(f"uno_nut_{i}", cx, cy, shelf_bot - 2.4, shelf_bot, 5.5, 0,
          "fastener", (150, 150, 155))

# Pi board screws (bench): M2 heads over board, washer+nut under pi_shelf
for i, (bw, bl) in enumerate(H.PI_BOSSES):
    cx, cy, _ = C(bw, bl, 0)
    plate_bot = H.PI_PLATE_Z - Z0
    screw(f"pi_screw_{i}", cx, cy, pb_z + 1.6, pb_z + 3.2,
          plate_bot - 0.2, pb_z + 1.6, 0, +1, head_d=3.8, shaft_d=2.0)
    # M2 nut flush inside the pi_shelf's underside hex pocket (no washer)
    hex_c(f"pi_nut_{i}", cx, cy, plate_bot, plate_bot + 1.6, 4.0, 0,
          "fastener", (150, 150, 155), "nut in pi_shelf underside pocket")

# wire-tunnel keep-out (must stay empty): the header field of the shield
# (±26.5) over the full board length, the user's 28.5mm plug-in height
box_c("KEEPOUT_wire_tunnel", ux, uy, ub_z + H.UNO_STACK_H,
      H.BATT_DECK_Z - Z0, 53.0, H.UNO_L, 9, "keepout", (220, 60, 60),
      "28.5mm jumper access over the shield headers")

# staged driver volumes (Ø7 shaft; 25 = stubby/L-key FAIL, 80 = straight)
DRIVERS = []
for name, cx, cy, hz0, hz1, ddir, stage in FASTENERS:
    if stage == 0:
        continue  # bench-assembled
    for length, sev in ((25.0, "FAIL"), (80.0, "WARN")):
        z0 = hz1 if ddir > 0 else hz0 - length
        z1 = hz1 + length if ddir > 0 else hz0
        with BuildPart() as bp:
            with Locations((cx, cy, z0)):
                Cylinder(3.5, z1 - z0, align=(Align.CENTER, Align.CENTER,
                                              Align.MIN))
        DRIVERS.append(dict(name=f"driver[{name},{int(length)}]",
                            solid=bp.part, stage=stage, sev=sev,
                            owner_prefix=name))

# ---------------------------------------------------------------- checks
findings = []
names = list(OBJECTS)

# legitimate engagements: screw threads inside their own nut/washer, and
# board-mount screws passing through the (solid) board envelopes' real holes
WHITELIST = set()
for i in range(4):
    WHITELIST.add((f"uno_screw_{i}_head", "uno_stack_env"))
    WHITELIST.add((f"uno_screw_{i}_shaft", "uno_stack_env"))
    WHITELIST.add((f"uno_screw_{i}_shaft", f"uno_nut_{i}"))
    WHITELIST.add((f"pi_screw_{i}_head", "pi_env"))
    WHITELIST.add((f"pi_screw_{i}_shaft", "pi_env"))
    WHITELIST.add((f"pi_screw_{i}_shaft", f"pi_nut_{i}"))
    WHITELIST.add((f"deck_bolt_{i}_shaft", f"deck_nut_{i}"))
    WHITELIST.add((f"pi_seat_screw_{i}_shaft", f"tower_nut_{i}"))
    WHITELIST.add((f"uno_screw_{i}_shaft", f"standoff_nut_{i}"))
    WHITELIST.add((f"standoff_stud_{i}", f"standoff_nut_{i}"))

def pair_ok(a, b):
    return (a, b) in WHITELIST or (b, a) in WHITELIST

def vol(shape):
    try:
        return shape.volume
    except Exception:
        return 0.0

print(f"objects: {len(names)}; pairwise interference...")
sols = {n: OBJECTS[n]["solid"] for n in names}
bbs = {n: sols[n].bounding_box() for n in names}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if OBJECTS[a]["cat"] == "keepout" or OBJECTS[b]["cat"] == "keepout":
            continue
        if pair_ok(a, b):
            continue
        ba, bb = bbs[a], bbs[b]
        if (ba.max.X < bb.min.X - 0.01 or bb.max.X < ba.min.X - 0.01 or
                ba.max.Y < bb.min.Y - 0.01 or bb.max.Y < ba.min.Y - 0.01 or
                ba.max.Z < bb.min.Z - 0.01 or bb.max.Z < ba.min.Z - 0.01):
            continue
        v = vol(sols[a].intersect(sols[b]))
        if v > 0.11:
            findings.append(("FAIL", f"{a} ∩ {b} = {v:.1f} mm³"))

# keep-out intrusion
ko = sols["KEEPOUT_wire_tunnel"]
for n in names:
    if n == "KEEPOUT_wire_tunnel" or OBJECTS[n]["stage"] == 0:
        pass
    if n == "KEEPOUT_wire_tunnel":
        continue
    v = vol(ko.intersect(sols[n]))
    if v > 0.11:
        findings.append(("FAIL", f"KEEPOUT wire_tunnel violated by {n}: "
                                 f"{v:.1f} mm³"))

# staged driver access
for d in DRIVERS:
    for n in names:
        o = OBJECTS[n]
        if o["cat"] == "keepout" or o["stage"] > d["stage"]:
            continue
        if n.startswith(d["owner_prefix"]):
            continue
        bb = bbs[n]
        db = d["solid"].bounding_box()
        if (db.max.X < bb.min.X or bb.max.X < db.min.X or
                db.max.Y < bb.min.Y or bb.max.Y < db.min.Y or
                db.max.Z < bb.min.Z or bb.max.Z < db.min.Z):
            continue
        v = vol(d["solid"].intersect(sols[n]))
        if v > 0.11:
            findings.append((d["sev"],
                             f"driver blocked: {d['name']} hits {n} "
                             f"({v:.1f} mm³)"))

# printed/proxy parts vs chassis meshes (proximity, sampled)
print("chassis proximity...")
for n in names:
    stl_path = HERE / "proxies" / f"{n}.stl"
    export_stl(sols[n], str(stl_path))
    if OBJECTS[n]["cat"] in ("keepout",):
        continue
    m = trimesh.load(stl_path)
    pts = m.sample(400) if len(m.faces) > 2 else m.vertices
    for cn, cm in CHASSIS_MESHES.items():
        d = trimesh.proximity.signed_distance(cm, pts)
        pen = float(d.max())
        if pen > 0.1:
            findings.append(("FAIL", f"{n} penetrates {cn} by {pen:.2f} mm"))

# ---------------------------------------------------------------- report
sev_rank = {"FAIL": 0, "WARN": 1}
findings.sort(key=lambda f: sev_rank.get(f[0], 2))
lines = [f"Wall-A simulation report — {len(names)} solids, "
         f"{len(DRIVERS)} driver checks", "=" * 60]
if not findings:
    lines.append("ALL CLEAR — no interference, no blocked drivers, "
                 "keep-out empty")
for sev, msg in findings:
    lines.append(f"[{sev}] {msg}")
report = "\n".join(lines)
(HERE / "report.txt").write_text(report, encoding="utf-8")
print(report)

# manifest for the FreeCAD assembly builder
manifest = dict(chassis=[dict(name=n, path=str(MR6 / f"{n}.stl"),
                              color=(230, 115, 140))
                         for n in CHASSIS_MESHES],
                objects=[dict(name=n, stl=str(HERE / "proxies" / f"{n}.stl"),
                              color=OBJECTS[n]["color"],
                              cat=OBJECTS[n]["cat"],
                              transparency=(70 if OBJECTS[n]["cat"] ==
                                            "keepout" else 0))
                         for n in names])
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=1),
                                    encoding="utf-8")
print(f"\nmanifest.json + proxies/ written; "
      f"{sum(1 for s, _ in findings if s == 'FAIL')} FAIL / "
      f"{sum(1 for s, _ in findings if s == 'WARN')} WARN")
sys.exit(1 if any(s == "FAIL" for s, _ in findings) else 0)
