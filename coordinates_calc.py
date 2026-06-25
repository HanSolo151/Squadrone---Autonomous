import matplotlib.pyplot as plt
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import transform
import pyproj
import math


points = [
    (12.8579488, 77.4411603),
    (12.8582210, 77.4413001),
    (12.8581422, 77.4415192),
    (12.8578366, 77.4414079),
]
 
 
def generate_lawnmower_with_5m_spacing(points, spacing=10, buffer_m=2, decimals=7, waypoint_spacing=5):

    def truncate(num):
        factor = 10 ** decimals
        return math.trunc(num * factor) / factor

    # Build original polygon
    poly = Polygon([(lon, lat) for lat, lon in points])

    # Local projection
    proj_latlon = pyproj.CRS("EPSG:4326")
    proj_local = pyproj.CRS.from_proj4(
        f"+proj=tmerc +lat_0={poly.centroid.y} +lon_0={poly.centroid.x} +units=m +datum=WGS84"
    )
    to_m = pyproj.Transformer.from_crs(proj_latlon, proj_local, always_xy=True).transform
    to_deg = pyproj.Transformer.from_crs(proj_local, proj_latlon, always_xy=True).transform

    # Offset inward
    poly_m = transform(to_m, poly)
    poly_inward_m = poly_m.buffer(-buffer_m)
    poly_inward = transform(to_deg, poly_inward_m)

    inward_coords = [
        (truncate(lat), truncate(lon))
        for lon, lat in poly_inward.exterior.coords[:-1]
    ]

    # Generate lawnmower sweep lines
    poly_m = transform(to_m, Polygon([(lon, lat) for lat, lon in inward_coords]))
    minx, miny, maxx, maxy = poly_m.bounds

    lines = []
    y = miny
    while y <= maxy:
        lines.append(LineString([(minx, y), (maxx, y)]))
        y += spacing

    # Clip & zig-zag
    path_m = []
    for i, line in enumerate(lines):
        clipped = line.intersection(poly_m)
        if clipped.is_empty:
            continue

        segs = []
        if clipped.geom_type == "LineString":
            segs = [clipped]
        elif clipped.geom_type == "MultiLineString":
            segs = list(clipped.geoms)

        for seg in segs:
            coords = list(seg.coords)
            if i % 2 == 1:
                coords.reverse()
            path_m.extend(coords)

    # Convert to GPS
    path_latlon = [transform(to_deg, Point(x, y)) for x, y in path_m]
    path = [(truncate(pt.y), truncate(pt.x)) for pt in path_latlon]

    # -------------------------------
    # DENSIFY 5-meter waypoints
    # -------------------------------
    if len(path) > 1:
        lat0, lon0 = path[0]

        # Local projection for densification
        proj_local2 = pyproj.CRS.from_proj4(
            f"+proj=tmerc +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84"
        )
        to_m2 = pyproj.Transformer.from_crs(proj_latlon, proj_local2, always_xy=True).transform
        to_deg2 = pyproj.Transformer.from_crs(proj_local2, proj_latlon, always_xy=True).transform

        line_m2 = LineString([to_m2(lon, lat) for lat, lon in path])
        total_len = line_m2.length

        dense = []
        d = 0
        while d <= total_len:
            x, y = line_m2.interpolate(d).coords[0]
            lon, lat = to_deg2(x, y)
            dense.append((truncate(lat), truncate(lon)))
            d += waypoint_spacing

        path = dense

    return path

def generate_lawnmower_with_5m_spacing(points, spacing=10, buffer_m=2, decimals=7, waypoint_spacing=5):
    def truncate(num):
        factor = 10 ** decimals
        return math.trunc(num * factor) / factor

    poly = Polygon([(lon, lat) for lat, lon in points])
    proj_latlon = pyproj.CRS("EPSG:4326")
    proj_local = pyproj.CRS.from_proj4(
        f"+proj=tmerc +lat_0={poly.centroid.y} +lon_0={poly.centroid.x} +units=m +datum=WGS84"
    )
    to_m = pyproj.Transformer.from_crs(proj_latlon, proj_local, always_xy=True).transform
    to_deg = pyproj.Transformer.from_crs(proj_local, proj_latlon, always_xy=True).transform

    poly_m = transform(to_m, poly)
    poly_inward_m = poly_m.buffer(-buffer_m)
    poly_inward = transform(to_deg, poly_inward_m)
    inward_coords = [(truncate(lat), truncate(lon)) for lon, lat in poly_inward.exterior.coords[:-1]]

    poly_m = transform(to_m, Polygon([(lon, lat) for lat, lon in inward_coords]))
    minx, miny, maxx, maxy = poly_m.bounds

    lines = []
    y = miny
    while y <= maxy:
        lines.append(LineString([(minx, y), (maxx, y)]))
        y += spacing

    path_m = []
    for i, line in enumerate(lines):
        clipped = line.intersection(poly_m)
        if clipped.is_empty:
            continue
        segs = []
        if clipped.geom_type == "LineString":
            segs = [clipped]
        elif clipped.geom_type == "MultiLineString":
            segs = list(clipped.geoms)
        for seg in segs:
            coords = list(seg.coords)
            if i % 2 == 1:
                coords.reverse()
            path_m.extend(coords)

    path_latlon = [transform(to_deg, Point(x, y)) for x, y in path_m]
    path = [(truncate(pt.y), truncate(pt.x)) for pt in path_latlon]

    if len(path) > 1:
        lat0, lon0 = path[0]
        proj_local2 = pyproj.CRS.from_proj4(
            f"+proj=tmerc +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84"
        )
        to_m2 = pyproj.Transformer.from_crs(proj_latlon, proj_local2, always_xy=True).transform
        to_deg2 = pyproj.Transformer.from_crs(proj_local2, proj_latlon, always_xy=True).transform

        line_m2 = LineString([to_m2(lon, lat) for lat, lon in path])
        total_len = line_m2.length

        dense = []
        d = 0
        while d <= total_len:
            x, y = line_m2.interpolate(d).coords[0]
            lon, lat = to_deg2(x, y)
            dense.append((truncate(lat), truncate(lon)))
            d += waypoint_spacing

        path = dense

    # Flip path
    path.reverse()

    return inward_coords, path

print(generate_lawnmower_with_5m_spacing(points))