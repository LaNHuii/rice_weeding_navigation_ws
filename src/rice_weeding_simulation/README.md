# rice_weeding_simulation

当前世界表达20 m × 15 m单一连续矩形田埂外框、边界内的浅水与泥面，以及
按15 cm行株距覆盖全部内区的绿色逐株作物。由于没有留出地头，该场景必须保持
motion disabled。
稻苗没有刚性碰撞。全田植株实例化、差速笼式轮动力学、打滑和传感器噪声属于下一门禁。

```bash
ros2 launch rice_weeding_simulation paddy_world.launch.py
```
