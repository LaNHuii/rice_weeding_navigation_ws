"""Phase 4 rice-field semantic map validation."""

from dataclasses import dataclass, field
import math
import re


FEATURE_GEOMETRY = {
    "field_boundary": "Polygon",
    "crop_row": "LineString",
    "weed_patch": "Polygon",
    "hard_obstacle": "Polygon",
    "negative_obstacle": "Polygon",
    "headland_zone": "Polygon",
    "keepout_zone": "Polygon",
    "work_direction": "LineString",
}
REQUIRED_FEATURE_COUNTS = {
    "field_boundary": 1,
    "headland_zone": 1,
    "work_direction": 1,
}
FEATURE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
GEOMETRY_EPSILON = 1.0e-9


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "ERROR"
    object_id: str = "<document>"


@dataclass
class ValidationReport:
    issues: list = field(default_factory=list)

    @property
    def valid(self):
        return not any(issue.severity == "ERROR" for issue in self.issues)

    def add(self, code, message, object_id="<document>", severity="ERROR"):
        self.issues.append(
            ValidationIssue(code, message, severity=severity, object_id=object_id)
        )


def validate_semantic_map(semantic_map):
    report = ValidationReport()
    if semantic_map.schema_version != "1.0":
        report.add(
            "unsupported_schema_version",
            f"unsupported schema version: {semantic_map.schema_version}",
        )
    if semantic_map.frame_id != "map":
        report.add("invalid_frame", "semantic map frame_id must be map")
    if not semantic_map.map_id:
        report.add("missing_map_id", "semantic map map_id is required")

    seen_ids = set()
    enabled_counts = {feature_type: 0 for feature_type in FEATURE_GEOMETRY}
    for feature in semantic_map.features:
        _validate_feature(feature, seen_ids, enabled_counts, report)

    for feature_type, minimum_count in REQUIRED_FEATURE_COUNTS.items():
        if enabled_counts[feature_type] < minimum_count:
            report.add(
                "missing_feature_type",
                f"at least {minimum_count} enabled {feature_type} is required",
                feature_type,
            )
    return report


def _validate_feature(feature, seen_ids, enabled_counts, report):
    object_id = feature.id or "<missing>"
    if feature.id in seen_ids:
        report.add("duplicate_feature_id", f"duplicate feature id: {feature.id}", object_id)
    seen_ids.add(feature.id)
    if not FEATURE_ID.fullmatch(feature.id):
        report.add("invalid_feature_id", "feature id must use lowercase snake_case", object_id)
    if feature.frame_id != "map":
        report.add("invalid_feature_frame", "feature frame_id must be map", object_id)
    if not isinstance(feature.enabled, bool):
        report.add("invalid_enabled", "feature enabled must be boolean", object_id)

    expected_geometry = FEATURE_GEOMETRY.get(feature.feature_type)
    if expected_geometry is None:
        report.add("unknown_feature_type", f"unknown feature type: {feature.feature_type}", object_id)
        return
    if feature.enabled:
        enabled_counts[feature.feature_type] += 1
    if feature.geometry_type != expected_geometry:
        report.add(
            "invalid_geometry_type",
            f"{feature.feature_type} requires {expected_geometry}",
            object_id,
        )
        return
    _validate_geometry(feature, report)
    _validate_semantic_policy(feature, report)


def _validate_geometry(feature, report):
    object_id = feature.id or "<missing>"
    coordinates = feature.coordinates
    if feature.geometry_type == "LineString":
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            report.add("line_too_short", "LineString requires at least two points", object_id)
            return
        if not all(_is_point(point) for point in coordinates):
            report.add("invalid_line_coordinate", "LineString coordinates must be finite points", object_id)
            return
        if _line_length(coordinates) <= GEOMETRY_EPSILON:
            report.add("zero_length_line", "LineString length must be positive", object_id)
    elif feature.geometry_type == "Polygon":
        if not isinstance(coordinates, list) or not coordinates:
            report.add("invalid_polygon", "Polygon requires an outer ring", object_id)
            return
        ring = coordinates[0]
        if not isinstance(ring, list) or not all(_is_point(point) for point in ring):
            report.add("invalid_polygon_coordinate", "Polygon ring must contain finite points", object_id)
            return
        if len(ring) < 4 or ring[0] != ring[-1]:
            report.add("polygon_not_closed", "Polygon ring must be closed", object_id)
        vertices = ring[:-1] if ring and ring[0] == ring[-1] else ring
        if len({tuple(point) for point in vertices}) < 3:
            report.add("polygon_too_small", "Polygon requires at least three unique vertices", object_id)
        if _polygon_area(vertices) <= GEOMETRY_EPSILON:
            report.add("zero_area_polygon", "Polygon area must be positive", object_id)


def _validate_semantic_policy(feature, report):
    object_id = feature.id or "<missing>"
    if feature.feature_type == "crop_row":
        if feature.properties.get("navigation_obstacle", False) is True:
            report.add(
                "crop_row_as_obstacle",
                "crop rows are protected crop semantics, not default obstacles",
                object_id,
            )
    if feature.feature_type == "weed_patch":
        if feature.properties.get("navigation_obstacle", False) is True:
            report.add(
                "weed_as_obstacle",
                "weeds are work targets, not default navigation obstacles",
                object_id,
            )
    if feature.feature_type in {"hard_obstacle", "negative_obstacle", "keepout_zone"}:
        if feature.properties.get("safety_layer", "") == "":
            report.add(
                "missing_safety_layer",
                f"{feature.feature_type} must declare a safety_layer",
                object_id,
            )


def _is_point(value):
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(number, (int, float)) and math.isfinite(number) for number in value)
    )


def _line_length(points):
    return sum(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(points, points[1:])
    )


def _polygon_area(vertices):
    if len(vertices) < 3:
        return 0.0
    total = 0.0
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        total += a[0] * b[1] - b[0] * a[1]
    return abs(total) * 0.5
