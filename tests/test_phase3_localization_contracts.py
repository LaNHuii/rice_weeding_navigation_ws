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


def test_health_logic_warns_until_real_thresholds_and_inputs_exist():
    observation = LOGIC.LocalizationHealthInput()
    thresholds = LOGIC.LocalizationHealthThresholds()

    level, summary, reasons = LOGIC.evaluate_localization_health(
        observation, thresholds
    )

    assert level == LOGIC.WARN
    assert summary == "localization_health_contract_warn"
    assert "thresholds_unverified" in reasons
    assert "rtk_fix_unavailable" in reasons
    assert "input_missing" in reasons


def test_health_logic_can_enforce_replay_contract_values():
    observation = LOGIC.LocalizationHealthInput(
        gnss_left_fix_ok=True,
        gnss_right_fix_ok=True,
        gnss_left_age=0.10,
        gnss_right_age=0.70,
        imu_age=0.20,
        wheel_odometry_age=0.20,
        fused_odometry_age=0.20,
        position_covariance=0.04,
        yaw_covariance=0.01,
        position_jump=0.40,
    )
    thresholds = LOGIC.LocalizationHealthThresholds(
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

    level, _, reasons = LOGIC.evaluate_localization_health(observation, thresholds)

    assert level == LOGIC.WARN
    assert "gnss_right_stale" in reasons
    assert "position_jump_detected" in reasons
    assert "position_covariance_high" not in reasons
    assert "yaw_covariance_high" not in reasons
