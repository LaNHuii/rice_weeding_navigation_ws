from pathlib import Path
import sys
import subprocess
import os

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/rice_weeding_semantics/rice_weeding_semantics"
sys.path.insert(0, str(ROOT / "src/rice_weeding_semantics"))

from rice_weeding_semantics import semantic_io as IO
from rice_weeding_semantics import semantic_model as MODEL
from rice_weeding_semantics import profile_semantic_builder as BUILDER
from rice_weeding_semantics import semantic_mask as MASK
from rice_weeding_semantics import semantic_validation as VALIDATION


def load_yaml(relative_path):
    with (ROOT / relative_path).open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_phase4_semantics_package_keeps_preview_read_only():
    manifest = (ROOT / "src/rice_weeding_semantics/package.xml").read_text()
    cmake = (ROOT / "src/rice_weeding_semantics/CMakeLists.txt").read_text()
    readme = (ROOT / "src/rice_weeding_semantics/README.md").read_text()
    preview = (
        ROOT / "src/rice_weeding_semantics/scripts/semantic_marker_preview.py"
    ).read_text()
    schema = load_yaml("src/rice_weeding_semantics/config/rice_semantic_schema.yaml")

    assert "<name>rice_weeding_semantics</name>" in manifest
    assert "rclpy" in manifest
    assert "visualization_msgs" in manifest
    assert "geometry_msgs" in manifest
    assert "nav_msgs" in manifest
    assert "python3-pyqt5" not in manifest
    assert "install(DIRECTORY" in cmake
    assert schema["reference"]["direct_tool_migration"] is False
    assert "standalone, plug-in-like modules only" in readme
    assert "generate_profile_semantic_map.py" in cmake
    assert "generate_keepout_mask.py" in cmake
    assert "semantic_keepout_mask_publisher.py" in cmake
    assert "semantic_marker_preview.py" in cmake
    assert "/rice_weeding/semantics/markers" in preview
    assert "MarkerArray" in preview
    assert "TRANSIENT_LOCAL" in preview
    assert "load_semantic_map" in preview
    assert "create_subscription" not in preview
    assert "TransformBroadcaster" not in preview
    assert "Odometry" not in preview
    assert "Twist" not in preview
    assert "OccupancyGrid" not in preview
    assert "/rice_weeding/semantics/keepout_mask" not in preview
    mask_generator = (
        ROOT / "src/rice_weeding_semantics/scripts/generate_keepout_mask.py"
    ).read_text()
    assert "OccupancyGrid" not in mask_generator
    assert "rclpy" not in mask_generator
    assert "semantic_map server" not in mask_generator
    mask_publisher = (
        ROOT / "src/rice_weeding_semantics/scripts/semantic_keepout_mask_publisher.py"
    ).read_text()
    assert "/rice_weeding/semantics/keepout_mask" in mask_publisher
    assert "OccupancyGrid" in mask_publisher
    assert "TRANSIENT_LOCAL" in mask_publisher
    assert "--acknowledge-simulation-only" in mask_publisher
    assert "build_keepout_mask" in mask_publisher
    assert "crop_row and weed_patch are excluded" in mask_publisher
    assert "TransformBroadcaster" not in mask_publisher
    assert "Odometry" not in mask_publisher
    assert "Twist" not in mask_publisher
    assert "NavigateToPose" not in mask_publisher


def test_phase4_schema_keeps_crop_and_weed_out_of_default_obstacles():
    schema = load_yaml("src/rice_weeding_semantics/config/rice_semantic_schema.yaml")
    feature_types = schema["feature_types"]
    assert set(feature_types) == {
        "field_boundary",
        "crop_row",
        "weed_patch",
        "hard_obstacle",
        "negative_obstacle",
        "headland_zone",
        "keepout_zone",
        "work_direction",
    }
    assert feature_types["crop_row"]["navigation_obstacle_default"] is False
    assert feature_types["weed_patch"]["navigation_obstacle_default"] is False
    assert "hard_obstacle" in schema["policies"]["keepout_mask_sources"]
    assert "negative_obstacle" in schema["policies"]["keepout_mask_sources"]
    assert "keepout_zone" in schema["policies"]["keepout_mask_sources"]
    assert "crop_row" not in schema["policies"]["keepout_mask_sources"]
    assert "weed_patch" not in schema["policies"]["keepout_mask_sources"]


def test_phase4_example_semantic_map_validates():
    semantic_map = IO.load_semantic_map(
        ROOT / "src/rice_weeding_semantics/examples/paddy_demo/semantic_map.geojson"
    )
    report = VALIDATION.validate_semantic_map(semantic_map)
    assert report.valid
    feature_types = {feature.feature_type for feature in semantic_map.features}
    assert "crop_row" in feature_types
    assert "weed_patch" in feature_types
    assert "hard_obstacle" in feature_types
    crop = next(feature for feature in semantic_map.features if feature.feature_type == "crop_row")
    weed = next(feature for feature in semantic_map.features if feature.feature_type == "weed_patch")
    assert crop.properties["navigation_obstacle"] is False
    assert weed.properties["navigation_obstacle"] is False


def test_phase4_profile_builder_consumes_environment_profile():
    environment_profile = load_yaml("profiles/environments/paddy_field.yaml")
    semantic_map = BUILDER.build_paddy_semantic_map(environment_profile)
    report = VALIDATION.validate_semantic_map(semantic_map)
    assert report.valid

    environment = environment_profile["environment"]
    field = environment["field"]
    bund = field["bund"]["thickness"]
    headland = field["headland_width"]
    length = field["boundary_outer_length"]
    width = field["boundary_outer_width"]
    row_spacing = environment["crop_grid"]["row_spacing"]
    expected_rows = int(round((width - 2.0 * bund) / row_spacing)) + 1

    features = {feature.id: feature for feature in semantic_map.features}
    assert features["field_outer_boundary"].coordinates[0] == [
        [0.0, 0.0], [length, 0.0], [length, width], [0.0, width], [0.0, 0.0]
    ]
    assert features["west_headland"].coordinates[0][1][0] == headland + bund
    assert features["east_headland"].coordinates[0][0][0] == length - headland - bund
    crop_rows = [
        feature for feature in semantic_map.features
        if feature.feature_type == "crop_row"
    ]
    assert len(crop_rows) == expected_rows
    assert crop_rows[0].coordinates == [[headland + bund, bund], [length - headland - bund, bund]]
    assert crop_rows[0].properties["simulation_only"] is True
    assert crop_rows[0].properties["navigation_obstacle"] is False


def test_phase4_profile_generator_writes_valid_geojson(tmp_path):
    output_path = tmp_path / "generated_semantic_map.geojson"
    script = ROOT / "src/rice_weeding_semantics/scripts/generate_profile_semantic_map.py"
    text = script.read_text()
    assert "/home/" not in text
    assert "paddy_field.yaml" in text
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--environment-profile",
            str(ROOT / "profiles/environments/paddy_field.yaml"),
            "--output",
            str(output_path),
            "--map-id",
            "generated_test",
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT / "src/rice_weeding_semantics"),
        },
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    semantic_map = IO.load_semantic_map(output_path)
    assert semantic_map.map_id == "generated_test"
    assert VALIDATION.validate_semantic_map(semantic_map).valid


def test_phase4_validation_rejects_bad_semantics():
    bad_crop = MODEL.SemanticMap(
        map_id="bad",
        features=[
            MODEL.SemanticFeature(
                id="field",
                feature_type="field_boundary",
                name="field",
                geometry_type="Polygon",
                coordinates=[[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]],
            ),
            MODEL.SemanticFeature(
                id="headland",
                feature_type="headland_zone",
                name="headland",
                geometry_type="Polygon",
                coordinates=[[[0.0, 0.0], [1.0, 0.0], [1.0, 0.5], [0.0, 0.0]]],
            ),
            MODEL.SemanticFeature(
                id="direction",
                feature_type="work_direction",
                name="direction",
                geometry_type="LineString",
                coordinates=[[0.0, 0.0], [1.0, 0.0]],
            ),
            MODEL.SemanticFeature(
                id="crop",
                feature_type="crop_row",
                name="crop",
                geometry_type="LineString",
                coordinates=[[0.0, 0.2], [1.0, 0.2]],
                properties={"navigation_obstacle": True},
            ),
            MODEL.SemanticFeature(
                id="stone",
                feature_type="hard_obstacle",
                name="stone",
                geometry_type="Polygon",
                coordinates=[[[0.2, 0.2], [0.3, 0.2], [0.3, 0.3], [0.2, 0.2]]],
            ),
        ],
    )

    report = VALIDATION.validate_semantic_map(bad_crop)
    codes = {issue.code for issue in report.issues}
    assert "crop_row_as_obstacle" in codes
    assert "missing_safety_layer" in codes
    assert not report.valid


def test_phase4_keepout_mask_uses_only_safety_semantics():
    semantic_map = IO.load_semantic_map(
        ROOT / "src/rice_weeding_semantics/examples/paddy_demo/semantic_map.geojson"
    )
    geometry = MASK.GridGeometry(width=200, height=150, resolution=0.1)
    mask = MASK.build_keepout_mask(semantic_map, geometry)

    assert mask.width == 200
    assert mask.height == 150
    assert mask.frame_id == "map"
    assert isinstance(mask.data, tuple)
    assert mask.occupied_count > 0

    # Sample crop row and weed patch cells stay free; the hard obstacle cell is occupied.
    crop_index = 30 * geometry.width + 100
    weed_index = 62 * geometry.width + 82
    stone_index = 82 * geometry.width + 122
    assert mask.data[crop_index] == 0
    assert mask.data[weed_index] == 0
    assert mask.data[stone_index] == 100


def test_phase4_keepout_mask_geometry_can_derive_from_semantic_bounds():
    semantic_map = IO.load_semantic_map(
        ROOT / "src/rice_weeding_semantics/examples/paddy_demo/semantic_map.geojson"
    )
    geometry = MASK.geometry_from_semantic_bounds(semantic_map, resolution=0.1)
    assert geometry.width == 200
    assert geometry.height == 150
    assert geometry.origin_x == 0.0
    assert geometry.origin_y == 0.0
    assert geometry.frame_id == "map"


def test_phase4_keepout_mask_generator_writes_simulation_only_artifacts(tmp_path):
    semantic_map_path = ROOT / "src/rice_weeding_semantics/examples/paddy_demo/semantic_map.geojson"
    output_yaml = tmp_path / "keepout_mask.yaml"
    script = ROOT / "src/rice_weeding_semantics/scripts/generate_keepout_mask.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--semantic-map",
            str(semantic_map_path),
            "--output-yaml",
            str(output_yaml),
            "--resolution",
            "0.1",
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT / "src/rice_weeding_semantics"),
        },
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    output_pgm = output_yaml.with_suffix(".pgm")
    metadata = yaml.safe_load(output_yaml.read_text(encoding="utf-8"))
    pgm_text = output_pgm.read_text(encoding="utf-8")

    assert metadata["image"] == "keepout_mask.pgm"
    assert metadata["width"] == 200
    assert metadata["height"] == 150
    assert metadata["resolution"] == 0.1
    assert metadata["simulation_only"] is True
    assert metadata["verified"] is False
    assert "crop_row" in metadata["excluded_default_semantics"]
    assert "weed_patch" in metadata["excluded_default_semantics"]
    assert pgm_text.startswith("P2\n200 150\n100\n")
