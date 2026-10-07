"""Lightweight FreeCADCmd verification for the generated chess board."""
import json
import os
import FreeCAD as App

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
checks["marker_bbox"] = [round(marker.Shape.BoundBox.XLength, 3), round(marker.Shape.BoundBox.YLength, 3), round(marker.Shape.BoundBox.ZLength, 3)]
checks["storage_bbox"] = [round(storage.Shape.BoundBox.XLength, 3), round(storage.Shape.BoundBox.YLength, 3), round(storage.Shape.BoundBox.ZLength, 3)]
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
checks["butterfly_clip_fits"] = connector.Shape.BoundBox.XLength == 40.0 and connector.Shape.BoundBox.YLength == 20.0 and connector.Shape.BoundBox.ZLength == 5.6
checks["connector_placements"] = all(abs(o.Placement.Base.z - 0.2) < 1e-6 for o in doc.getObject("ConnectorParts").Group)
checks["last_move_marker_safe_gap"] = (
    abs(doc.getObject("LastMoveMarker_01").Placement.Base.x - 24.5) < 1e-6
    and abs(doc.getObject("LastMoveMarker_01").Placement.Base.y + 21.0) < 1e-6
    and abs(doc.getObject("LastMoveMarker_01").Placement.Base.z - 31.0) < 1e-6
    and marker.Shape.BoundBox.XLength == 7.0
    and marker.Shape.BoundBox.YLength == 26.0
    and marker.Shape.BoundBox.ZLength == 6.0
)
checks["storage_box_dimensions"] = (
    checks["storage_bbox"] == [160.0, 55.0, 45.0]
    and float(params.StorageBoxWall) == 8.0
)
checks["storage_box_placement"] = (
    abs(doc.getObject("StorageBox_01").Placement.Base.x - 32.0) < 1e-6
    and abs(doc.getObject("StorageBox_01").Placement.Base.y + 55.0) < 1e-6
    and abs(doc.getObject("StorageBox_01").Placement.Base.z) < 1e-6
)
checks["storage_connector_placements"] = (
    all(abs(o.Placement.Base.z - 0.2) < 1e-6 for o in doc.getObject("StorageConnectorParts").Group)
    and [round(o.Placement.Base.x, 3) for o in doc.getObject("StorageConnectorParts").Group] == [56.0, 168.0]
    and all(abs(o.Placement.Base.y) < 1e-6 for o in doc.getObject("StorageConnectorParts").Group)
)
print(json.dumps(checks, ensure_ascii=False, indent=2))
if not all(v for k, v in checks.items() if isinstance(v, bool)):
    raise RuntimeError("chess board verification failed")

