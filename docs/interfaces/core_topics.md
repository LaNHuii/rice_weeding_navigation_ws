# 核心接口合同

所有 frame 名不带前导 `/`，所有项目 topic 使用 `/rice_weeding/<domain>/<name>`。

| 接口 | 类型 | 发布者 | 消费者 | 当前状态 |
| --- | --- | --- | --- | --- |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo Sim | 全部仿真节点 | Phase 1 已动态验证 |
| `/rice_weeding/simulation/pose_info` | `tf2_msgs/msg/TFMessage` | Gazebo world 动态姿态经 bridge | 仿真真值适配器、仿真底盘里程计 | Phase 2 内部原始接口 |
| `/rice_weeding/simulation/ground_truth` | `nav_msgs/msg/Odometry` | 仿真真值适配器 | 评测 | Phase 2 真值门禁 |
| `/rice_weeding/localization/odometry` | `nav_msgs/msg/Odometry` | 仿真底盘里程计 | Nav2 | Phase 2 里程计门禁 |
| `/joint_states` | `sensor_msgs/msg/JointState` | Gazebo 轮关节状态经 bridge | robot_state_publisher、调试工具 | Phase 2 差速替身门禁 |
| `/map` | `nav_msgs/msg/OccupancyGrid` | profile 驱动的稻田静态地图节点 | Nav2 global/local costmap、RViz | Phase 2：只将田埂写为占用，稻苗为 free/作物语义 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Nav2 velocity_smoother | Nav2 命令适配器 | Phase 2 Nav2 标准内部输出；不连接 Gazebo |
| `/rice_weeding/navigation/cmd_vel_raw` | `geometry_msgs/msg/Twist` | Nav2 命令适配器 | `rice_weeding_safety` | Phase 2 安全门禁输入；不能直连 Gazebo |
| `/rice_weeding/safety/cmd_vel` | `geometry_msgs/msg/Twist` | `rice_weeding_safety` | Gazebo DiffDrive bridge | 默认入口持续为零；仅显式仿真运动时输出非零 |
| `/rice_weeding/safety/status` | `diagnostic_msgs/msg/DiagnosticArray` | `rice_weeding_safety` | 运维/未来作业协调器 | motion disabled、限幅、非法输入和超时原因 |
| `/rice_weeding/perception/obstacle_cloud` | `sensor_msgs/msg/PointCloud2` | 未来感知层 | local costmap | 接口占位 |
| `/rice_weeding/perception/crop_rows` | `visualization_msgs/msg/MarkerArray` | 未来稻行感知 | 显示/行跟踪 | 接口占位 |
| `/rice_weeding/perception/weeds` | 待定义 | 未来杂草感知 | 作业协调器 | 本阶段不定义自定义消息 |

## TF 发布责任

| TF edge | Phase 1 owner | 实车 owner |
| --- | --- | --- |
| `map -> odom` | 仿真真值定位 | 全局融合定位 |
| `odom -> base_footprint` | 仿真底盘 | 连续里程计 |
| `base_footprint -> base_link` | robot_state_publisher | robot_state_publisher |
| `base_link -> sensor` | robot_state_publisher | robot_state_publisher |

不得为了“让 RViz 看起来正常”额外发布单位 `map -> odom`。

Phase 2 仿真入口中，`odom` 与 Gazebo world 初始对齐，而 `map` 原点位于外边界左下角。
对当前 `20 m × 15 m` 田块，真值适配器从 environment profile 派生并唯一发布平移
`(10.0, 7.5, 0) m` 的 `map -> odom`。Gazebo 中 `rice_weeding_robot` 模型的世界位姿加上
同一平移后，以 `map -> base_footprint` 语义写入真值 `Odometry` 消息，但不直接广播
这条 TF。独立仿真底盘里程计使用未加 map 平移的 Gazebo world 位姿发布
`/rice_weeding/localization/odometry` 和唯一的 `odom -> base_footprint`，从而闭合 TF 树。
motion disabled 时定位 Odometry 的 Twist 显式为零；motion enabled 时其 Twist 由相邻
Gazebo 位姿差分得到。这仍不是真实轮速里程计。两个仿真节点均禁止在实车入口启动。

四个轮子现为 simulation-only 连续关节。Gazebo DiffDrive 只监听内部 topic
`/rice_weeding/simulation/internal/locked_cmd_vel`；它只接受安全命令的 ROS→Gazebo bridge，
原始导航命令不能直连。插件自身的内部 odometry/TF 同样不桥接到 ROS，避免与上表唯一的
`odom -> base_footprint` owner 冲突。当前只把轮关节状态单向桥接为 `/joint_states`，用于
更新轮子姿态和诊断，不代表速度链已经开放。

## 速度安全边界

当前项目没有复用参考项目的 BUNKER 手动仲裁或 CAN 参数。独立安全门禁只处理当前已定义
的导航原始速度：检查 Twist 所有分量为有限数、拒绝差速底盘不支持的非平面分量，并使用
platform profile 中的前进、后退和角速度限制。命令时效使用单调墙钟，因此 Gazebo
`/clock` 冻结不会延长旧命令寿命。

默认 Phase 2 入口显式传入 `startup_motion_enabled=false`；即使收到非零 raw command，安全
输出也保持零。显式 `motion_enabled:=true` 时，只有 `/rice_weeding/safety/cmd_vel` 单向桥接到
Gazebo 内部 DiffDrive；原始命令和插件内部 odometry 仍不桥接。真实底盘不得复用该 bridge。

## Phase 2 Nav2 定点导航门禁

`rice_weeding_paddy_navigation_map` 从 environment profile 读取地图边界和田埂厚度，发布
`/map`。地图原点就是 `map` 的西南外边界原点；四周田埂栅格为占用，内部为可通行。该“可通行”
只表示当前静态地图不阻挡稻苗，不能被误读为允许碾压或替代后续的稻行/作业约束。

官方 Nav2 的 `/cmd_vel` 先经过本仓库的无状态命令适配器写为 `cmd_vel_raw`，再由已有安全门禁
检查和限幅；只有 safe topic 能进入 Gazebo。Phase 2 行为树没有 Spin、BackUp 或自动恢复动作，
控制器也关闭原地转向和倒车：无路径或控制失败时应中止并依赖 watchdog 停车，而不是在作物区
尝试恢复动作。

## 作物语义

- `crop_row`：必须保护的稻苗结构，不能直接等价为占用障碍。
- `weed`：作业目标，不是导航障碍。
- `hard_obstacle`：人员、石块、农具、田埂等，需要进入局部安全链。
- `negative_obstacle`：沟渠、坑洞，后续以独立可通行性层表达。
