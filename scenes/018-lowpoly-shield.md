# 018 低模游戏道具：圆盾

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。

## 结构

- 盾面：12 边微凸圆盘，半径 0.85，顶点隆起至 z=0.26，木色
- 铁箍：低模圆环（12×6 段，管半径 0.05），沿盾沿一圈
- 盾心：8 边渐细钢质圆顶（底半径 0.23 → 顶 0.07，高 0.20），扣在盾面顶点
- 铆钉：12 颗黄铜八面体铆钉，沿半径 0.68 一圈均布，z 由盾面轮廓插值算出（0.13）
- 背面握把：横向木条（0.55 长）+ 两块连接支架，位于盾背
- 摆放：整盾绕 X 轴 +90° 立起，盾面朝向相机（-Y），中心高 1.0

## 面数

- 总面数：258（三角面 136，四边面 122，N-gon 0）
- Face：48
- Rim：72
- Boss：24
- Rivet_00：8
- Rivet_01：8
- Rivet_02：8
- Rivet_03：8
- Rivet_04：8
- Rivet_05：8
- Rivet_06：8
- Rivet_07：8
- Rivet_08：8
- Rivet_09：8
- Rivet_10：8
- Rivet_11：8
- Grip：6
- Bracket_L：6
- Bracket_R：6

## 材质

- Shield_Wood：盾面木色（roughness 0.75）
- Shield_Iron：铁箍（metallic 0.85）
- Shield_Steel：钢质盾心（metallic 0.9，roughness 0.25）
- Shield_Brass：黄铜铆钉（metallic 0.9）
- Shield_WoodDark：背面握把深木色

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
