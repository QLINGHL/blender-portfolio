# 012 资产质检单：低模宝箱（010）

被检资产：`scenes/010-lowpoly-chest.blend`（41 个宝箱部件，不含场景地面/灯光/相机）
检查方式：Blender bmesh 实测，非目测估算。

## 1. 拓扑

| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 最高顶点价数 |
| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | ------------ |
| Body_Bottom | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Body_Front | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Body_Back | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Body_Left | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Body_Right | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Inner_Floor | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Rim_Front | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Rim_Back | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Rim_Left | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Rim_Right | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Front_7 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Back_7 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Bottom_7 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Front_7.001 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Back_7.001 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Band_Bottom_7.001 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Hasp_Body | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Padlock | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Padlock_Shankle | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Coin_L0_0 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_1 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_2 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_3 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_4 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_5 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L0_6 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L1_0 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L1_1 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L1_2 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L1_3 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L1_4 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L2_0 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L2_1 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_L2_2 | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Coin_Top | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Gem_Red | 14 | 18 | 12 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| Gem_Blue | 14 | 18 | 12 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 6 |
| Lid | 18 | 23 | 14 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 9 |
| LidBand_7 | 18 | 8 | 0 | 8 | 0 | 0 | 0 | 18 | 0 | 0 | 3 |
| LidBand_7.001 | 18 | 8 | 0 | 8 | 0 | 0 | 0 | 18 | 0 | 0 | 3 |
| LidHasp | 4 | 1 | 0 | 1 | 0 | 0 | 0 | 4 | 0 | 0 | 2 |
| **合计** | **526** | **574** | **294** | **280** | **0** | **0** | **0** | **40** | **0** | **0** | — |

- 无 N-gon（>4 边面）：通过
- 无重叠顶点：通过
- 无散边 / 无非流形边：通过
- 无退化面（面积≈0）：通过
- 边界边：仅出现在设计为开口的 3 个部件（LidBand_7、LidBand_7.001 为单面飘带，LidHasp 为单面四边板），其余 38 个部件均为闭合网格：通过
- 最高顶点价数 8（圆柱盖面中心扇形顶点，属正常结构）；箱体盒子顶点价数 3

## 2. 法线

- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：通过，倒置面 0 个

## 3. UV

- UV 层存在：通过（41 个部件均已 Smart UV Project 展开）
- UV 超出 0–1 范围：0 个 UV 点，通过
- UV 利用率（各部件独立 0–1 空间）：
  - Body_Bottom：72.7%
  - Body_Front：76.7%
  - Body_Back：76.7%
  - Body_Left：60.1%
  - Body_Right：60.1%
  - Inner_Floor：84.0%
  - Rim_Front：15.1%
  - Rim_Back：15.1%
  - Rim_Left：30.5%
  - Rim_Right：30.5%
  - Band_Front_7：38.4%
  - Band_Back_7：38.4%
  - Band_Bottom_7：24.5%
  - Band_Front_7.001：38.4%
  - Band_Back_7.001：38.4%
  - Band_Bottom_7.001：24.5%
  - Hasp_Body：58.8%
  - Padlock：70.2%
  - Padlock_Shankle：68.8%
  - Coin_L0_0：48.3%
  - Coin_L0_1：48.3%
  - Coin_L0_2：48.3%
  - Coin_L0_3：48.3%
  - Coin_L0_4：48.3%
  - Coin_L0_5：48.3%
  - Coin_L0_6：48.3%
  - Coin_L1_0：48.3%
  - Coin_L1_1：48.6%
  - Coin_L1_2：48.3%
  - Coin_L1_3：48.3%
  - Coin_L1_4：48.3%
  - Coin_L2_0：48.3%
  - Coin_L2_1：48.3%
  - Coin_L2_2：48.3%
  - Coin_Top：48.6%
  - Gem_Red：64.0%
  - Gem_Blue：62.0%
  - Lid：66.0%
  - LidBand_7：29.8%
  - LidBand_7.001：29.8%
  - LidHasp：68.3%
  （注：各部件 UV 互不共享空间，不宜相加；圆柱盖面扇形展开后利用率低属正常）
- UV 岛数量：215
- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：0.00%，通过（阈值 <1%）

## 4. 宝箱结构（实测）

- 铰链：盖子原点位于铰链线（y=+0.7, z=0.9），实测位置 (0.0, 0.7, 0.9)；开盖角度 100.0°（设计 100°）：通过
- 随盖转动：父级为 Lid 的部件为 LidBand_7、LidBand_7.001、LidHasp：通过
- 金币/宝石收纳：18 个宝藏部件，全部顶点均在内腔范围（x ±1.1、y ±0.6、z 0.1–0.95）内：通过
- 内腔真实开口（自正上方垂直向下射线检测）：
  - 宝藏正上方首命中：Coin_L2_2（z=0.60）
  - 腔内空角首命中：Inner_Floor（z=0.12，应为 Inner_Floor）
  - 结论：通过

## 5. 材质 / 贴图

- Body_Bottom → `Chest_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Body_Front → `Chest_Wood`：图片贴图 无（程序化 Principled 材质）
- Body_Back → `Chest_Wood`：图片贴图 无（程序化 Principled 材质）
- Body_Left → `Chest_Wood`：图片贴图 无（程序化 Principled 材质）
- Body_Right → `Chest_Wood`：图片贴图 无（程序化 Principled 材质）
- Inner_Floor → `Chest_WoodInner`：图片贴图 无（程序化 Principled 材质）
- Rim_Front → `Chest_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Rim_Back → `Chest_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Rim_Left → `Chest_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Rim_Right → `Chest_WoodDark`：图片贴图 无（程序化 Principled 材质）
- Band_Front_7 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Band_Back_7 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Band_Bottom_7 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Band_Front_7.001 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Band_Back_7.001 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Band_Bottom_7.001 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Hasp_Body → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Padlock → `Brass_Lock`：图片贴图 无（程序化 Principled 材质）
- Padlock_Shankle → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_0 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_1 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_2 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_3 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_4 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_5 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L0_6 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L1_0 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L1_1 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L1_2 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L1_3 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L1_4 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L2_0 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L2_1 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_L2_2 → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Coin_Top → `Gold_Coin`：图片贴图 无（程序化 Principled 材质）
- Gem_Red → `Gem_Red`：图片贴图 无（程序化 Principled 材质）
- Gem_Blue → `Gem_Blue`：图片贴图 无（程序化 Principled 材质）
- Lid → `Chest_Wood`：图片贴图 无（程序化 Principled 材质）
- LidBand_7 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- LidBand_7.001 → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- LidHasp → `Iron_Band`：图片贴图 无（程序化 Principled 材质）
- 空材质槽：0 个，通过
- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）

## 结论

**总体：通过，可进游戏管线**

## 附：本次质检发现并修复的缺陷

- 初测（修复前）：倒置面 123 个——19 个盒子部件（箱体 5 板、内衬底、包边框 4、铁包边 6、锁扣 3）每件 6 面全反，共 114 面；箱盖 9 面（1 个端盖扇形全反 + 底板 1 面）。
- 初测另有：N-gon 36 个——16 枚金币 + 2 颗宝石的圆柱两端盖面各为 8 边 / 6 边 N-gon；重叠顶点 4 个、退化面 4 个、边界边 8 条——均在箱盖：端盖多加了 2 个与弧线端点重合的底板角顶点，扇形三角随之退化、盖口不闭合。
- 验证方法：recalc_face_normals 逐面比对；盒子绕序另用叉积手算核对（底面法线应为 -Z、顶面 +Z、前面 -Y）。
- 影响：Blender Eevee 默认双面渲染，渲染图上看不出来；但游戏引擎开背面剔除时整个箱体会直接看不见，盖面会在接缝处漏光/显黑；N-gon 盖面进引擎也会被强制三角化，面数不可控。
- 修复：改 `scenes/010-lowpoly-chest.py`——`box()` 六面全部反转绕序；`cylinder()` 两端盖面改三角扇形（加中心顶点）；`build_lid()` 删掉每环 2 个重复顶点，端盖改以弧线起点为扇心、两环分别取向（-X / +X），底板四边面绕序修正为朝下。重建 010（面数 334 → 574，三角 294、四边 280、N-gon 0），复测倒置面 0、N-gon 0、重叠顶点 0、退化面 0，边界边 40 条仅在设计开口的 3 个部件（2 条盖带各 18 条 + 盖搭扣 4 条），线框图随之重画（631 段）。
- 其余初测数值与修复后一致（UV、铰链、宝藏收纳、内腔射线均未变）。
