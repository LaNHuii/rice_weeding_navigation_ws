# rice_weeding_safety

该包定义导航速度进入仿真底盘或未来实车底盘之前的独立 fail-closed 边界。它只消费
`/rice_weeding/navigation/cmd_vel_raw`，持续发布 `/rice_weeding/safety/cmd_vel` 和诊断。

当前标准入口强制 `startup_motion_enabled=false`，所以任何输入都会得到零输出。只有通过
地头 profile 检查并显式启用的仿真入口，才会把安全输出单向桥接到 Gazebo；它仍没有连接
真实底盘。隔离测试也可显式启用节点，以验证限幅、非法 Twist 拒绝和命令超时归零。

本门禁使用单调墙钟判断命令时效，因此 `/clock` 停止也不会让旧速度保持有效。它不替代
硬件急停、底盘驱动 watchdog、障碍碰撞监测或实车制动距离测试。
