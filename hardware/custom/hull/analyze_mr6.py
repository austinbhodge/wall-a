"""Measure the MR6 chassis interface: shelf hole patterns and the slot/hole
geometry of the track frame mounts. Parts are in a shared assembly frame."""
from pathlib import Path
import numpy as np
import trimesh

BASE = Path(r"C:\Users\austi\Documents\3dModels"
            r"\MR6 - Mini Prototyping Tank Robot - 2753227\files")

def circles_in_slice(mesh, z, rmin=1.0, rmax=3.5):
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return []
    out = []
    for pts in sec.discrete:
        c = pts.mean(axis=0)
        r = np.linalg.norm(pts[:, :2] - c[:2], axis=1)
        if rmin < r.mean() < rmax and r.std() < 0.2:
            out.append((round(c[0], 2), round(c[1], 2), round(2 * r.mean(), 2)))
    return sorted(out)

for name in ("Bottom_Shelf", "Middle_Shelf", "Top_Shelf"):
    m = trimesh.load(BASE / f"{name}.stl")
    zmid = m.bounds[:, 2].mean()
    print(f"{name}: z[{m.bounds[0][2]:.1f},{m.bounds[1][2]:.1f}] "
          f"x[{m.bounds[0][0]:.1f},{m.bounds[1][0]:.1f}] "
          f"y[{m.bounds[0][1]:.1f},{m.bounds[1][1]:.1f}]")
    for h in circles_in_slice(m, zmid):
        print("   hole (x,y,d):", h)

# track frame mount: profile along z — where are the slots?
lhs = trimesh.load(BASE / "LHS_Track_Frame_Mount.stl")
print(f"\nLHS mount bounds:\n{np.round(lhs.bounds, 1)}")
print("inner-face x extents vs z (slot detection, slice every 1mm):")
for z in np.arange(-16.5, 45.5, 1.0):
    sec = lhs.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        continue
    pts = np.vstack(sec.discrete)
    print(f"  z={z:6.1f}: x[{pts[:,0].min():7.2f},{pts[:,0].max():7.2f}] "
          f"y[{pts[:,1].min():7.2f},{pts[:,1].max():7.2f}]")
