# 059 低模游戏道具：炼金药水架

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。双层木架，上下两层共 8 瓶不同形状的药水（圆腹瓶 / 高身瓶 / 锥形瓶 / 小药瓶），瓶内彩色药水自发光，软木塞封口，羊皮纸标签贴在瓶身前面；顶板上立着 3 个备用软木塞，中层前面嵌一块黄铜铭牌。接 047 炼金实验室场景的道具线。

## 结构

- 木架（Post_L/R + Shelf_1/2/3 + BackRail）：两根立柱 0.045×0.06×0.54（x ±0.27），下层板 / 中层板 / 顶板 0.585×0.17×0.03（z 0.03/0.27/0.51），后横档 0.50×0.02×0.04（y 0.075，z 0.44），深色木
- 铭牌（Nameplate）：黄铜薄板 0.12×0.002×0.03，嵌在中层板前面（y -0.086，z 0.27），金属度 0.7
- 瓶身（Bottle_*）：车削轮廓（lathe），16 段，底面扇形封口；圆腹瓶高 0.145（最大腹径 r 0.052）、高身瓶高 0.17（r 0.033）、锥形瓶高 0.125（底 r 0.048）、小药瓶高 0.10（r 0.024）；瓶身为半透明玻璃（Alpha 0.45，dithered），透出瓶内发光药水
- 药水（Liquid_* + LiquidTop_*）：瓶身轮廓按 0.8 缩径、截到瓶高 65% 处，顶部加薄圆盘封口；自发光材质（Emission 0.7，混合 55%），六色：琥珀 / 绿 / 蓝 / 红 / 青 / 紫
- 瓶塞（Cork_*）：锥形圆柱，8 段，颈口 r 约 0.014，塞入瓶颈、露出约 0.022
- 标签（Label_*）：羊皮纸薄板，宽取 min(0.05, 最大腹径×1.1)，高为瓶高 30%，贴在瓶身前面（-Y），按标签高度处轮廓半径定位；标签按瓶壁斜率倾斜（atan2(下沿半径-上沿半径, 标签高)），锥形瓶下沿不再埋进瓶壁
- 下层（z 0.045）：L1 圆腹琥珀、L2 高身绿、L3 小药瓶蓝、L4 锥形紫
- 上层（z 0.285）：U1 圆腹红、U2 高身青、U3 小药瓶琥珀、U4 锥形绿；上层最高瓶顶（瓶塞）约 z 0.477，顶板底 0.495，不穿帮
- 备用软木塞（SpareCork_1–3）：3 个锥形圆柱立在顶板上（z 0.525–0.552，x -0.10/0/0.10）
- 整体约 0.59 m 宽 × 0.55 m 高 × 0.17 m 深

## 面数

- 总面数：2242（三角面 688，四边面 1554，N-gon 0）
- Post_L：6
- Post_R：6
- Shelf_1：6
- Shelf_2：6
- Shelf_3：6
- BackRail：6
- Nameplate：6
- Bottle_L1：128
- Liquid_L1：80
- LiquidTop_L1：48
- Cork_L1：24
- Label_L1：6
- Bottle_L2：112
- Liquid_L2：64
- LiquidTop_L2：48
- Cork_L2：24
- Label_L2：6
- Bottle_L3：112
- Liquid_L3：64
- LiquidTop_L3：48
- Cork_L3：24
- Label_L3：6
- Bottle_L4：112
- Liquid_L4：80
- LiquidTop_L4：48
- Cork_L4：24
- Label_L4：6
- Bottle_U1：128
- Liquid_U1：80
- LiquidTop_U1：48
- Cork_U1：24
- Label_U1：6
- Bottle_U2：112
- Liquid_U2：64
- LiquidTop_U2：48
- Cork_U2：24
- Label_U2：6
- Bottle_U3：112
- Liquid_U3：64
- LiquidTop_U3：48
- Cork_U3：24
- Label_U3：6
- Bottle_U4：112
- Liquid_U4：80
- LiquidTop_U4：48
- Cork_U4：24
- Label_U4：6
- SpareCork_1：24
- SpareCork_2：24
- SpareCork_3：24

## 绕向自检

质心检测，全部部件逐一核查。

- Post_L：内翻面 0
- Post_R：内翻面 0
- Shelf_1：内翻面 0
- Shelf_2：内翻面 0
- Shelf_3：内翻面 0
- BackRail：内翻面 0
- Nameplate：内翻面 0
- Bottle_L1：内翻面 0
- Liquid_L1：内翻面 0
- LiquidTop_L1：内翻面 0
- Cork_L1：内翻面 0
- Label_L1：内翻面 0
- Bottle_L2：内翻面 0
- Liquid_L2：内翻面 0
- LiquidTop_L2：内翻面 0
- Cork_L2：内翻面 0
- Label_L2：内翻面 0
- Bottle_L3：内翻面 0
- Liquid_L3：内翻面 0
- LiquidTop_L3：内翻面 0
- Cork_L3：内翻面 0
- Label_L3：内翻面 0
- Bottle_L4：内翻面 0
- Liquid_L4：内翻面 0
- LiquidTop_L4：内翻面 0
- Cork_L4：内翻面 0
- Label_L4：内翻面 0
- Bottle_U1：内翻面 0
- Liquid_U1：内翻面 0
- LiquidTop_U1：内翻面 0
- Cork_U1：内翻面 0
- Label_U1：内翻面 0
- Bottle_U2：内翻面 0
- Liquid_U2：内翻面 0
- LiquidTop_U2：内翻面 0
- Cork_U2：内翻面 0
- Label_U2：内翻面 0
- Bottle_U3：内翻面 0
- Liquid_U3：内翻面 0
- LiquidTop_U3：内翻面 0
- Cork_U3：内翻面 0
- Label_U3：内翻面 0
- Bottle_U4：内翻面 0
- Liquid_U4：内翻面 0
- LiquidTop_U4：内翻面 0
- Cork_U4：内翻面 0
- Label_U4：内翻面 0
- SpareCork_1：内翻面 0
- SpareCork_2：内翻面 0
- SpareCork_3：内翻面 0

## 材质

- Rack_Wood / Rack_WoodDark：木架棕色 / 深棕（roughness 0.85/0.9）
- Rack_Brass：铭牌黄铜（metallic 0.7，roughness 0.35）
- Rack_Cork：瓶塞软木色（roughness 0.9）
- Rack_Parchment：标签羊皮纸色（roughness 0.85）
- Glass_*：六色瓶身，浅色玻璃色（roughness 0.15）
- Liquid_*：六色药水自发光（Emission 0.7，混合 55%）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%，方向 (0, -1, 0.30)）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
