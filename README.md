# InkFrame

InkFrame 是一款面向 Windows 的屏幕录制与实时标注工具，支持全屏、指定区域和应用窗口录制，并可在录制期间绘制标注或放大屏幕局部。

## 功能

- 全屏、区域和应用窗口录制
- 实时矩形、椭圆、直线、箭头、画笔和文本标注
- 局部放大，支持调整放大倍数
- 麦克风音频录制与输出设置
- 精简控制模式和全局快捷键

## 环境要求

- Windows 10/11
- Python 3.8 或更高版本
- FFmpeg：可选。未安装时仍可录制视频，但音视频合并及 H.264 转码需要 FFmpeg。

## 安装与运行

```powershell
git clone https://github.com/ozparsec/inkframe.git
cd inkframe
python -m pip install -r requirements.txt
python main.py
```

如需音频合并和 H.264 转码，请安装 FFmpeg 并确保 `ffmpeg.exe` 位于系统 `PATH` 中，或将其放在项目根目录。

## 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+Alt+R` | 开始/停止录制 |
| `Ctrl+Alt+P` | 暂停/恢复录制 |
| `Ctrl+Alt+D` | 切换标注模式 |
| `Ctrl+M` | 切换精简模式 |
| `R` / `E` / `L` | 矩形 / 椭圆 / 直线 |
| `A` / `P` / `T` | 箭头 / 画笔 / 文本 |
| `Z` | 局部放大工具 |
| `Delete` | 清除所有标注 |
| `Ctrl+Z` / `Ctrl+Y` | 撤销 / 重做 |
| `Esc` | 退出标注模式 |
| `+` / `-` | 调节放大倍数 |

## 构建 Windows 可执行文件

```powershell
python -m pip install pyinstaller
pyinstaller --noconfirm InkFrame.spec
```

构建会生成 `dist/InkFrame.exe`。如果项目根目录存在 `ffmpeg.exe`，构建配置会将其一并捆绑；否则程序会尝试使用系统 `PATH` 中的 FFmpeg。

FFmpeg 不包含在本仓库中。请从 FFmpeg 官方渠道获取，并遵守其适用的许可证条款。

## 许可证

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
