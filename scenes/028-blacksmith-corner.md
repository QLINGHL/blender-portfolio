# 028 低模场景：铁匠铺角落

低多边形环境场景资产，平面着色（flat shading），干净拓扑。

## 结构

- 角落墙体：后墙（y=+2.2，5.4×2.6）+ 左墙（x=-2.2，4.6×2.6），石材；深色石基座沿墙脚，木梁压顶 + 角柱
- 地面：12 块石板铺地（0.86×0.86，灰度交错，微旋转）
- 铁砧：复用 023 设计（底座/台阶/腰身/砧身/抛光砧面/砧角/砧尾 + 方孔/圆孔），整体绕 Z 转 -20°，位于 (-0.45, 0.35)
- 木桶：12 边鼓形桶身（三段渐变筒：底 0.44→0.52→顶 0.44），高 0.90，浅色桶盖 + 3 道铁箍，位于 (2.0, -0.2)
- 战斧：复用 025 设计（斧柄/皮革握把/斧底帽/斧头座/扇形斧刃/亮钢刃口/顶楔），整体绕 Y 倾 15° 斜靠在桶沿上，斧柄底端位于 (1.18, -0.2)，斧身在 z≈0.9 处搭在桶沿
- 火盆：石墩 + 铁碗 + 3 块发光炭块（Emission 橙光），位于左墙边 (-1.75, 0.10)，上方暖色点光源（250W，橙色）模拟炉火辉光
- 淬火桶：10 边小木桶 + 水面（深蓝低粗糙度）+ 铁箍，位于铁砧左前方 (-1.50, -0.70)
- 铁锤：平放在地面，木柄 + 铁头，位于 (0.55, -0.95)，转 35°
- 铁锭 3 块（叠放，铁砧前方）+ 煤块 3 块（火盆边）

## 面数

- 总面数：852（三角面 472，四边面 380，N-gon 0）
- Wall_Back：6
- Wall_Left：6
- WallBase_Back：6
- WallBase_Left：6
- Beam_Back：6
- Beam_Left：6
- Post_Corner：6
- Paver_00：6
- Paver_01：6
- Paver_02：6
- Paver_03：6
- Paver_04：6
- Paver_05：6
- Paver_06：6
- Paver_07：6
- Paver_08：6
- Paver_09：6
- Paver_10：6
- Paver_11：6
- Anvil_Base：6
- Anvil_Pedestal：6
- Anvil_Waist：6
- Anvil_Body：6
- Anvil_TopPlate：6
- Anvil_Horn：24
- Anvil_Heel：6
- Anvil_HardyHole：6
- Anvil_PritchelHole：24
- Barrel_Bottom：36
- Barrel_Middle：36
- Barrel_Top：36
- Barrel_Lid：36
- Barrel_Hoop_12：36
- Barrel_Hoop_45：36
- Barrel_Hoop_78：36
- Axe_Haft：24
- Axe_Grip：24
- Axe_Pommel：24
- Axe_Socket：6
- Axe_Blade：18
- Axe_CuttingEdge：6
- Axe_TopWedge：6
- Brazier_Pedestal：6
- Brazier_Bowl：24
- Ember_0：20
- Ember_1：20
- Ember_2：20
- Bucket：30
- Bucket_Water：30
- Bucket_Hoop：30
- Hammer_Handle：24
- Hammer_Head：6
- Ingot_0：6
- Ingot_1：6
- Ingot_2：6
- Coal_0：20
- Coal_1：20
- Coal_2：20

## 绕向自检

- Wall_Back：内翻面 0
- Wall_Left：内翻面 0
- WallBase_Back：内翻面 0
- WallBase_Left：内翻面 0
- Beam_Back：内翻面 0
- Beam_Left：内翻面 0
- Post_Corner：内翻面 0
- Paver_00：内翻面 0
- Paver_01：内翻面 0
- Paver_02：内翻面 0
- Paver_03：内翻面 0
- Paver_04：内翻面 0
- Paver_05：内翻面 0
- Paver_06：内翻面 0
- Paver_07：内翻面 0
- Paver_08：内翻面 0
- Paver_09：内翻面 0
- Paver_10：内翻面 0
- Paver_11：内翻面 0
- Anvil_Base：内翻面 0
- Anvil_Pedestal：内翻面 0
- Anvil_Waist：内翻面 0
- Anvil_Body：内翻面 0
- Anvil_TopPlate：内翻面 0
- Anvil_Horn：内翻面 0
- Anvil_Heel：内翻面 0
- Anvil_HardyHole：内翻面 0
- Anvil_PritchelHole：内翻面 0
- Barrel_Bottom：内翻面 0
- Barrel_Middle：内翻面 0
- Barrel_Top：内翻面 0
- Barrel_Lid：内翻面 0
- Barrel_Hoop_12：内翻面 0
- Barrel_Hoop_45：内翻面 0
- Barrel_Hoop_78：内翻面 0
- Axe_Haft：内翻面 0
- Axe_Grip：内翻面 0
- Axe_Pommel：内翻面 0
- Axe_Socket：内翻面 0
- Axe_Blade：内翻面 0
- Axe_CuttingEdge：内翻面 0
- Axe_TopWedge：内翻面 0
- Brazier_Pedestal：内翻面 0
- Brazier_Bowl：内翻面 0
- Ember_0：内翻面 0
- Ember_1：内翻面 0
- Ember_2：内翻面 0
- Bucket：内翻面 0
- Bucket_Water：内翻面 0
- Bucket_Hoop：内翻面 0
- Hammer_Handle：内翻面 0
- Hammer_Head：内翻面 0
- Ingot_0：内翻面 0
- Ingot_1：内翻面 0
- Ingot_2：内翻面 0
- Coal_0：内翻面 0
- Coal_1：内翻面 0
- Coal_2：内翻面 0

## 材质

- Corner_StoneWall：墙体石材（roughness 0.95）
- Anvil_Steel / Anvil_TopSteel：砧身 / 抛光砧面
- Barrel_Wood：桶身；Barrel_Hoop：铁箍
- Ember：发光炭块（Emission 橙，强度 3.0）+ ForgeGlow 点光源
- Bucket_Water：淬火水面（roughness 0.1）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光 + 炉火暖光，40mm 镜头
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
