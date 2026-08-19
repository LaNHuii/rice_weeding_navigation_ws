# 核心接口合同

所有 frame 名不带前导 `/`，所有项目 topic 使用 `/rice_weeding/<domain>/<name>`。

| 接口 | 类型 | 发布者 | 消费者 | 当前状态 |
| --- | --- | --- | --- | --- |
| `/clock` | `rosgraph_msgs/msg/Clock` | Gazebo Sim | 全部仿真节点 | Phase 1 已动态验证 |
| `/rice_weeding/simulation/pose_info` | `tf2_msgs/msg/TFMessage` | Gazebo world 动态姿态经 bridge | 仿真真值适配器 | Phase 2 内部原始接口 |
| `/rice_weeding/simulation/ground_truth` | `nav_msgs/msg/Odometry` | 仿真真值适配器 | 评测 | Phase 2 真值门禁 |
| `/rice_weeding/localization/odometry` | `nav_msgs/msg/Odometry` | 仿真底盘 | Nav2 | 接口占位 |
| `/rice_weeding/navigation/cmd_vel_raw` | `geometry_msgs/msg/Twist` | Nav2 controller | 未来安全层 | 接口占位 |
| `/rice_weeding/safety/cmd_vel` | `geometry_msgs/msg/Twist` | 未来安全层 | 仿真/实车底盘 | 禁止发布非零值 |
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
同一平移后，以
`map -> base_footprint` 语义写入真值
`Odometry` 消息，但不直接广播这条 TF。下一门禁才由仿真底盘唯一发布
`odom -> base_footprint`，从而闭合 TF 树。真值适配器禁止在实车入口启动。

## 作物语义

- `crop_row`：必须保护的稻苗结构，不能直接等价为占用障碍。
- `weed`：作业目标，不是导航障碍。
- `hard_obstacle`：人员、石块、农具、田埂等，需要进入局部安全链。
- `negative_obstacle`：沟渠、坑洞，后续以独立可通行性层表达。
