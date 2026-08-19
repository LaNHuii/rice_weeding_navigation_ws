# rice_weeding_navigation

Nav2 接口边界包。

Phase 1 的 `nav2_phase1_contract.yaml` 保留为历史合同。Phase 2 新增最小定点导航入口：

```text
profile-derived /map (bund occupied; crops free)
  -> Nav2 plan/controller -> /cmd_vel
  -> nav2_command_adapter -> /rice_weeding/navigation/cmd_vel_raw
  -> rice_weeding_safety -> /rice_weeding/safety/cmd_vel -> Gazebo DiffDrive
```

`phase2_navigation.launch.py` 只启动地图、Nav2 和命令适配器；完整仿真使用
`rice_weeding_bringup/phase2_nav2_simulation.launch.py`。footprint 在启动时从平台 profile
渲染进 Nav2 临时参数文件，未在 Nav2 YAML 中复制第二份几何。

当前行为树刻意只允许“规划 + 跟随”，不包含自动 Spin 或 BackUp 恢复动作；控制器也禁用
原地转向和倒车。因此当前验收只覆盖田埂内、朝向前方的简单目标点。稻苗仍是 visual/作物
语义，未写进 Nav2 障碍层；人员、石块、农具等动态障碍还未接入本门禁。
