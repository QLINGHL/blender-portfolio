# 017 资产质检单：低模魔法祭坛（016）

被检资产：`scenes/016-lowpoly-altar.blend`（43 个祭坛部件，不含场景地面/灯光/相机）
检查方式：Blender bmesh 实测，非目测估算。

## 1. 拓扑

| 部件 | 顶点 | 面 | 三角 | 四边 | N-gon | 重叠顶点 | 散边 | 边界边 | 非流形边 | 退化面 | 最高顶点价数 |
| ---- | ---- | -- | ---- | ---- | ----- | -------- | ---- | ------ | -------- | ------ | ------------ |
| Platform_Tier1 | 34 | 48 | 32 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| Platform_Tier2 | 34 | 48 | 32 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| Platform_Tier3 | 34 | 48 | 32 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| Step_Low | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Step_High | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Altar_Block | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Altar_Slab | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Rune_Ring | 96 | 96 | 0 | 96 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| RuneStone_0 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_1 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_2 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_3 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_4 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_5 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_6 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RuneStone_7 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_0 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_1 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_2 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_3 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_4 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_5 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_6 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| RunePlate_7 | 8 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| Candle_L_Base | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_L_Stem | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_L_Cup | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_L_Candle | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_L_Flame | 10 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_R_Base | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_R_Stem | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_R_Cup | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_R_Candle | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_R_Flame | 10 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_Tall_Base | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_Tall_Stem | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_Tall_Cup | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_Tall_Candle | 18 | 24 | 16 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Candle_Tall_Flame | 10 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 |
| Crystal_Main | 6 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| Crystal_Shard_0 | 6 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| Crystal_Shard_1 | 6 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| Crystal_Shard_2 | 6 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 |
| **合计** | **628** | **728** | **368** | **360** | **0** | **0** | **0** | **0** | **0** | **0** | — |

- 无 N-gon（>4 边面）：通过
- 无重叠顶点：通过
- 无散边 / 无非流形边：通过
- 无退化面（面积≈0）：通过
- 边界边：全部 43 个部件均为闭合网格，无边界边：通过
- 最高顶点价数 16

## 2. 法线

- 法线朝外一致（与 Blender recalc_face_normals 的外法线逐面比对）：通过，倒置面 0 个

## 3. UV

- UV 层存在：通过（43 个部件均已 Smart UV Project 展开）
- UV 超出 0–1 范围：0 个 UV 点，通过
- UV 利用率（各部件独立 0–1 空间）：
  - Platform_Tier1：43.0%
  - Platform_Tier2：44.0%
  - Platform_Tier3：45.7%
  - Step_Low：80.8%
  - Step_High：82.5%
  - Altar_Block：72.7%
  - Altar_Slab：57.1%
  - Rune_Ring：7.3%
  - RuneStone_0：76.3%
  - RuneStone_1：76.3%
  - RuneStone_2：76.3%
  - RuneStone_3：76.3%
  - RuneStone_4：76.3%
  - RuneStone_5：76.3%
  - RuneStone_6：76.3%
  - RuneStone_7：76.3%
  - RunePlate_0：90.0%
  - RunePlate_1：90.0%
  - RunePlate_2：90.0%
  - RunePlate_3：90.0%
  - RunePlate_4：90.0%
  - RunePlate_5：90.0%
  - RunePlate_6：90.0%
  - RunePlate_7：90.0%
  - Candle_L_Base：60.8%
  - Candle_L_Stem：48.3%
  - Candle_L_Cup：64.8%
  - Candle_L_Candle：66.6%
  - Candle_L_Flame：40.9%
  - Candle_R_Base：60.8%
  - Candle_R_Stem：48.3%
  - Candle_R_Cup：64.8%
  - Candle_R_Candle：66.6%
  - Candle_R_Flame：40.9%
  - Candle_Tall_Base：60.8%
  - Candle_Tall_Stem：29.9%
  - Candle_Tall_Cup：64.8%
  - Candle_Tall_Candle：66.6%
  - Candle_Tall_Flame：23.8%
  - Crystal_Main：30.1%
  - Crystal_Shard_0：30.1%
  - Crystal_Shard_1：30.1%
  - Crystal_Shard_2：30.1%
  （注：各部件 UV 互不共享空间，不宜相加；圆柱盖面扇形展开后利用率低属正常）
- UV 岛数量：247
- UV 重叠（512 网格内点采样，仅计不同 UV 岛之间，最高单部件）：0.00%，通过（阈值 <1%）

## 4. 祭坛结构（实测）

- 符文环：圆环中心 z=1.11（设计 1.11），最低点 z=1.05（三层石台顶面 z=1.05，应贴合）：通过
- 符文石：8 块立石，中心半径均为 2.00，角度间隔 45°，向外倾斜 8°：
  - RuneStone_0：半径 2.00，角度 0.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_1：半径 2.00，角度 45.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_2：半径 2.00，角度 90.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_3：半径 2.00，角度 135.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_4：半径 2.00，角度 180.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_5：半径 2.00，角度 225.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_6：半径 2.00，角度 270.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - RuneStone_7：半径 2.00，角度 315.0°，倾斜 8.0°，最低点 z=0.696（二层石台顶面 z=0.70，倾斜使一侧边缘略沉入台面，属设计内）
  - 结论：通过
- 悬浮水晶：主水晶最低点 z=2.70，祭坛顶板顶面 z=2.07，悬空 0.63；3 颗碎片最低点 z=2.77 / 3.12 / 2.87，均高于三层石台顶面 z=1.05：通过
- 烛火对接（火焰锥底 = 蜡烛顶）：
  - Candle_L：蜡烛顶 z=2.73，火焰底 z=2.73，间隙 0.000；蜡烛底部沉入烛杯 0.00
  - Candle_R：蜡烛顶 z=2.73，火焰底 z=2.73，间隙 0.000；蜡烛底部沉入烛杯 0.00
  - Candle_Tall：蜡烛顶 z=1.91，火焰底 z=1.91，间隙 0.000；蜡烛底部沉入烛杯 0.00
  - 结论：通过

## 5. 材质 / 贴图

- Platform_Tier1 → `Altar_StoneDark`：图片贴图 无（程序化 Principled 材质）
- Platform_Tier2 → `Altar_StoneMid`：图片贴图 无（程序化 Principled 材质）
- Platform_Tier3 → `Altar_StoneLight`：图片贴图 无（程序化 Principled 材质）
- Step_Low → `Altar_StoneMid`：图片贴图 无（程序化 Principled 材质）
- Step_High → `Altar_StoneLight`：图片贴图 无（程序化 Principled 材质）
- Altar_Block → `Altar_Block`：图片贴图 无（程序化 Principled 材质）
- Altar_Slab → `Altar_StoneLight`：图片贴图 无（程序化 Principled 材质）
- Rune_Ring → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_0 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_0 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_1 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_1 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_2 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_2 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_3 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_3 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_4 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_4 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_5 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_5 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_6 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_6 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- RuneStone_7 → `Rune_Stone`：图片贴图 无（程序化 Principled 材质）
- RunePlate_7 → `Rune_Glow`：图片贴图 无（程序化 Principled 材质）
- Candle_L_Base → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_L_Stem → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_L_Cup → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_L_Candle → `Candle_Wax`：图片贴图 无（程序化 Principled 材质）
- Candle_L_Flame → `Candle_Flame`：图片贴图 无（程序化 Principled 材质）
- Candle_R_Base → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_R_Stem → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_R_Cup → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_R_Candle → `Candle_Wax`：图片贴图 无（程序化 Principled 材质）
- Candle_R_Flame → `Candle_Flame`：图片贴图 无（程序化 Principled 材质）
- Candle_Tall_Base → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_Tall_Stem → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_Tall_Cup → `Altar_Brass`：图片贴图 无（程序化 Principled 材质）
- Candle_Tall_Candle → `Candle_Wax`：图片贴图 无（程序化 Principled 材质）
- Candle_Tall_Flame → `Candle_Flame`：图片贴图 无（程序化 Principled 材质）
- Crystal_Main → `Altar_Crystal`：图片贴图 无（程序化 Principled 材质）
- Crystal_Shard_0 → `Altar_Crystal`：图片贴图 无（程序化 Principled 材质）
- Crystal_Shard_1 → `Altar_Crystal`：图片贴图 无（程序化 Principled 材质）
- Crystal_Shard_2 → `Altar_Crystal`：图片贴图 无（程序化 Principled 材质）
- 空材质槽：0 个，通过
- 自发光材质（节点实测 Emission Strength）：
  - Rune_Glow：设计 1.8，实测 1.8：通过
  - Altar_Crystal：设计 1.4，实测 1.4：通过
  - Candle_Flame：设计 2.5，实测 2.5：通过
- 贴图分辨率：不适用（本资产无图片贴图，全部程序化材质）

## 结论

**总体：通过，可进游戏管线**

## 附：本次质检发现并修复的缺陷

- 初测（修复前）：倒置面 168 个——20 个盒子部件（2 级台阶、祭坛块、顶板、8 块符文石、8 块符文板）每件 6 面全反，共 120 面；3 支烛火锥每件 16 面全反（侧面 8 + 底面扇形 8），共 48 面。
- 验证方法：recalc_face_normals 逐面比对；盒子绕序另用叉积手算核对（底面法线应为 -Z、顶面 +Z）；锥体侧面与底面扇形分别手算核对。
- 影响：Blender Eevee 默认双面渲染，渲染图上看不出来；但游戏引擎开背面剔除时 20 个盒子部件 + 3 支烛火会直接看不见。这是 012 在 010 宝箱上发现过的同类绕序 bug，016 的 `box()` / `cone()` 是另一份拷贝，未同步修正。
- 修复：改 `scenes/016-lowpoly-altar.py`——`box()` 六面全部反转绕序（与 010 修正后一致）；`cone()` 侧面与底面扇形绕序反转。重建 016（面数 728 不变，三角 368、四边 360、N-gon 0），复测倒置面 0，其余初测数值与修复后一致（UV、符文环、符文石、水晶悬空、烛火对接、自发光强度均未变）。
- 另：初测烛火项曾判不通过，原因是质检脚本的判定条件写错（要求蜡烛底部“沉入”烛杯 > 0）；实测蜡烛底部 z 与烛杯顶面 z 完全相等（2.51），是恰好搭在杯口、无缝隙、无悬空，属正确结构。已修正脚本判定条件（沉入 ≥ -0.001 即通过），复测通过。
