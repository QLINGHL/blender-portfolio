# 001 低模游戏道具：宝剑

低多边形游戏武器资产，平面着色（flat shading），干净拓扑。

## 结构

- 剑身：菱形截面，4 段环 + 尖顶收束
- 剑格：横向护手，锥形收窄
- 剑柄：六边形握把，皮革材质
- 剑首：低多边形球形配重

## 面数

- 总面数：81（三角面 32，四边面 49，N-gon 0）
- Blade：17
- Guard：6
- Grip：18
- Pommel：40

## 材质

- Blade_Steel：亮银金属（metallic 1.0，roughness 0.25）
- Guard_Gold：金色金属（metallic 1.0，roughness 0.35）
- Grip_Leather：深棕皮革（roughness 0.9）
- Pommel_Bronze：青铜金属（metallic 1.0，roughness 0.4）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
