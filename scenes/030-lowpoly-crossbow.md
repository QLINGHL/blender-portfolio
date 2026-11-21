# 030 低模游戏道具：弩

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。弩身平放于地面，3/4 俯视角度展示。

## 结构

- 弩身（Stock）：木质 0.10×0.95×0.07，z 0.00–0.07
- 枪托（Butt）：木质 0.13×0.18×0.08，y 0.38–0.56；贴腮垫皮革 0.09×0.12×0.02
- 箭槽（BoltGroove）：深色木质 0.03×0.70×0.012，弩身顶部
- 照门（RearSight）：铁质小块 0.05×0.03×0.02，箭槽后端
- 弩臂（Limb）：钢质，每侧长 0.52、截面 0.045×0.028，从 x=±0.05 伸至 x=±0.55，前倾约 10.2°（y -0.38→-0.47）
- 弩臂尖（LimbTip）：铁质小块，位于两端 x=±0.55
- 弩臂座（ProdBinding）：铁质 0.14×0.08×0.05，将弩臂固定于弩身前端
- 弓弦（String）：两段 r 0.004 细圆柱，从弩臂尖 (±0.55, -0.47) 收至待发点 (0, -0.02, 0.055)，呈 V 形
- 待发弩箭：木质箭杆 r 0.008，y -0.34–0.30；钢质箭头圆锥 r 0.011、长 0.05，箭尾两片羽片（薄板，倾斜 20°）
- 扳机（Trigger）：铁质，弩身下方倾斜；扳机护圈铁条
- 蹬环（Stirrup）：扁平半圆环（major r 0.07，minor r 0.008），平放于前端 (0, -0.55)，供脚蹬上弦
- 箭匣（Quiver）：右侧挂深色木盒 0.06×0.30×0.10，皮革盖；内插 3 支备用弩箭（竖立，箭杆高 0.22，钢质箭头朝上）
- 整体约 1.10 m 宽（弩臂尖到尖）× 1.13 m 长（含蹬环）

## 面数

- 总面数：472（三角面 164，四边面 308，N-gon 0）
- Stock：6
- Butt：6
- CheekRest：6
- BoltGroove：6
- RearSight：6
- Limb_-1：6
- LimbTip_-1：6
- Limb_+1：6
- LimbTip_+1：6
- ProdBinding：6
- String_-1：18
- String_+1：18
- BoltShaft：24
- BoltTip：16
- Fletch_-1：6
- Fletch_+1：6
- Trigger：6
- TriggerGuard：6
- Stirrup：156
- Quiver：6
- QuiverLid：6
- SpareBolt_1：24
- SpareTip_1：24
- SpareBolt_2：24
- SpareTip_2：24
- SpareBolt_3：24
- SpareTip_3：24

## 绕向自检

蹬环为半圆环几何，绕向用环中心线检测（质心检测不适用于环形）；其余部件用质心检测。

- Stock：内翻面 0
- Butt：内翻面 0
- CheekRest：内翻面 0
- BoltGroove：内翻面 0
- RearSight：内翻面 0
- Limb_-1：内翻面 0
- LimbTip_-1：内翻面 0
- Limb_+1：内翻面 0
- LimbTip_+1：内翻面 0
- ProdBinding：内翻面 0
- String_-1：内翻面 0
- String_+1：内翻面 0
- BoltShaft：内翻面 0
- BoltTip：内翻面 0
- Fletch_-1：内翻面 0
- Fletch_+1：内翻面 0
- Trigger：内翻面 0
- TriggerGuard：内翻面 0
- Stirrup：内翻面 0
- Quiver：内翻面 0
- QuiverLid：内翻面 0
- SpareBolt_1：内翻面 0
- SpareTip_1：内翻面 0
- SpareBolt_2：内翻面 0
- SpareTip_2：内翻面 0
- SpareBolt_3：内翻面 0
- SpareTip_3：内翻面 0

## 材质

- Crossbow_Wood：弩身/枪托（roughness 0.7）
- Crossbow_WoodDark：箭槽/箭匣（roughness 0.75）
- Crossbow_Steel：弩臂/箭头（metallic 0.85，roughness 0.35）
- Crossbow_Iron：弩臂尖/弩臂座/扳机/蹬环（metallic 0.7，roughness 0.5）
- Crossbow_String：弓弦（浅色，roughness 0.9）
- Crossbow_Leather：贴腮垫/箭匣盖（roughness 0.85）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
