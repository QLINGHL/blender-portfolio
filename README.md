# Blender 作品集

Blender 低模建模与三维资产作品集。

## 方向

1. **低模建模**：游戏角色 / 道具资产制作
2. **三维资产质检**：拓扑、法线、UV、材质贴图检查
3. **角色关节拓扑**：绑定准备、动画兼容性检查
4. **大模型 3D 训练数据**：构建、专业标注、复核

## 作品

| 作品 | 方向 | 说明 | 渲染图 |
| ---- | ---- | ---- | ------ |
| 001 低模游戏道具：宝剑 | 低模建模 | 低多边形宝剑，干净拓扑，游戏资产标准 | [renders/001-lowpoly-sword.png](renders/001-lowpoly-sword.png) |
| 002 低模游戏角色 | 低模建模 / 关节拓扑 | 风格化角色，关节处环形拓扑，绑定就绪 | [renders/002-lowpoly-character.png](renders/002-lowpoly-character.png) |
| 003 资产质检单 | 资产质检 | 道具的拓扑 / 法线 / UV / 材质检查表 | [renders/003-asset-qa-sheet.png](renders/003-asset-qa-sheet.png) |
| 004 3D 训练数据样本 | 训练数据 | 多视角渲染 + 标注示例 | [renders/004-training-data-sample.png](renders/004-training-data-sample.png) |

## 目录

- `scenes/`：Blender 场景源文件（.blend）
- `renders/`：渲染成品图

## 工具

- Blender 5.3
- 渲染：Eevee（快速出图）/ Cycles
