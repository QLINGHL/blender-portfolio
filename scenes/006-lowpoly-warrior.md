# 006 低模游戏角色：女战士

低多边形风格化女战士，平面着色（flat shading），绑定就绪。

## 造型

- 金发马尾：发髻 + 向后下方垂落的马尾（4 环锥形管）
- 钢甲胸甲：4 环收腰造型（肩 / 胸 / 腰 / 胯），金色腰带
- 红色裙甲：8 边喇叭形裙摆（胯 → 膝上），4 环
- 右手持剑：木柄 + 金护手 + 扁平锥形钢刃（剑尖朝上）
- 左臂圆盾：钢盾 + 金色盾心
- 肩甲：两侧半球形钢肩甲；靴子为前指式方靴

## 关节拓扑（绑定就绪）

- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）
- 腿部：5 个环形边线，中间环正好落在膝关节
- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配
- 关节处无三角面集中、无极点（pole）堆积
- 4 个 N-gon 均为圆柱体端盖（圆盾 2 个、剑柄 2 个），不在关节处

## 面数

- 总面数：580（三角面 224，四边面 352，N-gon 4）
- Head：48
- Hair：40
- Ponytail：30
- Eye：18
- Eye.001：18
- Neck：18
- Torso：14
- Belt：6
- Skirt：40
- Arm：36
- ShoulderPad：32
- Hand：24
- Arm.001：36
- ShoulderPad.001：32
- Hand.001：24
- Leg：36
- Boot：6
- Leg.001：36
- Boot.001：6
- SwordHandle：8
- SwordGuard：6
- SwordBlade：20
- Shield：14
- ShieldBoss：32

## 材质

- Armor_Steel：钢甲（metallic 0.75）；Blade_Steel：剑刃（metallic 0.9）
- Trim_Gold：金色饰边 / 腰带 / 护手 / 盾心
- Cloth_Red：红色裙甲；Pants_Navy：裤子；Boots_Brown：靴 / 剑柄
- Skin / Hair_Blonde / Eyes_Dark：皮肤、金发、眼睛

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线
