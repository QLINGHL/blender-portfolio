# 055 低模游戏道具：炼金坩埚

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。铸铁坩埚置于三脚支架上，锅底燃着小篝火，锅内是发光的绿色药水与气泡，木质搅拌棒横搁在锅沿上。接 047 炼金实验室场景的道具线。

## 结构

- 锅身（Pot）：车削轮廓（lathe），7 个断面，24 段，z 0.14–0.40，最大腹径 r 0.160（z 0.27），底面扇形封口，铸铁
- 锅沿（Rim）：暗铁圆环，z 0.40，R 0.138，管 r 0.009
- 腹箍（BellyBand）：暗铁圆环，z 0.27，R 0.160，管 r 0.008
- 药水面（Potion）：圆盘，z 0.382–0.385，r 0.132，绿色自发光（Emission 0.8，混合 70%）
- 气泡（Bubble_1–5）：小球，r 0.011–0.018，半浸在药水面上，亮绿自发光（混合 60%）
- 提环（Handle_1–2）：竖直圆环（torus_yz 直接在 YZ 平面生成），R 0.035，管 r 0.008，中心 (±0.155, 0, 0.33)，暗铁，半嵌锅壁
- 支腿（Leg_1–3）：斜撑铁柱，r 0.018，8 段，从锅底（r 0.10，z 0.16）外张至地面（r 0.20，z 0），方位 90°/210°/330°，正面可见两腿
- 足垫（FootPad_1–3）：暗铁扁球，r 0.022，z 0.012，位于三腿落地点
- 篝火木柴（Log_1–2）：深木圆柱，r 0.026，长 0.30，交叉平放于锅底地面，z 0.025
- 火焰（Flame_1–3）：锥形，底 r 0.035–0.045，高 0.12–0.17，橙色自发光；焰心（FlameCore）亮黄，底 r 0.028，高 0.09
- 搅拌棒（StirStick）：木质圆柱，r 0.011，长约 0.34，横搁锅沿，z 约 0.41
- 整体约 0.55 m 宽（提环外缘）× 0.42 m 高

## v1 修正（目视检查发现两处问题后重渲）

- 提环错位：v1 用 torus_xy 建平环再 rotation_euler 绕世界原点旋转，两只提环被甩到 x 0.33 处，一只沉到地面以下；改 torus_yz 直接在 YZ 平面生成，绕向自检随之归零
- 药水面不可见：v1 药水面 z 0.375 且相机俯角小，视线越过近侧锅沿后始终高于药水面；药水面抬至 z 0.385，相机方向改为 (0, -1, 0.45)，自发光混合比提至 70%（火焰同）

## 面数

- 总面数：1360（三角面 392，四边面 968，N-gon 0）
- Pot：168
- Rim：144
- BellyBand：144
- Potion：72
- Bubble_1：50
- Bubble_2：50
- Bubble_3：50
- Bubble_4：50
- Bubble_5：50
- Handle_1：96
- Handle_2：96
- Leg_1：24
- FootPad_1：50
- Leg_2：24
- FootPad_2：50
- Leg_3：24
- FootPad_3：50
- Log_1：24
- Log_2：24
- Flame_1：24
- Flame_2：24
- Flame_3：24
- FlameCore：24
- StirStick：24

## 绕向自检

圆环类部件用环中心线检测（平环用 XY 版，竖环用 YZ 版）；其余部件用质心检测。

- Rim：内翻面 0
- BellyBand：内翻面 0
- Handle_1：内翻面 0
- Handle_2：内翻面 0
- Pot：内翻面 0
- Potion：内翻面 0
- Bubble_1：内翻面 0
- Bubble_2：内翻面 0
- Bubble_3：内翻面 0
- Bubble_4：内翻面 0
- Bubble_5：内翻面 0
- Leg_1：内翻面 0
- FootPad_1：内翻面 0
- Leg_2：内翻面 0
- FootPad_2：内翻面 0
- Leg_3：内翻面 0
- FootPad_3：内翻面 0
- Log_1：内翻面 0
- Log_2：内翻面 0
- Flame_1：内翻面 0
- Flame_2：内翻面 0
- Flame_3：内翻面 0
- FlameCore：内翻面 0
- StirStick：内翻面 0

## 材质

- Cauldron_Iron：锅身铸铁（metallic 0.7，roughness 0.55）
- Cauldron_IronDark：锅沿/腹箍/提环/足垫暗铁（metallic 0.65，roughness 0.6）
- Cauldron_Wood：搅拌棒木色（roughness 0.8）
- Cauldron_WoodDark：篝火木柴深木色（roughness 0.85）
- Cauldron_Potion：药水面亮绿自发光（Emission 0.8，混合 70%）
- Cauldron_Bubble：气泡亮绿自发光（Emission 0.6，混合 60%）
- Cauldron_Flame：火焰橙色自发光（Emission 1.2，混合 70%）
- Cauldron_FlameCore：焰心亮黄自发光（Emission 1.4，混合 70%）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%，方向 (0, -1, 0.45)：俯角更大以便看到锅内药水面）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
