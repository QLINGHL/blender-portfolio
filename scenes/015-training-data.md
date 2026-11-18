# 015 3D 训练数据：小木屋场景多视角标注

011 小木屋场景（房屋 + 松树 + 岩石）的多视角训练数据：4 个视角的
逐物体包围盒 + 关键点，全部由相机真实投影算出，不编造。

## 标注对象

- `lowpoly_cabin`（房屋及院落，906 面）：原木墙、山墙、屋顶、脊梁、烟囱、门、
  窗、石阶、石板小径
- `lowpoly_pine`（松树，37 面）：树干 + 三层锥形树冠
- `lowpoly_rocks`（岩石，60 面）：3 块低多边形岩石
- 总面数：1003（与 011 实测一致）

## 视角（4 个，512x512 拼成 1024x1024 样张）

- front（方位 0°，仰角 5.5°）、side（90°，5.3°）、
  back（180°，5.5°）、top45（45°，36.8°）
- 样张：`renders/015-training-data-sample.png`
- 标注 JSON：`scenes/015-training-data-annotations.json`
  （每视角含场景包围盒 + 每物体包围盒 + 关键点，归一化坐标，
  原点左上、y 向下；`panel` 给出该视角在样张中的位置）
- 场景源文件：`scenes/015-cabin-training-data.blend`

## 关键点（真实投影）

- 房屋：屋脊顶点、烟囱顶、门顶、门把手中心
- 松树：树顶、树干底部、第二层树冠左右端
- 岩石：三块岩石各自顶点 + 岩石组中心点

## 面数明细（实测）

- 房屋分项：原木 700、窗 72、门 36、石板路 40、烟囱 18、
  石阶 12、屋顶 12、山墙 10、脊梁 6
- 松树：树干 10、三层树冠各 9；岩石每块 20

## 渲染

- Blender 5.3 / Eevee，1024x1024 样张，三点式影棚灯光
- 构建脚本：`scenes/015-render-views.py`（从 011 的 .blend 导入物体、
  渲染 4 视角并计算标注）、`scenes/015-compose-sample.py`（拼样张）
- 目视检查：4 视角物体完整、构图居中、无全黑/穿帮；top45 视角
  左上角可看到地面边缘（30m 地面在该角度下露出边界），属背景
  小瑕疵，不影响标注与主体构图

## 环境备注（本轮遇到的问题）

- 本轮虚拟机在 23:17 和 23:21 两次更换，系统里 apt 装好的
  mesa-vulkan-drivers 和 libEGL 随旧虚拟机丢失，两次渲染失败。
- 改走持久化方案：把 mesa-vulkan-drivers / libegl-mesa0 /
  libegl1 / libgl1-mesa-dri 的 .deb 下载解压到 `~/workspace/mesa/`，
  Blender 用 `LD_LIBRARY_PATH` + `VK_ICD_FILENAMES` 指向解压后的
  lavapipe 驱动渲染成功；注意 Mesa 25.x 的 ICD 文件名是
  `lvp_icd.json`（不是 `lvp_icd.x86_64.json`），驱动在
  `usr/lib/x86_64-linux-gnu/libvulkan_lvp.so`。
- 一键脚本：`scenes/015-setup-render.sh`（缺库时自动下载解压，
  已有则直接渲染；渲染采样 16）。
- 以后各轮直接复用 `~/workspace/mesa/`，不再需要 apt 安装。
