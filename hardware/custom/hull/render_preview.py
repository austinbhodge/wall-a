"""Quick STL previews for eyeballing hull geometry. Not part of the model."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

HERE = Path(__file__).parent
STL = HERE / "stl"
OUT = HERE / "preview"
OUT.mkdir(exist_ok=True)

VIEWS = {  # name: (elev, azim)
    "front_top": (28, -55),
    "rear_bottom": (-25, 130),
    "interior_top": (75, -90),
}


def render(mesh, path, elev, azim, title):
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(projection="3d")
    tris = mesh.vertices[mesh.faces]
    normals = mesh.face_normals
    light = np.array([0.4, -0.6, 0.7])
    light = light / np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(normals @ light, 0, 1)
    colors = plt.cm.YlOrBr(0.35 * np.ones(len(shade)))
    colors[:, :3] *= shade[:, None]
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    pc = Poly3DCollection(tris, facecolors=colors, edgecolors="none")
    ax.add_collection3d(pc)
    lo, hi = mesh.bounds
    c = (lo + hi) / 2
    r = (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r)
    ax.set_ylim(c[1] - r, c[1] + r)
    ax.set_zlim(c[2] - r, c[2] + r)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


for name in ("hull_base", "pi_tray", "lid"):
    mesh = trimesh.load(STL / f"{name}.stl")
    for view, (elev, azim) in VIEWS.items():
        render(mesh, OUT / f"{name}_{view}.png", elev, azim, f"{name} — {view}")
    print(name, "bounds", np.round(mesh.bounds, 1).tolist())

print("previews in", OUT)
