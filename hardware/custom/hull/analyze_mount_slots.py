"""Probe the LHS track frame mount around the two shelf slots using
point-membership tests: where is material along the slot band, which
direction is open for insertion, and where are the screw holes."""
from pathlib import Path
import numpy as np
import trimesh

MR6 = Path(r"C:\Users\austi\Documents\3dModels"
           r"\MR6 - Mini Prototyping Tank Robot - 2753227\files")
m = trimesh.load(MR6 / "LHS_Track_Frame_Mount.stl")
print("watertight:", m.is_watertight, " bodies:", m.body_count)

def runs(mask, ys):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = ys[i]
        if not v and start is not None:
            out.append((start, ys[i - 1])); start = None
    if start is not None:
        out.append((start, ys[-1]))
    return out

ys = np.arange(-17.0, 102.0, 0.5)
# slot band x: shelf overlaps mount x -98..-91; probe mid-band
for z, label in ((-3.5, "bottom slot level"), (20.0, "middle slot level"),
                 (-10.0, "below bottom slot"), (5.0, "between slots")):
    pts = np.column_stack([np.full_like(ys, -94.5), ys, np.full_like(ys, z)])
    inside = m.contains(pts)
    print(f"z={z:6.1f} ({label}): material y-runs:",
          [(round(a, 1), round(b, 1)) for a, b in runs(inside, ys)])

# vertical probes at the bottom-shelf screw positions: is there a hole
# (empty) through material above/below the slot?
for y in (25.5, 43.5, 61.5):
    zs = np.arange(-17.0, 20.0, 0.5)
    pts = np.column_stack([np.full_like(zs, -94.5), np.full_like(zs, y), zs])
    inside = m.contains(pts)
    print(f"screw line (x-94.5, y={y}): material z-runs:",
          [(round(a, 1), round(b, 1)) for a, b in runs(inside, zs)])

# how far down does the mount inner face go — pelvis must fit between
for z in (-3.5, -10.0, -16.0):
    xs = np.arange(-98.0, -85.0, 0.25)
    pts = np.column_stack([xs, np.full_like(xs, 75.0), np.full_like(xs, z)])
    inside = m.contains(pts)
    print(f"x-probe at y=75, z={z}: material x-runs:",
          [(round(a, 2), round(b, 2)) for a, b in runs(inside, xs)])
