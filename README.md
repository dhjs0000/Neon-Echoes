# Neon Echoes

一个基于终端的音游，使用 ANSI 转义序列进行渲染。

![版本](https://img.shields.io/badge/version-0.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![平台](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## 简介

Neon Echoes 是一款轻量级的终端音乐节奏游戏。玩家需要在音符到达判定线时按下对应的按键，获得分数。

## 特性

- 🎵 支持自定义谱面格式（.chart）
- 🎮 4键下落式音游玩法
- 🖥️ 基于 ANSI 转义序列的终端渲染
- 🎹 内置制谱器（Chart Editor）
- 🔊 音频播放支持
- ⚡ 性能优化，流畅运行

## 安装

### 环境要求

- Python 3.8 或更高版本
- 支持 ANSI 转义序列的终端

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 启动游戏（ANSI 版本）

```bash
python main_ansi.py
```

### 启动制谱器

```bash
python chart_editor.py
```

### 启动非 ANSI 版本（备用）

```bash
python main_NoAnsi.py
```

## 游戏控制

游戏支持10个轨道，每个轨道有3个可选按键。当音符到达判定线时，按下对应轨道的任意一个按键即可。

### 轨道按键映射

| 轨道 | 可选按键 | 说明 |
|------|----------|------|
| 轨道 1 | `Q` `A` `Z` | 最左侧轨道 |
| 轨道 2 | `W` `S` `X` | |
| 轨道 3 | `E` `D` `C` | |
| 轨道 4 | `R` `F` `V` | |
| 轨道 5 | `T` `G` `B` | 中间轨道 |
| 轨道 6 | `Y` `H` `N` | |
| 轨道 7 | `U` `J` `M` | |
| 轨道 8 | `I` `K` `,` | |
| 轨道 9 | `O` `L` `.` | |
| 轨道 10 | `P` `;` `'` | 最右侧轨道 |

### 功能按键

| 按键 | 功能 |
|------|------|
| `Space` (空格) | 触发大音符 / 暂停/继续游戏 |
| `↑` `↓` `←` `→` | 菜单导航 |
| `Enter` | 确认选择 |
| `ESC` | 返回/退出 |

## 项目结构

```
.
├── audio/              # 音频文件
│   ├── notes/          # 音效文件
│   └── *.mp3           # 音乐文件
├── charts/             # 谱面文件 (.chart)
├── ansi_renderer.py    # ANSI 渲染器
├── ansi_tui_manager.py # TUI 管理器
├── audio_manager.py    # 音频管理
├── chart_editor.py     # 制谱器
├── chart_parser.py     # 谱面解析器
├── game_engine.py      # 游戏引擎
├── input_handler.py    # 输入处理
├── main_ansi.py        # 主程序入口
└── game_config.json    # 游戏配置
```

## 谱面格式

谱面使用自定义 `.chart` 格式，详细文档请参考 [chart_format_documentation.md](chart_format_documentation.md)。

## 配置

游戏配置存储在 `game_config.json` 中：

```json
{
    "music_volume": 1.0,
    "sfx_volume": 1.0,
    "music_delay": 100,
    "fps": 60,
    "key_bindings": {
        "track_0": "d",
        "track_1": "f",
        "track_2": "j",
        "track_3": "k",
        "pause": " "
    }
}
```

## 依赖

- PySide6 >= 6.4.0（制谱器 GUI）
- pygame >= 2.0.0（音频播放）
- keyboard >= 0.13.5（键盘输入）
- pynput >= 1.7.0（高级键盘事件）
- matplotlib >= 3.7.0（中文显示）

## 版本历史

### 0.1.0
- 初始版本
- 基础游戏功能
- 谱面解析与播放
- ANSI 渲染支持
- 制谱器工具

## 许可证与版权声明

### 许可证

本项目采用 **知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议**（Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License）进行许可。

[![CC BY-NC-SA 4.0](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

**许可协议链接**: https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh

### 版权所有者

**error-0x12** - https://github.com/error-0x12

### 版权声明

#### 原创内容（受 CC BY-NC-SA 4.0 保护）

以下文件和内容受上述许可证保护，版权归属 error-0x12：

- **所有 Python 源代码文件** (`*.py`) - 包括但不限于游戏引擎、渲染器、解析器、编辑器及相关工具
- **所有谱面文件** (`*.chart`) - 包括但不限于 `charts/` 目录下的所有自定义谱面
- **所有文档文件** (`*.md`) - 包括但不限于项目说明、格式规范及技术文档
- **许可证及相关法律文件** - 包括但不限于 LICENSE、NOTICE 等文件

#### 第三方内容（**不受上述许可证保护**）

以下目录中的内容**不属于**原创作者创作，**不享有**上述许可证授予的权利：

- **`audio/` 目录下的音乐文件**（`audio/notes/` 目录中的音效文件除外）
  - 包括但不限于：`Rush E.mp3`、`戏剧性反讽.mp3`、`死别.mp3` 等
  - 这些音乐文件的版权归属于各自的原始创作者或版权持有者
  - 本项目作者 **未获得** 这些音乐文件的正式授权，仅作功能展示用途
  - **使用者需自行确保拥有合法使用这些音乐文件的权利**
  - 如需商业使用或公开分发，请自行联系原始版权方获取授权

#### 例外内容

- **`audio/notes/` 目录** - 该目录下的音效文件（如 `drag.wav`、`hold.wav`、`tab.wav` 等）为项目原创或已获得适当授权，受 CC BY-NC-SA 4.0 保护

### 使用限制与义务

根据 CC BY-NC-SA 4.0 协议，使用本项目原创内容时，您必须：

1. **署名** - 必须给出适当的署名，提供指向本许可证的链接，并指明是否进行了修改
2. **非商业性使用** - 不得将本作品用于商业目的
3. **相同方式共享** - 如对本作品进行混合、转换或基于本作品创作，必须使用与本作品相同的许可协议分发您的贡献

### 免责声明

本软件按"原样"提供，作者不对因使用本软件而产生的任何直接或间接损失承担责任。第三方音乐文件的使用风险由使用者自行承担。

## 贡献

欢迎提交 Issue 和 Pull Request！提交贡献即表示您同意将您的贡献内容在 CC BY-NC-SA 4.0 许可协议下授权给本项目。
