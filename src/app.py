#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用主类 - 整合所有模块
"""

import os
import numpy as np
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
import keyboard
import threading
from PySide6.QtCore import QObject, Signal

class HotkeyManager(QObject):
    """全局快捷键管理器"""
    hotkey_triggered = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._hotkeys = {}
        self._running = True
        
    def register(self, hotkey, callback):
        """注册快捷键"""
        # 将Qt风格快捷键转换为keyboard风格
        # Ctrl+` -> ctrl+grave
        # Ctrl+~ -> ctrl+grave (容错处理)
        k_hotkey = hotkey.lower().replace("`", "grave").replace("~", "grave")
        
        # 处理 ` 符号在不同键盘布局可能的问题，虽然 "ctrl+`" 通常能工作
        # 但 keyboard 库可能对某些符号有特定别名要求
        # 暂时保持直接传递，增加日志
        
        # 移除旧的
        if k_hotkey in self._hotkeys:
            try:
                keyboard.remove_hotkey(self._hotkeys[k_hotkey])
            except:
                pass
                
        # 注册新的
        try:
            handler = keyboard.add_hotkey(k_hotkey, lambda: self.hotkey_triggered.emit(hotkey), suppress=True)
            self._hotkeys[k_hotkey] = handler
        except Exception as e:
            print(f"Failed to register hotkey {hotkey}: {e}")
            
    def unregister_all(self):
        """注销所有快捷键"""
        keyboard.unhook_all()

from .ui.main_window import MainWindow
from .ui.region_selector import RegionSelector
from .ui.window_selector import WindowSelector
from .overlay.canvas import AnnotationCanvas
from .core.screen_capture import ScreenCapture
from .core.video_encoder import VideoEncoder, generate_output_path
from .core.audio_recorder import AudioRecorder
from .utils.config import Config


class ScreenRecorderApp(MainWindow):
    """录屏应用主类"""
    
    # 定义信号
    recording_started = Signal()
    recording_stopped = Signal(str)  # filename
    recording_paused = Signal()
    recording_resumed = Signal()
    error_occurred = Signal(str)

    
    def __init__(self):
        super().__init__()
        
        # 加载配置
        self._config = Config.load()
        
        # 初始化组件
        self._screen_capture = ScreenCapture(fps=self._config.fps)
        self._video_encoder: Optional[VideoEncoder] = None
        self._annotation_canvas = AnnotationCanvas()
        self._region_selector = RegionSelector()
        self._hotkey_manager = HotkeyManager()
        
        # 鼠标点击高亮
        
        self._audio_recorder = None
        
        # 连接信号
        self._connect_signals()
        self._setup_global_hotkeys()
        
        # 设置帧回调
        self._screen_capture.set_frame_callback(self._on_frame_captured)
        
        # 录制区域
        self._record_region: Optional[Tuple[int, int, int, int]] = None  # (left, top, width, height)
        self._record_mode = "fullscreen"  # fullscreen, region, window
        
    def _connect_signals(self):
        """连接信号"""
        # 控制面板信号
        panel = self.control_panel
        panel.start_recording.connect(self._start_recording)
        panel.pause_recording.connect(self._pause_recording)
        panel.stop_recording.connect(self._stop_recording)
        panel.toggle_annotation.connect(self._toggle_annotation)
        panel.region_mode_changed.connect(self._on_region_mode_changed)
        panel.select_region_clicked.connect(self._show_region_selector)
        panel.select_window_clicked.connect(self._show_window_selector)
        
        # 工具栏信号
        toolbar = self.toolbar
        toolbar.tool_selected.connect(self._annotation_canvas.set_tool)
        toolbar.color_changed.connect(self._annotation_canvas.set_color)
        toolbar.width_changed.connect(self._annotation_canvas.set_line_width)
        toolbar.zoom_scale_changed.connect(self._annotation_canvas.set_zoom_scale)
        toolbar.undo_clicked.connect(self._annotation_canvas.undo)
        toolbar.redo_clicked.connect(self._annotation_canvas.redo)
        toolbar.clear_clicked.connect(self._annotation_canvas.clear)
        
        # 区域选择器信号
        self._region_selector.region_selected.connect(self._on_region_selected)
        self._region_selector.selection_cancelled.connect(self._on_region_cancelled)
        
        # 标注模式快捷键
        # self._annotation_shortcut = QShortcut(QKeySequence(self._config.hotkey_annotate), self)
        # self._annotation_shortcut.activated.connect(self._toggle_annotation_shortcut)
        
        # 全局快捷键信号
        # 全局快捷键信号
        self._hotkey_manager.hotkey_triggered.connect(self._on_global_hotkey)
        
        
        # 鼠标点击信号

        # 错误信号
        self.error_occurred.connect(self._on_error_occurred)


    def _setup_global_hotkeys(self):
        """设置全局快捷键"""
        self._hotkey_manager.register(self._config.hotkey_start_stop, lambda: None) # 仅用于触发信号
        self._hotkey_manager.register(self._config.hotkey_pause, lambda: None)
        self._hotkey_manager.register(self._config.hotkey_annotate, lambda: None)
        
    def _on_global_hotkey(self, hotkey: str):
        """处理全局快捷键"""
        # 规范化 hotkey 以匹配 config 中的定义 (config 是原始字符串，hotkey可能是小写)
        # 简单做大小写不敏感比较
        target_hotkey = hotkey.lower()
        
        if target_hotkey == self._config.hotkey_start_stop.lower():
            # 开始/停止
            if self.control_panel.is_recording:
                self.control_panel._on_stop_clicked()
            else:
                self.control_panel._on_record_clicked()
                
        elif target_hotkey == self._config.hotkey_pause.lower():
            # 暂停/恢复
            if self.control_panel.is_recording:
                self.control_panel._on_pause_clicked()
                
        elif target_hotkey == self._config.hotkey_annotate.lower():
            # 切换标注
            self._toggle_annotation_shortcut()
        
    def _start_recording(self):
        """开始录制"""
        try:
            # 确保未在新线程中（Qt限制）
            if self._video_encoder is not None:
                return
                
            # 初始化录制
            filename = generate_output_path(self._config.output_dir, "recording")
            self._video_encoder = VideoEncoder(
                filename, 
                fps=self._config.fps,
                frame_size=(
                    self._record_region[2],
                    self._record_region[3]
                ) if self._record_region else None
            )
            
            # 设置录制区域
            self._screen_capture.set_region(self._record_region)
            
            # 开始录制音频（如果启用）
            # 优先使用UI按钮状态
            if self.control_panel._audio_btn.isChecked():
                audio_path = filename.rsplit('.', 1)[0] + '_audio.wav'
                self._audio_recorder = AudioRecorder(audio_path)
                self._audio_recorder.start()
            
            # 开启视频编码器
            self._video_encoder.start()
            
            # 开启屏幕捕获
            self._screen_capture.start()
            
            self.recording_started.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            self._stop_recording()

    def _pause_recording(self):
        """暂停/恢复录制"""
        if self._screen_capture.is_paused:
            self._screen_capture.resume()
        else:
            self._screen_capture.pause()
            
    def _stop_recording(self):
        """停止录制"""
        filename = ""
        
        # 停止屏幕捕获
        self._screen_capture.stop()
        
        # 停止音频录制
        if self._audio_recorder:
            self._audio_recorder.stop()
            audio_file = self._audio_recorder.output_path
            self._audio_recorder = None
        else:
            audio_file = None
            
        # 停止视频编码器
        if self._video_encoder:
            self._video_encoder.stop()
            filename = self._video_encoder.output_path
            self._video_encoder = None
            
        # 合并音视频
        if filename and audio_file and os.path.exists(audio_file):
            try:
                merged_path = filename + ".merged.mp4"
                if AudioRecorder.merge_audio_video(filename, audio_file, merged_path):
                    os.replace(merged_path, filename)
                # 清理音频临时文件
                try:
                    os.remove(audio_file)
                except OSError:
                    pass
            except Exception as e:
                print(f"Merge error: {e}")
                
        if filename:
            self.recording_stopped.emit(filename)
            
        # 隐藏标注画布
        self._annotation_canvas.hide()
        
        if filename and Path(filename).exists():
            reply = QMessageBox.information(
                self,
                "录制完成",
                f"视频已保存到:\n{filename}\n\n是否打开所在文件夹？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                import subprocess
                folder = str(Path(filename).parent)
                if os.name == 'nt':
                    os.startfile(folder)
                else:
                    subprocess.run(['xdg-open', folder])
                    
    def _toggle_annotation(self, enabled: bool):
        """切换标注模式"""
        if enabled:
            # 根据录制区域设置标注画布位置
            if self._record_region:
                # 有指定区域，只覆盖该区域
                left, top, width, height = self._record_region
                self._annotation_canvas.show_on_region(left, top, width, height)
            else:
                # 全屏模式
                screen = QApplication.primaryScreen()
                self._annotation_canvas.show_fullscreen_on_screen(screen)
        else:
            self._annotation_canvas.hide()
            
    def _toggle_annotation_shortcut(self):
        """快捷键切换标注模式"""
        # 获取当前状态并切换
        btn = self.control_panel._annotate_btn
        new_state = not btn.isChecked()
        
        # 阻止信号以避免循环触发
        btn.blockSignals(True)
        btn.setChecked(new_state)
        btn.blockSignals(False)
        
        # 同步精简模式的按钮状态
        compact_btn = self._compact_widget._annotate_btn
        compact_btn.blockSignals(True)
        compact_btn.setChecked(new_state)
        compact_btn.blockSignals(False)
        
        # 直接调用切换方法
        self._toggle_annotation(new_state)
        


            
    def _on_region_mode_changed(self, mode: str):
        """录制模式变化"""
        self._record_mode = mode
        if mode == "fullscreen":
            self._record_region = None
            self.control_panel.set_region_info("")
            self.setWindowTitle("InkFrame") # 重置标题
            
    def _show_region_selector(self):
        """显示区域选择器"""
        self.hide()  # 隐藏主窗口
        QTimer.singleShot(200, lambda: self._region_selector.show_fullscreen())
        
    def _on_region_selected(self, region: tuple):
        """区域选择完成"""
        self._record_region = region
        self.control_panel.set_region_info(f"{region[2]}x{region[3]}")
        self.setWindowTitle(f"InkFrame - 区域: {region[2]}x{region[3]}")
        self.show()
        self.activateWindow()
        
    def _on_region_cancelled(self):
        """区域选择取消"""
        self.show()
        self.activateWindow()
        
    def _on_error_occurred(self, message: str):
        """处理错误信息"""
        QMessageBox.critical(self, "错误", f"发生错误: {message}")
        
    def _show_window_selector(self):
        """显示窗口选择器"""
        window_info = WindowSelector.select_window(self)
        if window_info:
            self._record_region = window_info.region
            # 缩短标题用于状态栏
            title_short = f"{window_info.title[:20]}..." if len(window_info.title) > 20 else window_info.title
            
            # 更新主窗口标题
            self.setWindowTitle(f"InkFrame - {window_info.title} ({window_info.width}x{window_info.height})")
            
            self.control_panel.set_region_info(
                f"{title_short} ({window_info.width}x{window_info.height})"
            )
            
    def _on_frame_captured(self, frame: np.ndarray, timestamp: float):
        """帧捕获回调"""
        if self._video_encoder and self._video_encoder.is_running:
            # 写入帧（带时间戳）
            # 注意：标注层已被屏幕捕获包含（所见即所得），无需手动合成，否则会导致双重影像
            self._video_encoder.write_frame(frame, None, timestamp)
            
    def _pixmap_to_numpy(self, pixmap: QPixmap) -> np.ndarray:
        """将QPixmap转换为numpy数组"""
        image = pixmap.toImage()
        image = image.convertToFormat(QImage.Format.Format_RGBA8888)
        
        width = image.width()
        height = image.height()
        
        ptr = image.bits()
        arr = np.array(ptr).reshape(height, width, 4)
        
        # RGBA -> BGRA
        arr = arr[:, :, [2, 1, 0, 3]]
        
        return arr
        
    def closeEvent(self, event):
        """关闭事件"""
        # 隐藏标注画布和区域选择器
        self._annotation_canvas.hide()
        self._region_selector.hide()
        
        # 停止录制
        if self._screen_capture.is_running:
            self._screen_capture.stop()
        if self._video_encoder and self._video_encoder.is_running:
            self._video_encoder.stop()
            
        # 停止鼠标追踪
        # 注销全局快捷键
        self._hotkey_manager.unregister_all()
            
        # 保存配置
        self._config.save()
        
        super().closeEvent(event)

