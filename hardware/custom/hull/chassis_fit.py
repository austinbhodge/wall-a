"""Render the v0.5 shelves + boards in the MR6 chassis assembly frame.

Hull-local -> chassis: x = w - 61, y = l + 57.5, z = z - 5.1.
"""
from pathlib import Path
import sys
import numpy as np
import trimesh

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import hull as H

MR6 = Path(r"C:\Users\austi\Documents\3dModels"
           r"\MR6 - Mini Prototyping Tank Robot - 2753227\files")
T_HULL = trimesh.transformations.translation_matrix([-61, 57.5, -5.1])

pieces = {}
for name in ("uno_shelf", "batt_deck", "pi_shelf"):
    m = trimesh.load(HERE / "stl" / f"{name}.stl")
    m.apply_transform(T_HULL)
    pieces[name] = m

# the bracket prints twice; mirror the second about the w axis
br = trimesh.load(HERE / "stl" / "batt_bracket.stl")
br2 = br.copy()
mirror = np.eye(4); mirror[0, 0] = -1
br2.apply_transform(mirror)
br2.invert()   # keep normals outward after mirroring
for b in (br, br2):
    b.apply_transform(T_HULL)
pieces["bracket_R"], pieces["bracket_L"] = br, br2

# battery proxy boxes: wide pi/arduino pack below, slim motor pack on top
bed = H.BATT_DECK_Z + H.PLATE_T
battery = trimesh.creation.box(extents=[H.BATT2_W, H.BATT2_L, H.BATT2_H])
battery.apply_translation([0, H.BATT_CTR_L, bed + H.BATT2_H / 2])
battery.apply_transform(T_HULL)
battery1 = trimesh.creation.box(extents=[H.BATT_W, H.BATT_L, H.BATT_H])
battery1.apply_translation([0, H.BATT_CTR_L,
                            bed + H.BATT2_H + H.BATT_H / 2])
battery1.apply_transform(T_HULL)

# stock 30mm standoff proxies
standoffs = []
for hw, hl in H.STANDOFF_HOLES:
    s = trimesh.creation.cylinder(radius=2.75, height=30.0, sections=24)
    s.apply_translation([hw, hl, H.MID_RAIL_TOP + H.PLATE_T + 15.0])
    s.apply_transform(T_HULL)
    standoffs.append(s)

chassis = {}
for n in ("LHS_Track_Frame_Mount", "RHS_Track_Frame_Mount",
          "Motor_Mount", "Back_Panel", "Bottom_Shelf"):
    try:
        chassis[n] = trimesh.load(MR6 / f"{n}.stl")
    except Exception:
        pass
chassis.pop("Bottom_Shelf", None)   # user runs without the stock shelves

REF = HERE.parents[1] / "reference"
pi = trimesh.load(REF / "raspberry_pi_5.stl")
TP = np.eye(4)
TP[:3, :3] = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])
TP[:3, 3] = [0, H.PI_CTR_L, H.PI_BOARD_Z]
pi.apply_transform(T_HULL @ TP)
uno = trimesh.load(REF / "arduino_uno.stl")
TU = np.eye(4)
TU[:3, :3] = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
TU[:3, 3] = [0, H.UNO_BOARD_FRONT - 33.0, H.UNO_BOARD_Z]
uno.apply_transform(T_HULL @ TU)

ub = pieces["uno_shelf"].bounds
print(f"uno_shelf spans x[{ub[0][0]:.1f},{ub[1][0]:.1f}] into the middle "
      f"rails; z {ub[0][2]:.1f}..{ub[1][2]:.1f}")
print(f"pi_shelf underside z {pieces['pi_shelf'].bounds[0][2]:.1f} "
      f"(stock standoff tops at 51.5)")
print(f"Uno stack top {H.UNO_STACK_TOP-5.1:.1f} | clearance "
      f"{H.TOP_SHELF_Z - H.UNO_STACK_TOP:.1f}")

def render(meshes_colors, path, elev, azim, title):
    fig = plt.figure(figsize=(9, 8))
    ax = fig.add_subplot(projection="3d")
    light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    for mesh, rgb in meshes_colors:
        tris = mesh.vertices[mesh.faces]
        shade = 0.35 + 0.65 * np.clip(mesh.face_normals @ light, 0, 1)
        colors = np.tile(np.array([*rgb, 1.0]), (len(shade), 1))
        colors[:, :3] *= shade[:, None]
        ax.add_collection3d(Poly3DCollection(tris, facecolors=colors,
                                             edgecolors="none"))
    lo = np.minimum.reduce([m.bounds[0] for m, _ in meshes_colors])
    hi = np.maximum.reduce([m.bounds[1] for m, _ in meshes_colors])
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r)
    ax.set_zlim(c[2]-r, c[2]+r)
    ax.view_init(elev=elev, azim=azim); ax.set_axis_off(); ax.set_title(title)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)

pink = (0.9, 0.45, 0.55)
scene = [(pieces["uno_shelf"], (0.88, 0.68, 0.28)),
         (pieces["batt_deck"], (0.8, 0.6, 0.22)),
         (pieces["bracket_R"], (0.75, 0.55, 0.2)),
         (pieces["bracket_L"], (0.75, 0.55, 0.2)),
         (pieces["pi_shelf"], (0.88, 0.68, 0.28)),
         (battery, (0.35, 0.35, 0.4)), (battery1, (0.45, 0.45, 0.5)),
         (pi, (0.2, 0.65, 0.35)), (uno, (0.3, 0.7, 0.75))] + \
        [(s, (0.7, 0.7, 0.72)) for s in standoffs] + \
        [(m, pink) for m in chassis.values()]
render(scene, HERE / "preview" / "chassis_fit_front.png", 18, -35,
       "shelves in MR6 chassis — front 3/4")
render(scene, HERE / "preview" / "chassis_fit_rear.png", 20, 140,
       "shelves in MR6 chassis — rear 3/4")
render(scene, HERE / "preview" / "chassis_fit_side.png", 2, 0,
       "shelves in MR6 chassis — side")
print("renders: preview/chassis_fit_{front,rear,side}.png")
