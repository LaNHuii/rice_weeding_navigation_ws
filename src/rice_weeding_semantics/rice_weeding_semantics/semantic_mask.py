"""Pure-data keepout mask generation for rice semantic maps."""

from dataclasses import dataclass
import math
import os
from pathlib import Path
import tempfile

import yaml


MASK_FEATURE_TYPES = {"hard_obstacle", "negative_obstacle", "keepout_zone"}


@dataclass(frozen=True)
class GridGeometry:
    width: int
    height: int
    resolution: float
    origin_x: float = 0.0
    origin_y: float = 0.0
    frame_id: str = "map"

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("grid width and height must be positive")
        if self.resolution <= 0.0:
            raise ValueError("grid resolution must be positive")
        if self.frame_id != "map":
            raise ValueError("semantic mask geometry must use frame_id map")


@dataclass(frozen=True)
class KeepoutMask:
    width: int
    height: int
    resolution: float
    origin_x: float
    origin_y: float
    frame_id: str
    data: tuple
    occupied_count: int


def geometry_from_semantic_bounds(semantic_map, resolution, padding=0.0):
    """Create a map-frame grid large enough to cover all enabled features."""
    if resolution <= 0.0:
        raise ValueError("resolution must be positive")
    if padding < 0.0:
        raise ValueError("padding must be non-negative")

    bounds = _semantic_bounds(semantic_map)
    min_x, min_y, max_x, max_y = bounds
    origin_x = math.floor((min_x - padding) / resolution) * resolution
    origin_y = math.floor((min_y - padding) / resolution) * resolution
    end_x = math.ceil((max_x + padding) / resolution) * resolution
    end_y = math.ceil((max_y + padding) / resolution) * resolution
    width = max(1, int(round((end_x - origin_x) / resolution)))
    height = max(1, int(round((end_y - origin_y) / resolution)))
    return GridGeometry(
        width=width,
        height=height,
        resolution=resolution,
        origin_x=origin_x,
        origin_y=origin_y,
        frame_id=semantic_map.frame_id,
    )


def build_keepout_mask(semantic_map, geometry, free_value=0, occupied_value=100):
    """Return bottom-up row-major mask data without ROS or Nav2 dependencies."""
    _validate_values(free_value, occupied_value)
    occupied = [False] * (geometry.width * geometry.height)
    for feature in semantic_map.features:
        if not feature.enabled or feature.feature_type not in MASK_FEATURE_TYPES:
            continue
        if feature.geometry_type != "Polygon" or not feature.coordinates:
            continue
        _rasterize_polygon(feature.coordinates[0], geometry, occupied)
    data = tuple(occupied_value if value else free_value for value in occupied)
    return KeepoutMask(
        width=geometry.width,
        height=geometry.height,
        resolution=geometry.resolution,
        origin_x=geometry.origin_x,
        origin_y=geometry.origin_y,
        frame_id=geometry.frame_id,
        data=data,
        occupied_count=sum(1 for value in data if value == occupied_value),
    )


def save_keepout_mask_files(mask, yaml_path, image_path=None):
    """Save a pure-data keepout mask as a small PGM image plus YAML metadata."""
    yaml_path = Path(yaml_path)
    if image_path is None:
        image_path = yaml_path.with_suffix(".pgm")
    image_path = Path(image_path)
    _write_pgm(mask, image_path)
    metadata = {
        "image": image_path.name,
        "resolution": mask.resolution,
        "origin": [mask.origin_x, mask.origin_y, 0.0],
        "frame_id": mask.frame_id,
        "width": mask.width,
        "height": mask.height,
        "occupied_count": mask.occupied_count,
        "free_value": 0,
        "occupied_value": 100,
        "mode": "trinary",
        "simulation_only": True,
        "verified": False,
        "source": "rice_weeding_semantics semantic keepout mask contract",
        "mask_sources": sorted(MASK_FEATURE_TYPES),
        "excluded_default_semantics": ["crop_row", "weed_patch"],
        "data_order": "bottom_up_row_major",
    }
    _atomic_write_text(yaml_path, yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True))


def _semantic_bounds(semantic_map):
    points = []
    for feature in semantic_map.features:
        if not feature.enabled:
            continue
        points.extend(_feature_points(feature))
    if not points:
        raise ValueError("semantic map has no enabled geometry")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _feature_points(feature):
    if feature.geometry_type == "LineString":
        return list(feature.coordinates)
    if feature.geometry_type == "Polygon" and feature.coordinates:
        return list(feature.coordinates[0])
    return []


def _rasterize_polygon(ring, geometry, occupied):
    if len(ring) < 4:
        return
    min_x = min(point[0] for point in ring)
    max_x = max(point[0] for point in ring)
    min_y = min(point[1] for point in ring)
    max_y = max(point[1] for point in ring)
    min_grid_x = max(0, math.floor((min_x - geometry.origin_x) / geometry.resolution))
    max_grid_x = min(geometry.width - 1, math.floor((max_x - geometry.origin_x) / geometry.resolution))
    min_grid_y = max(0, math.floor((min_y - geometry.origin_y) / geometry.resolution))
    max_grid_y = min(geometry.height - 1, math.floor((max_y - geometry.origin_y) / geometry.resolution))
    for grid_y in range(min_grid_y, max_grid_y + 1):
        world_y = geometry.origin_y + (grid_y + 0.5) * geometry.resolution
        for grid_x in range(min_grid_x, max_grid_x + 1):
            world_x = geometry.origin_x + (grid_x + 0.5) * geometry.resolution
            if _point_in_polygon(world_x, world_y, ring):
                occupied[grid_y * geometry.width + grid_x] = True


def _point_in_polygon(x, y, ring):
    inside = False
    previous = ring[-1]
    for current in ring:
        xi, yi = current
        xj, yj = previous
        crosses = (yi > y) != (yj > y)
        if crosses:
            intersection_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < intersection_x:
                inside = not inside
        previous = current
    return inside


def _validate_values(free_value, occupied_value):
    for name, value in (("free_value", free_value), ("occupied_value", occupied_value)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100")
    if free_value == occupied_value:
        raise ValueError("free and occupied mask values must differ")


def _write_pgm(mask, path):
    rows = ["P2", f"{mask.width} {mask.height}", "100"]
    for grid_y in range(mask.height - 1, -1, -1):
        row = mask.data[grid_y * mask.width:(grid_y + 1) * mask.width]
        rows.append(" ".join(str(value) for value in row))
    _atomic_write_text(Path(path), "\n".join(rows) + "\n")


def _atomic_write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
