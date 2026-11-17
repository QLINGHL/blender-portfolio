# 005 低模游戏道具：药水瓶

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。

## 结构

- 瓶身：10 边车削轮廓（底座 → 肚 → 肩 → 颈 → 瓶口唇），半透明玻璃
- 药水：瓶内同形缩小液面，液面高度 z = 1.00，亮红药水
- 瓶塞：8 边锥形木塞 + 加宽顶盖
- 标签：贴合瓶肚的弧形羊皮纸标签（面向相机）
- 蜡封：标签上的红色圆形蜡封

## 面数

- 总面数：218（三角面 68，四边面 150，N-gon 0）
- Bottle：100
- Liquid：60
- Cork：40
- Label：6
- WaxSeal：12

## 材质

- Bottle_Glass：半透明青绿玻璃（alpha 0.38，roughness 0.08，不投阴影）
- Potion_Liquid：亮红药水（roughness 0.15）
- Cork_Wood：木色软木塞（roughness 0.85）
- Label_Parchment：羊皮纸标签（roughness 0.9）
- Wax_Seal：深红蜡封（roughness 0.5）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
