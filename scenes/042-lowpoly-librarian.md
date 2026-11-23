# 042 低模游戏角色：图书管理员

低多边形风格化图书管理员，平面着色（flat shading），绑定就绪。

## 造型

- 头部：皮肤球头 + 灰发（顶部发盖 + 脑后发髻）+ 圆框黄铜眼镜（双圆环镜框 + 鼻梁 + 镜腿）
- 上身：酒红长袍（5 环，自肩部微喇叭下摆至脚踝）+ 深红披肩 + 奶油色领口
- 腰部：深棕皮带 + 黄铜带扣（正面）
- 双臂前伸怀抱一本皮面书：红色书封 + 奶油书页 + 黄铜锁扣，书身微向前倾 8°
- 腿部藏于袍下：灰裤 + 深棕皮鞋，鞋尖从袍摆前探出

## 关节拓扑（绑定就绪）

- 手臂：5 个环形边线，中间环正好落在肘关节（肘部可弯曲不断裂）
- 腿部：5 个环形边线，中间环正好落在膝关节
- 手腕另有奶油袖口（2 环），不遮挡肘部关节环
- 肩 / 腕 / 踝 / 髋各有独立环，便于蒙皮权重分配
- 关节处无三角面集中、无极点（pole）堆积
- N-gon 均为圆柱体端盖（颈、领口、披肩、长袍、皮带、袖口、裤腿等），不在关节处

## 面数

- 总面数：706（三角面 268，四边面 438，N-gon 0）
- Head：48
- Eye：18
- Eye.001：18
- HairCap：40
- HairBun：40
- GlassesRim：48
- GlassesRim.001：48
- GlassesBridge：12
- GlassesTemple：12
- GlassesTemple.001：12
- Neck：18
- Collar：24
- Shawl：32
- Robe：48
- Belt：24
- Buckle：6
- Arm：36
- Cuff：18
- Hand：24
- Arm.001：36
- Cuff.001：18
- Hand.001：24
- BookCover：6
- BookPages：6
- BookClasp：6
- Leg：36
- Shoe：6
- Leg.001：36
- Shoe.001：6

## 材质

- Robe_Burgundy / Robe_Dark：酒红长袍与深红披肩
- Collar_Cream / Pages_Cream：奶油领口与书页
- Leather_Brown / Leather_Dark：皮带、皮鞋；Brass：眼镜、带扣、书锁扣
- Skin / Eyes_Dark / Hair_Grey：皮肤、眼睛、灰发；Book_Red：书封

## 渲染

- Blender 5.3 / Eevee，1024x1024，三点式影棚灯光，40mm 镜头
- 相机用 fit_camera_to_objects 自动取景（目标填充 78%%）
- 线框图：同角度，美观渲染 + 真实投影边线叠加（可见边判定），可见关节环形边线
