# 最小检查

```bash
source /opt/ros/humble/setup.bash
cd "$RICE_WEEDING_WS"
env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /usr/bin/python3 -m pytest -q tests
colcon list
colcon build --symlink-install
```

静态检查覆盖：

- 用户确认尺寸、`0.30 m` 作物网格和 `2.50 m` 地头未被漂移修改。
- footprint 只有 platform profile 一份真源。
- Xacro 不发布 `map -> odom` 或 `odom -> base_footprint`。
- SDF 世界使用米制 ENU 约定且稻苗骨架无碰撞。
- 包清单不依赖参考仓库的绝对路径。

已执行的 Gazebo 动态检查（2026-08-17）：

- `/clock` 存在且返回仿真时间（采样值 `1360.822 s`）。
- ROS 节点仅包含时钟桥和机器人状态发布者，话题中无 `/cmd_vel`。
- 在独立 Gazebo transport 分区中截图确认 `crop_field` 新场景生效：12,936 株绿色
  作物覆盖全部内区，田埂为单一连续矩形外框，泥面和浅水无越界。
- Phase 2 入口返回 `OK creation of entity`，Gazebo 实体树和截图均确认
  `rice_weeding_robot` 存在；ROS 话题中仍无 `/cmd_vel`。
- Phase 2 真值入口从 Gazebo world 动态位姿读取机器人实际位置；左下角原点调整后隔离
  动态验证 world `(0, 0, 0.05 m)` 正确转换为 map `(10, 7.5, 0.05 m)`；
  `/rice_weeding/simulation/ground_truth` 发布者数为 1。
- `map -> odom` 动态查询为 `(10, 7.5, 0) m` 平移；ROS 图中仍无 `/cmd_vel` 和
  `/rice_weeding/localization/odometry`。
- 隔离注入仿真时钟 `123.456 s` 与位姿 `(1, 2, 0.05 m)` 后，真值输出保持相同位姿并
  使用 `123.456 s`，证明 Fortress Pose_V 顶层时间戳缺失的适配已生效。

已执行的仿真底盘里程计动态门禁（2026-08-19）：

- `/rice_weeding/localization/odometry` 只有一个发布者，frame 为 `odom`，child 为
  `base_footprint`。
- `odom -> base_footprint` 只由仿真底盘里程计发布，并与 Odometry pose 一致。
- TF 树闭合为 `map -> odom -> base_footprint -> base_link -> sensors`。
- motion disabled 时 Twist 全零，且 ROS 图中仍无 `/cmd_vel`。
- 隔离注入 odom pose `(1,2,0.05)` 后，完整 `map -> base_link` 查询为
  `(11,9.5,0.28)`，与 map 偏移、底盘位姿和 canonical 主体高度之和一致。

已执行的仿真差速底盘替身动态门禁（2026-08-19）：

- `headless:=true` 返回 `OK creation of entity`，验证过程未弹出 Gazebo GUI。
- `/joint_states` 只有一个发布者并包含四个连续轮关节；轮速仅有约 `10^-18 rad/s` 的
  数值舍入量。
- ROS 图无 `/cmd_vel` 和插件内部 odometry；Gazebo 内部 locked command topic 明确无发布者。
- 不发布速度命令连续观察 `10.008 s`，平面位置漂移 `0.000000000 m`、偏航漂移
  `0.000000000 rad`，均小于 platform profile 中的 `0.002` 阈值。

已执行的软件速度安全门禁（2026-08-19）：

- Conda `(base)` 环境曾使 `env python3` 选择错误运行库；安全节点固定使用系统
  `/usr/bin/python3` 后，标准 Phase 2 无界面入口正常启动。
- 标准入口中安全 output publisher 没有订阅者；注入 `(0.20 m/s, 0.20 rad/s)` 后输出仍为
  全零，诊断为 `motion_disabled`。
- 在不启动 Gazebo、没有底盘订阅者的独立 ROS 域显式启用测试门禁；输入
  `(0.8 m/s, 0.8 rad/s)` 被限为 `(0.25 m/s, 0.35 rad/s)`。
- 停止输入后，以单调墙钟测得最后一条命令到全零输出为 `0.508 s`，诊断为
  `input_timeout`，符合 profile 的 `0.50 s` timeout 和 20 Hz 发布周期。
- 以上只证明软件 topic 输出归零，不证明 Gazebo/实车实际制动距离。

已执行的地头运动动态门禁（2026-08-20）：

- 当前场景改为两端 `2.50 m` headland，行距与株距均改为 `0.30 m`；生成 2,401 株 visual-only 稻苗。
- `motion_enabled:=true` 通过 profile 地头检查后，唯一 ROS→Gazebo 速度 bridge 为
  `/rice_weeding/safety/cmd_vel → /rice_weeding/simulation/internal/locked_cmd_vel`。
- 东侧地头内完成分段低速掉头：`90°` 转向、横移约 `0.64 m`、再转 `90°`；最终真值 map
  位姿为约 `(18.595, 8.136)`，朝向约 `179.4°`，仍在地头 footprint-safe 区间。
- 停止发送命令后，`/rice_weeding/localization/odometry` 的线速度和角速度均为零。

后续动态门禁：

- Nav2 输出必须只经 `/rice_weeding/navigation/cmd_vel_raw → rice_weeding_safety → Gazebo`。
- 机器人不得越过田埂或在种植区原地旋转。

已执行的 Nav2 启动级动态检查（2026-08-20）：

- 修正 Humble 局部 costmap `width/height` 参数类型后，控制器状态服务返回 `active`。
- 单目标和多目标入口均加载项目自有 forward-only 行为树；两棵树均无 Spin、BackUp 或恢复运动。
- 使用临时 ASCII 行为树路径规避中文工作空间经过 `RewrittenYaml` 后路径损坏。
- `/navigate_to_pose`、`/compute_path_to_pose` 和 `/follow_path` action 均可发现；发送目标前
  仿真真值为 map `(18.5, 7.5)`。
- 目标运动命令尚未实际发出；定点到达、停车和田埂外目标拒绝仍属于后续动态门禁。
