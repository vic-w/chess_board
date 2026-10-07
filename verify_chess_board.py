"""Lightweight FreeCADCmd verification for the generated chess board."""
import json
import os
import FreeCAD as App
import Part
import Mesh

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
doc = App.openDocument(os.path.join(ROOT, "WallChessBoard.FCStd"))
checks = {}
params = doc.getObject("DesignParameters")
checks["parameters"] = all(hasattr(params, name) for name in ("CellWidth", "CellHeight", "ModuleWidth", "BoardWidth", "MagnetDiameter", "MagnetCenterZ", "BackWallThickness", "FaceWallThickness", "PositionPostDiameter", "PositionPostHeight", "ShelfChamfer", "LastMoveMarkerWidth", "LastMoveMarkerHeight", "LastMoveMarkerHookDepth", "StorageBoxWidth", "StorageBoxHeight", "StorageBoxDepth", "StorageBoxWall"))
black = doc.getObject("BlackModule_Print")
white = doc.getObject("WhiteTile_Print")
connector = doc.getObject("ButterflyClip_Print")
marker = doc.getObject("LastMoveMarker_Print")
storage = doc.getObject("StorageBox_Print")
checks["black_valid"] = bool(black.Shape.isValid())
checks["white_valid"] = bool(white.Shape.isValid())
checks["connector_valid"] = bool(connector.Shape.isValid())
checks["marker_valid"] = bool(marker.Shape.isValid())
checks["storage_valid"] = bool(storage.Shape.isValid())
checks["single_black_solid"] = len(black.Shape.Solids) == 1
checks["single_storage_solid"] = len(storage.Shape.Solids) == 1
checks["black_bbox"] = [round(black.Shape.BoundBox.XLength, 3), round(black.Shape.BoundBox.YLength, 3), round(black.Shape.BoundBox.ZLength, 3)]
checks["white_bbox"] = [round(white.Shape.BoundBox.XLength, 3), round(white.Shape.BoundBox.YLength, 3), round(white.Shape.BoundBox.ZLength, 3)]
checks["connector_bbox"] = [round(connector.Shape.BoundBox.XLength, 3), round(connector.Shape.BoundBox.YLength, 3), round(connector.Shape.BoundBox.ZLength, 3)]
checks["marker_bbox"] = [round(getattr(marker.Shape.optimalBoundingBox(False), a + "Length"), 3) for a in "XYZ"]
checks["storage_bbox"] = [round(getattr(storage.Shape.optimalBoundingBox(False), a + "Length"), 3) for a in "XYZ"]
checks["black_modules"] = len(doc.getObject("BlackParts").Group)
checks["white_tiles"] = len(doc.getObject("WhiteParts").Group)
checks["connectors"] = len(doc.getObject("ConnectorParts").Group)
checks["markers"] = len(doc.getObject("MarkerParts").Group)
checks["storage_boxes"] = len(doc.getObject("StorageBoxParts").Group)
checks["storage_connectors"] = len(doc.getObject("StorageConnectorParts").Group)
assembly_objects = list(doc.getObject("BlackParts").Group) + list(doc.getObject("WhiteParts").Group) + list(doc.getObject("ConnectorParts").Group) + list(doc.getObject("MarkerParts").Group) + list(doc.getObject("StorageBoxParts").Group) + list(doc.getObject("StorageConnectorParts").Group)
checks["assembly_groups"] = len(doc.getObject("Assembly").Group)
checks["assembly_objects"] = len(assembly_objects)
checks["all_assembly_valid"] = all(bool(o.Shape.isValid()) for o in assembly_objects)
checks["expected_counts"] = checks["black_modules"] == 8 and checks["white_tiles"] == 32 and checks["connectors"] == 10 and checks["markers"] == 1 and checks["storage_boxes"] == 1 and checks["storage_connectors"] == 2 and checks["assembly_groups"] == 6 and checks["assembly_objects"] == 54
checks["thick_back_wall"] = black.Shape.BoundBox.ZLength >= 34.0 and hasattr(params, "BackWallThickness")
checks["face_wall_removed"] = float(params.FaceWallThickness) == 0.0 and white.Shape.BoundBox.XLength == 28.0 and white.Shape.BoundBox.YLength == 56.0
checks["shelf_chamfer"] = float(params.ShelfChamfer) == 1.5
checks["magnet_is_centered_in_platform"] = float(params.MagnetCenterZ) == 24.0


def inside(x, y, z):
    return black.Shape.isInside(App.Vector(x, y, z), 1e-6, False)


checks["continuous_shelves"] = all(inside(x, y, 32) for x in (1, 28, 56, 84, 111) for y in (2.5, 63.5))
checks["blind_magnet_pockets"] = all(
    not inside(x, y + 3, 24) and inside(x, y + 0.5, 24)
    for y in (0, 61) for x in (14, 42, 70, 98)
)
checks["white_openings_alternate"] = (
    inside(14, 30, 12) and not inside(42, 30, 12)
    and not inside(14, 90, 12) and inside(42, 90, 12)
)
checks["no_dividers_or_rails"] = all(inside(x, y, 32) for x in (0.5, 28, 56, 84, 111.5) for y in (2.5, 63.5))
checks["no_white_cell_walls"] = all(
    not inside(x, y, 12)
    for x, y in ((28.5, 5.5), (55.5, 5.5), (28.5, 60.5), (55.5, 60.5),
                 (0.5, 66.5), (27.5, 66.5), (0.5, 121.5), (27.5, 121.5))
)
checks["locating_posts_present"] = all(
    inside(x, y, 12)
    for x, y in ((32, 9), (52, 9), (32, 57), (52, 57))
)
checks["white_tile_locating_holes"] = all(
    not white.Shape.isInside(App.Vector(x, y, 1.0), 1e-6, False)
    for x, y in ((4, 4), (24, 4), (4, 52), (24, 52))
)
checks["keyhole_has_captured_head_channel"] = (
    not inside(16, 112, 2) and not inside(19, 118, 3)
    and inside(19, 118, 1) and inside(16, 112, 5.5)
)
checks["white_tiles_flush"] = all(abs(o.Placement.Base.z + white.Shape.BoundBox.ZLength - 14) < 1e-6 for o in doc.getObject("WhiteParts").Group)
checks["magnet_cylinder_faces"] = len([
    f for f in black.Shape.Faces
    if hasattr(f.Surface, "Radius") and abs(f.Surface.Radius - 2.0) < 1e-6
])
checks["eight_magnet_pockets"] = checks["magnet_cylinder_faces"] == 8
checks["butterfly_clip_fits"] = checks["connector_bbox"] == [40.0, 20.0, 4.8]
checks["connector_placements"] = all(abs(o.Placement.Base.z - 0.2) < 1e-6 for o in doc.getObject("ConnectorParts").Group)
checks["last_move_marker_safe_gap"] = (
    abs(doc.getObject("LastMoveMarker_01").Placement.Base.x - 16.0) < 1e-6
    and abs(doc.getObject("LastMoveMarker_01").Placement.Base.y + 5.0) < 1e-6
    and abs(doc.getObject("LastMoveMarker_01").Placement.Base.z - 28.0) < 1e-6
    and checks["marker_bbox"] == [24.0, 14.0, 9.5]
)
checks["storage_box_dimensions"] = (
    checks["storage_bbox"] == [168.0, 76.0, 68.0]
    and float(params.StorageBoxWall) == 4.0
)
checks["storage_box_placement"] = (
    abs(doc.getObject("StorageBox_01").Placement.Base.x - 28.0) < 1e-6
    and abs(doc.getObject("StorageBox_01").Placement.Base.y + 76.0) < 1e-6
    and abs(doc.getObject("StorageBox_01").Placement.Base.z) < 1e-6
)
checks["storage_connector_placements"] = (
    all(abs(o.Placement.Base.z - 0.2) < 1e-6 for o in doc.getObject("StorageConnectorParts").Group)
    and [round(o.Placement.Base.x, 3) for o in doc.getObject("StorageConnectorParts").Group] == [56.0, 168.0]
    and all(abs(o.Placement.Base.y) < 1e-6 for o in doc.getObject("StorageConnectorParts").Group)
)

# These checks exercise the failures the old dimensional checks missed:
# continuous retention walls, an accessible opening, and real mating solids.
bin_shape = storage.Shape
checks["storage_closed_front"] = all(
    bin_shape.isInside(App.Vector(x, y, z), 1e-6, False)
    for x in (20, 56, 84, 112, 148) for y in (10, 30, 53) for z in (64.5, 66, 67.5)
)
checks["storage_floor_and_sides"] = all(
    bin_shape.isInside(App.Vector(*p), 1e-6, False)
    for p in ((84, 2, 30), (2, 25, 30), (166, 25, 30), (84, 25, 4))
)
checks["storage_open_top"] = all(
    not bin_shape.isInside(App.Vector(x, y, z), 1e-6, False)
    for x in (30, 84, 138) for y in (56.1, 60, 75) for z in (20, 43, 60)
)
checks["storage_rounded_corners"] = (
    not bin_shape.isInside(App.Vector(1, 25, 67), 1e-6, False)
    and bin_shape.isInside(App.Vector(12, 25, 66), 1e-6, False)
)
stored_king = Part.makeCylinder(10, 50, App.Vector(84, 5.1, 40), App.Vector(0, 1, 0))
checks["storage_fits_king_upright"] = bin_shape.common(stored_king).Volume < 1e-6
placed_bin = doc.getObject("StorageBox_01").Shape
placed_marker = doc.getObject("LastMoveMarker_01").Shape
board_solids = Part.makeCompound([o.Shape for o in doc.getObject("BlackParts").Group])
checks["storage_no_board_collision"] = placed_bin.common(board_solids).Volume < 1e-6
insertion = Part.makeCylinder(10, 150, App.Vector(112, -70.9, 53), App.Vector(0, 1, 0))
checks["king_top_insertion_clear"] = (
    placed_bin.common(insertion).Volume < 1e-6
    and board_solids.common(insertion).Volume < 1e-6
)
checks["marker_clear_of_board_and_box"] = (
    placed_marker.common(board_solids).Volume < 1e-6
    and placed_marker.common(placed_bin).Volume < 1e-6
)
pieces = Part.makeCompound([
    Part.makeCylinder(10, 50, App.Vector(x, y + 5, 24), App.Vector(0, 1, 0))
    for x in (14, 42) for y in (0, -61)
])
checks["marker_clear_of_piece_cylinders"] = placed_marker.common(pieces).Volume < 1e-6
insertion_sweep = Part.makeBox(6, 5, 34, App.Vector(25, 0, 0))
checks["marker_slide_in_path_clear"] = placed_marker.common(insertion_sweep).Volume < 1e-6
checks["marker_has_upper_and_lower_jaws"] = all(
    placed_marker.isInside(App.Vector(28, y, 30), 1e-6, False) for y in (-1, 6)
)
checks["marker_text_engraved"] = (
    marker.FaceText == "LAST MOVE"
    and len([f for f in marker.Shape.Faces
             if abs(f.BoundBox.ZMin - 8.8) < 1e-5 and abs(f.BoundBox.ZMax - 8.8) < 1e-5]) == 8
)
clips = list(doc.getObject("ConnectorParts").Group) + list(doc.getObject("StorageConnectorParts").Group)
checks["all_clips_clear_of_mating_solids"] = all(
    o.Shape.common(board_solids).Volume < 1e-6 and o.Shape.common(placed_bin).Volume < 1e-6
    for o in clips
)
checks["storage_clips_bridge_seam"] = all(
    o.Shape.BoundBox.YMin < -19 and o.Shape.BoundBox.YMax > 19
    for o in doc.getObject("StorageConnectorParts").Group
)
checks["exported_accessories_watertight"] = True
checks["printable_accessories_fit_a1_mini"] = True
for filename in ("last_move_marker.stl", "storage_box.stl"):
    mesh = Mesh.Mesh(os.path.join(ROOT, "exports", filename))
    checks["exported_accessories_watertight"] &= mesh.isSolid() and mesh.Volume > 0
    checks["printable_accessories_fit_a1_mini"] &= all(
        getattr(mesh.BoundBox, a + "Length") <= 180.01 for a in "XYZ") and abs(mesh.BoundBox.ZMin) < 0.01
with open(os.path.join(ROOT, "verification_results.json"), "w", encoding="utf-8") as fh:
    json.dump(checks, fh, ensure_ascii=False, indent=2)
print(json.dumps(checks, ensure_ascii=False, indent=2))
if not all(v for k, v in checks.items() if isinstance(v, bool)):
    raise RuntimeError("chess board verification failed")

