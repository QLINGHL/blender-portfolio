# 038 低模游戏道具：铁匠锤

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。铁匠锤直立展示，3/4 俯视角度。

## 结构

- 锤头（HeadBody）：钢块 0.24×0.10×0.10，z 0.73–0.83
- 击面（Face）：浅色钢圆柱沿 X 轴，x 0.12–0.16，r 0.055，16 段
- 击面唇缘（FaceRim）：锻造唇，x 0.155–0.167，r 0.057
- 锤砧/横楔（Peen）：楔形，从锤头 x=-0.12 处半厚 0.05 收至 x=-0.26 处半厚 0.0075，z 0.73–0.83
- 锤柄（Handle）：木质锥形圆柱，z 0.02–0.845，r 0.026→0.020，12 段
- 柄尾帽（Pommel）：深色木，z 0.02–0.08，r 0.030→0.033
- 握把缠皮（GripWrap）：皮革，z 0.14–0.38，r 0.027→0.0255
- 套箍（Collar）：钢环，锤柄入头处，z 0.70–0.73，r 0.030
- 眼楔（EyeWedge）：钢楔 0.036×0.028×0.018，位于柄顶 z 0.848，绕 Z 轴转 0.25 弧度，半沉入柄顶
- 绑带（Strap_1/2）：皮革圆环，z 0.64 / 0.685，环 R 为当地柄半径 +0.001，管 r 0.0055
- 整体约 0.43 m 宽（x -0.26–0.167）× 0.86 m 高

## 面数

- 总面数：558（三角面 168，四边面 390，N-gon 0）
- HeadBody：6
- Face：48
- FaceRim：48
- Peen：6
- Handle：36
- Pommel：36
- GripWrap：36
- Collar：48
- EyeWedge：6
- Strap_1：144
- Strap_2：144

## 绕向自检

绑带为闭合圆环几何，绕向用环中心线检测；其余部件用质心检测。

- HeadBody：内翻面 0
- Face：内翻面 0
- FaceRim：内翻面 0
- Peen：内翻面 0
- Handle：内翻面 0
- Pommel：内翻面 0
- GripWrap：内翻面 0
- Collar：内翻面 0
- EyeWedge：内翻面 0
- Strap_1：内翻面 0
- Strap_2：内翻面 0

## 材质

- Hammer_HeadSteel：锤头/唇缘/套箍深钢（metallic 0.85，roughness 0.45）
- Hammer_FaceSteel：击面浅钢（metallic 0.9，roughness 0.28）
- Hammer_WedgeSteel：眼楔钢（metallic 0.8，roughness 0.4）
- Hammer_Wood：锤柄木色（roughness 0.8）
- Hammer_WoodDark：柄尾帽深木色（roughness 0.85）
- Hammer_Leather：握把缠皮/绑带皮革（roughness 0.9）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
