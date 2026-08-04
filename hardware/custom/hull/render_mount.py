"""Visualize the LHS track frame mount: inner-side 3D view + y-z section
profiles through the shelf-overlap band, to understand the slot levels."""
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).parent
MR6 = Path(r"C:\Users\austi\Documents\3dModels"
           r"\MR6 - Mini Prototyping Tank Robot - 2753227\files")
m = trimesh.load(MR6 / "LHS_Track_Frame_Mount.stl")

# ---- y-z section profiles at several x through the mount
fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
for ax, x0 in zip(axes, (-92.5, -94.5, -97.0)):
    sec = m.section(plane_origin=[x0, 0, 0], plane_normal=[1, 0, 0])
    if sec is None:
        ax.set_title(f"x={x0}: empty"); continue
    for loop in sec.discrete:
        ax.plot(loop[:, 1], loop[:, 2], "k-", lw=0.8)
    for z, c in ((-5.1, "tab:blue"), (-2.1, "tab:blue"),
                 (18.5, "tab:red"), (21.5, "tab:red")):
        ax.axhline(z, color=c, lw=0.6, ls="--")
    ax.set_title(f"section x={x0}")
    ax.set_xlabel("chassis y"); ax.set_aspect("equal")
axes[0].set_ylabel("chassis z")
fig.suptitle("LHS mount y-z profiles (blue dashes: bottom shelf, red: middle)")
fig.tight_layout()
fig.savefig(HERE / "preview" / "mount_sections.png", dpi=110)
plt.close(fig)

# ---- 3D view from the inner (+x) side
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(projection="3d")
light = np.array([0.5, -0.5, 0.7]); light /= np.linalg.norm(light)
tris = m.vertices[m.faces]
shade = 0.35 + 0.65 * np.clip(m.face_normals @ light, 0, 1)
colors = np.tile(np.array([0.9, 0.45, 0.55, 1.0]), (len(shade), 1))
colors[:, :3] *= shade[:, None]
ax.add_collection3d(Poly3DCollection(tris, facecolors=colors, edgecolors="none"))
lo, hi = m.bounds
c, r = (lo + hi) / 2, (hi - lo).max() / 2
ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r)
ax.set_zlim(c[2]-r, c[2]+r)
ax.view_init(elev=18, azim=25)
ax.set_axis_off(); ax.set_title("LHS mount from inner side")
fig.tight_layout()
fig.savefig(HERE / "preview" / "mount_inner.png", dpi=110)
print("saved preview/mount_sections.png, preview/mount_inner.png")
