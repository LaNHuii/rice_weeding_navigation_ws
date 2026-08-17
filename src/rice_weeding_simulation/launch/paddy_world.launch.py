from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    sim_share = Path(get_package_share_directory("rice_weeding_simulation"))
    description_share = Path(get_package_share_directory("rice_weeding_description"))
    ros_gz_share = Path(get_package_share_directory("ros_gz_sim"))
    world = sim_share / "worlds" / "paddy_field.sdf"
    bridge_config = sim_share / "config" / "bridge.yaml"
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(ros_gz_share / "launch" / "gz_sim.launch.py")),
            launch_arguments={"gz_args": f"-r {world}"}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(description_share / "launch" / "description.launch.py")),
            launch_arguments={"use_sim_time": "true"}.items()),
        Node(package="ros_gz_bridge", executable="parameter_bridge",
             name="rice_weeding_clock_bridge", output="screen",
             parameters=[{"config_file": str(bridge_config)}]),
    ])
