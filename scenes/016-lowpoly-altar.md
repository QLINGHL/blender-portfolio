# 016 低模场景：魔法祭坛

低多边形环境场景资产，平面着色（flat shading），干净拓扑。

## 结构

- 三层石台：16 边圆柱逐层收窄（半径 3.0 / 2.4 / 1.8，每层高 0.35），顶面 z=1.05
- 祭坛：中央石块 1.1x0.7x0.9 + 顶板 1.4x1.0x0.12（顶面 z=2.07）
- 符文环：发光圆环（主半径 1.35，24x4 段），平铺于三层石台顶面，环绕祭坛
- 符文石：8 块立石（0.35x0.12x0.9），45° 均布于二层石台（半径 2.0），向外倾斜 8°，内侧各贴一块发光符文板
- 烛台：祭坛顶板上两支（黄铜底座 + 杆 + 烛杯 + 蜡烛 + 火焰锥），三层石台上一支高烛台（杆高 0.55）
- 悬浮水晶：中央八面体水晶（0.30x0.30x0.45，z=3.15）+ 3 颗小碎片环绕
- 台阶：祭坛正面两级石阶，通向一层石台
- 补光：水晶处冷色点光（40）+ 烛光处暖色点光（12）

## 面数

- 总面数：728（三角面 368，四边面 360，N-gon 0）
- Platform_Tier1：48
- Platform_Tier2：48
- Platform_Tier3：48
- Step_Low：6
- Step_High：6
- Altar_Block：6
- Altar_Slab：6
- Rune_Ring：96
- RuneStone_0：6
- RunePlate_0：6
- RuneStone_1：6
- RunePlate_1：6
- RuneStone_2：6
- RunePlate_2：6
- RuneStone_3：6
- RunePlate_3：6
- RuneStone_4：6
- RunePlate_4：6
- RuneStone_5：6
- RunePlate_5：6
- RuneStone_6：6
- RunePlate_6：6
- RuneStone_7：6
- RunePlate_7：6
- Candle_L_Base：24
- Candle_L_Stem：24
- Candle_L_Cup：24
- Candle_L_Candle：24
- Candle_L_Flame：16
- Candle_R_Base：24
- Candle_R_Stem：24
- Candle_R_Cup：24
- Candle_R_Candle：24
- Candle_R_Flame：16
- Candle_Tall_Base：24
- Candle_Tall_Stem：24
- Candle_Tall_Cup：24
- Candle_Tall_Candle：24
- Candle_Tall_Flame：16
- Crystal_Main：8
- Crystal_Shard_0：8
- Crystal_Shard_1：8
- Crystal_Shard_2：8

## 材质

- Altar_StoneDark / Mid / Light：三层石台（roughness 0.95）
- Altar_Block：祭坛石块；Rune_Stone：符文石
- Rune_Glow：青色自发光（强度 1.8），符文环 + 符文板
- Altar_Crystal：蓝色水晶自发光（强度 1.4）
- Altar_Brass：黄铜烛台（metallic 0.9）
- Candle_Wax：米白蜡烛；Candle_Flame：橙色火焰自发光（2.5）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
