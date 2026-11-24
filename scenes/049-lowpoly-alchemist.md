# 049 低模游戏角色：炼金术士

低多边形风格化炼金术士，平面着色（flat shading），绑定就绪。接 047 炼金实验室场景的人物线。

## 造型

- 头部：皮肤球头 + 棕色发盖 + 灰色短须 + 前额黄铜护目镜（双圆环镜框 + 绿色镜片 + 绕头皮带），护目镜推上额头
- 上身：深青长袍（5 环，自肩部微喇叭下摆至脚踝）+ 深青披肩 + 棕色皮围裙（前片 + 兜 + 双肩带）
- 腰部：深棕皮带 + 黄铜带扣，正面挂三瓶药水（红 / 蓝 / 紫，瓶身 + 瓶塞）
- 双手身前持一只锥形烧瓶：透明玻璃锥体 + 瓶颈 + 瓶塞，内装亮绿药液；烧瓶中心 y=-0.48，位于围裙前片（y≈-0.38）前方 0.10，正面清晰可见（042 教训）
- 腿部藏于袍下：灰裤 + 深棕皮鞋，鞋尖从袍摆前探出，鞋底 z=0 落地

## 关节拓扑（绑定就绪）

- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）
- 腿部：5 个环形边线，中间环正好落在膝关节
- 手腕另有皮质袖口（2 环），不遮挡肘部关节环
- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配
- 关节处无三角面集中、无极点（pole）堆积
- N-gon 均为圆柱体端盖（颈、领口、披肩、长袍、皮带、袖口、裤腿、药水瓶等），不在关节处

## 面数

- 总面数：1004（三角面 392，四边面 612，N-gon 0）
- Head：48
- Eye：18
- Eye.001：18
- HairCap：40
- Beard：40
- GoggleRim：48
- GoggleLens：24
- GoggleRim.001：48
- GoggleLens.001：24
- GoggleStrap：64
- Neck：18
- Collar：24
- Shawl：32
- Robe：48
- Apron：6
- ApronPocket：6
- ApronStrap：6
- ApronStrap.001：6
- Belt：24
- Buckle：6
- PotionRedBody：24
- PotionRedCork：18
- PotionBlueBody：24
- PotionBlueCork：18
- PotionPurpleBody：24
- PotionPurpleCork：18
- Arm：36
- Cuff：18
- Hand：24
- Arm.001：36
- Cuff.001：18
- Hand.001：24
- Flask：40
- FlaskLiquid：32
- FlaskCork：18
- Leg：36
- Shoe：6
- Leg.001：36
- Shoe.001：6

## 材质

- Robe_Teal / Robe_Dark：深青长袍与深青披肩
- Apron_Brown / Apron_Dark：棕色围裙与围裙兜；Leather_Dark：皮带、皮鞋、护目镜带
- Brass：护目镜框、带扣；Lens_Green：护目镜镜片
- Flask_Glass / Flask_Liquid：烧瓶玻璃与亮绿药液；Potion_Red/Blue/Purple：三瓶药水
- Skin / Eyes_Dark / Hair_Brown / Beard_Grey：皮肤、眼睛、棕发、灰须

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线
