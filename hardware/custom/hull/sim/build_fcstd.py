"""Build wall_a.FCStd — the full Wall-A assembly as a FreeCAD document.

Run under FreeCAD's interpreter (after sim/simulate.py has written
manifest.json + proxies/):

  & "C:\\Program Files\\FreeCAD 1.1\\bin\\freecadcmd.exe" sim/build_fcstd.py

Open the result in FreeCAD GUI to orbit/section the robot. Groups:
Chassis / Printed / Electronics / Batteries / Fasteners / Keepouts.
"""
import json
import os

import FreeCAD
import Mesh

HERE = os.path.dirname(os.path.abspath(__file__))
manifest = json.load(open(os.path.join(HERE, "manifest.json")))

doc = FreeCAD.newDocument("wall_a")
groups = {}

def group_for(cat):
    label = dict(printed="Printed", electronics="Electronics",
                 battery="Batteries", fastener="Fasteners",
                 keepout="Keepouts", chassis="Chassis").get(cat, "Other")
    if label not in groups:
        groups[label] = doc.addObject("App::DocumentObjectGroup", label)
    return groups[label]

def add_mesh(name, path, color, cat, transparency=0):
    m = Mesh.Mesh(path)
    obj = doc.addObject("Mesh::Feature", name)
    obj.Mesh = m
    obj.Label = name
    group_for(cat).addObject(obj)
    try:  # headless: ViewObject may be absent; harmless if so
        obj.ViewObject.ShapeColor = tuple(c / 255.0 for c in color)
        obj.ViewObject.Transparency = transparency
    except Exception:
        pass

for c in manifest["chassis"]:
    add_mesh(c["name"], c["path"], c["color"], "chassis")
for o in manifest["objects"]:
    add_mesh(o["name"], o["stl"], o["color"], o["cat"],
             o.get("transparency", 0))

doc.recompute()
out = os.path.join(HERE, "wall_a.FCStd")
doc.saveAs(out)
print("saved", out, "with", len(doc.Objects), "objects")
