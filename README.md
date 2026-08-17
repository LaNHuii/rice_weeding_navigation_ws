# rice_weeding_navigation_ws

面向浅水稻田除草机器人的 ROS 2 Humble 独立工作空间。参考工程
`agt_navigation_v2-main` 只作为接口与安全思路参考；本工作空间不依赖其源码路径，也不复制其中
的第三方算法。

## 当前阶段

Phase 1 当前只建立一条数据链：

```text
稻田仿真世界 -> 仿真真值定位 -> Nav2 接口边界
```

本提交包含机器人/环境 canonical profile、TF 与 topic 合同、Xacro 外形骨架、Gazebo Sim 世界
骨架、组合启动占位和合同测试。当前4个ROS包已完成构建，8项静态合同测试通过，安装态
`robot_state_publisher`已启动验证。RTK/IMU融合、稻行视觉、杂草识别、覆盖执行和实车底盘
驱动尚未实现。

## 已确认与暂定参数

- 用户已确认：主体长 `1.0 m`、宽 `1.0 m`、地面到主体顶面 `0.30 m`。
- 用户已确认：稻苗行距与株距均为 `0.15 m`。
- 仿真假设：四个窄型笼式轮、左右差速、轮距 `0.75 m`、底盘净空 `0.16 m`。
- 仿真假设：工作速度 `0.12 m/s`，最大速度 `0.25 m/s`，作业带宽 `0.75 m`。
- 仿真假设：当前视觉验收场景为 `20 m x 15 m`、全内区作物覆盖、`0.05--0.10 m` 浅水。

未经验证的值在 profile 中均带有 `verified: false` 或 `simulation_only: true`，不得直接用于实车。

## 包

- `rice_weeding_description`：机器人几何、固定 TF 和 Xacro。
- `rice_weeding_simulation`：稻田世界与 Gazebo Sim 接口边界。
- `rice_weeding_navigation`：Nav2 参数/行为树边界，目前为占位包。
- `rice_weeding_bringup`：第一阶段组合启动入口，目前执行依赖预检后启动场景骨架。

## 环境预检

```bash
cd "$RICE_WEEDING_WS"
./tools/check_phase1_dependencies.sh
```

本机已检测到 ROS 2 Humble、Nav2、Xacro、`ros_gz_sim` 与 `ros_gz_bridge`。
2026-08-17 动态验证中 Gazebo 成功加载稻田世界，`/clock`
桥接返回仿真时间；验收过程未发布 `/cmd_vel`。

## 构建和测试

```bash
source /opt/ros/humble/setup.bash
cd "$RICE_WEEDING_WS"
colcon build --symlink-install
source install/setup.bash
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest -q tests
```

第一阶段场景入口为：

```bash
ros2 launch rice_weeding_bringup phase1_simulation.launch.py
```

该入口当前不允许运动，也不会发布实车速度。后续完成 Gazebo 差速驱动和 Nav2 真值闭环后，
才会继续推进仿真底盘与 Nav2 真值闭环状态。
