# 010 低模游戏道具：宝箱（可开盖）

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。

## 结构

- 箱体：5 块板拼出真实内腔（底 + 前后左右壁，壁厚 0.10），内衬底板 + 顶部包边框
- 箱盖：8 段半圆拱形盖，铰链在后沿（y=+0.7, z=0.9），绕 X 轴打开 100°
- 金币堆：16 枚 8 边金币，三层堆叠（7/5/3）+ 顶层 1 枚，金色金属材质
- 宝石：红、蓝宝石各 1 枚，堆在金币顶上
- 铁包边：箱体前后 + 底部各 2 道，箱盖前唇 2 道（随盖转动）
- 锁扣：箱体前板铁搭扣 + 黄铜挂锁 + 锁梁

## 面数

- 总面数：574（三角面 294，四边面 280，N-gon 0）
- Body_Bottom：6
- Body_Front：6
- Body_Back：6
- Body_Left：6
- Body_Right：6
- Inner_Floor：6
- Rim_Front：6
- Rim_Back：6
- Rim_Left：6
- Rim_Right：6
- Band_Front_7：6
- Band_Back_7：6
- Band_Bottom_7：6
- Band_Front_7.001：6
- Band_Back_7.001：6
- Band_Bottom_7.001：6
- Hasp_Body：6
- Padlock：6
- Padlock_Shankle：6
- Coin_L0_0：24
- Coin_L0_1：24
- Coin_L0_2：24
- Coin_L0_3：24
- Coin_L0_4：24
- Coin_L0_5：24
- Coin_L0_6：24
- Coin_L1_0：24
- Coin_L1_1：24
- Coin_L1_2：24
- Coin_L1_3：24
- Coin_L1_4：24
- Coin_L2_0：24
- Coin_L2_1：24
- Coin_L2_2：24
- Coin_Top：24
- Gem_Red：18
- Gem_Blue：18
- Lid：23
- LidBand_7：8
- LidBand_7.001：8
- LidHasp：1

## 材质

- Chest_Wood：箱体木色（roughness 0.8）
- Chest_WoodDark：底板 / 包边深木色
- Iron_Band：铁包边（metallic 0.85）
- Gold_Coin：金币（metallic 0.9）
- Gem_Red / Gem_Blue：红蓝宝石
- Brass_Lock：黄铜挂锁（metallic 0.9）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
