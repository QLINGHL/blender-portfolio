# 011 低模场景：小木屋

低多边形环境场景资产，平面着色（flat shading），干净拓扑。

## 结构

- 原木墙：8 排 8 边原木叠砌（前/后墙沿 X、侧墙沿 Y），前墙门洞处 6 排原木左右分段留出 0.95m 宽门洞
- 端头圆盘：前后墙两端各 8 个原木截面圆盘（浅色木纹）
- 山墙：两侧三角形棱柱，墙高 2.24m、山墙高 1.10m
- 屋顶：两块斜坡板（坡角约 36°，出檐 0.45m）+ 脊梁
- 烟囱：砖砌烟囱 + 石盖板，立于后坡屋顶
- 门：木门板 + 门框 + 竖纹饰条 + 黄铜把手，门前两级石阶
- 窗：前墙两扇（框 + 玻璃 + 十字窗棂 + 石窗台），后墙一扇
- 环境：松树 1 棵（三层锥形树冠 + 树干）、低多边形岩石 3 块、石板小径 4 块

## 面数

- 总面数：1003（三角面 88，四边面 762，N-gon 153）
- Log_Front_R0_L：10
- Log_Front_R0_R：10
- Log_Back_R0：10
- Log_Side_R0_L：10
- Log_Side_R0_R：10
- Log_Front_R1_L：10
- Log_Front_R1_R：10
- Log_Back_R1：10
- Log_Side_R1_L：10
- Log_Side_R1_R：10
- Log_Front_R2_L：10
- Log_Front_R2_R：10
- Log_Back_R2：10
- Log_Side_R2_L：10
- Log_Side_R2_R：10
- Log_Front_R3_L：10
- Log_Front_R3_R：10
- Log_Back_R3：10
- Log_Side_R3_L：10
- Log_Side_R3_R：10
- Log_Front_R4_L：10
- Log_Front_R4_R：10
- Log_Back_R4：10
- Log_Side_R4_L：10
- Log_Side_R4_R：10
- Log_Front_R5_L：10
- Log_Front_R5_R：10
- Log_Back_R5：10
- Log_Side_R5_L：10
- Log_Side_R5_R：10
- Log_Front_R6：10
- Log_Back_R6：10
- Log_Side_R6_L：10
- Log_Side_R6_R：10
- Log_Front_R7：10
- Log_Back_R7：10
- Log_Side_R7_L：10
- Log_Side_R7_R：10
- LogEnd_F_R0_L：10
- LogEnd_B_R0_L：10
- LogEnd_F_R0_R：10
- LogEnd_B_R0_R：10
- LogEnd_F_R1_L：10
- LogEnd_B_R1_L：10
- LogEnd_F_R1_R：10
- LogEnd_B_R1_R：10
- LogEnd_F_R2_L：10
- LogEnd_B_R2_L：10
- LogEnd_F_R2_R：10
- LogEnd_B_R2_R：10
- LogEnd_F_R3_L：10
- LogEnd_B_R3_L：10
- LogEnd_F_R3_R：10
- LogEnd_B_R3_R：10
- LogEnd_F_R4_L：10
- LogEnd_B_R4_L：10
- LogEnd_F_R4_R：10
- LogEnd_B_R4_R：10
- LogEnd_F_R5_L：10
- LogEnd_B_R5_L：10
- LogEnd_F_R5_R：10
- LogEnd_B_R5_R：10
- LogEnd_F_R6_L：10
- LogEnd_B_R6_L：10
- LogEnd_F_R6_R：10
- LogEnd_B_R6_R：10
- LogEnd_F_R7_L：10
- LogEnd_B_R7_L：10
- LogEnd_F_R7_R：10
- LogEnd_B_R7_R：10
- Gable_L：5
- Gable_R：5
- Roof_F：6
- Roof_B：6
- RidgeBeam：6
- Chimney：6
- Chimney_Cap：6
- Chimney_Top：6
- Door_Frame_L：6
- Door_Frame_R：6
- Door_Frame_Top：6
- Door_Panel：6
- Door_Plank_V：6
- Door_Handle：6
- Step_1：6
- Step_2：6
- Window_Frame_13：6
- Window_Glass_13：6
- Window_BarV_13：6
- Window_BarH_13：6
- Window_Sill_13：6
- Window_Frame_13.001：6
- Window_Glass_13.001：6
- Window_BarV_13.001：6
- Window_BarH_13.001：6
- Window_Sill_13.001：6
- Window_Back_Frame：6
- Window_Back_Glass：6
- Pine_Trunk：10
- Pine_Cone_0：9
- Pine_Cone_1：9
- Pine_Cone_2：9
- Rock_0：20
- Rock_1：20
- Rock_2：20
- PathStone_0：10
- PathStone_1：10
- PathStone_2：10
- PathStone_3：10

## 材质

- Cabin_Log：原木（roughness 0.85）
- Cabin_LogEnd：原木截面浅色
- Cabin_Roof：深红棕屋顶
- Cabin_Gable：山墙木色
- Cabin_Door：深色木门；Cabin_Frame：浅色窗框/门框
- Cabin_Glass：蓝灰玻璃（roughness 0.15）
- Cabin_Stone：石阶/窗台/石板；Cabin_Brick：砖烟囱
- Pine_Needles：松针绿；Pine_Trunk：树干棕

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
