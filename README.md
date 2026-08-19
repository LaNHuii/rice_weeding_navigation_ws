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

## Phase 2（保留 Phase 1 归档后新增）

Phase 2 不改写上述 Phase 1 入口和验收内容，使用新的组合启动文件。当前第一个
门禁是把已有 Xacro/URDF 通过 `robot_description` 生成为 Gazebo 中的
`rice_weeding_robot` 实体。

```bash
source /opt/ros/humble/setup.bash
cd "$RICE_WEEDING_WS"
source install/setup.bash
ros2 launch rice_weeding_bringup phase2_simulation.launch.py
```

该初始门禁当时强制 `motion_enabled=false`，不提供差速驱动、`/cmd_vel`、仿真里程计或
真值 TF。机器人实体可见不等于 Nav2 闭环已完成；这些状态记录保留用于说明阶段演进。

2026-08-17 动态验收中，`ros_gz_sim create` 返回 `OK creation of entity`，Gazebo
实体树出现 `rice_weeding_robot`，且 ROS 图中仍无 `/cmd_vel`。因此“机器人实体生成”
门禁已通过，下一门禁是仿真真值定位接口。

### Phase 2：仿真真值定位门禁

在机器人实体生成成果之上，新增 Gazebo world 动态位姿的 Pose_V bridge 和只由 Phase 2
入口启动的真值适配器。该链路输出
`/rice_weeding/simulation/ground_truth`，并唯一发布 `map -> odom`。

本门禁不发布 `/rice_weeding/localization/odometry` 或 `odom -> base_footprint`，这两项属于
下一步仿真底盘里程计；也没有开启 `/cmd_vel`。因此当前仍不能让 Nav2 驱动车辆，
`motion_enabled` 继续强制为 `false`。

2026-08-18 动态验收中，Gazebo 真值位置约为 `(0, 0, 0.05 m)`，真值话题只有一个
发布者，`map -> odom` 为单位变换，且没有 `/cmd_vel` 和 Nav2 定位里程计话题。另以隔离
消息注入验证仿真时间戳：输入 `123.456 s` 后真值输出保持 `123.456 s`。因此“仿真真值
定位”门禁通过，下一门禁是仿真底盘里程计与 `odom -> base_footprint`。

随后按用户要求将导航 `map` 原点调整到田块外边界左下角。Gazebo 场景继续以中心为
world 原点，适配器从 environment profile 的 `20 m × 15 m` 尺寸派生 `(10, 7.5) m`
平移；因此边界坐标为 `[0,20] × [0,15] m`，中心出生点的 map 坐标为 `(10,7.5)`。
隔离动态验证中，world `(0,0,0.05)` 输出为 map `(10,7.5,0.05)`，同时
`map -> odom` 查询结果为 `(10,7.5,0)`，坐标调整门禁通过。

### Phase 2：仿真底盘里程计门禁

新增独立的 simulation-only 底盘里程计节点，消费 Gazebo world 中的机器人模型位姿，
发布 `/rice_weeding/localization/odometry`，并唯一广播 `odom -> base_footprint`。因此
TF 可闭合为：

```text
map -> odom -> base_footprint -> base_link -> wheels/sensors
```

该门禁没有启用差速驱动或 `/cmd_vel`。当前 Twist 在 motion disabled 条件下显式为零，
所以不能把这一成果描述为轮速里程计、打滑仿真或Nav2运动闭环。

2026-08-19 隔离动态验收中，注入 `odom` pose `(1,2,0.05)` 后，定位 Odometry数值一致且
只有一个发布者；完整 `map -> base_link` 查询为 `(11,9.5,0.28)`，与 map平移、底盘位姿
和主体固定高度之和一致。TF树已经闭合，ROS图中仍无`/cmd_vel`，因此“仿真底盘里程计”
门禁通过。下一门禁是仿真差速驱动替身与零速度不漂移测试。
