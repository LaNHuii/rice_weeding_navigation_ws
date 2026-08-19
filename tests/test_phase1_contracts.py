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
    assert platform["drive"]["wheel_mass"] == 1.0
    assert platform["drive"]["wheel_inertia_model"] == "solid_cylinder_substitute"
    assert platform["drive"]["joint_damping"] > 0.0
    assert platform["drive"]["zero_command_test_duration"] == 10.0
    assert platform["drive"]["zero_command_position_tolerance"] == 0.002
    assert platform["drive"]["zero_command_yaw_tolerance"] == 0.002
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
    assert crop_grid["row_spacing"] == 0.30
    assert crop_grid["plant_spacing"] == 0.30
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
        "rice_weeding_safety",
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
    link_names = {link.attrib["name"] for link in root.findall("link")}
    assert len(children) == len(set(children))
    assert "map" not in link_names
    assert "odom" not in link_names
    assert all(joint.find("parent").attrib["link"] not in {"map", "odom"}
               for joint in joints)
    assert all(child not in {"map", "odom"} for child in children)


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
    crop_grid = environment["crop_grid"]
    inner_width = field["boundary_outer_width"] - 2.0 * field["bund"]["thickness"]
    inner_length = field["boundary_outer_length"] - 2.0 * field["bund"]["thickness"]
    visual = crop_grid["visual_model"]
    headland = field["headland_width"]
    expected_plants = ((int((inner_width - visual["footprint_width"]) / crop_grid["row_spacing"]) + 1) *
                       (int((inner_length - 2.0 * headland - visual["footprint_length"]) /
                            crop_grid["plant_spacing"]) + 1))
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


def test_field_area_is_exactly_halved_and_crops_leave_motion_headlands():
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    field = environment["field"]
    assert field["boundary_outer_length"] * field["boundary_outer_width"] == 300.0
    assert field["boundary_outer_area"] * 2.0 == field["previous_boundary_outer_area"]
    platform = load_yaml("profiles/platforms/rice_weeding_prototype.yaml")["platform"]
    assert field["headland_width"] >= platform["coverage"]["required_headland_width"]
    assert field["headland_axis"] == "field_length_ends"
    assert environment["crop_grid"]["full_inner_coverage"]["enabled"] is False
    assert environment["crop_grid"]["full_inner_coverage"]["motion_compatible"] is True
    vertices = []
    mesh = ROOT / "src/rice_weeding_simulation/meshes/paddy_crops.obj"
    for line in mesh.read_text().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(float(value) for value in line.split()[1:]))
    inner_half_length = (field["boundary_outer_length"] / 2.0 -
                         field["bund"]["thickness"])
    inner_half_width = (field["boundary_outer_width"] / 2.0 -
                        field["bund"]["thickness"])
    assert inner_half_length - max(abs(vertex[0]) for vertex in vertices) >= field["headland_width"]
    assert max(abs(vertex[1]) for vertex in vertices) <= inner_half_width


def test_navigation_contract_is_fail_closed():
    contract = load_yaml(
        "src/rice_weeding_navigation/config/nav2_phase1_contract.yaml"
    )
    assert contract["status"] == "interface_stub"
    assert contract["motion"]["enabled"] is False
    assert contract["safety"]["gate_package"] == "rice_weeding_safety"
    assert contract["safety"]["startup_motion_enabled"] is False
    assert contract["safety"]["output_connected_to_chassis"] is True
    assert contract["safety"]["watchdog_clock"] == "monotonic_wall"
    assert contract["crop_policy"]["in_crop_in_place_rotation_allowed"] is False


def test_phase2_nav2_uses_profile_map_and_safety_boundary_only():
    config = load_yaml("src/rice_weeding_navigation/config/nav2_phase2.yaml")
    controller = config["controller_server"]["ros__parameters"]
    smoother = config["smoother_server"]["ros__parameters"]
    waypoint = config["waypoint_follower"]["ros__parameters"]
    local_costmap = config["local_costmap"]["local_costmap"]["ros__parameters"]
    global_costmap = config["global_costmap"]["global_costmap"]["ros__parameters"]
    map_publisher = (
        ROOT / "src/rice_weeding_navigation/scripts/paddy_navigation_map.py"
    ).read_text()
    adapter = (
        ROOT / "src/rice_weeding_navigation/scripts/nav2_command_adapter.py"
    ).read_text()
    nav_launch = (
        ROOT / "src/rice_weeding_navigation/launch/phase2_navigation.launch.py"
    ).read_text()
    combined_launch = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_nav2_simulation.launch.py"
    ).read_text()
    tree = (
        ROOT / "src/rice_weeding_navigation/behavior_trees/navigate_to_pose_forward_only.xml"
    ).read_text()
    through_poses_tree = (
        ROOT
        / "src/rice_weeding_navigation/behavior_trees/navigate_through_poses_forward_only.xml"
    ).read_text()

    assert global_costmap["plugins"] == [
        "static_layer", "inflation_layer"
    ]
    assert local_costmap["plugins"] == [
        "static_layer", "inflation_layer"
    ]
    assert controller["FollowPath"]["use_rotate_to_heading"] is False
    assert controller["FollowPath"]["allow_reversing"] is False
    assert smoother["smoother_plugins"] == ["simple_smoother"]
    assert smoother["simple_smoother"]["plugin"] == "nav2_smoother::SimpleSmoother"
    assert waypoint["waypoint_task_executor_plugin"] == "wait_at_waypoint"
    assert "__PLATFORM_NAVIGATION_FOOTPRINT__" in global_costmap["footprint"]
    assert "__PLATFORM_NAVIGATION_FOOTPRINT__" in local_costmap["footprint"]
    assert isinstance(global_costmap["footprint"], str)
    assert isinstance(local_costmap["footprint"], str)
    assert isinstance(local_costmap["width"], int)
    assert isinstance(local_costmap["height"], int)
    assert local_costmap["inflation_layer"]["inflation_radius"] >= 0.52
    assert global_costmap["inflation_layer"]["inflation_radius"] >= 0.52
    assert "crops_are_navigation_obstacles" in map_publisher
    assert "bund_thickness" in map_publisher
    assert '"/map"' in map_publisher
    assert '"/cmd_vel"' in adapter
    assert '"/rice_weeding/navigation/cmd_vel_raw"' in adapter
    assert '"/rice_weeding/safety/cmd_vel"' not in adapter
    assert "ros_gz" not in adapter
    assert "navigation_footprint" in nav_launch
    assert "phase2_simulation.launch.py" in combined_launch
    assert "phase2_navigation.launch.py" in combined_launch
    assert "__PHASE2_THROUGH_POSES_BT_XML__" in config["bt_navigator"]["ros__parameters"]["default_nav_through_poses_bt_xml"]
    assert "NamedTemporaryFile" in nav_launch
    assert "Spin" not in tree and "BackUp" not in tree
    assert "Spin" not in through_poses_tree and "BackUp" not in through_poses_tree


def test_architecture_changes_have_required_documents():
    required = [
        "AGENTS.md",
        "docs/architecture/overview.md",
        "docs/interfaces/core_topics.md",
        "docs/migration/migration_matrix.md",
    ]
    assert all((ROOT / item).is_file() for item in required)


def test_phase2_spawn_gate_is_separate_and_fail_closed():
    phase1 = (ROOT / "src/rice_weeding_bringup/launch/phase1_simulation.launch.py").read_text()
    phase2 = (ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py").read_text()
    assert "ros_gz_sim" not in phase1
    assert 'executable="create"' in phase2
    assert '"-topic", "robot_description"' in phase2
    assert 'DeclareLaunchArgument("motion_enabled", default_value="false")' in phase2
    assert "Motion requires the platform-profile minimum headland width" in phase2


def test_phase2_spawn_pose_is_explicitly_simulation_only():
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    pose = environment["simulation_spawn_pose"]
    assert pose["verified"] is False
    assert pose["simulation_only"] is True
    assert pose["frame_id"] == "gazebo_world"
    assert pose["x"] == 8.50
    assert environment["terrain"]["surface_elevation"] == 0.05


def test_map_origin_is_the_user_selected_southwest_outer_corner():
    environment = load_yaml("profiles/environments/paddy_field.yaml")["environment"]
    origin = environment["map_origin"]
    assert origin["verified"] is True
    assert origin["reference"] == "southwest_outer_boundary_corner"
    assert origin["x_axis"] == "boundary_length_positive"
    assert origin["y_axis"] == "boundary_width_positive"
    field = environment["field"]
    assert field["boundary_outer_length"] / 2.0 == 10.0
    assert field["boundary_outer_width"] / 2.0 == 7.5


def test_phase2_truth_pose_bridge_and_adapter_are_simulation_scoped():
    bridge = load_yaml("src/rice_weeding_simulation/config/bridge.yaml")
    pose_bridge = next(
        item for item in bridge
        if item["ros_topic_name"] == "/rice_weeding/simulation/pose_info"
    )
    assert pose_bridge["gz_topic_name"] == "/world/paddy_field/dynamic_pose/info"
    assert pose_bridge["ros_type_name"] == "tf2_msgs/msg/TFMessage"
    assert pose_bridge["direction"] == "GZ_TO_ROS"

    phase1 = (
        ROOT / "src/rice_weeding_bringup/launch/phase1_simulation.launch.py"
    ).read_text()
    phase2 = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py"
    ).read_text()
    assert "simulation_truth_adapter.py" not in phase1
    assert "simulation_truth_adapter.py" in phase2


def test_truth_adapter_does_not_claim_chassis_odometry_edge():
    adapter = (
        ROOT / "src/rice_weeding_simulation/scripts/simulation_truth_adapter.py"
    ).read_text()
    assert '"ground_truth_topic"' in adapter
    assert '"/rice_weeding/simulation/ground_truth"' in adapter
    assert '"map_frame", "map"' in adapter
    assert '"odom_frame", "odom"' in adapter
    assert '"base_frame", "base_footprint"' in adapter
    assert '"world_to_map_x", 0.0' in adapter
    assert '"world_to_map_y", 0.0' in adapter
    assert "self.get_clock().now().to_msg()" in adapter
    assert "if rclpy.ok():" in adapter
    assert "/rice_weeding/localization/odometry" not in adapter
    assert "from tf2_ros import TransformBroadcaster" not in adapter
    assert "StaticTransformBroadcaster(" in adapter

    phase2 = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py"
    ).read_text()
    assert '0.5 * field["boundary_outer_length"]' in phase2
    assert '0.5 * field["boundary_outer_width"]' in phase2


def test_phase2_chassis_odometry_owns_only_its_declared_edge():
    chassis = (
        ROOT / "src/rice_weeding_simulation/scripts/simulation_chassis_odometry.py"
    ).read_text()
    truth = (
        ROOT / "src/rice_weeding_simulation/scripts/simulation_truth_adapter.py"
    ).read_text()
    phase2 = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py"
    ).read_text()

    assert '"/rice_weeding/localization/odometry"' in chassis
    assert '"odom_frame", "odom"' in chassis
    assert '"base_frame", "base_footprint"' in chassis
    assert "from tf2_ros import TransformBroadcaster" in chassis
    assert "StaticTransformBroadcaster" not in chassis
    assert '"motion_enabled", False' in chassis
    assert "self.motion_enabled" in chassis
    assert "odometry.twist.twist.linear.x" in chassis
    assert "odometry.twist.twist.angular.z" in chassis
    assert "/rice_weeding/localization/odometry" not in truth
    assert "simulation_chassis_odometry.py" in phase2
    assert "ParameterValue(" in phase2


def test_phase2_diff_drive_substitute_stays_behind_locked_internal_topics():
    xacro = (
        ROOT / "src/rice_weeding_description/urdf/rice_weeding_robot.urdf.xacro"
    ).read_text()
    bridge = load_yaml("src/rice_weeding_simulation/config/bridge.yaml")
    paddy_launch = (
        ROOT / "src/rice_weeding_simulation/launch/paddy_world.launch.py"
    ).read_text()
    phase2 = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py"
    ).read_text()

    assert xacro.count('type="continuous"') == 1  # one macro expands to all four wheels
    assert '<axis xyz="0 1 0"/>' in xacro
    assert xacro.count("<left_joint>") == 2
    assert xacro.count("<right_joint>") == 2
    assert "JointStatePublisher" in xacro
    assert "DiffDrive" in xacro
    assert "/rice_weeding/simulation/internal/locked_cmd_vel" in xacro
    assert "/rice_weeding/simulation/internal/diff_drive_odometry" in xacro

    joint_state_bridge = next(
        item for item in bridge if item["ros_topic_name"] == "/joint_states"
    )
    assert joint_state_bridge["ros_type_name"] == "sensor_msgs/msg/JointState"
    assert joint_state_bridge["gz_type_name"] == "gz.msgs.Model"
    assert joint_state_bridge["direction"] == "GZ_TO_ROS"
    assert all("diff_drive_odometry" not in item["gz_topic_name"] for item in bridge)
    safe_bridge = next(
        item for item in bridge
        if item["ros_topic_name"] == "/rice_weeding/safety/cmd_vel"
    )
    assert safe_bridge["gz_topic_name"] == "/rice_weeding/simulation/internal/locked_cmd_vel"
    assert safe_bridge["ros_type_name"] == "geometry_msgs/msg/Twist"
    assert safe_bridge["direction"] == "ROS_TO_GZ"
    assert all(item["ros_topic_name"] != "/rice_weeding/navigation/cmd_vel_raw" for item in bridge)
    assert 'DeclareLaunchArgument("headless", default_value="false")' in paddy_launch
    assert 'DeclareLaunchArgument("headless", default_value="false")' in phase2


def test_velocity_safety_gate_is_profile_driven_and_disconnected_from_gazebo():
    platform = load_yaml("profiles/platforms/rice_weeding_prototype.yaml")["platform"]
    safety = platform["safety"]
    launch = (
        ROOT / "src/rice_weeding_safety/launch/safety_gate.launch.py"
    ).read_text()
    gate = (
        ROOT / "src/rice_weeding_safety/scripts/velocity_safety_gate.py"
    ).read_text()
    phase2 = (
        ROOT / "src/rice_weeding_bringup/launch/phase2_simulation.launch.py"
    ).read_text()
    bridge = load_yaml("src/rice_weeding_simulation/config/bridge.yaml")

    assert safety["verified"] is False
    assert safety["simulation_only"] is True
    assert safety["startup_motion_enabled"] is False
    assert safety["command_timeout"] == 0.5
    assert "platform[\"limits\"]" in launch
    assert 'DeclareLaunchArgument("startup_motion_enabled", default_value="false")' in launch
    assert '"/rice_weeding/navigation/cmd_vel_raw"' in gate
    assert '"/rice_weeding/safety/cmd_vel"' in gate
    assert "time.monotonic()" in gate
    assert '"startup_motion_enabled": LaunchConfiguration("motion_enabled")' in phase2
    safe_bridge = next(item for item in bridge if item["ros_topic_name"] == "/rice_weeding/safety/cmd_vel")
    assert safe_bridge["direction"] == "ROS_TO_GZ"
