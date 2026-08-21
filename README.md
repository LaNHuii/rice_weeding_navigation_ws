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
- 用户当前确认：稻苗行距与株距均为 `0.30 m`。
- 仿真假设：四个窄型笼式轮、左右差速、轮距 `0.75 m`、底盘净空 `0.16 m`。
- 仿真假设：工作速度 `0.12 m/s`，最大速度 `0.25 m/s`，作业带宽 `0.75 m`。
- 仿真假设：当前导航验收场景为 `20 m x 15 m`、沿稻行两端各 `2.50 m` 地头、
  `0.05--0.10 m` 浅水。

未经验证的值在 profile 中均带有 `verified: false` 或 `simulation_only: true`，不得直接用于实车。

## 包

- `rice_weeding_description`：机器人几何、固定 TF 和 Xacro。
- `rice_weeding_simulation`：稻田世界与 Gazebo Sim 接口边界。
- `rice_weeding_navigation`：Nav2 参数/行为树边界，目前为占位包。
- `rice_weeding_safety`：独立、默认禁用的速度安全门禁和墙钟 watchdog。
- `rice_weeding_localization`：Phase 3 定位输入、融合输出和健康状态接口桩。
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

### Phase 2：仿真差速底盘替身门禁

在保留上述真值和里程计链路的基础上，四个轮子改为 simulation-only 连续关节；轮质量、
固体圆柱惯量替身、关节阻尼/摩擦以及差速几何继续只从 platform profile 读取。Gazebo
内部加载 JointStatePublisher 和 DiffDrive，轮关节状态单向桥接为 ROS `/joint_states`。

安全边界没有改变：ROS `/cmd_vel` 未创建，DiffDrive 的内部命令 topic 没有 bridge 或
正常发布者，插件内部 odometry/TF 也不桥接 ROS，因此不会抢占现有唯一的
`odom -> base_footprint`。Phase 2 入口增加 `headless:=true`，用于不弹出 Gazebo 窗口的
动态检查。当时只允许验证插件加载、关节状态和零指令不漂移；当时场景没有 headland，
因此不允许机器人实际行驶。

2026-08-19 无界面动态验收中，机器人实体正常生成，`/joint_states` 只有一个发布者且包含
四个轮关节；ROS 图无 `/cmd_vel` 和插件内部 odometry，Gazebo 内部命令 topic 也没有
发布者。连续 `10.008 s` 的零指令观测得到平面位置漂移 `0.000000000 m`、偏航漂移
`0.000000000 rad`，因此该替身门禁通过。当时的下一门禁是 `/cmd_vel` 软件安全边界；
后续仍需在创建显式 headland 后才能解锁非零运动。

### Phase 2：软件速度安全门禁

对比了三种速度链方案：直接桥接最简单但没有失联保护；Nav2 `velocity_smoother` 适合
平滑而不能作为独立授权边界；独立安全门禁能够在 Nav2 或仿真时钟异常时继续 fail closed。
因此新增项目自有的 `rice_weeding_safety`，只保留当前需要的导航命令检查，没有复制参考
项目的 BUNKER 履带参数、手动仲裁或 CAN 驱动逻辑。

门禁消费 `/rice_weeding/navigation/cmd_vel_raw`，检查有限数与差速平面分量，按 platform
profile 限制前进、后退和角速度，并使用单调墙钟执行 `0.50 s` 输入 watchdog。标准
默认 Phase 2 启动强制 motion disabled。profile 地头检查通过且显式设置
`motion_enabled:=true` 后，安全输出 `/rice_weeding/safety/cmd_vel` 才会桥接到 Gazebo。

2026-08-19 无界面验证中，标准入口收到 `(0.20, 0.20)` 非零命令仍输出全零，状态为
`motion_disabled`。在完全不启动 Gazebo 的隔离 ROS 域中，输入 `(0.8, 0.8)` 被限制为
`(0.25, 0.35)`，最后一条命令后 `0.508 s` 自动归零并报告 `input_timeout`。该门禁因此
通过，但当时这里只验证软件输出，不代表 Gazebo 或实车已完成制动；后续经用户授权创建
显式 headland 并连接安全输出，结果记录在下一节。

### Phase 2：地头场景与低速掉头门禁

经用户授权，当前 `paddy_field` 直接改为导航验证场景：外边界继续保持 `20 m × 15 m`，
稻苗行距与株距改为 `0.30 m`，沿稻行两端各保留 `2.50 m` 地头。根据离散网格生成结果，
场景共有 2,401 株 visual-only 稻苗，实际无苗地头宽度约 `2.64 m`。

当且仅当 profile 地头宽度满足平台所需 `2.50 m` 且显式设置 `motion_enabled:=true` 时，
安全门禁输出才单向桥接到 Gazebo DiffDrive；原始导航命令不能直连。2026-08-20 无界面
验证中，机器人在东侧地头完成“转 `90°`、横移约 `0.64 m`、再转 `90°`”的低速掉头，最终
真值 map 位姿约为 `(18.595, 8.136)`、朝向约 `179.4°`，并在超时后以零 Odometry Twist
停止。下一门禁是 Nav2 的定点导航和田埂边界拒绝。

### Phase 2：Nav2 定点导航门禁（正在验证）

新增 profile 驱动的静态 `/map`：地图原点仍是田块西南外边界；四周田埂标为占用，稻苗保持
作物语义而不写入 Nav2 障碍层。标准 Nav2 的 `/cmd_vel` 由一个无状态适配器转发至
`/rice_weeding/navigation/cmd_vel_raw`，之后仍必须经过已有的限幅、平面检查和 `0.50 s`
墙钟 watchdog，只有 safe output 可到 Gazebo DiffDrive。

当前控制器只接受简单的前向目标点，行为树没有 Spin、BackUp 或自动恢复动作，并关闭原地转向和
倒车；这确保失败会中止并由门禁停车，而不是在作物区尝试恢复。完整启动入口为：

```bash
ros2 launch rice_weeding_bringup phase2_nav2_simulation.launch.py motion_enabled:=true
```

2026-08-20 无界面隔离启动验证中，修正了 Humble 对局部代价地图整数尺寸参数、行为树插件
预加载以及中文工作空间路径重写的兼容问题。随后 `controller_server`、`planner_server` 和
`bt_navigator` 均启动，控制器状态服务返回 `active`，`/navigate_to_pose` 等 action 可发现；
发送目标前真值为 map `(18.5, 7.5)`。定点运动命令因执行权限审批连接中断而没有实际发出，
所以动态目标到达、停车和田埂外目标拒绝仍待验收，当前不得标记为通过。

## Phase 3（定位融合接口与健康门禁设计）

Phase 3 先建立未来实车定位的接口与验收边界，不实现 RTK/IMU/轮速融合算法、不接入真实
设备，也不改变现有 Gazebo 真值、Nav2 或速度链的运行行为。当前新增
`rice_weeding_localization` 包和健康状态合同入口，用来表达“当前位置是否可信”，但不发布
真实 `map -> odom`、不发布假的融合定位。

规划中的输入和输出如下；传感器/融合话题均为接口占位，当前只有健康监视器会发布状态：

| 类别 | 规划接口 | ROS 类型 | 用途 |
| --- | --- | --- | --- |
| 左 GNSS 天线 | `/rice_weeding/localization/gnss_left/fix` | `sensor_msgs/msg/NavSatFix` | 双天线基线的左端原始定位 |
| 右 GNSS 天线 | `/rice_weeding/localization/gnss_right/fix` | `sensor_msgs/msg/NavSatFix` | 双天线基线的右端原始定位 |
| IMU | `/rice_weeding/localization/imu/data` | `sensor_msgs/msg/Imu` | 姿态与角速度观测 |
| 轮速里程计 | `/rice_weeding/localization/wheel_odometry` | `nav_msgs/msg/Odometry` | 连续局部运动观测 |
| 融合里程计 | `/rice_weeding/localization/fused/odometry` | `nav_msgs/msg/Odometry` | 未来供 Nav2 消费的统一定位输出 |
| 定位健康状态 | `/rice_weeding/localization/status` | `diagnostic_msgs/msg/DiagnosticArray` | Phase 3 已有合同桩；报告 Fix、协方差、时效、跳变与门禁原因 |

未来实车只能由唯一的定位融合节点发布 `map -> odom`；轮速里程计节点唯一发布
`odom -> base_footprint`。现有仿真真值适配器只能保留在仿真入口，绝不能被当作实车融合定位。
健康门禁将至少检查 RTK Fix 状态、位置/偏航协方差、消息时效与位置跳变；具体数值阈值在取得
实车传感器数据前均不设为已验证参数。

Phase 3 合同入口为：

```bash
ros2 launch rice_weeding_bringup phase3_localization_contract.launch.py
```

新增的可回放合同入口为：

```bash
ros2 launch rice_weeding_bringup phase3_localization_replay.launch.py scenario:=nominal
```

`scenario` 可取 `nominal`、`no_fix`、`left_no_fix`、`right_no_fix`、`high_covariance`、
`stale`、`jump`，分别用于验证正常输入、双天线无 Fix、单天线无 Fix、协方差过高、数据过期
和位置跳变诊断。该入口只发布 simulation-only 样例消息，不启动 Gazebo 和 Nav2，也不会让机器人运动。
Phase 3 的完成条件是接口、坐标外参、TF 所有权、健康状态语义和可回放的测试用例均已定义；
它不等于 RTK 实测精度、传感器标定完成或实车自主行驶通过。

第二个终端可用 `localization_status_expect.py` 自动等待目标诊断原因，例如
`position_jump_detected`、`rtk_fix_unavailable` 或 `gnss_left_stale`。该工具只读
`/rice_weeding/localization/status`，不会发布速度、TF 或定位。

Phase 3 的坐标外参和未来 rosbag 记录规范见
`docs/testing/phase3_localization_checks.md`。当前 GNSS/IMU 外参均来自仿真 profile 和
robot_description 固定 TF，仍为未验证值；真实天线相位中心、IMU 安装方向和时延必须等实车
测量后再升级。
