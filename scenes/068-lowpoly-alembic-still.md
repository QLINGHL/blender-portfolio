# 068 低模游戏道具：炼金蒸馏器

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。木质底板上放一套完整蒸馏装置：左边的玻璃曲颈甑（圆底烧瓶 + 直颈）装着发光青绿药液，底下是黄铜酒精灯（火焰尖正好碰到瓶底）；一根竖杆 + 黄铜圆环夹住甑颈；斜玻璃管把蒸汽导向右边的立式冷凝器——玻璃直管外绕 3 圈铜盘管，冷凝液经细滴管滴进下方的小圆底收集瓶，瓶内是发光琥珀色蒸馏液。接 047 炼金实验室场景的道具线。

## 结构

- 木质底板（BaseBoard）：0.62×0.34×0.02，z 0.01
- 玻璃曲颈甑（RetortFlask）：车削轮廓 8 个断面、24 段；圆底球半径 0.10、球心 (-0.16, 0, 0.20)，肩部收到颈半径 0.028、直颈到 z 0.44；口沿一圈玻璃卷边（RetortRimLip，R 0.028、管径 0.004）
- 甑内药液（RetortLiquid）：车削轮廓 6 个断面、24 段；球半径 0.096，顶面 z 0.2117（平顶）；发光青绿（Emission 0.7，混合 55%）
- 酒精灯（Burner）：黄铜圆柱半径 0.035，z 0.02–0.06；灯芯（BurnerWick）半径 0.008，z 0.06–0.075；火焰 （Flame）锥形，底径 0.018、顶径 0.002，z 0.075–0.10，火焰尖正好碰到瓶底 z 0.10；发光橙（Emission 1.2，混合 80%）
- 固定架（StandRod / RingArm / StandRing）：黄铜竖杆半径 0.008，z 0.01–0.50（x -0.30）；横臂 0.14×0.02×0.015（z 0.34）；圆环 R 0.035、管径 0.006，套在甑颈上（颈半径 0.028，环内径 0.029，余量 0.001）
- 蒸汽斜管（VapourArm）：两点直管，(-0.16, 0, 0.44) → (0.10, 0, 0.36)，半径 0.016；两端各一枚黄铜卡箍 （Collar_Neck R 0.030 / Collar_Condenser R 0.026，管径 0.005）
- 冷凝器（CondenserTube）：玻璃直管半径 0.024，z 0.18–0.36；铜盘管（CondenserCoil）螺旋半径 0.042、管径 0.007，3 圈，z 0.20–0.34（每圈 16 段、管截面 6 边）
- 滴管（DripTube）：细玻璃直管半径 0.010，z 0.18–0.10，穿过收集瓶颈（颈半径 0.018，余量 0.008），管底在收集液面上方 0.0428
- 收集瓶（CollectionFlask）：车削轮廓 7 个断面、24 段；圆底球半径 0.055、球心 (0.10, 0, 0.075)，瓶底落在底板上（z 0.02），颈半径 0.018、颈顶 z 0.16
- 收集液（CollectionLiquid）：车削轮廓 4 个断面、24 段；球半径 0.052，顶面 z 0.0572（平顶）；发光琥珀色（066 同款：Emission 0.5，混合 40%，roughness 0.9）
- 整体约 0.62 m 宽 × 0.50 m 高 × 0.34 m 深

## 面数

- 总面数：1752（三角面 284，四边面 1468，N-gon 0）
- BaseBoard：6
- RetortFlask：192
- RetortRimLip：144
- RetortLiquid：144
- Burner：48
- BurnerWick：24
- Flame：36
- StandRod：36
- RingArm：6
- StandRing：144
- VapourArm：36
- Collar_Neck：144
- Collar_Condenser：144
- CondenserTube：48
- CondenserCoil：300
- DripTube：36
- CollectionFlask：168
- CollectionLiquid：96

## 绕向自检

车削件（RetortFlask / RetortLiquid / CollectionFlask / CollectionLiquid）用轮廓段法线检查；圆环（RetortRimLip / StandRing / Collar_Neck / Collar_Condenser）用环中心线法线检查；铜盘管用螺旋中心线法线检查；其余凸形部件用质心法检查。

- RetortFlask：轮廓段法线检查，内翻面 0
- RetortLiquid：轮廓段法线检查，内翻面 0
- CollectionFlask：轮廓段法线检查，内翻面 0
- CollectionLiquid：轮廓段法线检查，内翻面 0
- RetortRimLip：内翻面 0
- StandRing：内翻面 0
- Collar_Neck：内翻面 0
- Collar_Condenser：内翻面 0
- CondenserCoil：螺旋中心线法线检查，内翻面 0
- BaseBoard：内翻面 0
- Burner：内翻面 0
- BurnerWick：内翻面 0
- Flame：内翻面 0
- StandRod：内翻面 0
- RingArm：内翻面 0
- VapourArm：内翻面 0
- CondenserTube：内翻面 0
- DripTube：内翻面 0

## 实测间隙

- 火焰尖 z 0.10 − 瓶底 z 0.10 = 0.000（设计贴合）
- 固定环内径 0.029 − 甑颈半径 0.028 = 0.001
- 铜盘管内径 0.035 − 冷凝管半径 0.024 = 0.011
- 滴管半径 0.010，收集瓶颈半径 0.018，余量 0.008
- 甑内药液顶面半径 0.0953，z 0.2117 处瓶内半径 0.0993，间隙 0.0040
- 收集液顶面半径 0.0489，z 0.0572 处瓶内半径 0.0520，间隙 0.0031
- 滴管底端 z 0.10 − 收集液面 z 0.0572 = 0.0428
- 冷凝管底端 z 0.18 − 收集瓶颈顶 z 0.16 = 0.020

## 材质

- Base_Wood：底板暖棕木（roughness 0.8）
- Stand_Brass：酒精灯 / 竖杆 / 横臂 / 固定环 / 卡箍（metallic 0.7，roughness 0.35）
- Coil_Copper：铜盘管（metallic 0.8，roughness 0.3）
- Glass_Clear：甑 / 冷凝管 / 斜管 / 滴管 / 收集瓶无色玻璃（Alpha 0.35，dithered，roughness 0.15；059 同款做法，瓶内药液可见）
- Liquid_Teal：甑内青绿药液（Emission 0.7，混合 55%）
- Liquid_Amber：收集瓶琥珀蒸馏液（Emission 0.5，混合 40%，roughness 0.9；066 同款防顶面过曝）
- Flame_Orange：火焰（Emission 1.2，混合 80%）
- Wick_Dark：灯芯深灰（roughness 0.9）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%，方向 (0, -1, 0.35)）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
