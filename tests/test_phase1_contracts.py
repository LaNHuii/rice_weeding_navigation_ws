from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path):
    with (ROOT / relative_path).open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_confirmed_vehicle_dimensions_and_provisional_drive_are_explicit():
    platform = load_yaml("profiles/platforms/rice_weeding_prototype.yaml")["platform"]
    dimensions = platform["geometry"]["outer_dimensions"]
    assert dimensions == {
        "verified": True,
        "length": 1.0,
        "width": 1.0,
        "height_from_ground": 0.30,
    }
    assert platform["drive"]["simulation_only"] is True
    assert platform["drive"]["track_width"] == 0.75
    assert platform["geometry"]["body_clearance"]["verified"] is False


def test_navigation_footprint_matches_outer_geometry_plus_declared_margin():
    geometry = load_yaml("profiles/platforms/rice_weeding_prototype.yaml")["platform"]["geometry"]
    margin = geometry["navigation_margin"]["value"]
    expected = [[x + (margin if x > 0 else -margin), y + (margin if y > 0 else -margin)]
                for x, y in geometry["footprint"]]
    assert geometry["navigation_footprint"] == expected


def test_confirmed_crop_grid_and_visual_only_policy():
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    crop_grid = environment["crop_grid"]
    assert crop_grid["row_spacing"] == 0.15
    assert crop_grid["plant_spacing"] == 0.15
    assert crop_grid["collision_policy"] == "visual_only"
    visual_model = crop_grid["visual_model"]
    assert visual_model["verified"] is False
    assert visual_model["simulation_only"] is True
    assert visual_model["footprint_length"] * visual_model["footprint_width"] == 0.0009
    assert 0.15 <= visual_model["height"] <= 0.20
    assert visual_model["color_rgba"][1] > visual_model["color_rgba"][0]
    assert visual_model["color_rgba"][1] > visual_model["color_rgba"][2]
    assert environment["semantic_classes"]["crops_are_navigation_obstacles"] is False
    assert environment["semantic_classes"]["weeds_are_navigation_obstacles"] is False


def test_ros_packages_are_independent_and_discoverable():
    packages = sorted(path.parent.name for path in (ROOT / "src").glob("*/package.xml"))
    assert packages == [
        "rice_weeding_bringup",
        "rice_weeding_description",
        "rice_weeding_navigation",
        "rice_weeding_simulation",
    ]
    for manifest in (ROOT / "src").glob("*/package.xml"):
        text = manifest.read_text(encoding="utf-8")
        assert "agt_navigation_v2" not in text
        assert "/home/" not in text


def test_description_owns_fixed_edges_only():
    xacro = ROOT / "src/rice_weeding_description/urdf/rice_weeding_robot.urdf.xacro"
    root = ET.parse(xacro).getroot()
    joints = root.findall("joint")
    children = [joint.find("child").attrib["link"] for joint in joints]
    assert len(children) == len(set(children))
    assert "map" not in xacro.read_text(encoding="utf-8")
    assert "odom" not in xacro.read_text(encoding="utf-8")


def test_sdf_crop_field_uses_full_width_individual_plant_mesh():
    world = ET.parse(ROOT / "src/rice_weeding_simulation/worlds/paddy_field.sdf").getroot()
    crop = world.find(".//model[@name='crop_field']")
    assert crop is not None
    assert crop.find(".//collision") is None
    assert crop.find(".//mesh/uri").text == "../meshes/paddy_crops.obj"
    mesh = (ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.obj").read_text()
    material = (ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.mtl").read_text()
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    field = environment["field"]
    inner_width = field["boundary_outer_width"] - 2.0 * field["bund"]["thickness"]
    inner_length = field["boundary_outer_length"] - 2.0 * field["bund"]["thickness"]
    visual = environment["crop_grid"]["visual_model"]
    expected_plants = ((int((inner_width - visual["footprint_width"]) / 0.15) + 1) *
                       (int((inner_length - visual["footprint_length"]) / 0.15) + 1))
    assert mesh.count("\nv ") == expected_plants * 8
    assert mesh.count("\nf ") == expected_plants * 6
    assert "mtllib paddy_crops.mtl" in mesh
    assert "usemtl rice_green" in mesh
    assert mesh.count("\nvn ") == 6
    assert "//1" in mesh and "//6" in mesh
    assert "Kd 0.05 0.72 0.08" in material


def test_field_surfaces_and_bunds_form_one_closed_rectangle():
    world = ET.parse(ROOT / "src/rice_weeding_simulation/worlds/paddy_field.sdf").getroot()
    assert world.find(".//model[@name='mud_surface']/link/visual/geometry/box/size").text == "19.700 14.700 0.10"
    assert world.find(".//model[@name='shallow_water_visual']/link/visual/geometry/box/size").text == "19.700 14.700 0.01"
    boundary = world.find(".//model[@name='field_boundary']")
    assert boundary is not None
    assert boundary.find(".//mesh/uri").text == "../meshes/paddy_boundary.obj"
    mesh = (ROOT / "src/rice_weeding_simulation/meshes/paddy_boundary.obj").read_text()
    assert mesh.count("\nv ") == 16
    assert mesh.count("\nf ") == 16
    assert "o paddy_boundary" in mesh
    for name in ("north_bund", "south_bund", "east_bund", "west_bund"):
        model = world.find(f".//model[@name='{name}']")
        assert model.find(".//collision/geometry/box/size") is not None
        assert model.find(".//visual") is None


def test_field_area_is_exactly_halved_and_crops_stay_inside_bunds():
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    field = environment["field"]
    assert field["boundary_outer_length"] * field["boundary_outer_width"] == 300.0
    assert field["boundary_outer_area"] * 2.0 == field["previous_boundary_outer_area"]
    assert field["headland_width"] == 0.0
    assert environment["crop_grid"]["full_inner_coverage"]["enabled"] is True
    assert environment["crop_grid"]["full_inner_coverage"]["motion_compatible"] is False
    vertices = []
    mesh = ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.obj"
    for line in mesh.read_text().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(float(value) for value in line.split()[1:]))
    inner_half_length = (field["boundary_outer_length"] / 2.0 -
                         field["bund"]["thickness"])
    inner_half_width = (field["boundary_outer_width"] / 2.0 -
                        field["bund"]["thickness"])
    assert max(abs(vertex[0]) for vertex in vertices) <= inner_half_length
    assert max(abs(vertex[1]) for vertex in vertices) <= inner_half_width


def test_navigation_contract_is_fail_closed():
    contract = load_yaml(
        "src/rice_weeding_navigation/config/nav2_phase1_contract.yaml"
    )
    assert contract["status"] == "interface_stub"
    assert contract["motion"]["enabled"] is False
    assert contract["crop_policy"]["in_crop_in_place_rotation_allowed"] is False


def test_architecture_changes_have_required_documents():
    required = [
        "AGENTS.md",
        "docs/architecture/overview.md",
        "docs/interfaces/core_topics.md",
        "docs/migration/migration_matrix.md",
    ]
    assert all((ROOT / item).is_file() for item in required)
