from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = Path(get_package_share_directory("rice_weeding_description"))
    profile = share / "profiles" / "platforms" / "rice_weeding_prototype.yaml"
    with profile.open("r", encoding="utf-8") as stream:
        platform = yaml.safe_load(stream)["platform"]
    geometry = platform["geometry"]
    dimensions = geometry["outer_dimensions"]
    clearance = geometry["body_clearance"]["nominal"]
    body_height = dimensions["height_from_ground"] - clearance
    body_center_z = clearance + 0.5 * body_height
    drive = platform["drive"]
    sensors = platform["sensors"]
    xacro_file = share / "urdf" / "rice_weeding_robot.urdf.xacro"
    robot_description = ParameterValue(
        Command([
            "xacro ", str(xacro_file),
            " body_length:=", str(dimensions["length"]),
            " body_width:=", str(dimensions["width"]),
            " body_height:=", str(body_height),
            " body_center_z:=", str(body_center_z),
            " mass:=", str(platform["mass"]["value"]),
            " wheel_diameter:=", str(drive["wheel_diameter"]),
            " wheel_width:=", str(drive["wheel_width"]),
            " track_width:=", str(drive["track_width"]),
            " wheelbase:=", str(drive["wheelbase"]),
            " sensor_height:=", str(sensors["operational_sensor_height"]["value"]),
            " gnss_baseline:=", str(sensors["dual_gnss_baseline"]["value"]),
        ]), value_type=str)
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             name="rice_weeding_robot_state_publisher", output="screen",
             parameters=[{"robot_description": robot_description},
                         {"use_sim_time": LaunchConfiguration("use_sim_time")}]),
    ])
