# 035 低模游戏道具：魔法书

低多边形游戏道具资产，平面着色（flat shading），干净拓扑。合拢的魔法书平放于地面，3/4 俯视角度展示。

## 结构

- 下封面（CoverBottom）：深紫皮革 0.56×0.76×0.018，z 0.000–0.018
- 书页块（PageBlock）：米色 0.50×0.70×0.062，z 0.018–0.080；前切口/天头/地脚各内缩 0.03，书脊侧齐平
- 上封面（CoverTop）：深紫皮革 0.56×0.76×0.018，z 0.080–0.098
- 书脊（Spine）：深色皮革圆柱，沿 Y 轴 x=-0.28，r 0.022，长 0.76，半嵌进书身形成圆脊
- 书页纹（PageLine）：前切口/天头/地脚各 3 条细槽，深米色 0.006 厚，微凸出页块表面 0.002
- 符文环（RuneRing）：黄铜圆环平放于上封面，R 0.14，管 r 0.012，32×8 段
- 符文星（RuneStar）：5 条黄铜细条，72° 均布，0.024×0.26×0.006，交于封面中心
- 宝石（Gem）：紫水晶正八面体，a 0.035，位于封面中心，高出封面约 0.05
- 锁扣（Clasp）：铁质；顶部扣带 0.16×0.05 横跨封面，前切口竖带 0.006×0.05×0.10，顶部圆柱扣钉 r 0.014
- 护角（Corner）：4 块黄铜平板 0.07×0.07×0.006，位于上封面四角
- 书签（Bookmark）：绯红缎带 0.035×0.12×0.004，从地脚伸出书外 0.05
- 整体约 0.56 m 宽 × 0.78 m 深 × 0.115 m 厚（含宝石）

## 面数

- 总面数：468（三角面 48，四边面 420，N-gon 0）
- CoverBottom：6
- PageBlock：6
- CoverTop：6
- Spine：36
- PageLineFore_1：6
- PageLineFore_2：6
- PageLineFore_3：6
- PageLineHead_1：6
- PageLineHead_2：6
- PageLineHead_3：6
- PageLineTail_1：6
- PageLineTail_2：6
- PageLineTail_3：6
- RuneRing：256
- RuneStar_1：6
- RuneStar_2：6
- RuneStar_3：6
- RuneStar_4：6
- RuneStar_5：6
- Gem：8
- ClaspTop：6
- ClaspFront：6
- ClaspStud：24
- Corner_-1-1：6
- Corner_-1+1：6
- Corner_+1-1：6
- Corner_+1+1：6
- Bookmark：6

## 绕向自检

符文环为闭合圆环几何，绕向用环中心线检测（质心检测不适用于环形）；其余部件用质心检测。

- CoverBottom：内翻面 0
- PageBlock：内翻面 0
- CoverTop：内翻面 0
- Spine：内翻面 0
- PageLineFore_1：内翻面 0
- PageLineFore_2：内翻面 0
- PageLineFore_3：内翻面 0
- PageLineHead_1：内翻面 0
- PageLineHead_2：内翻面 0
- PageLineHead_3：内翻面 0
- PageLineTail_1：内翻面 0
- PageLineTail_2：内翻面 0
- PageLineTail_3：内翻面 0
- RuneRing：内翻面 0
- RuneStar_1：内翻面 0
- RuneStar_2：内翻面 0
- RuneStar_3：内翻面 0
- RuneStar_4：内翻面 0
- RuneStar_5：内翻面 0
- Gem：内翻面 0
- ClaspTop：内翻面 0
- ClaspFront：内翻面 0
- ClaspStud：内翻面 0
- Corner_-1-1：内翻面 0
- Corner_-1+1：内翻面 0
- Corner_+1-1：内翻面 0
- Corner_+1+1：内翻面 0
- Bookmark：内翻面 0

## 材质

- Spellbook_Leather：上下封面深紫皮革（roughness 0.8）
- Spellbook_LeatherDark：书脊深色皮革（roughness 0.85）
- Spellbook_Pages：书页米色（roughness 0.9）
- Spellbook_PageLine：书页纹深米色（roughness 0.9）
- Spellbook_Brass：符文环/符文星/护角黄铜（metallic 0.85，roughness 0.35）
- Spellbook_Iron：锁扣铁质（metallic 0.7，roughness 0.5）
- Spellbook_Amethyst：宝石紫水晶（metallic 0.3，roughness 0.2）
- Spellbook_Ribbon：书签绯红缎带（roughness 0.8）

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机自动取景（fit_camera_to_objects，目标填充 78%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定）
