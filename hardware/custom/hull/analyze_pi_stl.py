"""One-off: measure the reference RASPBERRY_PI_5_.stl — board outline,
mounting hole positions, and port overhangs — to calibrate hull.py."""
from pathlib import Path
import numpy as np
import trimesh

m = trimesh.load(Path(__file__).parents[2] / "reference" / "raspberry_pi_5.stl")

def loops_at(y):
    sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return None
    planar, _ = sec.to_2D()
    return planar.discrete  # list of (n,2) closed polylines in slice coords

for y in (0.2, 0.7, 1.0, 1.6, 5.0, 10.0, 15.0):
    loops = loops_at(y)
    if loops is None:
        print(f"y={y}: no section")
        continue
    allpts = np.vstack(loops)
    print(f"y={y}: {len(loops)} loops, slice bbox x[{allpts[:,0].min():.2f},"
          f"{allpts[:,0].max():.2f}] z[{allpts[:,1].min():.2f},{allpts[:,1].max():.2f}]")

print("\ncircle-ish loops at y=0.7 (candidate mount holes):")
for pts in loops_at(0.7):
    c = pts.mean(axis=0)
    r = np.linalg.norm(pts - c, axis=1)
    if 0.8 < r.mean() < 2.2 and r.std() < 0.15:
        print(f"  center ({c[0]:8.2f}, {c[1]:8.2f})  d={2*r.mean():.2f}")
