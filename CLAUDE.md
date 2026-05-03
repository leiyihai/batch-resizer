# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

批量图片尺寸修改工具 — 基于 Python tkinter 的桌面 GUI 应用，支持选择输入/输出文件夹、预设或自定义目标尺寸，批量缩放图片并保留原目录结构和文件名。已通过 PyInstaller 打包为独立 `.exe`。

## 技术栈

- **语言**: Python 3.12
- **GUI**: tkinter + ttk（Python 内置，无额外依赖）
- **图像处理**: Pillow >= 10.0.0
- **打包**: PyInstaller（`--onefile --windowed`）

## 常用命令

```bash
# 开发运行
python main.py

# 打包为独立 exe
pyinstaller --onefile --windowed --name "批量图片尺寸修改工具" main.py
# 输出位置: dist/批量图片尺寸修改工具.exe
```

## 架构

三个文件，职责分离：

- `main.py` — 入口，仅调用 `create_app()` 启动 tkinter 主循环
- `ui.py` — 所有 GUI 逻辑：`ResizerApp` 类管理界面布局、文件夹选择、尺寸选择、运行按钮、进度条。通过 `queue.Queue` + `root.after()` 实现线程安全的进度更新
- `processor.py` — 纯图片处理逻辑，不依赖 UI。`process_images(input_dir, output_dir, target_size, progress_callback)` 遍历图片、缩放、保存，返回 `(成功数, 失败数, 错误列表)`

## 关键设计点

- **线程模型**: 点击"开始处理"后开 `daemon` 线程跑 `processor.process_images()`，通过 `queue.Queue` 将进度/完成消息传回主线程（`_poll_progress` 每 100ms 轮询）。tkinter 不是线程安全的，UI 更新必须在主线程
- **RGBA→RGB 转换**: JPEG 不支持透明通道，`processor.py:42-43` 在保存为 `.jpg/.jpeg` 时自动将 RGBA/LA/P 模式转为 RGB
- **预设尺寸**: 定义在 `ui.py` 的 `PRESET_SIZES` 列表，修改它即可增删预设选项
