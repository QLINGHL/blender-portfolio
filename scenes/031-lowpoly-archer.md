# 031 低模游戏角色：弓箭手

低多边形风格化弓箭手，平面着色（flat shading），绑定就绪。

## 造型

- 兜帽：前部开口 60° 的锥形兜帽（5 环），裹住头侧、脸部露出，帽尖前倾小锥
- 上身：绿色束腰外衣（5 环微喇叭裙摆）+ 棕色皮质胸甲（肩披下方露出的棕色胸带）+ 肩披 + 双肩垫
- 腰带：深棕皮带 + 铁质带扣（正面）
- 背后箭袋：斜挎皮质箭筒，内插 3 支箭（木杆 + 铁箭头 + 双羽片）
- 左手持反曲弓：7 点弧线弓身（弓梢前倾），弓弦绷直，握把皮革缠绕
- 腿部：棕色裤腿 + 方头皮靴 + 靴口皮环

## 关节拓扑（绑定就绪）

- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）
- 腿部：5 个环形边线，中间环正好落在膝关节
- 前臂另有皮质护腕（3 环），不遮挡肘部关节环
- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配
- 关节处无三角面集中、无极点（pole）堆积
- N-gon 均为圆柱体端盖（箭筒、箭杆、弓身、握把等），不在关节处

## 面数

- 总面数：966（三角面 464，四边面 502，N-gon 0）
- Head：48
- Eye：18
- Eye.001：18
- Neck：18
- Hood：48
- HoodTip：12
- ShoulderCape：32
- Tunic：48
- ChestPlate：32
- Belt：24
- Buckle：6
- ShoulderPad：40
- ShoulderPad.001：40
- Arm：36
- Bracer：24
- Hand：24
- Arm.001：36
- Bracer.001：24
- Hand.001：24
- Leg：36
- Boot：6
- BootCuff：18
- Leg.001：36
- Boot.001：6
- BootCuff.001：18
- Quiver：24
- ArrowShaft_1：18
- ArrowTip_1：12
- ArrowFletch_1_-1：6
- ArrowFletch_1_+1：6
- ArrowShaft_2：18
- ArrowTip_2：12
- ArrowFletch_2_-1：6
- ArrowFletch_2_+1：6
- ArrowShaft_3：18
- ArrowTip_3：12
- ArrowFletch_3_-1：6
- ArrowFletch_3_+1：6
- BowLimb_0：18
- BowLimb_1：18
- BowLimb_2：18
- BowLimb_3：18
- BowLimb_4：18
- BowLimb_5：18
- BowString：18
- BowGrip：18

## 材质

- Tunic_Green / Tunic_DarkGreen：绿色外衣与深绿兜帽、肩披
- Leather_Brown / Leather_Dark：皮质胸甲、护腕、肩垫、箭袋、靴子
- Bow_Wood：弓身与箭杆；Bow_String：弓弦；Iron：带扣、箭头
- Skin / Eyes_Dark：皮肤、眼睛；Pants_Brown：裤腿

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线
