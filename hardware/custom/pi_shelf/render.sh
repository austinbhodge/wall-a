#!/usr/bin/env bash
# Regenerate the Pi shelf STLs and the preview images in this directory.
# Requires OpenSCAD. Image rendering needs a display; on a headless box the
# script falls back to xvfb-run if it is installed.
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p stl img

SCAD=${OPENSCAD:-openscad}
if [ -z "${DISPLAY:-}" ] && command -v xvfb-run >/dev/null; then
    GUI="xvfb-run -a $SCAD"
else
    GUI="$SCAD"
fi

for part in base yoke plate; do
    echo "==> stl/$part.stl"
    "$SCAD" --export-format=binstl -D "part=\"$part\"" -o "stl/$part.stl" pi_shelf.scad
done

echo "==> img/assembly.png"
$GUI -D 'part="assembly"' --imgsize=1500,1050 \
     --camera=0,0,15,62,0,32,320 --colorscheme=Tomorrow \
     -o img/assembly.png pi_shelf.scad

echo "==> img/plate.png"
$GUI -D 'part="plate"' --imgsize=1400,1000 \
     --camera=0,25,10,58,0,25,330 --colorscheme=Tomorrow \
     -o img/plate.png pi_shelf.scad

echo "done"
