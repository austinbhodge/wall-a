"""Fit-check for the v0.5 shelves: mount the reference Pi 5 and Uno STLs
on their shelves and verify hole alignment, standoff clearances, and the
measured-stack height chain. Imports hull.py so numbers always match.
"""
from pathlib import Path
import sys
import numpy as np
import trimesh

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import hull as H

for name in ("uno_shelf", "batt_bracket", "batt_deck", "pi_shelf"):
    mesh = trimesh.load(HERE / "stl" / f"{name}.stl")
    n = len(mesh.split(only_watertight=False))
    print(f"{name}: {n} component(s) [{'OK' if n == 1 else 'FLOATING'}]")
    assert n == 1

def near(v, targets, tol=0.6):
    return any(abs(v - t) < tol for t in targets)

# ================================================================== Pi 5
pi = trimesh.load(HERE.parents[1] / "reference" / "raspberry_pi_5.stl")
sec = pi.section(plane_origin=[0, 0.7, 0], plane_normal=[0, 1, 0])
loops = sec.discrete
outline = max(loops, key=lambda p: np.ptp(p[:, 0]) * np.ptp(p[:, 2]))
bx0, bz0 = outline[:, 0].min(), outline[:, 2].min()
holes = []
for pts in loops:
    c = pts.mean(axis=0)
    r = np.linalg.norm(pts[:, [0, 2]] - c[[0, 2]], axis=1)
    if 1.25 < r.mean() < 1.45 and r.std() < 0.1:
        if near(c[0] - bx0, (3.5, 61.5)) and near(c[2] - bz0, (3.5, 52.5)):
            holes.append((c[0], c[2]))
assert len(holes) == 4

T = np.eye(4)
T[:3, :3] = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
T[:3, 3] = [0.0, H.PI_CTR_L, H.PI_BOARD_Z]
pi_h = pi.copy(); pi_h.apply_transform(T)
pi_bosses = np.array(H.PI_BOSSES)
model_holes = np.array([(T @ [mx, 0.7, mz, 1.0])[:2] for mx, mz in holes])
err = max(np.linalg.norm(model_holes - b, axis=1).min() for b in pi_bosses)
print(f"Pi hole-to-boss max error: {err:.3f} mm")
pb = pi_h.bounds
print(f"Pi: w[{pb[0][0]:.1f},{pb[1][0]:.1f}] l[{pb[0][1]:.1f},{pb[1][1]:.1f}]"
      f" z[{pb[0][2]:.1f},{pb[1][2]:.1f}] (chassis z top "
      f"{pb[1][2]-5.1:.1f}); shelf front edge l={H.PI_SHELF_FRONT}")

# ================================================================== Uno
uno = trimesh.load(HERE.parents[1] / "reference" / "arduino_uno.stl")
TU = np.eye(4)
TU[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
TU[:3, 3] = [0.0, H.UNO_BOARD_FRONT - 33.0, H.UNO_BOARD_Z]
uno_h = uno.copy(); uno_h.apply_transform(TU)

sec = uno.section(plane_origin=[0, 0.8, 0], plane_normal=[0, 1, 0])
uholes = []
for pts in sec.discrete:
    c = pts.mean(axis=0)
    r = np.linalg.norm(pts[:, [0, 2]] - c[[0, 2]], axis=1)
    if 1.3 < r.mean() < 1.9 and r.std() < 0.2:
        uholes.append((c[0], c[2]))
assert len(uholes) == 4
uno_bosses = np.array(H.UNO_BOSSES)
model_uholes = np.array([(TU @ [mx, 0.8, mz, 1.0])[:2] for mx, mz in uholes])
uerr = max(np.linalg.norm(model_uholes - b, axis=1).min() for b in uno_bosses)
print(f"Uno hole-to-boss max error: {uerr:.3f} mm")
ub = uno_h.bounds
print(f"Uno: w[{ub[0][0]:.1f},{ub[1][0]:.1f}] l[{ub[0][1]:.1f},{ub[1][1]:.1f}]"
      f" z[{ub[0][2]:.1f},{ub[1][2]:.1f}]; shelf spans l "
      f"{H.UNO_SHELF_REAR}..{H.UNO_SHELF_FRONT} (USB tip past front edge: "
      f"{ub[1][1] - H.UNO_SHELF_FRONT:.1f})")

# ---- standoff clearance: 30mm standoffs run chassis z 21.5..51.5 through
# the Uno's airspace; nut/stud hardware sits atop the pi_shelf plate
for label, mesh, zlo, zhi, pts, min_r in (
        ("Uno vs standoffs", uno_h.vertices, H.MID_RAIL_TOP, H.TOP_SHELF_Z,
         H.STANDOFF_HOLES, 4.0),
        ("Pi vs seat screws", pi_h.vertices, H.PI_PLATE_Z,
         H.PI_PLATE_Z + 20, H.PI_SEATS, 4.0)):
    v = mesh[(mesh[:, 2] > zlo) & (mesh[:, 2] < zhi)]
    dmin = min(np.linalg.norm(v[:, :2] - [hw, hl], axis=1).min()
               for hw, hl in pts) if len(v) else 99.0
    print(f"{label}: min distance {dmin:.2f} mm "
          f"[{'OK' if dmin > min_r else 'TOO CLOSE'}]")
    assert dmin > min_r

# battery bridge: stacked packs + wire tunnel
print(f"pi/arduino pack ({H.BATT2_W} x {H.BATT2_L} x {H.BATT2_H}) on the "
      f"deck bed {H.BATT_DECK_Z + H.PLATE_T - 5.1:.1f}.."
      f"{H.BATT_DECK_Z + H.PLATE_T + H.BATT2_H - 5.1:.1f} chassis; "
      f"motor pack ({H.BATT_W} x {H.BATT_L} x {H.BATT_H}) on top to "
      f"{H.BATT_STACK_TOP - 5.1:.1f}")
print(f"rails inner ±{H.BATT2_W/2 + 0.4:.1f}; towers inner face "
      f"±{H.BATT_SHELF_W/2 - H.TOWER_T:.1f}")
tunnel = H.BATT_DECK_Z - H.UNO_STACK_TOP
print(f"wire tunnel over the shield: {tunnel:.1f} mm (need {H.WIRE_CLEAR}); "
      f"bracket legs inner face ±{35.25 - H.LEG_T/2:.1f} vs stack ±~29.5")
assert tunnel >= H.WIRE_CLEAR - 0.01, "wire tunnel too low"
assert 35.25 - H.LEG_T / 2 > 30.0, "bracket legs pinch the shield zone"
assert H.BATT_SHELF_W / 2 - H.TOWER_T > H.BATT2_W / 2 + 0.3, \
    "towers pinch the wide pack"
assert H.PI_PLATE_Z - H.BATT_STACK_TOP >= 1.0, "packs pinched under pi_shelf"
assert H.BATT_SHELF_FRONT - H.BATT_SHELF_REAR >= H.BATT2_L + 2, "deck short"

# ---- the height chain that makes this all work
print("all checks passed")
