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

### FFmpeg（可选依赖）

InkFrame 使用 FFmpeg 将录制的视频转换为 H.264/MP4，并在启用麦克风录音时合并音轨。没有 FFmpeg 时，屏幕录制仍可使用，但音频合并和 H.264/MP4 转换不可用；录制文件可能保留为 AVI。

获取方法：

1. 打开 [FFmpeg 官方下载页](https://ffmpeg.org/download.html)，进入 Windows builds 区域。FFmpeg 官方页面提供 Windows 构建的下载入口。
2. 可选用 [gyan.dev Windows builds](https://www.gyan.dev/ffmpeg/builds/) 的 `ffmpeg-release-essentials.zip`。解压后找到 `bin/ffmpeg.exe`。
3. 将 `ffmpeg.exe` 放在 `InkFrame.exe` 同一目录，或把其所在目录加入 Windows `PATH`，然后重新启动 InkFrame。

本项目不捆绑或分发 FFmpeg。不同 FFmpeg 构建可能采用不同许可证；下载和使用前请查看所选构建的许可说明。

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

构建会生成 `dist/InkFrame.exe`，默认不会捆绑 FFmpeg。程序会尝试使用系统 `PATH` 中的 FFmpeg，也可以将其放在 EXE 旁边。

FFmpeg 不包含在本仓库或默认构建产物中。只有在确认有权分发所用 FFmpeg 构建并履行其许可义务后，才通过 `INKFRAME_BUNDLE_FFMPEG=1` 显式要求捆绑。

## 许可证

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
