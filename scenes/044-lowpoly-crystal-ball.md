# 044 低模游戏道具：魔法水晶球

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。水晶球置于雕花木底座上，符文环斜绕球体，3/4 俯视角度。

## 结构

- 底座底盘（Plinth）：锥形圆柱，z 0–0.03，r 0.24→0.22，24 段，深木色
- 底盘饰环（TrimRing）：黄铜圆环，z 0.03，R 0.225，管 r 0.008
- 底座身（BaseBody）：锥形圆柱，z 0.03–0.13，r 0.20→0.16，24 段，木色
- 底座箍带（BaseBand）：黄铜圆环，z 0.13，R 0.165，管 r 0.007
- 托杯（Cup）：外翻锥形圆柱，z 0.13–0.17，r 0.16→0.185，深木色
- 杯口唇缘（CupLip）：黄铜圆环，z 0.17，R 0.185，管 r 0.010
- 雕花叶瓣（Petal_1–8）：黄铜扁盒 0.014×0.055×0.095，绕底座身一圈，外倾 12°
- 底盘铆钉（Stud_01–12）：六边形黄铜柱，r 0.009，z 0.004–0.014，绕底盘边缘一圈
- 爪托（Claw_1–4）：黄铜锥形柱，r 0.011，6 段，从杯口（r 0.17，z 0.155）斜伸至球面（r 0.128，z 0.285）
- 水晶球（CrystalBall）：UV 球，r 0.16，球心 z 0.34，24×12 段；Principled 透明材质（alpha 0.35，BLEND，roughness 0.08，淡紫）——Eevee 透射会把球内辉光核遮成乳白实心球，改用透明混合后辉光可见
- 辉光核（GlowCore）：r 0.09 紫色自发光球，球心 z 0.34，强度 4.0，透过球体可见
- 闪光宝石（SparkleGem）：二十面体 r 0.032，z 0.375，白色自发光，强度 6.0
- 符文环（RuneRing）：黄铜圆环，R 0.20，管 r 0.012，绕球心 z 0.34，绕 X 轴倾 25°
- 符文牌（RuneTablet_1–8）：黄铜扁盒 0.05×0.008×0.062，以环为父级，均布于环上，切向排列
- 整体约 0.55 m 宽 × 0.62 m 高（球顶 z 0.50，符文环上缘约 z 0.56）

## 面数

- 总面数：1724（三角面 436，四边面 1288，N-gon 0）
- Plinth：72
- TrimRing：144
- BaseBody：72
- BaseBand：144
- Cup：72
- CupLip：144
- Petal_1：6
- Petal_2：6
- Petal_3：6
- Petal_4：6
- Petal_5：6
- Petal_6：6
- Petal_7：6
- Petal_8：6
- Stud_01：18
- Stud_02：18
- Stud_03：18
- Stud_04：18
- Stud_05：18
- Stud_06：18
- Stud_07：18
- Stud_08：18
- Stud_09：18
- Stud_10：18
- Stud_11：18
- Stud_12：18
- Claw_1：18
- Claw_2：18
- Claw_3：18
- Claw_4：18
- CrystalBall：288
- GlowCore：128
- SparkleGem：20
- RuneRing：256
- RuneTablet_1：6
- RuneTablet_2：6
- RuneTablet_3：6
- RuneTablet_4：6
- RuneTablet_5：6
- RuneTablet_6：6
- RuneTablet_7：6
- RuneTablet_8：6

## 绕向自检

圆环类部件用环中心线检测（符文环在倾斜前检测）；其余部件用质心检测。

- TrimRing：内翻面 0
- BaseBand：内翻面 0
- CupLip：内翻面 0
- RuneRing：内翻面 0
- Plinth：内翻面 0
- BaseBody：内翻面 0
- Cup：内翻面 0
- Petal_1：内翻面 0
- Petal_2：内翻面 0
- Petal_3：内翻面 0
- Petal_4：内翻面 0
- Petal_5：内翻面 0
- Petal_6：内翻面 0
- Petal_7：内翻面 0
- Petal_8：内翻面 0
- Stud_01：内翻面 0
- Stud_02：内翻面 0
- Stud_03：内翻面 0
- Stud_04：内翻面 0
- Stud_05：内翻面 0
- Stud_06：内翻面 0
- Stud_07：内翻面 0
- Stud_08：内翻面 0
- Stud_09：内翻面 0
- Stud_10：内翻面 0
- Stud_11：内翻面 0
- Stud_12：内翻面 0
- Claw_1：内翻面 0
- Claw_2：内翻面 0
- Claw_3：内翻面 0
- Claw_4：内翻面 0
- CrystalBall：内翻面 0
- GlowCore：内翻面 0
- SparkleGem：内翻面 0
- RuneTablet_1：内翻面 0
- RuneTablet_2：内翻面 0
- RuneTablet_3：内翻面 0
- RuneTablet_4：内翻面 0
- RuneTablet_5：内翻面 0
- RuneTablet_6：内翻面 0
- RuneTablet_7：内翻面 0
- RuneTablet_8：内翻面 0

## 材质

- Ball_Wood：底座身木色（roughness 0.75）
- Ball_WoodDark：底盘/托杯深木色（roughness 0.8）
- Ball_Brass：饰环/箍带/杯口/爪托/符文环黄铜（metallic 0.9，roughness 0.35）
- Ball_BrassDark：雕花叶瓣/符文牌暗黄铜（metallic 0.85，roughness 0.45）
- Ball_Crystal：水晶球透明材质（alpha 0.35，BLEND，roughness 0.08）
- Ball_GlowCore：辉光核紫色自发光（强度 4.0）
- Ball_Sparkle：闪光宝石白色自发光（强度 6.0）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定；辉光核与闪光宝石在球体内，不参与线框）
