# 009 3D 训练数据：多物体场景（宝剑 + 药水瓶）多视角标注

多物体 3D 训练数据样本：把 001 低模宝剑与 005 低模药水瓶放进同一场景，
4 个视角渲染，每个视角给每个物体单独的包围盒与关键点标注，全部由相机
投影真实算出（不编造）。

## 场景

- 宝剑（001，81 面）立于 x = -0.95，药水瓶（005，218 面）立于 x = +0.95，
  双双立于 z = 0 地面
- 总面数：299（宝剑 81：Blade 17、Guard 6、Grip 18、Pommel 40；
  药水瓶 218：Bottle 100、Liquid 60、Cork 40、Label 6、WaxSeal 12）
- 地面 30x30（俯视 45° 时不穿帮），三点式影棚灯光

## 视角与标注

4 个视角：front（方位 0°）、side（90°）、back（180°）、top45（45°、仰角 36.4°），
每视角 512x512，拼成 1024x1024 样张 `renders/009-training-data-sample.png`。

标注文件 `scenes/009-training-data-annotations.json`，每个视角含：

- `scene_bbox`：两物体整体包围盒
- 每个物体独立的 `bbox` 与 `keypoints`
  - 宝剑：tip（剑尖）、guard_left / guard_right（剑格两端）、pommel（剑首底）
  - 药水瓶：cork_top（瓶塞顶）、bottle_base_left / bottle_base_right（瓶底两端）、
    wax_seal_center（蜡封中心）
- 坐标：各视角面板内归一化 0–1，原点左上、y 向下；`panel` 给出该视角在
  1024x1024 样张中的位置

## 渲染

- Blender 5.3 / Eevee，1024x1024 样张，三点式影棚灯光
- 构建脚本：`scenes/009-render-views.py`（从 001、005 的 .blend append 物体，
  渲染 4 视角并投影算标注）、`scenes/009-compose-sample.py`（拼 2x2 样张）

## 制作手记

- 首版标注有偏差：移动物体后未刷新 depsgraph，`matrix_world` 仍是旧值，
  包围盒算成了两物体重叠在原点的样子。已用 `009-recompute-annotations.py`
  （`view_layer.update()` 后重算）修正，修正后的包围盒与画面实测一致
  （正面宝剑 x 0.267–0.383、药水瓶 x 0.609–0.741）。
- top45 初版地面 12x12 边缘穿帮进画面，已把地面放大到 30x30 并只重渲
  top45 一张（`009-fix-top45.py`）。
- 本轮还发现：换机后 `mesa-vulkan-drivers` 与 libEGL 未装，Eevee 无法启动；
  已用 sudo 装回（mesa-vulkan-drivers 25.2.8、libegl1），后续轮次若再换机
  需复查。
