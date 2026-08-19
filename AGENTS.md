# AGENTS.md

## Scope

- 本仓库用于稻田除草机器人自主导航与仿真。
- 当前阶段只推进“稻田场景 -> 仿真真值 -> Nav2 接口”这一条数据链。
- 只创建架构文档、包骨架、接口桩、场景资产、测试和依赖清单。
- 不迁移第三方算法源码，不接入真实底盘运动。

## Hard rules

- 一次只迁移一个模块或一条数据链。
- 禁止硬编码用户名、工作空间路径、设备路径、地图路径和 RTK 基站地址。
- `profiles/platforms/rice_weeding_prototype.yaml` 是车辆几何唯一真源。
- `profiles/environments/paddy_field.yaml` 是第一版稻田场景参数唯一真源。
- 未验证参数必须显式标为 `verified: false` 或 `simulation_only: true`。
- 架构或接口变化必须同时更新 `docs/`、本文件和
  `docs/migration/migration_matrix.md`。
- 不允许多个节点发布同一 TF edge。
- 不得把稻苗点云无条件写入 Nav2 障碍层；稻苗、杂草和真实障碍必须分层表达。
- 仿真真值 TF 只能在仿真入口中启用，真实系统不得复用真值发布者。
- 仿真入口默认 motion disabled；只有 profile 明确提供足够地头、速度经过安全门禁且
  显式设置 `motion_enabled:=true` 时才允许仿真运动。
- `/rice_weeding/navigation/cmd_vel_raw` 不得直接连接 Gazebo 或实车底盘；只有
  `rice_weeding_safety` 可以发布 `/rice_weeding/safety/cmd_vel`。
- 安全门禁 watchdog 必须使用单调墙钟，不得因仿真 `/clock` 停止而保留旧速度。

## TF ownership

- `map -> odom`：Phase 1 仅由仿真真值定位发布；未来实车由全局融合定位唯一发布。
- `odom -> base_footprint`：Phase 1 仅由仿真底盘发布；未来实车由连续里程计唯一发布。
- `base_footprint -> base_link -> sensor`：仅由机器人描述发布固定 TF。

## Geometry and crop-row contract

- 主体外廓为用户确认的 `1.0 m x 1.0 m x 0.30 m`。
- 导航 footprint 必须从 platform profile 消费，不得在 Nav2、覆盖规划或仿真中复制第二份。
- `0.75 m` 轮距、`0.16 m` 净空、笼式轮尺寸与质量均为仿真假设，实车使用前必须测量。
- 当前导航场景的 canonical 行距和株距均为 `0.30 m`。
- `map` 原点为田块外边界左下（西南）角；x 沿外边界长度正向，y 沿外边界宽度正向，z 向上。
- Gazebo 作物必须逐株表达，不得使用连续长条代替；单株仿真几何只从
  environment profile 消费。
- 田埂可见几何必须是单一连续矩形外框，不得使用会在田块内相交的长条。
- 作物区禁止原地转向；掉头必须发生在显式 headland 中。
- 当前场景在沿稻行的两端各保留 `2.50 m` 显式 headland；作物网格离散后实际无苗宽度
  不得小于该值。作物区禁止原地转向，地头内可进行仿真掉头。
- 稻苗是作物语义，不是默认障碍物；人员、田埂、沟渠、石块和农具才进入安全障碍链。

## Phase 1 non-goals

- RTK/IMU/轮速融合实现。
- 稻行或杂草视觉算法。
- 覆盖路径执行、除草机构控制和实车速度输出。
- 水体流体动力学、泥土有限元或高保真植株接触仿真。
- 复制 FAST-LIVO2、Nav2、OpenNav、Fields2Cover 或其他第三方源码。

## Phase 2 current gate

- Phase 1 的文档、启动入口和验收证据必须保留，Phase 2 使用独立入口迭代。
- Gazebo 机器人实体生成门禁已通过，初始位姿从 environment profile 消费。
- 仿真真值定位门禁已通过；当前仿真入口允许真值适配器唯一发布 `map -> odom` 和仿真真值话题，该适配器不得在实车入口启用。
- 仿真底盘里程计门禁已通过；独立节点唯一发布 `odom -> base_footprint` 和 `/rice_weeding/localization/odometry`，真值适配器不得冒充其发布者。
- 当前里程计位姿来自 Gazebo 模型真值；motion disabled 时速度显式为零，motion enabled 时
  由相邻 Gazebo 位姿差分得到。两者均不得声称为轮编码器里程计或实车验证结果。
- 仿真差速底盘替身门禁已通过：四个连续轮关节、Gazebo内部DiffDrive和 `/joint_states` 已动态验证；内部命令与插件里程计不得桥接到ROS。
- 零指令 10 s 验收的平面位置和偏航漂移均为零，阈值由 platform profile 唯一提供；这不等于非零运动或停止测试通过。
- 软件速度安全门禁已通过：标准入口固定 motion disabled；隔离域验证限幅和 0.5 s 命令超时归零。该结果不代表硬件急停、实际制动或底盘 watchdog 已验证。
- `/rice_weeding/safety/cmd_vel` 只可桥接到仿真 DiffDrive 的内部命令话题；真实底盘不得复用该 bridge。
- 低速地头掉头和 timeout 后实际停止已通过；下一门禁是 Nav2 输出经同一安全门禁的定点导航。
- Nav2 Phase 2 静态地图只可从 environment profile 派生：田埂为占用，稻苗/杂草不得默认进入
  障碍层。Nav2 footprint 必须在启动时从 platform profile 消费。
- 当前 Nav2 验收只允许田埂内、前向的简单目标点；行为树不得含 Spin、BackUp 或自动恢复，
  控制器不得在作物区原地转向或倒车。失败应中止并由安全门禁停车。
- Nav2 单目标和多目标入口均只能加载项目自有的 forward-only 行为树；Humble 参数重写不得
  直接消费含非 ASCII 工作空间目录的行为树绝对路径，启动入口应使用临时 ASCII 路径副本。
- Nav2 生命周期节点 Active 与 action 可发现性已动态验证；定点到达、停车和田埂外目标拒绝
  尚未执行完成，不得将 Nav2 真值闭环标记为通过。
- 仿真真值定位、速度链、安全门禁与停止测试必须各自通过后才能解锁运动。
