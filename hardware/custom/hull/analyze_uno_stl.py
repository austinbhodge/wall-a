"""One-off: measure the reference Arduino-UNO.stl — board outline, hole
positions, USB-B and barrel jack geometry — to calibrate hull.py."""
from pathlib import Path
import numpy as np
import trimesh

m = trimesh.load(Path(__file__).parents[2] / "reference" / "arduino_uno.stl")

# PCB: find its y-slab. Slice at several heights to find the board plane.
for y in (0.0, 0.4, 0.8, 1.2, 1.6, 2.0):
    sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        print(f"y={y}: none"); continue
    pts = np.vstack(sec.discrete)
    print(f"y={y}: {len(sec.discrete)} loops, "
          f"x[{pts[:,0].min():.2f},{pts[:,0].max():.2f}] "
          f"z[{pts[:,1] if False else pts[:,2].min():.2f},{pts[:,2].max():.2f}]")

y_pcb = 0.8
sec = m.section(plane_origin=[0, y_pcb, 0], plane_normal=[0, 1, 0])
loops = sec.discrete
outline = max(loops, key=lambda p: np.ptp(p[:, 0]) * np.ptp(p[:, 2]))
bx0, bx1 = outline[:, 0].min(), outline[:, 0].max()
bz0, bz1 = outline[:, 2].min(), outline[:, 2].max()
print(f"\nboard outline: x[{bx0:.2f},{bx1:.2f}] ({bx1-bx0:.2f})  "
      f"z[{bz0:.2f},{bz1:.2f}] ({bz1-bz0:.2f})")

print("circle-ish loops (candidate M3 holes, d 3-3.5):")
for pts in loops:
    c = pts.mean(axis=0)
    r = np.linalg.norm(pts[:, [0, 2]] - c[[0, 2]], axis=1)
    if 1.3 < r.mean() < 1.9 and r.std() < 0.2:
        print(f"  ({c[0]:7.2f}, {c[2]:7.2f}) d={2*r.mean():.2f} "
          f"from-edges x({c[0]-bx0:.2f}|{bx1-c[0]:.2f}) z({c[2]-bz0:.2f}|{bz1-c[2]:.2f})")

# stuff overhanging the board edges = USB-B / barrel jack
v = m.vertices
over = v[v[:, 2] > bz1 + 0.1]
if len(over):
    print(f"\n+z overhang: x[{over[:,0].min():.1f},{over[:,0].max():.1f}] "
          f"y[{over[:,1].min():.1f},{over[:,1].max():.1f}] "
          f"z to {over[:,2].max():.1f}")
over = v[v[:, 2] < bz0 - 0.1]
if len(over):
    print(f"-z overhang: x[{over[:,0].min():.1f},{over[:,0].max():.1f}] "
          f"y[{over[:,1].min():.1f},{over[:,1].max():.1f}] "
          f"z to {over[:,2].min():.1f}")

# tall components (connector heights above PCB top ~y 1.6)
print(f"max component height: y={v[:,1].max():.2f}")
