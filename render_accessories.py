"""Render the delivered CAD solids, without a GUI or invented geometry."""
import os
import FreeCAD as App
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.abspath(__file__))
doc = App.openDocument(os.path.join(ROOT, "WallChessBoard.FCStd"))
OUT = os.path.join(ROOT, "previews")
os.makedirs(OUT, exist_ok=True)


def add_shape(ax, shape, color, engraved=False):
    triangles, colors = [], []
    light = np.array([-0.4, -0.65, 0.9])
    light /= np.linalg.norm(light)
    for face in shape.Faces:
        points, facets = face.tessellate(0.1)
        if not facets:
            continue
        points = np.array([[p.x, -p.z, p.y] for p in points])
        tris = points[np.array(facets)]
        norms = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        norms /= np.maximum(np.linalg.norm(norms, axis=1)[:, None], 1e-12)
        base = np.array(color)
        # Dark infill is a manual finishing option, not an extra printed part.
        if engraved and abs(face.BoundBox.ZMin - 8.8) < 1e-5 and abs(face.BoundBox.ZMax - 8.8) < 1e-5:
            base = np.array([0.16, 0.17, 0.18])
        shades = 0.72 + 0.28 * np.clip(norms @ light, 0, 1)
        triangles.extend(tris)
        colors.extend(np.clip(base[None, :] * shades[:, None], 0, 1))
    if not hasattr(ax, "cad_triangles"):
        ax.cad_triangles, ax.cad_colors = [], []
    ax.cad_triangles.extend(triangles)
    ax.cad_colors.extend(colors)


def frame(ax, bounds, elev=23, azim=-66, pad=0.04):
    # A per-pixel depth buffer avoids painter-order artifacts between coplanar
    # chess faces and the curved box. No CAD geometry is changed for the image.
    e, a = np.radians([elev, azim])
    right = np.array([-np.sin(a), np.cos(a), 0])
    up = np.array([-np.sin(e)*np.cos(a), -np.sin(e)*np.sin(a), np.cos(e)])
    eye = np.array([np.cos(e)*np.cos(a), np.cos(e)*np.sin(a), np.sin(e)])
    triangles = np.array(ax.cad_triangles)
    projected = triangles @ np.stack([right, up, eye], axis=1)
    pos = ax.get_position()
    width, height = int(pos.width * 3000), int(pos.height * 2250)
    lo, hi = projected.min(axis=(0, 1)), projected.max(axis=(0, 1))
    scale = min(width / (hi[0]-lo[0]), height / (hi[1]-lo[1])) * (1-2*pad)
    projected[:, :, 0] = (projected[:, :, 0] - (hi[0]+lo[0])/2) * scale + width/2
    projected[:, :, 1] = -(projected[:, :, 1] - (hi[1]+lo[1])/2) * scale + height/2
    pixels = np.full((height, width, 3), [243, 241, 236], dtype=np.uint8)
    depth = np.full((height, width), -np.inf)
    for tri, color in zip(projected, ax.cad_colors):
        xmin, ymin = np.maximum(np.floor(tri[:, :2].min(axis=0)).astype(int), 0)
        xmax, ymax = np.minimum(np.ceil(tri[:, :2].max(axis=0)).astype(int), [width-1, height-1])
        if xmax < xmin or ymax < ymin:
            continue
        x0, y0, z0 = tri[0]
        x1, y1, z1 = tri[1]
        x2, y2, z2 = tri[2]
        den = (y1-y2)*(x0-x2) + (x2-x1)*(y0-y2)
        if abs(den) < 1e-9:
            continue
        yy, xx = np.mgrid[ymin:ymax+1, xmin:xmax+1]
        w0 = ((y1-y2)*(xx-x2) + (x2-x1)*(yy-y2)) / den
        w1 = ((y2-y0)*(xx-x2) + (x0-x2)*(yy-y2)) / den
        w2 = 1-w0-w1
        zz = w0*z0 + w1*z1 + w2*z2
        tile = depth[ymin:ymax+1, xmin:xmax+1]
        mask = (w0 >= -1e-7) & (w1 >= -1e-7) & (w2 >= -1e-7) & (zz > tile)
        tile[mask] = zz[mask]
        pixels[ymin:ymax+1, xmin:xmax+1][mask] = np.array(color)*255
    ax.imshow(pixels, interpolation="lanczos")
    ax.set_axis_off()
    ax.set_facecolor("#f3f1ec")


fig = plt.figure(figsize=(16, 12), facecolor="#f3f1ec")
fig.text(0.045, 0.95, "WALL CHESS / REFINED ACCESSORIES", color="#20272c", fontsize=22, weight="bold")
fig.text(0.045, 0.922, "Actual CAD geometry  /  rounded forms  /  black + white PLA", color="#62686d", fontsize=12)

ax = fig.add_axes([0.025, 0.11, 0.40, 0.77])
for group in doc.getObject("Assembly").Group:
    for obj in group.Group:
        color = (0.88, 0.88, 0.83) if group.Name in ("WhiteParts", "MarkerParts") else (0.20, 0.22, 0.24)
        add_shape(ax, obj.Shape, color)
frame(ax, ((0, -68, -76), (224, 0, 488)), elev=12, azim=-78)
fig.text(0.06, 0.075, "01  WALL ASSEMBLY", fontsize=11, weight="bold", color="#20272c")
fig.text(0.06, 0.053, "Bin centred below the board; two hidden butterfly mounts", fontsize=10, color="#62686d")

ax = fig.add_axes([0.42, 0.53, 0.55, 0.35])
add_shape(ax, doc.getObject("StorageBox_Print").Shape, (0.23, 0.25, 0.27))
frame(ax, ((0, -68, 0), (168, 0, 76)), elev=31, azim=-66)
fig.text(0.48, 0.49, "02  OPEN-TOP STORAGE", fontsize=12, weight="bold", color="#20272c")
fig.text(0.48, 0.466, "168 x 76 x 68 mm  /  closed front  /  R12 corners", fontsize=11, color="#62686d")
fig.text(0.48, 0.444, "51 mm retention above floor; rim 20 mm below board", fontsize=10, color="#62686d")

ax = fig.add_axes([0.43, 0.14, 0.28, 0.26])
add_shape(ax, doc.getObject("LastMoveMarker_Print").Shape, (0.95, 0.94, 0.90), engraved=True)
frame(ax, ((0, -9.5, 0), (24, 0, 14)), elev=10, azim=-80)
fig.text(0.45, 0.102, "03  LAST MOVE", fontsize=12, weight="bold", color="#20272c")
fig.text(0.45, 0.078, "24 x 14 mm rounded badge", fontsize=10, color="#62686d")
fig.text(0.45, 0.056, "Recessed text; black infill shown", fontsize=10, color="#62686d")

ax = fig.add_axes([0.72, 0.14, 0.26, 0.26])
add_shape(ax, doc.getObject("LastMoveMarker_Print").Shape, (0.95, 0.94, 0.90))
frame(ax, ((0, -9.5, 0), (24, 0, 14)), elev=22, azim=52)
fig.text(0.75, 0.102, "04  REAR C-CLIP", fontsize=12, weight="bold", color="#20272c")
fig.text(0.75, 0.078, "6 mm wide / 5.4 mm shelf slot", fontsize=10, color="#62686d")
fig.text(0.75, 0.056, "Upper + lower jaws with lead-ins", fontsize=10, color="#62686d")

fig.savefig(os.path.join(OUT, "accessories.png"), dpi=150, facecolor=fig.get_facecolor())
plt.close(fig)
print("Rendered previews/accessories.png from WallChessBoard.FCStd")
