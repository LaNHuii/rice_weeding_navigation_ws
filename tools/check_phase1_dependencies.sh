#!/usr/bin/env bash
set -u

missing=0

check_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "MISSING command: $1"
    missing=1
  else
    echo "FOUND command: $1"
  fi
}

check_ros_package() {
  if ! ros2 pkg prefix "$1" >/dev/null 2>&1; then
    echo "MISSING ROS package: $1"
    missing=1
  else
    echo "FOUND ROS package: $1"
  fi
}

check_command ros2
check_command colcon
check_ros_package xacro
check_ros_package robot_state_publisher
check_ros_package nav2_bringup
check_ros_package ros_gz_sim
check_ros_package ros_gz_bridge

if [[ "$missing" -ne 0 ]]; then
  echo "Phase 1 dynamic simulation dependencies are incomplete."
  exit 1
fi

echo "Phase 1 dependency preflight passed."
