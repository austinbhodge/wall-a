# Wall-A Simulation Harness

The digital twin: every physical object modeled as a solid, checked for
interference, clearance, keep-outs, and **staged driver access** before
anything gets printed.

## Run the simulation

```bash
python sim/simulate.py
```

- Builds all ~80 solids in the chassis frame: printed parts (exact STEP),
  MR6 chassis meshes, measured board envelopes, both measured battery
  packs, standoffs, every screw/nut/washer, wire-tunnel keep-out.
- Checks: exact OCCT pairwise interference · chassis-mesh proximity ·
  keep-out intrusion · per-fastener driver volumes staged by assembly
  order (25mm stubby = FAIL, 80mm straight = WARN).
- Output: `report.txt` (exit 1 on FAIL), `manifest.json` + `proxies/`.

Known accepted WARNs: the two front deck bolts want a stubby driver or
ball-end key for a perfectly straight approach.

## View the assembly (FreeCAD)

```bash
& "C:\Program Files\FreeCAD 1.1\bin\python.exe" sim/build_fcstd.py
```

Then open `sim/wall_a.FCStd` in FreeCAD — the whole robot, grouped
(Chassis / Printed / Electronics / Batteries / Fasteners / Keepouts) and
colored; the wire tunnel is the translucent red box.

## Drive FreeCAD from Claude (MCP)

One-time setup, already installed:
- pip package `freecad-mcp` (the MCP server, wired in `../../../.mcp.json`
  at the repo root — Claude Code picks it up automatically in this repo)
- the `FreeCADMCP` addon in `%APPDATA%\FreeCAD\Mod`

To use it: open FreeCAD → select the **MCP Addon** workbench →
**Start RPC Server** (localhost:9875) → start a Claude Code session in
this repo and approve the `freecad` MCP server. Claude can then create/
edit objects, run scripts, and screenshot the viewport live.

## What the sim caught on its first runs (why this exists)

- Pi mounting nuts protruding 1.1mm into the motor pack (fixed: flush
  underside hex pockets)
- deck-bolt heads and driver paths colliding with the bracket legs
  (fixed: bolt line moved inboard, flanges widened)
- foot-screw drivers blocked by the bracket web's top chord (fixed:
  full-height access windows)
- tower cross-nut corners clipping the wide battery lane (fixed: slots
  raised above the pack)
- independently confirmed the MR6 rail cage voids line up with the
  standoff nuts/studs
