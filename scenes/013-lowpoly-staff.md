# 013 低模游戏道具：魔法杖

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。

## 结构

- 杖身：8 边渐细圆柱，高 2.9，底半径 0.11 → 顶 0.08，深木色
- 握把：中段深色缠绕段（高 0.55），上下各一道黄铜箍
- 水晶头：八面体水晶（8 面），中心 z=3.35，纵向拉长 1.45 倍，带轻微自发光
- 爪托：3 根铁质细爪，从底座斜向上扣住水晶赤道，120° 均布
- 底座：黄铜杯托（水晶下方）+ 杖首 / 杖尾黄铜箍
- 杖尾：黄铜底帽 + 一颗小八面体水晶
- 漂浮碎片：水晶头旁一颗小八面体碎片（0.55, 0.25, 3.55）

## 面数

- 总面数：252（三角面 176，四边面 76，N-gon 0）
- Shaft：24
- Grip：24
- Band_Top：24
- Band_Bottom：24
- Band_GripTop：24
- Band_GripBottom：24
- Pommel_Cap：24
- Pommel_Gem：8
- Crystal：8
- Crystal_Seat：24
- Prong_0：12
- Prong_1：12
- Prong_2：12
- Shard：8

## 材质

- Staff_Wood：杖身木色（roughness 0.8）
- Staff_WoodDark：握把深木色
- Brass_Band：黄铜箍 / 底座（metallic 0.9）
- Iron_Prong：铁爪（metallic 0.85）
- Crystal_Head：蓝色水晶（roughness 0.12，自发光 0.35）
- Crystal_Small：浅色小水晶（杖尾 + 漂浮碎片）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，35mm 镜头
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
