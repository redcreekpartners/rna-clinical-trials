#!/usr/bin/env python3
"""Build data/world-map.json: Natural Earth 110m as SVG paths, Robinson projection.

    python scripts/build_world_map.py

Run once; the output is committed. Baking the geometry in means the page loads
no mapping library and makes no third-party request.

Source: Natural Earth 110m admin-0 countries (public domain), in the TopoJSON
packaging published by the world-atlas project.
"""
import json
import math
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
OUT = ROOT / "data" / "world-map.json"
WIDTH = 1000.0

# Robinson rather than equirectangular. An equirectangular world stretches the
# high latitudes so far that Canada and Russia bloat while Europe, where most of
# these trials are, compresses into a smudge.
#
# Robinson's published table: X is a parallel's length, Y its distance from the
# equator, both relative to the equator, every 5 degrees, interpolated between.
RX = [1.0000, 0.9986, 0.9954, 0.9900, 0.9822, 0.9730, 0.9600, 0.9427, 0.9216, 0.8962,
      0.8679, 0.8350, 0.7986, 0.7597, 0.7186, 0.6732, 0.6213, 0.5722, 0.5322]
RY = [0.0000, 0.0620, 0.1240, 0.1860, 0.2480, 0.3100, 0.3720, 0.4340, 0.4958, 0.5571,
      0.6176, 0.6769, 0.7346, 0.7903, 0.8435, 0.8936, 0.9394, 0.9761, 1.0000]
# x and y carry different constants (0.8487 and 1.3523 times the earth's
# radius). Working in unit ranges drops them and squashes the aspect ratio, so
# the ratio is put back on y.
Y_SCALE = 1.3523 / (0.8487 * math.pi)

# ClinicalTrials.gov and Natural Earth name these countries differently.
ALIAS = {
    "United States": "United States of America",
    "Democratic Republic of the Congo": "Dem. Rep. Congo",
    "Turkey (Türkiye)": "Turkey",
}

# Places trials run in that have no polygon at 110m. They are drawn as markers
# so they stay clickable on the map, not only in the list beside it.
POINTS = {
    "Hong Kong": (114.17, 22.32),
    "Singapore": (103.82, 1.35),
    "Mauritius": (57.55, -20.35),
    "Malta": (14.42, 35.94),
    "Bahrain": (50.55, 26.07),
    "Luxembourg": (6.13, 49.61),
    "Iceland": (-19.02, 64.96),
}


def robinson(lon, lat):
    a = min(abs(lat), 90.0) / 5.0
    i = min(int(a), 17)
    f = a - i
    x = (RX[i] + (RX[i + 1] - RX[i]) * f) * (lon / 180.0)
    y = (RY[i] + (RY[i + 1] - RY[i]) * f) * (1.0 if lat >= 0 else -1.0) * Y_SCALE
    return x, y


def main():
    src = ROOT / ".cache" / "countries-110m.json"
    if not src.exists():
        src.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(SOURCE, src)
    topo = json.loads(src.read_text())
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = topo["arcs"]

    def arc(i):
        backwards = i < 0
        if backwards:
            i = ~i
        x = y = 0
        pts = []
        for dx, dy in arcs[i]:          # delta-encoded, quantised
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        return pts[::-1] if backwards else pts

    rings = {}
    for geom in topo["objects"]["countries"]["geometries"]:
        name = (geom.get("properties") or {}).get("name")
        # Antarctica has no trials and would take a third of the map's height.
        # Nothing else is cropped: clamping latitudes instead flattened southern
        # Chile onto a horizontal line drawn straight across the map.
        if not name or name == "Antarctica":
            continue
        ring_arcs = (geom["arcs"] if geom["type"] == "Polygon"
                     else [ring for poly in geom["arcs"] for ring in poly])
        pieces = []
        for ids in ring_arcs:
            pts = []
            for a in ids:
                seg = arc(a)
                pts.extend(seg[1:] if pts else seg)
            # Fiji straddles the antimeridian: consecutive points can sit at 177E
            # and 178W, which projects to opposite edges of the map and draws a
            # sliver across the Pacific. Split wherever longitude jumps more than
            # half the world.
            piece = []
            for k, (lon, lat) in enumerate(pts):
                if k and abs(lon - pts[k - 1][0]) > 180:
                    if len(piece) >= 3:
                        pieces.append(piece)
                    piece = []
                piece.append(robinson(lon, lat))
            if len(piece) >= 3:
                pieces.append(piece)
        rings[name] = pieces

    xs = [p[0] for rs in rings.values() for r in rs for p in r]
    ys = [p[1] for rs in rings.values() for r in rs for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    scale = WIDTH / (x1 - x0)
    height = (y1 - y0) * scale

    def px(x, y):
        # one decimal is ~0.4 px here: smooth coastlines, modest file
        return round((x - x0) * scale, 1), round((y1 - y) * scale, 1)

    paths = {}
    for name, pieces in rings.items():
        d = []
        for piece in pieces:
            pts, last = [], None
            for x, y in piece:
                p = px(x, y)
                if p != last:
                    pts.append(p)
                    last = p
            if len(pts) >= 3:
                d.append("M" + "L".join(f"{a},{b}" for a, b in pts) + "Z")
        if d:
            paths[name] = "".join(d)

    points = {name: list(px(*robinson(lon, lat)))
              for name, (lon, lat) in POINTS.items() if name not in paths}

    OUT.write_text(json.dumps({
        "source": "Natural Earth 110m via world-atlas (public domain), Robinson projection, "
                  "Antarctica omitted",
        "viewBox": f"0 0 {WIDTH:.0f} {height:.0f}",
        "alias": ALIAS,
        "points": points,
        "paths": paths,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"{OUT.name}: {len(paths)} countries, {len(points)} markers, "
          f"{OUT.stat().st_size / 1024:.0f} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
