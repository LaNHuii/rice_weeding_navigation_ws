"""Bring up the profile-derived map and the minimal Phase 2 Nav2 stack."""

from pathlib import Path
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def _configured_nav2(context):
    del context
    navigation_share = Path(get_package_share_directory("rice_weeding_navigation"))
    description_share = Path(get_package_share_directory("rice_weeding_description"))
    template_path = navigation_share / "config/nav2_phase2.yaml"
    template = template_path.read_text(encoding="utf-8")
    with (description_share / "profiles/platforms/rice_weeding_prototype.yaml").open(
        "r", encoding="utf-8"
    ) as stream:
        footprint = yaml.safe_load(stream)["platform"]["geometry"][
            "navigation_footprint"
        ]
    footprint_text = yaml.safe_dump(footprint, default_flow_style=True).strip()
    bt_tree = navigation_share / "behavior_trees/navigate_to_pose_forward_only.xml"
    through_poses_bt_tree = (
        navigation_share
        / "behavior_trees/navigate_through_poses_forward_only.xml"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="rice_weeding_nav2_pose_", suffix=".xml", delete=False,
        encoding="utf-8"
    ) as stream:
        stream.write(bt_tree.read_text(encoding="utf-8"))
        runtime_bt_tree = stream.name
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="rice_weeding_nav2_through_", suffix=".xml", delete=False,
        encoding="utf-8"
    ) as stream:
        stream.write(through_poses_bt_tree.read_text(encoding="utf-8"))
        runtime_through_poses_bt_tree = stream.name
    rendered = template.replace("__PLATFORM_NAVIGATION_FOOTPRINT__", footprint_text)
    rendered = rendered.replace("__PHASE2_BT_XML__", runtime_bt_tree)
    rendered = rendered.replace(
        "__PHASE2_THROUGH_POSES_BT_XML__", runtime_through_poses_bt_tree
    )
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="rice_weeding_nav2_", suffix=".yaml", delete=False,
        encoding="utf-8"
    ) as stream:
        stream.write(rendered)
        params_path = stream.name

    nav2_share = Path(get_package_share_directory("nav2_bringup"))
    return [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(str(nav2_share / "launch/navigation_launch.py")),
        launch_arguments={
            "use_sim_time": "true",
            "autostart": "true",
            "use_composition": "False",
            "params_file": params_path,
            "log_level": "warn",
        }.items(),
    )]


def generate_launch_description():
    navigation_share = Path(get_package_share_directory("rice_weeding_navigation"))
    simulation_share = Path(get_package_share_directory("rice_weeding_simulation"))
    environment_profile = simulation_share / "profiles/environments/paddy_field.yaml"
    return LaunchDescription([
        Node(
            package="rice_weeding_navigation",
            executable="paddy_navigation_map.py",
            name="rice_weeding_paddy_navigation_map",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "environment_profile": str(environment_profile),
            }],
        ),
        Node(
            package="rice_weeding_navigation",
            executable="nav2_command_adapter.py",
            name="rice_weeding_nav2_command_adapter",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
        OpaqueFunction(function=_configured_nav2),
    ])
