"""Build a simulation-only semantic map from the paddy environment profile."""

from .semantic_model import SemanticFeature, SemanticMap


def build_paddy_semantic_map(environment_profile, map_id="paddy_profile_demo"):
    environment = environment_profile["environment"]
    field = environment["field"]
    crop_grid = environment["crop_grid"]
    length = float(field["boundary_outer_length"])
    width = float(field["boundary_outer_width"])
    bund = float(field["bund"]["thickness"])
    headland = float(field["headland_width"])
    row_spacing = float(crop_grid["row_spacing"])

    features = [
        _polygon(
            "field_outer_boundary",
            "field_boundary",
            "Paddy outer boundary",
            [[0.0, 0.0], [length, 0.0], [length, width], [0.0, width], [0.0, 0.0]],
        ),
        _polygon(
            "west_headland",
            "headland_zone",
            "West headland",
            [[bund, bund], [headland + bund, bund], [headland + bund, width - bund], [bund, width - bund], [bund, bund]],
        ),
        _polygon(
            "east_headland",
            "headland_zone",
            "East headland",
            [[length - headland - bund, bund], [length - bund, bund], [length - bund, width - bund], [length - headland - bund, width - bund], [length - headland - bund, bund]],
        ),
        SemanticFeature(
            id="work_direction_lengthwise",
            feature_type="work_direction",
            name="Lengthwise work direction",
            geometry_type="LineString",
            coordinates=[[headland + bund, width * 0.5], [length - headland - bund, width * 0.5]],
        ),
    ]

    x0 = headland + bund
    x1 = length - headland - bund
    y = bund
    row_index = 0
    while y <= width - bund + 1.0e-9:
        features.append(
            SemanticFeature(
                id=f"crop_row_{row_index:03d}",
                feature_type="crop_row",
                name=f"Crop row {row_index:03d}",
                geometry_type="LineString",
                coordinates=[[x0, round(y, 6)], [x1, round(y, 6)]],
                properties={
                    "navigation_obstacle": False,
                    "row_spacing": row_spacing,
                    "simulation_only": True,
                },
            )
        )
        row_index += 1
        y = bund + row_index * row_spacing

    return SemanticMap(
        map_id=map_id,
        frame_id=environment["frame_id"],
        features=features,
    )


def _polygon(feature_id, feature_type, name, ring, properties=None):
    return SemanticFeature(
        id=feature_id,
        feature_type=feature_type,
        name=name,
        geometry_type="Polygon",
        coordinates=[ring],
        properties=properties or {},
    )
