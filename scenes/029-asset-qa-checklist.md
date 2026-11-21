# 029 资产质检单：铁匠铺角落场景（028）

被检资产：`scenes/028-blacksmith-corner.blend`（58 个场景部件，不含地面）
检查方式：Blender bmesh 实测 + 世界坐标实测，非目测估算。

## 1. 拓扑

| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 最高顶点价数 |
| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | ------------ |
| Anvil_Base | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_Body | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_HardyHole | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_Heel | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_Horn | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Anvil_Pedestal | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_PritchelHole | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Anvil_TopPlate | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Anvil_Waist | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Axe_Blade | 14 | 18 | 12 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| Axe_CuttingEdge | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Axe_Grip | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Axe_Haft | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Axe_Pommel | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Axe_Socket | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Axe_TopWedge | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Barrel_Bottom | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Hoop_12 | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Hoop_45 | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Hoop_78 | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Lid | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Middle | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Barrel_Top | 26 | 36 | 24 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 12 |
| Beam_Back | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Beam_Left | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Brazier_Bowl | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Brazier_Pedestal | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Bucket | 22 | 30 | 20 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| Bucket_Hoop | 22 | 30 | 20 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| Bucket_Water | 22 | 30 | 20 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 10 |
| Coal_0 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Coal_1 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Coal_2 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Ember_0 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Ember_1 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Ember_2 | 12 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 |
| Hammer_Handle | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Hammer_Head | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Ingot_0 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Ingot_1 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Ingot_2 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_00 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_01 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_02 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_03 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_04 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_05 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_06 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_07 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_08 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_09 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_10 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Paver_11 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Post_Corner | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| WallBase_Back | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| WallBase_Left | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Wall_Back | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Wall_Left | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| **合计** | **732** | **852** | **472** | **380** | **0** | **0** | **0** | **0** | **0** | **0** | — |

- N-gon：共 0 个（设计值 0）：通过
- 无重叠顶点：通过
- 无散边 / 无非流形边：通过
- 无退化面（面积≈0）：通过
- 闭合网格（无边界边）：通过

## 2. 法线

- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：通过，倒置面 0 个

## 3. UV

- UV 层存在：通过（58 个部件均已 Smart UV Project 展开）
- UV 超出 0–1 范围：0 个 UV 点，通过
- UV 利用率最低的 5 个部件：
  - Axe_Haft：13.8%
  - Beam_Back：18.8%
  - Beam_Left：22.1%
  - Hammer_Handle：27.3%
  - WallBase_Back：28.9%
  （注：各部件 UV 互不共享空间，不宜相加；细长部件展开后利用率低属正常）
- UV 岛数量：344
- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：0.00%，通过（阈值 <1%）

## 4. 场景结构（实测）

- 角落墙体：后墙 y 2.05–2.35、z 0.00–2.60，左墙 x -2.35–-2.05、z 0.00–2.60；木梁 z 2.34–2.56 / 2.34–2.56 在墙顶之下；角柱 z 0.00–2.60 落地；左墙端头伸入后墙墙身、角部无缝隙：是（注：后墙向左超出左墙外侧 0.35，角部外侧有一小段外露墙端）：通过
- 石板铺地：共 12 块，全部 z 0.00–0.04 贴地：通过
- 铁砧：底座 z 0.00–0.18 落地；砧面顶 z=1.06（设计 1.06）；砧角最远 x=0.64 超出砧身 x=0.12；方孔顶 z=1.07：通过
- 木桶：三段 z 0.00–0.35 / 0.35–0.55 / 0.55–0.90 无缝叠合；桶盖 z 0.87–0.90；三道铁箍半径均大于该高度桶身半径（间隙 0.023 / 0.015 / 0.023）：通过
- 战斧斜靠：战斧与桶身表面的最小水平间隙 0.327（最近点 ('Axe_Grip', 1.225, -0.2, 0.033)，斧柄轴线采样 + 全部顶点实测）；桶沿高度 z=0.90 处斧柄表面离桶身 0.582；斧刃最低 z=0.954（桶顶 z=0.90，斧刃整体高于桶顶）；斧底帽最低 z=-0.013：不通过
- 火盆：石墩 z 0.00–0.50 落地；铁碗 z 0.49–0.75 坐在墩顶；3 块炭块底部均低于碗沿 z=0.75；ForgeGlow 点光源位于 (-1.75, 0.10, 1.15)，能量 250.0W 橙色：通过
- 淬火桶：桶身 z 0.00–0.35 落地；水面 z 0.29–0.31，低于桶沿 0.040：通过
- 地面小件：铁锤柄最低 z=-0.028、锤头 z 0.00–0.07；铁锭叠放（顶层 z 0.07–0.14 在下层之上）：是；煤块最低 z 0.004, 0.004, 0.004：不通过
- 落地检查：共检查 25 个应落地部件，离地部件：无：通过

## 5. 材质 / 贴图

- Wall_Back → `Corner_StoneWall`：图片贴图 无（程序化 Principled 材质）
- Wall_Left → `Corner_StoneWall`：图片贴图 无（程序化 Principled 材质）
- WallBase_Back → `Corner_StoneDark`：图片贴图 无（程序化 Principled 材质）
- WallBase_Left → `Corner_StoneDark`：图片贴图 无（程序化 Principled 材质）
- Beam_Back → `Corner_Beam`：图片贴图 无（程序化 Principled 材质）
- Beam_Left → `Corner_Beam`：图片贴图 无（程序化 Principled 材质）
- Post_Corner → `Corner_Beam`：图片贴图 无（程序化 Principled 材质）
- Paver_00 → `Paver_0`：图片贴图 无（程序化 Principled 材质）
- Paver_01 → `Paver_1`：图片贴图 无（程序化 Principled 材质）
- Paver_02 → `Paver_2`：图片贴图 无（程序化 Principled 材质）
- Paver_03 → `Paver_3`：图片贴图 无（程序化 Principled 材质）
- Paver_04 → `Paver_4`：图片贴图 无（程序化 Principled 材质）
- Paver_05 → `Paver_5`：图片贴图 无（程序化 Principled 材质）
- Paver_06 → `Paver_6`：图片贴图 无（程序化 Principled 材质）
- Paver_07 → `Paver_7`：图片贴图 无（程序化 Principled 材质）
- Paver_08 → `Paver_8`：图片贴图 无（程序化 Principled 材质）
- Paver_09 → `Paver_9`：图片贴图 无（程序化 Principled 材质）
- Paver_10 → `Paver_10`：图片贴图 无（程序化 Principled 材质）
- Paver_11 → `Paver_11`：图片贴图 无（程序化 Principled 材质）
- Anvil_Base → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Anvil_Pedestal → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Anvil_Waist → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Anvil_Body → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Anvil_TopPlate → `Anvil_TopSteel`：图片贴图 无（程序化 Principled 材质）
- Anvil_Horn → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Anvil_Heel → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Anvil_HardyHole → `Anvil_Dark`：图片贴图 无（程序化 Principled 材质）
- Anvil_PritchelHole → `Anvil_Dark`：图片贴图 无（程序化 Principled 材质）
- Barrel_Bottom → `Barrel_Wood`：图片贴图 无（程序化 Principled 材质）
- Barrel_Middle → `Barrel_Wood`：图片贴图 无（程序化 Principled 材质）
- Barrel_Top → `Barrel_Wood`：图片贴图 无（程序化 Principled 材质）
- Barrel_Lid → `Barrel_WoodLight`：图片贴图 无（程序化 Principled 材质）
- Barrel_Hoop_12 → `Barrel_Hoop`：图片贴图 无（程序化 Principled 材质）
- Barrel_Hoop_45 → `Barrel_Hoop`：图片贴图 无（程序化 Principled 材质）
- Barrel_Hoop_78 → `Barrel_Hoop`：图片贴图 无（程序化 Principled 材质）
- Axe_Haft → `Axe_Wood`：图片贴图 无（程序化 Principled 材质）
- Axe_Grip → `Axe_Leather`：图片贴图 无（程序化 Principled 材质）
- Axe_Pommel → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Axe_Socket → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Axe_Blade → `Anvil_Steel`：图片贴图 无（程序化 Principled 材质）
- Axe_CuttingEdge → `Axe_EdgeSteel`：图片贴图 无（程序化 Principled 材质）
- Axe_TopWedge → `Axe_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Brazier_Pedestal → `Corner_StoneDark`：图片贴图 无（程序化 Principled 材质）
- Brazier_Bowl → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Ember_0 → `Ember`：图片贴图 无（程序化 Principled 材质）
- Ember_1 → `Ember`：图片贴图 无（程序化 Principled 材质）
- Ember_2 → `Ember`：图片贴图 无（程序化 Principled 材质）
- Bucket → `Barrel_Wood`：图片贴图 无（程序化 Principled 材质）
- Bucket_Water → `Bucket_Water`：图片贴图 无（程序化 Principled 材质）
- Bucket_Hoop → `Barrel_Hoop`：图片贴图 无（程序化 Principled 材质）
- Hammer_Handle → `Axe_Wood`：图片贴图 无（程序化 Principled 材质）
- Hammer_Head → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Ingot_0 → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Ingot_1 → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Ingot_2 → `Anvil_Iron`：图片贴图 无（程序化 Principled 材质）
- Coal_0 → `Coal`：图片贴图 无（程序化 Principled 材质）
- Coal_1 → `Coal`：图片贴图 无（程序化 Principled 材质）
- Coal_2 → `Coal`：图片贴图 无（程序化 Principled 材质）
- 空材质槽：0 个，通过
- 材质节点值（Principled BSDF 实测 vs 设计值）：
  - Corner_StoneWall：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.3, 0.28, 0.26)（设计 (0.3, 0.28, 0.26)）：通过
  - Corner_StoneDark：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.2, 0.19, 0.19)（设计 (0.2, 0.19, 0.19)）：通过
  - Corner_Beam：metallic 0.00（设计 0.00），roughness 0.90（设计 0.90），底色 (0.32, 0.2, 0.1)（设计 (0.32, 0.2, 0.1)）：通过
  - Anvil_Steel：metallic 0.85（设计 0.85），roughness 0.35（设计 0.35），底色 (0.32, 0.33, 0.37)（设计 (0.32, 0.33, 0.37)）：通过
  - Anvil_TopSteel：metallic 0.90（设计 0.90），roughness 0.18（设计 0.18），底色 (0.62, 0.64, 0.68)（设计 (0.62, 0.64, 0.68)）：通过
  - Anvil_Iron：metallic 0.70（设计 0.70），roughness 0.50（设计 0.50），底色 (0.16, 0.16, 0.18)（设计 (0.16, 0.16, 0.18)）：通过
  - Anvil_Dark：metallic 0.30（设计 0.30），roughness 0.80（设计 0.80），底色 (0.05, 0.05, 0.06)（设计 (0.05, 0.05, 0.06)）：通过
  - Axe_EdgeSteel：metallic 0.90（设计 0.90），roughness 0.15（设计 0.15），底色 (0.62, 0.64, 0.68)（设计 (0.62, 0.64, 0.68)）：通过
  - Axe_Wood：metallic 0.00（设计 0.00），roughness 0.80（设计 0.80），底色 (0.45, 0.28, 0.14)（设计 (0.45, 0.28, 0.14)）：通过
  - Axe_WoodDark：metallic 0.00（设计 0.00），roughness 0.85（设计 0.85），底色 (0.3, 0.18, 0.09)（设计 (0.3, 0.18, 0.09)）：通过
  - Axe_Leather：metallic 0.00（设计 0.00），roughness 0.90（设计 0.90），底色 (0.2, 0.12, 0.08)（设计 (0.2, 0.12, 0.08)）：通过
  - Barrel_Wood：metallic 0.00（设计 0.00），roughness 0.85（设计 0.85），底色 (0.42, 0.27, 0.13)（设计 (0.42, 0.27, 0.13)）：通过
  - Barrel_WoodLight：metallic 0.00（设计 0.00），roughness 0.85（设计 0.85），底色 (0.6, 0.42, 0.22)（设计 (0.6, 0.42, 0.22)）：通过
  - Barrel_Hoop：metallic 0.80（设计 0.80），roughness 0.45（设计 0.45），底色 (0.12, 0.12, 0.13)（设计 (0.12, 0.12, 0.13)）：通过
  - Bucket_Water：metallic 0.10（设计 0.10），roughness 0.10（设计 0.10），底色 (0.1, 0.22, 0.32)（设计 (0.1, 0.22, 0.32)）：通过
  - Coal：metallic 0.00（设计 0.00），roughness 0.90（设计 0.90），底色 (0.04, 0.04, 0.05)（设计 (0.04, 0.04, 0.05)）：通过
  - Paver_0：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.3, 0.3, 0.32)（设计 (0.3, 0.3, 0.32)）：通过
  - Paver_1：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.36, 0.36, 0.38)（设计 (0.36, 0.36, 0.38)）：通过
  - Paver_2：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.26, 0.26, 0.28)（设计 (0.26, 0.26, 0.28)）：通过
  - Paver_3：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.4, 0.39, 0.38)（设计 (0.4, 0.39, 0.38)）：通过
  - Paver_4：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.3, 0.3, 0.32)（设计 (0.3, 0.3, 0.32)）：通过
  - Paver_5：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.36, 0.36, 0.38)（设计 (0.36, 0.36, 0.38)）：通过
  - Paver_6：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.26, 0.26, 0.28)（设计 (0.26, 0.26, 0.28)）：通过
  - Paver_7：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.4, 0.39, 0.38)（设计 (0.4, 0.39, 0.38)）：通过
  - Paver_8：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.3, 0.3, 0.32)（设计 (0.3, 0.3, 0.32)）：通过
  - Paver_9：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.36, 0.36, 0.38)（设计 (0.36, 0.36, 0.38)）：通过
  - Paver_10：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.26, 0.26, 0.28)（设计 (0.26, 0.26, 0.28)）：通过
  - Paver_11：metallic 0.00（设计 0.00），roughness 0.95（设计 0.95），底色 (0.4, 0.39, 0.38)（设计 (0.4, 0.39, 0.38)）：通过
  - Ember：Emission (1.0, 0.3, 0.05)（设计 (1.0, 0.30, 0.05)），强度 3.00（设计 3.0）：通过
- 未使用的设计材质：无
- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）

## 结论

**总体：复核（REVIEW NEEDED）**

未通过项：axe、floor_props。拓扑 / 法线 / UV / 材质实测全部通过，问题只在场景结构，见第 4 节。
