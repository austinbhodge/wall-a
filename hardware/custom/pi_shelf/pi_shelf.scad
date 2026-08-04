// ============================================================================
//  Wall-A — Raspberry Pi 5 clamp-on shelf
// ----------------------------------------------------------------------------
//  The Pi 5 now lives inside a closed case, so its four M2.5 board holes are
//  no longer reachable.  This shelf therefore grips the *case* instead of the
//  board: the case drops into a shallow tray and a removable yoke clamps down
//  across its top.  Nothing screws into the Pi, and the Pi comes out in about
//  ten seconds without unbolting the shelf from the chassis.
//
//  Capture directions:
//      +X  rear wall
//      -X  the two front towers
//      +/-Y  side curbs (deliberately low — both long faces of a Pi 5 carry
//            ports, so nothing may rise in front of them)
//      +Z  the yoke
//
//  Assembly:
//      1. Bolt the base to the chassis deck through the four slotted ears.
//      2. Drop the cased Pi into the tray, ports facing out over the low curbs.
//      3. Slide the yoke's rear tongue into the slot in the rear wall.
//      4. Swing the yoke down; its legs straddle the outside of the front
//         towers.  Drop an M3 nut into each tower's sliding nut channel.
//      5. Run an M3x10 through each leg and tighten.  The nut slides in its
//         channel, so the yoke clamps anywhere within +/- adjust/2 of the
//         nominal case height — one print covers a 6mm band of case heights.
//
//  Everything prints without support in the orientations produced by
//  part = "plate".
//
//  Rendering:
//      openscad -D 'part="base"'  -o base.stl  pi_shelf.scad
//      openscad -D 'part="yoke"'  -o yoke.stl  pi_shelf.scad
//      openscad -D 'part="plate"' -o plate.3mf pi_shelf.scad
//      openscad -D 'part="assembly"' ...        (preview only, not printable)
// ============================================================================

part = "assembly";  // "base" | "yoke" | "plate" | "assembly"

// ---------------------------------------------------------------------------
// [Case]  MEASURE YOUR OWN CASE AND EDIT THESE THREE NUMBERS FIRST.
// Take the measurement over the widest point, including lid overhang, rubber
// feet and any heatsink fins.  Defaults are a generic slim Pi 5 ABS case.
// ---------------------------------------------------------------------------
case_l = 96;    // X — long axis (the two port faces run along this)
case_w = 68;    // Y — short axis
case_h = 30;    // Z — total height, feet to lid
fit    = 0.6;   // clearance per side; raise to 0.8 for a looser drop-in

// ---------------------------------------------------------------------------
// [Shelf]
// ---------------------------------------------------------------------------
wall      = 3;    // curb / side wall thickness
floor_t   = 3;    // tray floor thickness
curb_h    = 4;    // side curb height — MUST stay below the case's port cutouts
rear_t    = 4;    // rear wall thickness at the top
rear_t0   = 9;    // rear wall thickness at the floor (it tapers — the taper is
                  // the wall's bracing, and unlike a gusset it stays inside
                  // the tray footprint and needs no support to print)
tower_t   = 5;    // front tower thickness (X)
tower_w   = 15;   // front tower width (Y)
adjust    = 6;    // vertical clamp travel (total, mm)
plate_r   = 3;    // outer corner radius

// ---------------------------------------------------------------------------
// [Yoke]
// ---------------------------------------------------------------------------
yoke_t    = 5;    // frame thickness
rail_w    = 10;   // frame rail width
leg_t     = 4;    // clamp leg thickness (X)
leg_gap   = 0.4;  // sliding clearance between leg and tower
hole_dz   = 13;   // screw axis, below the yoke underside. Deep enough that the
                  // whole nut channel fits under a tower that is itself short
                  // enough to stay out of the yoke's way — see the asserts.
tongue_w  = 44;   // rear tongue width
pad_d     = 0.8;  // recess under the rails for foam/silicone grip tape (0 = off)

// ---------------------------------------------------------------------------
// [Chassis mounting]
// The Thingiverse deck's hole pattern is not published, so every mounting hole
// is a slot: two ears slide along X, two along Y.  Between them they swallow
// roughly a 10mm error in either axis.  Use M3 with washers.
// ---------------------------------------------------------------------------
ear_len    = 12;  // how far the ears stick out past the tray
ear_w      = 18;  // ear width
slot_travel = 9;  // slot length beyond the hole diameter

// ---------------------------------------------------------------------------
// [Hardware]
// ---------------------------------------------------------------------------
m3_clear  = 3.4;  // M3 clearance hole
m3_head   = 6.4;  // M3 socket head / washer seat
m3_nut_af = 6.2;  // M3 nut across flats (+ fit)
m3_nut_t  = 2.8;  // M3 nut thickness (+ fit)

// ---------------------------------------------------------------------------
// [Vents]
// ---------------------------------------------------------------------------
vent_w    = 8;    // vent slot width
vent_n    = 6;    // number of vent slots
vent_gap  = 6;    // gap between vent slots

$fn = $preview ? 32 : 72;
eps = 0.01;

// ============================================================================
//  Derived geometry
// ============================================================================
cav_l = case_l + 2 * fit;               // cavity, X
cav_w = case_w + 2 * fit;               // cavity, Y
cav_h = case_h + fit;                   // top of case above the tray floor

x_case_front = -cav_l / 2;              // -X cavity face
x_case_rear  =  cav_l / 2;              // +X cavity face

x_tower_out  = x_case_front - tower_t;  // outer face of the front towers
x_leg_out    = x_tower_out - leg_gap - leg_t;   // outer face of the yoke legs
x_rear_out   = x_case_rear + rear_t;    // outer face of the rear wall, at the top
x_rear_base  = x_case_rear + rear_t0;   // ... and at the floor
x_plate_rear = x_rear_base;             // the plate has to carry the taper

y_out        = cav_w / 2 + wall;        // outer face of the side curbs

// Yoke frame extents, shared by the frame and the pads cut into it.
x_yoke_rear  = x_case_rear + 1;         // where the frame stops and the tongue starts
x_open_front = x_leg_out + leg_t + rail_w;   // inner edge of the front cross member
x_open_rear  = x_yoke_rear - rail_w;         // inner edge of the rear cross member

// Tower / leg centres sit hard in the front corners, clear of the USB and
// Ethernet clusters that occupy the middle of both long faces.
ty = y_out - tower_w / 2;

// Screw axis and its travel, in base coordinates.
z_screw   = cav_h - hole_dz;
z_slot_lo = z_screw - adjust / 2;
z_slot_hi = z_screw + adjust / 2;

// The towers have to duck under the yoke's *lowest* position, not just its
// nominal one — otherwise the frame lands on the towers and the case is never
// actually gripped when it measures shorter than case_h.
tower_h = cav_h - adjust / 2 - 1;
// Rear slot spans the yoke thickness plus the full clamp travel.
z_tongue_lo = cav_h - adjust / 2;
z_tongue_hi = cav_h + yoke_t + adjust / 2;
rear_h  = z_tongue_hi + 3;

// ---------------------------------------------------------------------------
//  Sanity checks — these are the invariants that make the clamp work.  Edit the
//  case dimensions freely; if a change breaks one of these, OpenSCAD says so
//  instead of quietly producing a part that cannot grip anything.
// ---------------------------------------------------------------------------
assert(curb_h < case_h - 6,
       "curb_h is too tall — it must stay below the case's port cutouts");
assert(tower_h >= z_slot_hi + m3_nut_af / 2 + 2,
       "towers too short to carry the nut channel: reduce adjust or raise hole_dz");
assert(z_slot_lo - m3_nut_af / 2 > 0,
       "nut channel runs into the tray floor: reduce hole_dz or adjust");
assert(cav_h - tower_h > adjust / 2,
       "the yoke would bottom out on the towers before it clamps the case");
assert(cav_h - hole_dz - 6 > curb_h,
       "the yoke legs would foul the tray: reduce hole_dz");
assert(tongue_w < cav_w - 2 * rail_w,
       "rear tongue is wider than the frame that carries it");

// ============================================================================
//  Helpers
// ============================================================================
module rrect2d(x0, x1, y0, y1, r) {
    hull() {
        translate([x0 + r, y0 + r]) circle(r = r);
        translate([x1 - r, y0 + r]) circle(r = r);
        translate([x0 + r, y1 - r]) circle(r = r);
        translate([x1 - r, y1 - r]) circle(r = r);
    }
}

module box(x0, x1, y0, y1, z0, z1) {
    translate([x0, y0, z0]) cube([x1 - x0, y1 - y0, z1 - z0]);
}

// A slot: two circles hulled, extruded along the axis given by rot.
module slot2d(d, travel) {
    hull() {
        translate([-travel / 2, 0]) circle(d = d);
        translate([ travel / 2, 0]) circle(d = d);
    }
}

// ============================================================================
//  Part A — tray / base
// ============================================================================
module base() {
    difference() {
        union() {
            floor_plate();
            side_curbs();
            rear_wall();
            front_towers();
        }
        vents();
        cable_tie_slots();
        ear_slots();
        tower_screw_slots();
        tower_nut_channels();
        rear_tongue_slot();
    }
}

module floor_plate() {
    linear_extrude(floor_t)
        union() {
            rrect2d(x_tower_out, x_plate_rear, -y_out, y_out, plate_r);
            ears2d();
        }
}

// Four mounting ears. Fronts slot along X, rears slot along Y, so the pair
// together will land on almost any rectangular hole pattern on the deck.
module ears2d() {
    for (sy = [-1, 1])
        for (sx = [-1, 1])
            translate([sx * (cav_l / 2 - ear_w / 2), sy * (y_out + ear_len / 2 - eps)])
                square([ear_w, ear_len + 2 * eps], center = true);
}

module ear_slots() {
    for (sy = [-1, 1])
        for (sx = [-1, 1])
            translate([sx * (cav_l / 2 - ear_w / 2),
                       sy * (y_out + ear_len / 2),
                       -eps])
                linear_extrude(floor_t + 2 * eps)
                    rotate(sx < 0 ? 0 : 90)      // front ears along X, rear along Y
                        slot2d(m3_clear, slot_travel);
}

module side_curbs() {
    for (sy = [-1, 1])
        box(x_tower_out, x_case_rear,
            sy > 0 ? cav_w / 2 : -y_out,
            sy > 0 ? y_out : -cav_w / 2,
            0, curb_h);
}

// Tapered so it braces itself: 9mm of foot at the floor, 4mm at the lip. The
// tongue slot puts a bending load here every time the clamp is tightened.
module rear_wall() {
    translate([0, y_out, 0])
        rotate([90, 0, 0])
            linear_extrude(2 * y_out)
                polygon([[x_case_rear, 0],
                         [x_rear_base, 0],
                         [x_rear_out,  rear_h],
                         [x_case_rear, rear_h]]);
}

module front_towers() {
    for (sy = [-1, 1])
        box(x_tower_out, x_case_front,
            sy * ty - tower_w / 2, sy * ty + tower_w / 2,
            0, tower_h);
}

// Vertical slot through each tower — this is what gives the clamp its travel.
module tower_screw_slots() {
    for (sy = [-1, 1])
        translate([x_tower_out - eps, sy * ty, z_screw])
            rotate([0, 90, 0])
                rotate(90)
                    linear_extrude(tower_t + 2 * eps)
                        slot2d(m3_clear, adjust);
}

// Sliding nut channel, recessed flush into the cavity-facing side of each
// tower so the nut cannot foul the case and cannot spin while you tighten.
module tower_nut_channels() {
    for (sy = [-1, 1])
        translate([x_case_front - m3_nut_t, sy * ty - m3_nut_af / 2, z_slot_lo - m3_nut_af / 2])
            cube([m3_nut_t + eps, m3_nut_af, adjust + m3_nut_af]);
}

module rear_tongue_slot() {
    box(x_case_rear - eps, x_rear_base + eps,
        -(tongue_w / 2 + 0.4), tongue_w / 2 + 0.4,
        z_tongue_lo, z_tongue_hi);
}

// Floor vents — airflow under the case, and a big weight saving.
module vents() {
    pitch = vent_w + vent_gap;
    span  = cav_w - 24;
    for (i = [0 : vent_n - 1])
        translate([(i - (vent_n - 1) / 2) * pitch, 0, -eps])
            linear_extrude(floor_t + 2 * eps)
                rotate(90)
                    slot2d(vent_w, span - vent_w);
}

// Strain relief for the USB-C lead and the CSI ribbon.
module cable_tie_slots() {
    for (sy = [-1, 1])
        for (sx = [-1, 1])
            translate([sx * (cav_l / 2 - 22), sy * (cav_w / 2 - 5), -eps])
                linear_extrude(floor_t + 2 * eps)
                    rotate(90)
                        slot2d(3, 6);
}

// ============================================================================
//  Part B — clamp yoke
//  Modelled in place: underside at z = cav_h, legs hanging down.  "plate"
//  flips it so the underside prints on the bed and the legs point up.
// ============================================================================
module yoke() {
    difference() {
        union() {
            translate([0, 0, cav_h]) linear_extrude(yoke_t) yoke2d();
            yoke_legs();
        }
        yoke_leg_holes();
        grip_pads();
    }
}

module yoke2d() {
    x_tip = x_rear_base - 0.5;     // tongue tip, just shy of breaking through
    difference() {
        union() {
            // front cross member — full width, carries both legs
            rrect2d(x_leg_out, x_open_front, -y_out, y_out, 2);
            // side rails + rear cross member
            rrect2d(x_leg_out + rail_w, x_yoke_rear, -cav_w / 2, cav_w / 2, 2);
            // rear tongue
            translate([x_yoke_rear - eps, -tongue_w / 2])
                square([x_tip - x_yoke_rear + eps, tongue_w]);
        }
        // open centre: top access, airflow, and a clear path for the CSI ribbon
        rrect2d(x_open_front, x_open_rear,
                -(cav_w / 2 - rail_w), cav_w / 2 - rail_w, 4);
    }
}

module yoke_legs() {
    for (sy = [-1, 1])
        box(x_leg_out, x_leg_out + leg_t,
            sy * ty - tower_w / 2, sy * ty + tower_w / 2,
            cav_h - (hole_dz + 6), cav_h);
}

module yoke_leg_holes() {
    for (sy = [-1, 1])
        translate([x_leg_out - eps, sy * ty, cav_h - hole_dz])
            rotate([0, 90, 0])
                cylinder(d = m3_clear, h = leg_t + 2 * eps);
}

// Shallow recesses so a strip of foam or silicone tape sits flush and the
// clamp grips an aluminium case without marking it.
module grip_pads() {
    if (pad_d > 0)
        for (sy = [-1, 1])
            translate([(x_open_front + x_open_rear) / 2,
                       sy * (cav_w / 2 - rail_w / 2),
                       cav_h - eps])
                linear_extrude(pad_d + eps)
                    square([x_open_rear - x_open_front - 4, rail_w - 3], center = true);
}

// ============================================================================
//  Preview aids
// ============================================================================
module mock_case() {
    color("#202020", 0.55)
        translate([0, 0, 0])
            linear_extrude(case_h)
                rrect2d(-case_l / 2, case_l / 2, -case_w / 2, case_w / 2, 4);
}

module assembly() {
    base();
    color("#e03020") yoke();
    mock_case();
}

// ============================================================================
//  Output selection
// ============================================================================
if (part == "base")
    base();
else if (part == "yoke")
    // printed underside-down: legs and tongue end up pointing straight up
    translate([0, 0, cav_h + yoke_t]) rotate([180, 0, 0]) yoke();
else if (part == "plate") {
    // Both parts, print-side down.  Needs a bed of ~185mm in Y — that is more
    // than the A1 Mini has, so on that printer run base.stl and yoke.stl as
    // two jobs instead.
    plate_gap = 6;
    base();
    translate([0, y_out + ear_len + plate_gap + y_out, cav_h + yoke_t])
        rotate([180, 0, 0]) yoke();
} else
    assembly();
