"""Generate the wall-mounted modular chess board described in readme.md.

The model is intentionally built with Part primitives so that it runs in
FreeCADCmd as well as in the graphical FreeCAD application.  All dimensions
are millimetres.
"""

import json
import math
import os

import FreeCAD as App
import Part


ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
EXPORT_DIR = os.path.join(ROOT, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)


# Design parameters from the brief.
CELL_W = 28.0
CELL_H = 56.0                         # clear playing height above each platform
MODULE_COLS = 4
MODULE_ROWS = 2
BACK_THICKNESS = 14.0
SHELF_DEPTH = 20.0                    # platform projection; magnet sits at its midpoint
SHELF_THICKNESS = 5.0                 # platform band below each clear cell
SHELF_CHAMFER = 1.5                   # chamfer on the two exposed long front edges
ROW_PITCH = CELL_H + SHELF_THICKNESS  # shelf band sits below the 56 mm cell
MODULE_W = CELL_W * MODULE_COLS       # 112 mm
MODULE_H = ROW_PITCH * MODULE_ROWS    # 122 mm
BOARD_COLS = 2
BOARD_ROWS = 4
BOARD_W = MODULE_W * BOARD_COLS       # 224 mm
BOARD_H = MODULE_H * BOARD_ROWS       # 488 mm
WHITE_THICKNESS = 3.2
CELL_FACE_W = CELL_W                                  # 28 mm; no perimeter wall
CELL_FACE_H = CELL_H                                  # 56 mm clear cell above shelf
MAGNET_DIAMETER = 4.0
MAGNET_DEPTH = 4.0
MAGNET_RADIUS = MAGNET_DIAMETER / 2.0
MAGNET_Z = BACK_THICKNESS + SHELF_DEPTH / 2.0
POSITION_POST_DIAMETER = 3.0
POSITION_POST_RADIUS = POSITION_POST_DIAMETER / 2.0
POSITION_POST_HEIGHT = 2.4
POSITION_POST_CLEARANCE = 0.25
POSITION_POST_OFFSET = 4.0
BUTTERFLY_SPAN = 40.0
BUTTERFLY_HALF_WIDTH = 10.0
BUTTERFLY_NECK_HALF_WIDTH = 4.0
BUTTERFLY_THICKNESS = 4.8          # fits the existing 5.1 mm-deep rear pockets
BUTTERFLY_POCKET_DEPTH = 5.0
BUTTERFLY_CLEARANCE = 0.35
FACE_WALL_THICKNESS = 0.0
LAST_MOVE_MARKER_WIDTH = 24.0
LAST_MOVE_MARKER_HEIGHT = 14.0
LAST_MOVE_MARKER_THICKNESS = 3.0
LAST_MOVE_MARKER_HOOK_DEPTH = 9.5
LAST_MOVE_CLIP_WIDTH = 6.0
LAST_MOVE_CLIP_GAP = 5.4
LAST_MOVE_TEXT_DEPTH = 0.7
LAST_MOVE_MARKER_X = CELL_W - LAST_MOVE_MARKER_WIDTH / 2.0
LAST_MOVE_MARKER_Y = -5.0
LAST_MOVE_MARKER_Z = 28.0
INTERNAL_JOINS = (BOARD_COLS - 1) * BOARD_ROWS + BOARD_COLS * (BOARD_ROWS - 1)
STORAGE_CLIPS = 2
TOTAL_BUTTERFLY_CLIPS = INTERNAL_JOINS + STORAGE_CLIPS
STORAGE_BOX_W = 168.0
STORAGE_BOX_H = 76.0
STORAGE_BOX_D = 68.0
STORAGE_BOX_WALL = 4.0
STORAGE_BOX_BACK = 8.0
STORAGE_BOX_FLOOR = 5.0
STORAGE_FRONT_HEIGHT = 56.0
STORAGE_CORNER_RADIUS = 12.0
STORAGE_BOX_X = (BOARD_W - STORAGE_BOX_W) / 2.0
STORAGE_BOX_Y = -STORAGE_BOX_H


def v(x, y, z):
    return App.Vector(float(x), float(y), float(z))


def box(dx, dy, dz, x=0, y=0, z=0):
    return Part.makeBox(float(dx), float(dy), float(dz), v(x, y, z))


def cylinder(radius, height, x, y, z, direction=(0, 0, 1)):
    return Part.makeCylinder(float(radius), float(height), v(x, y, z), v(*direction))


def make_shelf(x, y, z):
    """Make a full-width shelf with chamfers on its two exposed long edges."""
    c = SHELF_CHAMFER
    points = [
        v(x, y, z),
        v(x, y + SHELF_THICKNESS, z),
        v(x, y + SHELF_THICKNESS, z + SHELF_DEPTH - c),
        v(x, y + SHELF_THICKNESS - c, z + SHELF_DEPTH),
        v(x, y + c, z + SHELF_DEPTH),
        v(x, y, z + SHELF_DEPTH - c),
        v(x, y, z),
    ]
    return Part.Face(Part.makePolygon(points)).extrude(v(MODULE_W, 0, 0))


def butterfly_outline(span=BUTTERFLY_SPAN, half_width=BUTTERFLY_HALF_WIDTH, neck_half_width=BUTTERFLY_NECK_HALF_WIDTH):
    """Return a closed bow-tie outline centered at the origin."""
    h = float(span) / 2.0
    points = [
        (-h, -half_width),
        (-h * 0.42, -half_width),
        (0.0, -neck_half_width),
        (h * 0.42, -half_width),
        (h, -half_width),
        (h, half_width),
        (h * 0.42, half_width),
        (0.0, neck_half_width),
        (-h * 0.42, half_width),
        (-h, half_width),
    ]
    vectors = [v(x, y, 0) for x, y in points]
    vectors.append(v(points[0][0], points[0][1], 0))
    return Part.Face(Part.makePolygon(vectors))


def butterfly_prism(span=BUTTERFLY_SPAN, half_width=BUTTERFLY_HALF_WIDTH, neck_half_width=BUTTERFLY_NECK_HALF_WIDTH, thickness=BUTTERFLY_THICKNESS):
    return butterfly_outline(span, half_width, neck_half_width).extrude(v(0, 0, thickness))


def place_xy(shape, x, y, angle=0.0, z=0.0):
    result = shape.copy()
    result.rotate(v(0, 0, 0), v(0, 0, 1), float(angle))
    result.translate(v(x, y, z))
    return result


def make_black_module():
    """Make one complete black 4 x 2 module.

    Dark squares are integral with the back. Each rank has one continuous
    shelf, with one blind magnet pocket at every cell center.
    """
    body = box(MODULE_W, MODULE_H, BACK_THICKNESS)

    # White cells are full-cell openings in the black face. There is no narrow
    # perimeter wall or divider around them; the remaining 10.8 mm back plate
    # supports each white tile from below.
    for row in range(MODULE_ROWS):
        for col in range(MODULE_COLS):
            if (row + col) % 2 != 1:
                continue
            opening = box(
                CELL_W,
                CELL_H,
                WHITE_THICKNESS + 0.1,
                col * CELL_W,
                row * ROW_PITCH + SHELF_THICKNESS,
                BACK_THICKNESS - WHITE_THICKNESS,
            )
            body = body.cut(opening)

            # Four robust locating posts sit inside the opening. Matching
            # blind holes are cut into the underside of each white tile.
            post_xy = (
                (col * CELL_W + POSITION_POST_OFFSET, row * ROW_PITCH + SHELF_THICKNESS + POSITION_POST_OFFSET),
                (col * CELL_W + CELL_W - POSITION_POST_OFFSET, row * ROW_PITCH + SHELF_THICKNESS + POSITION_POST_OFFSET),
                (col * CELL_W + POSITION_POST_OFFSET, row * ROW_PITCH + ROW_PITCH - POSITION_POST_OFFSET),
                (col * CELL_W + CELL_W - POSITION_POST_OFFSET, row * ROW_PITCH + ROW_PITCH - POSITION_POST_OFFSET),
            )
            for px, py in post_xy:
                body = body.fuse(cylinder(
                    POSITION_POST_RADIUS,
                    POSITION_POST_HEIGHT,
                    px,
                    py,
                    BACK_THICKNESS - WHITE_THICKNESS,
                ))

    # The full-width shelf spans all four cells without cuts at color changes.
    # Its 5 mm thickness leaves a 1 mm floor below each 4 mm magnet pocket.
    for row in range(MODULE_ROWS):
        shelf = make_shelf(0, row * ROW_PITCH, BACK_THICKNESS)
        for col in range(MODULE_COLS):
            hole = cylinder(
                MAGNET_RADIUS,
                MAGNET_DEPTH,
                col * CELL_W + CELL_W / 2.0,
                row * ROW_PITCH + SHELF_THICKNESS,
                MAGNET_Z,
                direction=(0, -1, 0),
            )
            shelf = shelf.cut(hole)
        body = body.fuse(shelf)

    # Butterfly connector pockets are open on the rear face.  All four edges
    # use the same module drawing; unused outer-edge pockets are hidden when
    # the board is mounted against the wall.
    pocket_shape = butterfly_outline(
        BUTTERFLY_SPAN + BUTTERFLY_CLEARANCE,
        BUTTERFLY_HALF_WIDTH + BUTTERFLY_CLEARANCE,
        BUTTERFLY_NECK_HALF_WIDTH + BUTTERFLY_CLEARANCE,
    ).extrude(v(0, 0, BUTTERFLY_POCKET_DEPTH + 0.2))
    for x, y, angle in (
        (0.0, MODULE_H / 2.0, 0.0),
        (MODULE_W, MODULE_H / 2.0, 0.0),
        (MODULE_W / 2.0, 0.0, 90.0),
        (MODULE_W / 2.0, MODULE_H, 90.0),
    ):
        body = body.cut(place_xy(pocket_shape, x, y, angle, -0.1))

    # A rear keyhole has a wide head channel behind a narrow shank slot.
    # Both stay inside the back plate, leaving the chess face uninterrupted.
    for cx in (16.0, MODULE_W - 16.0):
        y = MODULE_H - 10.0
        entry = cylinder(4.0, 4.2, cx, y, -0.1)
        shank = box(4.2, 8.0, 2.1, cx - 2.1, y, -0.1)
        head_channel = box(8.0, 8.0, 2.1, cx - 4.0, y, 2.0)
        body = body.cut(entry.fuse(shank).fuse(head_channel))

    return body.removeSplitter()


def make_white_tile():
    """Make a full-cell white tile with four underside locating holes."""
    tile = box(CELL_FACE_W, CELL_FACE_H, WHITE_THICKNESS)
    hole_depth = POSITION_POST_HEIGHT + POSITION_POST_CLEARANCE
    for px, py in (
        (POSITION_POST_OFFSET, POSITION_POST_OFFSET),
        (CELL_FACE_W - POSITION_POST_OFFSET, POSITION_POST_OFFSET),
        (POSITION_POST_OFFSET, CELL_FACE_H - POSITION_POST_OFFSET),
        (CELL_FACE_W - POSITION_POST_OFFSET, CELL_FACE_H - POSITION_POST_OFFSET),
    ):
        tile = tile.cut(cylinder(
            POSITION_POST_RADIUS + POSITION_POST_CLEARANCE,
            hole_depth,
            px,
            py,
            -0.1,
        ))
    return tile.removeSplitter()


def make_butterfly_clip():
    """Make the separate black connector used between neighboring modules."""
    return butterfly_prism()


def rounded_plate(width, height, thickness, radius, z=0):
    plate = box(width, height, thickness, z=z)
    vertical = [e for e in plate.Edges if abs(e.BoundBox.ZLength - thickness) < 1e-6]
    return plate.makeFillet(radius, vertical)


def marker_lettering():
    """Return actual font solids used to engrave two readable lines."""
    font = os.environ.get("CHESS_FONT", "C:/Windows/Fonts/arialbd.ttf")
    letters = []
    for word, baseline in (("LAST", 8.0), ("MOVE", 2.0)):
        faces = [Part.makeFace(wires, "Part::FaceMakerBullseye")
                 for wires in Part.makeWireString(word, font, 4.0, 0.15) if wires]
        line = Part.makeCompound(faces)
        line.scale(3.7 / line.BoundBox.YLength)
        bb = line.BoundBox
        line.translate(v((LAST_MOVE_MARKER_WIDTH - bb.XLength) / 2 - bb.XMin,
                         baseline - bb.YMin, LAST_MOVE_MARKER_HOOK_DEPTH - LAST_MOVE_TEXT_DEPTH))
        letters.extend(f.extrude(v(0, 0, LAST_MOVE_TEXT_DEPTH + 0.1)) for f in line.Faces)
    return Part.makeCompound(letters)


def make_last_move_marker():
    """Rounded white badge with engraved text and a rear C-shaped slide clip.

    Only the 6 mm-wide jaws enter the gap between pieces. The wider badge
    sits 0.5 mm in front of the shelf/piece envelope. Both jaws clear the
    5 mm shelf by 0.2 mm, and the open back permits insertion from the front.
    """
    plate = rounded_plate(24, 14, 3, 3, z=6.5)
    front_edges = [e for e in plate.Edges if abs(e.BoundBox.ZMin - 9.5) < 1e-6]
    plate = plate.makeChamfer(0.5, front_edges)
    lower = box(LAST_MOVE_CLIP_WIDTH, 2.4, 7.0, 9, 2.4, 0)
    upper = box(LAST_MOVE_CLIP_WIDTH, 2.4, 7.0, 9, 10.2, 0)
    # Lead-ins at the open ends prevent a sharp edge catching the shelf.
    for name, jaw in (("lower", lower), ("upper", upper)):
        edges = [e for e in jaw.Edges if e.BoundBox.ZMax < 1e-6 and e.BoundBox.XLength > 5.9]
        jaw = jaw.makeChamfer(0.5, edges)
        if name == "lower":
            lower = jaw
        else:
            upper = jaw
    return plate.fuse(lower).fuse(upper).cut(marker_lettering()).removeSplitter()


def storage_footprint(width, depth, radius, x=0, z=0, y=0):
    """XZ face with straight rear edge and two generous front corner arcs."""
    r = radius
    q = r / math.sqrt(2)
    p = lambda a, b: v(x + a, y, z + b)
    edges = [Part.makeLine(p(0, 0), p(width, 0)),
             Part.makeLine(p(width, 0), p(width, depth-r)),
             Part.Arc(p(width, depth-r), p(width-r+q, depth-r+q), p(width-r, depth)).toShape(),
             Part.makeLine(p(width-r, depth), p(r, depth)),
             Part.Arc(p(r, depth), p(r-q, depth-r+q), p(0, depth-r)).toShape(),
             Part.makeLine(p(0, depth-r), p(0, 0))]
    return Part.Face(Part.Wire(edges))


def make_storage_box():
    """Open-top bin with a continuous front, rounded corners and hidden mounts."""
    outer = storage_footprint(STORAGE_BOX_W, STORAGE_BOX_D, STORAGE_CORNER_RADIUS).extrude(v(0, STORAGE_FRONT_HEIGHT, 0))
    bottom_edges = [e for e in outer.Edges if abs(e.BoundBox.YMax) < 1e-6]
    outer = outer.makeChamfer(1.5, bottom_edges)
    rear = box(STORAGE_BOX_W, STORAGE_BOX_H, STORAGE_BOX_BACK)
    outer = outer.fuse(rear)
    cavity = storage_footprint(
        STORAGE_BOX_W - 2 * STORAGE_BOX_WALL,
        STORAGE_BOX_D - STORAGE_BOX_BACK - STORAGE_BOX_WALL,
        STORAGE_CORNER_RADIUS - STORAGE_BOX_WALL,
        x=STORAGE_BOX_WALL, z=STORAGE_BOX_BACK, y=STORAGE_BOX_FLOOR,
    ).extrude(v(0, STORAGE_BOX_H, 0))
    tray = outer.cut(cavity).removeSplitter()
    rim = [e for e in tray.Edges
           if abs(e.BoundBox.YMin - STORAGE_FRONT_HEIGHT) < 1e-6
           and abs(e.BoundBox.YMax - STORAGE_FRONT_HEIGHT) < 1e-6
           and e.BoundBox.ZMin > STORAGE_BOX_BACK + 0.1]
    tray = tray.makeFillet(0.8, rim)
    pocket_shape = butterfly_outline(
        BUTTERFLY_SPAN + BUTTERFLY_CLEARANCE,
        BUTTERFLY_HALF_WIDTH + BUTTERFLY_CLEARANCE,
        BUTTERFLY_NECK_HALF_WIDTH + BUTTERFLY_CLEARANCE,
    ).extrude(v(0, 0, BUTTERFLY_POCKET_DEPTH + 0.2))
    for local_x in (MODULE_W / 2 - STORAGE_BOX_X, BOARD_W - MODULE_W / 2 - STORAGE_BOX_X):
        tray = tray.cut(place_xy(pocket_shape, local_x, STORAGE_BOX_H, 90.0, -0.1))
    return tray.removeSplitter()


def add_feature(doc, group, name, shape, label=None, color=None):
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label or name
    obj.Shape = shape
    if color and getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.ShapeColor = color
    group.addObject(obj)
    return obj


def add_string_property(obj, name, value, group="Design"):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyString", name, group)
    setattr(obj, name, value)


def add_length_property(obj, name, value, group="Design"):
    if name not in obj.PropertiesList:
        obj.addProperty("App::PropertyLength", name, group)
    setattr(obj, name, value)


def build_document():
    doc = App.newDocument("WallChessBoard")

    params = doc.addObject("App::FeaturePython", "DesignParameters")
    params.Label = "Design parameters (mm)"
    for name, value in (
        ("CellWidth", CELL_W),
        ("CellHeight", CELL_H),
        ("ModuleWidth", MODULE_W),
        ("ModuleHeight", MODULE_H),
        ("BoardWidth", BOARD_W),
        ("BoardHeight", BOARD_H),
        ("RowPitch", ROW_PITCH),
        ("BackWallThickness", BACK_THICKNESS),
        ("FaceWallThickness", FACE_WALL_THICKNESS),
        ("ShelfDepth", SHELF_DEPTH),
        ("ShelfThickness", SHELF_THICKNESS),
        ("ShelfChamfer", SHELF_CHAMFER),
        ("WhiteTileWidth", CELL_FACE_W),
        ("WhiteTileHeight", CELL_FACE_H),
        ("PositionPostDiameter", POSITION_POST_DIAMETER),
        ("PositionPostHeight", POSITION_POST_HEIGHT),
        ("PositionPostOffset", POSITION_POST_OFFSET),
        ("MagnetDiameter", MAGNET_DIAMETER),
        ("MagnetDepth", MAGNET_DEPTH),
        ("MagnetCenterZ", MAGNET_Z),
        ("LastMoveMarkerWidth", LAST_MOVE_MARKER_WIDTH),
        ("LastMoveMarkerHeight", LAST_MOVE_MARKER_HEIGHT),
        ("LastMoveMarkerThickness", LAST_MOVE_MARKER_THICKNESS),
        ("LastMoveMarkerHookDepth", LAST_MOVE_MARKER_HOOK_DEPTH),
        ("LastMoveClipWidth", LAST_MOVE_CLIP_WIDTH),
        ("LastMoveClipGap", LAST_MOVE_CLIP_GAP),
        ("LastMoveTextDepth", LAST_MOVE_TEXT_DEPTH),
        ("StorageBoxWidth", STORAGE_BOX_W),
        ("StorageBoxHeight", STORAGE_BOX_H),
        ("StorageBoxDepth", STORAGE_BOX_D),
        ("StorageBoxWall", STORAGE_BOX_WALL),
        ("StorageBoxBack", STORAGE_BOX_BACK),
        ("StorageBoxFloor", STORAGE_BOX_FLOOR),
        ("StorageFrontHeight", STORAGE_FRONT_HEIGHT),
        ("StorageCornerRadius", STORAGE_CORNER_RADIUS),
        ("KingHeightClearance", 50.0),
        ("KingDiameter", 20.0),
    ):
        add_length_property(params, name, value)
    add_string_property(params, "PrintMaterial", "Black and white PLA; no AMS required")
    add_string_property(params, "ModuleLayout", "2 columns x 4 rows; each module 4 columns x 2 rows")
    add_string_property(params, "MagnetNote", "One 4 mm diameter x 4 mm deep pocket per shelf, 64 total")

    assembly = doc.addObject("App::DocumentObjectGroup", "Assembly")
    assembly.Label = "Wall assembly (2 x 4 modules)"
    black_group = doc.addObject("App::DocumentObjectGroup", "BlackParts")
    black_group.Label = "Black parts (print 8 copies)"
    white_group = doc.addObject("App::DocumentObjectGroup", "WhiteParts")
    white_group.Label = "White inserts (print 32 copies)"
    connector_group = doc.addObject("App::DocumentObjectGroup", "ConnectorParts")
    connector_group.Label = "Board seam connectors (10 of 12 clips)"
    marker_group = doc.addObject("App::DocumentObjectGroup", "MarkerParts")
    marker_group.Label = "LAST MOVE marker (print 1 copy)"
    storage_group = doc.addObject("App::DocumentObjectGroup", "StorageBoxParts")
    storage_group.Label = "Chess-piece storage box (print 1 copy)"
    storage_connector_group = doc.addObject("App::DocumentObjectGroup", "StorageConnectorParts")
    storage_connector_group.Label = "Storage box butterfly clips (print 2 copies)"
    print_group = doc.addObject("App::DocumentObjectGroup", "PrintParts")
    print_group.Label = "Print-ready reference parts"

    black_shape = make_black_module()
    white_shape = make_white_tile()
    connector_shape = make_butterfly_clip()
    marker_shape = make_last_move_marker()
    storage_shape = make_storage_box()

    # One reference part for slicing and eight placed copies for the complete
    # wall board. Placement is in XY, with 34 mm projection in +Z.
    black_reference = add_feature(doc, print_group, "BlackModule_Print", black_shape, "BLACK MODULE - print 8x", (0.12, 0.12, 0.14))
    black_reference.addProperty("App::PropertyString", "PrintQuantity", "Print").PrintQuantity = "8"
    black_reference.addProperty("App::PropertyString", "PrintOrientation", "Print").PrintOrientation = "Flat, back plate on build plate"
    black_reference.addProperty("App::PropertyString", "Function", "Print").Function = "Black face, two continuous shelves and rear keyhole hangers"

    white_reference = add_feature(doc, print_group, "WhiteTile_Print", white_shape, "WHITE TILE - print 32x", (0.92, 0.92, 0.92))
    white_reference.addProperty("App::PropertyString", "PrintQuantity", "Print").PrintQuantity = "32"
    white_reference.addProperty("App::PropertyString", "PrintOrientation", "Print").PrintOrientation = "Flat"
    white_reference.addProperty("App::PropertyString", "Function", "Print").Function = "Full-cell white insert with four underside locating holes"
    connector_reference = add_feature(doc, print_group, "ButterflyClip_Print", connector_shape, "BUTTERFLY CLIP - print 12x", (0.18, 0.18, 0.20))
    connector_reference.addProperty("App::PropertyString", "PrintQuantity", "Print").PrintQuantity = str(TOTAL_BUTTERFLY_CLIPS)
    connector_reference.addProperty("App::PropertyString", "PrintOrientation", "Print").PrintOrientation = "Flat, bow-tie face on build plate"
    connector_reference.addProperty("App::PropertyString", "Function", "Print").Function = "Bridges two neighboring module edge pockets"
    marker_reference = add_feature(doc, print_group, "LastMoveMarker_Print", marker_shape, "LAST MOVE - white badge / print 1x", (0.92, 0.92, 0.92))
    marker_reference.addProperty("App::PropertyString", "PrintQuantity", "Print").PrintQuantity = "1"
    marker_reference.addProperty("App::PropertyString", "PrintOrientation", "Print").PrintOrientation = "STL is face-down; print in white PLA, 0.16 mm layers"
    marker_reference.addProperty("App::PropertyString", "Function", "Print").Function = "Rounded engraved LAST / MOVE badge; 6 mm C-clip and 5.4 mm shelf slot"
    add_string_property(marker_reference, "FaceText", "LAST MOVE")
    storage_reference = add_feature(doc, print_group, "StorageBox_Print", storage_shape, "PIECE STORAGE BOX - print 1x", (0.12, 0.12, 0.14))
    storage_reference.addProperty("App::PropertyString", "PrintQuantity", "Print").PrintQuantity = "1"
    storage_reference.addProperty("App::PropertyString", "PrintOrientation", "Print").PrintOrientation = "STL is upright on its bottom: 168 x 68 mm footprint; rear pocket roofs may need local support"
    storage_reference.addProperty("App::PropertyString", "Function", "Print").Function = "Open-top bin, closed front, radiused corners, two concealed butterfly mounts"
    # Visibility is a document property, so this also works in FreeCADCmd
    # where ViewObject is not instantiated.
    if hasattr(white_reference, "Visibility"):
        white_reference.Visibility = False
    if hasattr(black_reference, "Visibility"):
        black_reference.Visibility = False
    if hasattr(connector_reference, "Visibility"):
        connector_reference.Visibility = False
    if hasattr(marker_reference, "Visibility"):
        marker_reference.Visibility = False
    if hasattr(storage_reference, "Visibility"):
        storage_reference.Visibility = False

    # Assembly modules: 2 columns by 4 rows.  The module shape is copied so
    # the tree remains editable without eight independent sketches.
    module_number = 1
    for board_row in range(BOARD_ROWS):
        for board_col in range(BOARD_COLS):
            module = add_feature(
                doc,
                black_group,
                "BlackModule_%02d" % module_number,
                black_shape.copy(),
                "Black module %02d (%d,%d)" % (module_number, board_col + 1, board_row + 1),
                (0.12, 0.12, 0.14),
            )
            module.Placement.Base = v(board_col * MODULE_W, board_row * MODULE_H, 0)
            module.addProperty("App::PropertyInteger", "GridColumn", "Assembly").GridColumn = board_col + 1
            module.addProperty("App::PropertyInteger", "GridRow", "Assembly").GridRow = board_row + 1

            # White squares are the even-color cells (a1 is black in this
            # design).  Four tiles per module, 32 in the complete board.
            for local_row in range(MODULE_ROWS):
                for local_col in range(MODULE_COLS):
                    if (board_col * MODULE_COLS + local_col + board_row * MODULE_ROWS + local_row) % 2 != 1:
                        continue
                    x = board_col * MODULE_W + local_col * CELL_W
                    y = board_row * MODULE_H + local_row * ROW_PITCH + SHELF_THICKNESS
                    tile = add_feature(
                        doc,
                        white_group,
                        "WhiteTile_%02d" % len(white_group.Group),
                        white_shape.copy(),
                        "White tile (%d,%d)" % (local_col + 1, local_row + 1),
                        (0.92, 0.92, 0.92),
                    )
                    tile.Placement.Base = v(x, y, BACK_THICKNESS - WHITE_THICKNESS)
            module_number += 1

    # Place one connector at each internal module boundary: 4 vertical and 6
    # horizontal joins. Each clip is retained as an editable assembly part.
    connector_number = 1
    for board_row in range(BOARD_ROWS):
        for board_col in range(BOARD_COLS - 1):
            connector = add_feature(
                doc,
                connector_group,
                "ButterflyClip_%02d" % connector_number,
                connector_shape.copy(),
                "Butterfly clip %02d (vertical join)" % connector_number,
                (0.18, 0.18, 0.20),
            )
            connector.Placement.Base = v(MODULE_W, board_row * MODULE_H + MODULE_H / 2.0, 0.2)
            connector.addProperty("App::PropertyString", "JoinType", "Assembly").JoinType = "Vertical module seam"
            connector_number += 1
    for board_row in range(BOARD_ROWS - 1):
        for board_col in range(BOARD_COLS):
            connector = add_feature(
                doc,
                connector_group,
                "ButterflyClip_%02d" % connector_number,
                place_xy(connector_shape, 0, 0, 90.0),
                "Butterfly clip %02d (horizontal join)" % connector_number,
                (0.18, 0.18, 0.20),
            )
            connector.Placement.Base = v(board_col * MODULE_W + MODULE_W / 2.0, board_row * MODULE_H + MODULE_H, 0.2)
            connector.addProperty("App::PropertyString", "JoinType", "Assembly").JoinType = "Horizontal module seam"
            connector_number += 1

    # The narrow C-clip occupies the gap between two piece envelopes; the
    # engraved badge stays in front of the shelf instead of entering it.
    marker = add_feature(
        doc,
        marker_group,
        "LastMoveMarker_01",
        marker_shape.copy(),
        "LAST MOVE / white rounded badge",
        (0.92, 0.92, 0.92),
    )
    marker.Placement.Base = v(LAST_MOVE_MARKER_X, LAST_MOVE_MARKER_Y, LAST_MOVE_MARKER_Z)
    marker.addProperty("App::PropertyString", "Purpose", "Assembly").Purpose = "Last move indicator"
    marker.addProperty("App::PropertyString", "SafeGap", "Assembly").SafeGap = "6 mm clip in the 8 mm gap between piece envelopes; 24 mm badge beyond the front edge"
    marker.addProperty("App::PropertyString", "Mounting", "Assembly").Mounting = "Slides from the front; C-clip captures both sides of the 5 mm platform"

    # An open-top bin with a closed front hangs under the full board. Its two
    # top-edge pockets align with the existing bottom pockets at x=56 and
    # x=168, so the same butterfly clip design locks both parts together.
    storage = add_feature(
        doc,
        storage_group,
        "StorageBox_01",
        storage_shape.copy(),
        "Chess-piece storage box (under board)",
        (0.12, 0.12, 0.14),
    )
    storage.Placement.Base = v(STORAGE_BOX_X, STORAGE_BOX_Y, 0)
    storage.addProperty("App::PropertyString", "Purpose", "Assembly").Purpose = "Stores chess pieces below the complete board"
    storage.addProperty("App::PropertyString", "Opening", "Assembly").Opening = "Upward (+Y); rim 20 mm below board; closed front"
    storage.addProperty("App::PropertyString", "Mounting", "Assembly").Mounting = "Two butterfly clips at the board bottom edge"
    for storage_clip_number, clip_x in enumerate((MODULE_W / 2.0, BOARD_W - MODULE_W / 2.0), 1):
        storage_clip = add_feature(
            doc,
            storage_connector_group,
            "StorageButterflyClip_%02d" % storage_clip_number,
            place_xy(connector_shape, 0, 0, 90.0),
            "Storage box butterfly clip %02d" % storage_clip_number,
            (0.18, 0.18, 0.20),
        )
        storage_clip.Placement.Base = v(clip_x, 0, 0.2)
        storage_clip.addProperty("App::PropertyString", "JoinType", "Assembly").JoinType = "Storage box to board"

    # Keep the document tree useful: the assembly group contains the two
    # material groups, while each material group owns its placed components.
    assembly.addObject(black_group)
    assembly.addObject(white_group)
    assembly.addObject(connector_group)
    assembly.addObject(marker_group)
    assembly.addObject(storage_group)
    assembly.addObject(storage_connector_group)

    # Add a concise assembly note inside the document tree.
    notes = doc.addObject("App::FeaturePython", "AssemblyNotes")
    notes.Label = "Assembly notes"
    add_string_property(notes, "Step01", "Print 8 identical black modules, 32 white tiles, 12 butterfly clips, 1 LAST MOVE marker and 1 storage box.")
    add_string_property(notes, "Step02", "Press one 4x4 mm neodymium magnet into each shelf pocket (64 total).")
    add_string_property(notes, "Step03", "Drop each full-cell white tile onto the back plate and engage its four underside holes with the locating posts; there are no perimeter walls, dividers or front rails.")
    add_string_property(notes, "Step04", "Join neighboring modules with one butterfly clip at each internal seam, then engage the rear keyhole hangers.")
    add_string_property(notes, "Step05", "Print the rounded LAST MOVE badge in white, slide its C-clip over the shelf from the front in a gap between pieces. Recessed lettering can be filled with black paint.")
    add_string_property(notes, "Step06", "Before wall mounting, connect the open-top bin to the board bottom using two 4.8 mm butterfly clips. The continuous front wall retains pieces; load from above.")
    add_string_property(notes, "Clearance", "Each full-width shelf has 56 mm clear height above its 5 mm platform for a 50 mm king.")
    add_string_property(notes, "WallThickness", "There are no white-cell perimeter walls. The black back plate is 14 mm thick; connector pockets leave 9 mm of material behind them.")
    add_string_property(notes, "WallFixing", "Use two suitable wall screws per module or a continuous wall cleat rated for the assembled load.")

    # Hide duplicate reference grouping in the assembly view.
    for obj in print_group.Group:
        if hasattr(obj, "Visibility"):
            obj.Visibility = False
    if hasattr(print_group, "Visibility"):
        print_group.Visibility = False

    doc.recompute()
    return doc, black_shape, white_shape, connector_shape, marker_shape, storage_shape


def shape_bbox(shape):
    bb = shape.optimalBoundingBox(False)
    return {"x": round(bb.XLength, 3), "y": round(bb.YLength, 3), "z": round(bb.ZLength, 3)}


def export_parts(doc, black_shape, white_shape, connector_shape, marker_shape, storage_shape):
    # STEP exports preserve the exact solids and are convenient for editing in
    # other CAD packages.
    black_obj = doc.getObject("BlackModule_Print")
    white_obj = doc.getObject("WhiteTile_Print")
    connector_obj = doc.getObject("ButterflyClip_Print")
    marker_obj = doc.getObject("LastMoveMarker_Print")
    storage_obj = doc.getObject("StorageBox_Print")
    try:
        Part.export([black_obj], os.path.join(EXPORT_DIR, "black_module.step"))
        Part.export([white_obj], os.path.join(EXPORT_DIR, "white_tile.step"))
        Part.export([connector_obj], os.path.join(EXPORT_DIR, "butterfly_clip.step"))
        Part.export([marker_obj], os.path.join(EXPORT_DIR, "last_move_marker.step"))
        Part.export([storage_obj], os.path.join(EXPORT_DIR, "storage_box.step"))
    except Exception as exc:
        print("STEP export warning:", exc)

    # STL exports are the direct slicer inputs.  Mesh is imported lazily so
    # FreeCADCmd can still build the document if the mesh module is absent.
    try:
        import Mesh

        Mesh.export([black_obj], os.path.join(EXPORT_DIR, "black_module.stl"))
        Mesh.export([white_obj], os.path.join(EXPORT_DIR, "white_tile.stl"))
        Mesh.export([connector_obj], os.path.join(EXPORT_DIR, "butterfly_clip.stl"))
        import MeshPart
        # Orient accessory STLs for printing; STEP and assembly keep wall axes.
        for obj, filename, axis, angle in (
            (marker_obj, "last_move_marker.stl", v(0, 1, 0), 180),
            (storage_obj, "storage_box.stl", v(1, 0, 0), 90),
        ):
            printable = obj.Shape.copy()
            printable.rotate(v(0, 0, 0), axis, angle)
            bb = printable.optimalBoundingBox(False)
            printable.translate(v(-bb.XMin, -bb.YMin, -bb.ZMin))
            mesh = MeshPart.meshFromShape(Shape=printable, LinearDeflection=0.08,
                                         AngularDeflection=0.15, Relative=False)
            mesh.write(os.path.join(EXPORT_DIR, filename))
    except Exception as exc:
        print("STL export warning:", exc)

    # A complete assembly STEP gives a single reference for wall layout.
    assembly_objects = list(doc.getObject("BlackParts").Group) + list(doc.getObject("WhiteParts").Group) + list(doc.getObject("ConnectorParts").Group) + list(doc.getObject("MarkerParts").Group) + list(doc.getObject("StorageBoxParts").Group) + list(doc.getObject("StorageConnectorParts").Group)
    try:
        Part.export(assembly_objects, os.path.join(EXPORT_DIR, "wall_chess_board_assembly.step"))
    except Exception as exc:
        print("Assembly STEP export warning:", exc)


def write_validation(black_shape, white_shape, connector_shape, marker_shape, storage_shape):
    report = {
        "units": "mm",
        "cell": {"width": CELL_W, "height": CELL_H, "pitch": [CELL_W, ROW_PITCH], "clear_height": CELL_H},
        "module": {"width": MODULE_W, "height": MODULE_H, "layout": "4 x 2", "quantity": 8, "bbox": shape_bbox(black_shape), "back_wall_thickness": BACK_THICKNESS, "white_cell_perimeter_wall": FACE_WALL_THICKNESS, "position_posts_per_white_tile": 4},
        "board": {"width": BOARD_W, "height": BOARD_H, "layout": "2 x 4 modules"},
        "white_tile": {"quantity": 32, "bbox": shape_bbox(white_shape), "position_holes_per_tile": 4, "position_hole_diameter": POSITION_POST_DIAMETER + 2 * POSITION_POST_CLEARANCE, "position_hole_depth": POSITION_POST_HEIGHT + POSITION_POST_CLEARANCE},
        "butterfly_connector": {"quantity": TOTAL_BUTTERFLY_CLIPS, "board_seam_quantity": INTERNAL_JOINS, "storage_clip_quantity": STORAGE_CLIPS, "bbox": shape_bbox(connector_shape), "span": BUTTERFLY_SPAN, "thickness": BUTTERFLY_THICKNESS, "clearance": BUTTERFLY_CLEARANCE},
        "last_move_marker": {"quantity": 1, "material": "white PLA", "bbox": shape_bbox(marker_shape), "placement": [LAST_MOVE_MARKER_X, LAST_MOVE_MARKER_Y, LAST_MOVE_MARKER_Z], "clip_width": LAST_MOVE_CLIP_WIDTH, "slot_height": LAST_MOVE_CLIP_GAP, "text": "LAST MOVE", "engraving_depth": LAST_MOVE_TEXT_DEPTH, "print_orientation": "lettered face down", "purpose": "C-clip captures both sides of platform without colliding with pieces"},
        "storage_box": {"quantity": 1, "bbox": shape_bbox(storage_shape), "placement": [STORAGE_BOX_X, STORAGE_BOX_Y, 0.0], "side_and_front_wall": STORAGE_BOX_WALL, "back_wall": STORAGE_BOX_BACK, "floor": STORAGE_BOX_FLOOR, "front_height": STORAGE_FRONT_HEIGHT, "retaining_height_above_floor": STORAGE_FRONT_HEIGHT - STORAGE_BOX_FLOOR, "front_corner_radius": STORAGE_CORNER_RADIUS, "opening": "top (+Y)", "front_closed": True, "rim_below_board": STORAGE_BOX_H - STORAGE_FRONT_HEIGHT, "print_footprint": [STORAGE_BOX_W, STORAGE_BOX_D], "mounting": "two butterfly clips at board bottom edge"},
        "shelves": {"per_module": 2, "total": 16, "continuous_across_four_cells": True, "thickness": SHELF_THICKNESS, "depth": SHELF_DEPTH, "chamfer": SHELF_CHAMFER, "chamfered_long_edges": 2, "front_rails": False, "row_pitch": ROW_PITCH},
        "magnet_pockets": {"quantity": 64, "diameter": MAGNET_DIAMETER, "depth": MAGNET_DEPTH, "axis": "Y (platform thickness)", "center_z": MAGNET_Z},
        "king_clearance": {"piece_height": 50.0, "piece_diameter": 20.0, "clear_height": CELL_H},
        "black_white_dividers": False,
        "print_material": "black and white PLA; no AMS required",
        "a1_mini_fit": {"module_xy": [MODULE_W, MODULE_H], "box_xy": [STORAGE_BOX_W, STORAGE_BOX_D], "max_xy": [180.0, 180.0], "fits": max(MODULE_W, MODULE_H, STORAGE_BOX_W, STORAGE_BOX_D) <= 180},
        "files": [
            "WallChessBoard.FCStd",
            "exports/black_module.stl",
            "exports/white_tile.stl",
            "exports/butterfly_clip.stl",
            "exports/last_move_marker.stl",
            "exports/storage_box.stl",
            "exports/black_module.step",
            "exports/white_tile.step",
            "exports/butterfly_clip.step",
            "exports/last_move_marker.step",
            "exports/storage_box.step",
            "exports/wall_chess_board_assembly.step",
            "assembly_manual.html",
            "previews/accessories.png",
            "verification_results.json",
        ],
    }
    with open(os.path.join(ROOT, "validation_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)


def main():
    doc, black_shape, white_shape, connector_shape, marker_shape, storage_shape = build_document()
    doc.recompute()
    doc.saveAs(os.path.join(ROOT, "WallChessBoard.FCStd"))
    export_parts(doc, black_shape, white_shape, connector_shape, marker_shape, storage_shape)
    write_validation(black_shape, white_shape, connector_shape, marker_shape, storage_shape)
    print("Generated WallChessBoard.FCStd")
    print("Black module bbox:", shape_bbox(black_shape))
    print("White tile bbox:", shape_bbox(white_shape))
    print("Board:", BOARD_W, "x", BOARD_H, "mm; modules: 8; white tiles: 32; magnet pockets: 64; storage box: 1")


if __name__ == "__main__":
    main()
