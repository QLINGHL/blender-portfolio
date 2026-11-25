# 053 低模游戏道具：炼金天平

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。圆台木底座 + 黄铜立柱，横梁两端各挂一只浅托盘，右盘叠放三枚砝码，底座旁另有一枚备用砝码；指针自横梁垂至立柱前的刻度板，3/4 俯视角度。

## 结构

- 底座底盘（Plinth）：锥形圆柱，z 0–0.03，r 0.20→0.18，24 段，深木色
- 底盘饰环（PlinthTrim）：黄铜圆环，z 0.03，R 0.185，管 r 0.007
- 底座身（BaseBody）：锥形圆柱，z 0.03–0.06，r 0.16→0.13，24 段，木色
- 底座箍带（BaseBand）：黄铜圆环，z 0.06，R 0.135，管 r 0.006
- 立柱（Pillar）：锥形圆柱，z 0.06–0.40，r 0.028→0.022，12 段，黄铜
- 柱箍（Collar_1–2）：暗黄铜圆环，z 0.14 / 0.32，管 r 0.006
- 刻度板（DialPlate）：暗黄铜扁盒 0.06×0.008×0.03，立柱正面 z 0.315–0.345
- 指针臂（PointerArm）：暗黄铜柱，r 0.006，从横梁中心向前伸至 (0, -0.04, 0.42)
- 指针（Pointer）：锥形针，z 0.345–0.42，r 0.001→0.005，针尖正对刻度板顶缘
- 支点（Pivot）：暗黄铜球，r 0.02，横梁中心 z 0.42
- 横梁（Beam）：黄铜杆，沿 X 轴，z 0.42，长 0.52，r 0.012，8 段
- 梁端饰球（BeamFinial_1–2）：暗黄铜球，r 0.016，x ±0.26，z 0.42
- 柱顶饰球（TopFinial）：黄铜球，r 0.02，z 0.445
- 托盘（Pan_1–2）：浅锥台，底 r 0.03（z 0.285）→口 r 0.09（z 0.30），24 段，黄铜；顶面圆盘即盘面
- 盘沿（PanRim_1–2）：暗黄铜圆环，R 0.09，管 r 0.005，z 0.30
- 吊链（Chain_1_1–3 / Chain_2_1–3）：铁灰细柱，r 0.0025，4 段，每盘 3 根，从梁端汇聚至盘沿三点
- 砝码组（Weight_Large/Mid/Small）：右盘叠放三枚暗黄铜圆柱，r 0.030 / 0.022 / 0.015，高 0.02 / 0.018 / 0.015，16/16/12 段；大砝码带黄铜提钮（WeightKnob，r 0.008）
- 备用砝码（SpareWeight）：暗黄铜圆柱，r 0.028，高 0.025，置于地面 (0.32, 0.14)，带提钮 r 0.009
- 整体约 0.62 m 宽（梁端饰球外缘）× 0.465 m 高

## 面数

- 总面数：1798（三角面 560，四边面 1238，N-gon 0）
- Plinth：72
- PlinthTrim：144
- BaseBody：72
- BaseBand：144
- Pillar：36
- Collar_1：96
- Collar_2：96
- DialPlate：6
- PointerArm：18
- Pointer：18
- Pivot：72
- Beam：24
- BeamFinial_1：72
- BeamFinial_2：72
- TopFinial：72
- Pan_1：72
- PanRim_1：144
- Chain_1_1：12
- Chain_1_2：12
- Chain_1_3：12
- Pan_2：72
- PanRim_2：144
- Chain_2_1：12
- Chain_2_2：12
- Chain_2_3：12
- Weight_Large：48
- Weight_Mid：48
- Weight_Small：36
- WeightKnob：50
- SpareWeight：48
- SpareWeightKnob：50

## 绕向自检

圆环类部件用环中心线检测；其余部件用质心检测。

- PlinthTrim：内翻面 0
- BaseBand：内翻面 0
- Collar_1：内翻面 0
- Collar_2：内翻面 0
- PanRim_1：内翻面 0
- PanRim_2：内翻面 0
- Plinth：内翻面 0
- BaseBody：内翻面 0
- Pillar：内翻面 0
- DialPlate：内翻面 0
- PointerArm：内翻面 0
- Pointer：内翻面 0
- Pivot：内翻面 0
- Beam：内翻面 0
- BeamFinial_1：内翻面 0
- BeamFinial_2：内翻面 0
- TopFinial：内翻面 0
- Pan_1：内翻面 0
- Chain_1_1：内翻面 0
- Chain_1_2：内翻面 0
- Chain_1_3：内翻面 0
- Pan_2：内翻面 0
- Chain_2_1：内翻面 0
- Chain_2_2：内翻面 0
- Chain_2_3：内翻面 0
- Weight_Large：内翻面 0
- Weight_Mid：内翻面 0
- Weight_Small：内翻面 0
- WeightKnob：内翻面 0
- SpareWeight：内翻面 0
- SpareWeightKnob：内翻面 0

## 材质

- Scale_Wood：底座身木色（roughness 0.75）
- Scale_WoodDark：底盘深木色（roughness 0.8）
- Scale_Brass：立柱/横梁/托盘/饰环黄铜（metallic 0.9，roughness 0.35）
- Scale_BrassDark：柱箍/刻度板/指针/支点/盘沿/砝码暗黄铜（metallic 0.85，roughness 0.45）
- Scale_Iron：吊链铁灰（metallic 0.85，roughness 0.5）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
