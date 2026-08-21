import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
LOGIC_PATH = (
    ROOT / "src/rice_weeding_localization/scripts/localization_health_logic.py"
)
SPEC = importlib.util.spec_from_file_location("localization_health_logic", LOGIC_PATH)
LOGIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOGIC)


def load_yaml(relative_path):
    with (ROOT / relative_path).open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_phase3_localization_package_is_contract_only():
    manifest = (ROOT / "src/rice_weeding_localization/package.xml").read_text()
    cmake = (ROOT / "src/rice_weeding_localization/CMakeLists.txt").read_text()
    launch = (
        ROOT
        / "src/rice_weeding_localization/launch/localization_health_contract.launch.py"
    ).read_text()
    monitor = (
        ROOT
        / "src/rice_weeding_localization/scripts/localization_health_monitor.py"
    ).read_text()

    assert "<name>rice_weeding_localization</name>" in manifest
    assert "diagnostic_msgs" in manifest
    assert "sensor_msgs" in manifest
    assert "nav_msgs" in manifest
    assert "localization_health_monitor.py" in cmake
    assert '"thresholds_verified": False' in launch
    assert '"enforce_thresholds": False' in launch
    assert "TransformBroadcaster" not in monitor
    assert "StaticTransformBroadcaster" not in monitor
    assert "create_publisher(Odometry" not in monitor
    assert "status.level = bytes([level])" in monitor
    assert "/dev/" not in monitor
    assert "rtk" not in monitor.lower() or "rtk_fix" in monitor


def test_phase3_replay_samples_are_simulation_only_inputs():
    cmake = (ROOT / "src/rice_weeding_localization/CMakeLists.txt").read_text()
    replay = (
        ROOT
        / "src/rice_weeding_localization/scripts/localization_replay_sample_publisher.py"
    ).read_text()
    replay_launch = (
        ROOT
        / "src/rice_weeding_localization/launch/localization_replay_contract.launch.py"
    ).read_text()
    expect = (
        ROOT / "src/rice_weeding_localization/scripts/localization_status_expect.py"
    ).read_text()
    bringup = (
        ROOT / "src/rice_weeding_bringup/launch/phase3_localization_replay.launch.py"
    ).read_text()

    assert "localization_replay_sample_publisher.py" in cmake
    assert "localization_status_expect.py" in cmake
    assert "DeclareLaunchArgument(\"scenario\", default_value=\"nominal\")" in replay_launch
    assert "enforce_thresholds" in replay_launch
    assert '"thresholds_verified": False' in replay_launch
    assert "NavSatFix" in replay
    assert "Imu" in replay
    assert "Odometry" in replay
    assert "create_subscription" not in replay
    assert "TransformBroadcaster" not in replay
    assert "StaticTransformBroadcaster" not in replay
    assert "/dev/" not in replay
    assert "phase3_localization_replay.launch.py" in str(
        ROOT / "src/rice_weeding_bringup/launch/phase3_localization_replay.launch.py"
    )
    assert "localization_replay_contract.launch.py" in bringup
    assert '"/rice_weeding/localization/status"' in expect
    assert "expected_reason" in expect
    assert "sys.exit(0 if matched else 1)" in expect
    assert "create_publisher" not in expect
    assert "TransformBroadcaster" not in expect


def test_phase3_contract_defines_topics_and_unverified_health_thresholds():
    contract = load_yaml(
        "src/rice_weeding_localization/config/localization_phase3_contract.yaml"
    )["phase3_localization_contract"]

    assert contract["status"] == "interface_stub"
    assert contract["simulation_only"] is True
    assert contract["threshold_verified"] is False
    assert contract["tf_ownership"]["publishes_tf_in_phase3_stub"] is False
    assert contract["topics"] == {
        "gnss_left_fix": "/rice_weeding/localization/gnss_left/fix",
        "gnss_right_fix": "/rice_weeding/localization/gnss_right/fix",
        "imu_data": "/rice_weeding/localization/imu/data",
        "wheel_odometry": "/rice_weeding/localization/wheel_odometry",
        "fused_odometry": "/rice_weeding/localization/fused/odometry",
        "status": "/rice_weeding/localization/status",
    }
    semantics = contract["health_semantics"]
    assert set(semantics) == {
        "rtk_fix",
        "position_covariance",
        "yaw_covariance",
        "data_freshness",
        "position_jump",
    }
    assert all(item["verified"] is False for item in semantics.values())
    replay = contract["replay_contract"]
    assert replay["simulation_only"] is True
    assert replay["thresholds_verified"] is False
    assert replay["scenarios"] == [
        "nominal",
        "no_fix",
        "left_no_fix",
        "right_no_fix",
        "high_covariance",
        "stale",
        "jump",
    ]
    assert replay["thresholds"]["max_position_jump"] == 0.20


def test_phase3_extrinsics_and_rosbag_contract_are_unverified_and_safe():
    contract = load_yaml(
        "src/rice_weeding_localization/config/localization_phase3_contract.yaml"
    )["phase3_localization_contract"]
    checks_doc = (
        ROOT / "docs/testing/phase3_localization_checks.md"
    ).read_text()

    extrinsics = contract["extrinsics"]
    assert extrinsics["verified"] is False
    assert extrinsics["simulation_only"] is True
    assert extrinsics["parent_frame"] == "base_link"
    assert extrinsics["imu_link"]["xyz"] == [0.0, 0.0, 0.0]
    assert extrinsics["gnss_left_link"]["xyz"] == [0.0, 0.35, 0.42]
    assert extrinsics["gnss_right_link"]["xyz"] == [0.0, -0.35, 0.42]
    assert extrinsics["base_footprint_to_gnss_height"] == 0.65
    assert extrinsics["dual_gnss_baseline"] == 0.70

    rosbag = contract["rosbag_contract"]
    assert rosbag["status"] == "recording_spec_only"
    assert rosbag["verified"] is False
    assert rosbag["simulation_only"] is False
    assert "/tf" in rosbag["required_topics"]
    assert "/tf_static" in rosbag["required_topics"]
    assert "/rice_weeding/simulation/ground_truth" in rosbag["forbidden_topics"]
    assert "/rice_weeding/safety/cmd_vel" in rosbag["forbidden_topics"]
    assert "ros2 bag record" in checks_doc
    assert "Real antenna phase centers" in checks_doc
    assert "/rice_weeding/simulation/ground_truth" in checks_doc


def test_health_logic_warns_until_real_thresholds_and_inputs_exist():
    observation = LOGIC.LocalizationHealthInput()
    thresholds = LOGIC.LocalizationHealthThresholds()

    level, summary, reasons = LOGIC.evaluate_localization_health(
        observation, thresholds
    )

    assert level == LOGIC.WARN
    assert summary == "localization_health_contract_warn"
    assert "thresholds_unverified" in reasons
    assert "gnss_left_fix_unavailable" in reasons
    assert "gnss_right_fix_unavailable" in reasons
    assert "rtk_fix_unavailable" in reasons
    assert "input_missing" in reasons


def replay_thresholds():
    return LOGIC.LocalizationHealthThresholds(
        verified=False,
        enforce=True,
        max_gnss_age=0.50,
        max_imu_age=0.50,
        max_wheel_odometry_age=0.50,
        max_fused_odometry_age=0.50,
        max_position_covariance=0.10,
        max_yaw_covariance=0.05,
        max_position_jump=0.20,
    )


def test_health_logic_accepts_nominal_replay_contract_values():
    observation = LOGIC.LocalizationHealthInput(
        gnss_left_fix_ok=True,
        gnss_right_fix_ok=True,
        gnss_left_age=0.10,
        gnss_right_age=0.10,
        imu_age=0.10,
        wheel_odometry_age=0.10,
        fused_odometry_age=0.10,
        position_covariance=0.04,
        yaw_covariance=0.01,
        position_jump=0.0,
    )

    level, summary, reasons = LOGIC.evaluate_localization_health(
        observation, replay_thresholds()
    )

    assert level == LOGIC.OK
    assert summary == "localization_health_contract_ok"
    assert reasons == ["thresholds_unverified"]


def test_health_logic_detects_fix_state_variants():
    left_missing = LOGIC.LocalizationHealthInput(
        gnss_left_fix_ok=False,
        gnss_right_fix_ok=True,
        gnss_left_age=0.10,
        gnss_right_age=0.10,
        imu_age=0.10,
        wheel_odometry_age=0.10,
        fused_odometry_age=0.10,
        position_covariance=0.04,
        yaw_covariance=0.01,
        position_jump=0.0,
    )
    right_missing = LOGIC.LocalizationHealthInput(
        gnss_left_fix_ok=True,
        gnss_right_fix_ok=False,
        gnss_left_age=0.10,
        gnss_right_age=0.10,
        imu_age=0.10,
        wheel_odometry_age=0.10,
        fused_odometry_age=0.10,
        position_covariance=0.04,
        yaw_covariance=0.01,
        position_jump=0.0,
    )

    _, _, left_reasons = LOGIC.evaluate_localization_health(
        left_missing, replay_thresholds()
    )
    _, _, right_reasons = LOGIC.evaluate_localization_health(
        right_missing, replay_thresholds()
    )

    assert "gnss_left_fix_unavailable" in left_reasons
    assert "gnss_right_fix_unavailable" not in left_reasons
    assert "rtk_fix_unavailable" in left_reasons
    assert "gnss_right_fix_unavailable" in right_reasons
    assert "gnss_left_fix_unavailable" not in right_reasons
    assert "rtk_fix_unavailable" in right_reasons


def test_health_logic_detects_covariance_freshness_and_jump_contracts():
    observation = LOGIC.LocalizationHealthInput(
        gnss_left_fix_ok=True,
        gnss_right_fix_ok=True,
        gnss_left_age=0.10,
        gnss_right_age=0.70,
        imu_age=0.20,
        wheel_odometry_age=0.20,
        fused_odometry_age=0.20,
        position_covariance=0.25,
        yaw_covariance=0.10,
        position_jump=0.40,
    )

    level, _, reasons = LOGIC.evaluate_localization_health(
        observation, replay_thresholds()
    )

    assert level == LOGIC.WARN
    assert "gnss_right_stale" in reasons
    assert "position_jump_detected" in reasons
    assert "position_covariance_high" in reasons
    assert "yaw_covariance_high" in reasons
