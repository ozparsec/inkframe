#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
录制控制面板
"""

import time
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QComboBox, QFrame
)


class ControlPanel(QWidget):
    """录制控制面板"""
    
    # 信号
    start_recording = Signal()
    pause_recording = Signal()
    stop_recording = Signal()
    toggle_annotation = Signal(bool)
    region_mode_changed = Signal(str)  # "fullscreen", "region", "window"
    select_region_clicked = Signal()   # 请求选择区域
    select_window_clicked = Signal()   # 请求选择窗口
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._is_paused = False
        self._start_time = 0
        self._elapsed_time = 0
        
        self._setup_ui()
        self._setup_timer()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 录制区域选择
        self._region_combo = QComboBox()
        self._region_combo.addItems(["全屏录制", "区域录制", "窗口录制"])
        self._region_combo.setFixedWidth(100)
        self._region_combo.currentIndexChanged.connect(self._on_region_changed)
        layout.addWidget(self._region_combo)
        
        # 音频开关
        self._audio_btn = QPushButton("🎤")
        self._audio_btn.setFixedSize(30, 30)
        self._audio_btn.setCheckable(True)
        self._audio_btn.setToolTip("录制系统声音/麦克风")
        self._audio_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
            }
            QPushButton:checked { background: #e74c3c; }
        """)
        layout.addWidget(self._audio_btn)
        
        # 选择按钮（区域/窗口选择时显示）
        self._select_btn = QPushButton("选择")
        self._select_btn.setFixedWidth(80)
        self._select_btn.setStyleSheet(self._get_button_style("#9b59b6"))
        self._select_btn.clicked.connect(self._on_select_clicked)
        self._select_btn.hide()  # 初始隐藏
        layout.addWidget(self._select_btn)
        

        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 录制控制按钮
        self._record_btn = QPushButton("⏺ 开始录制")
        self._record_btn.setFixedWidth(100)
        self._record_btn.setStyleSheet(self._get_button_style("#e74c3c"))
        self._record_btn.clicked.connect(self._on_record_clicked)
        self._record_btn.setToolTip("快捷键: Ctrl+Alt+R")
        layout.addWidget(self._record_btn)
        
        self._pause_btn = QPushButton("⏸ 暂停")
        self._pause_btn.setFixedWidth(80)
        self._pause_btn.setEnabled(False)
        self._pause_btn.setStyleSheet(self._get_button_style("#f39c12"))
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        self._pause_btn.setToolTip("快捷键: Ctrl+Alt+P")
        layout.addWidget(self._pause_btn)
        
        self._stop_btn = QPushButton("⏹ 停止")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(self._get_button_style("#2c3e50"))
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self._stop_btn)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 标注模式切换
        self._annotate_btn = QPushButton("✏ 标注模式")
        self._annotate_btn.setCheckable(True)
        self._annotate_btn.setFixedWidth(100)
        self._annotate_btn.setStyleSheet(self._get_button_style("#3498db"))
        self._annotate_btn.setToolTip("标注模式 (Ctrl+Alt+D)")
        self._annotate_btn.toggled.connect(self.toggle_annotation.emit)
        layout.addWidget(self._annotate_btn)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 时间显示
        self._time_label = QLabel("00:00:00")
        self._time_label.setStyleSheet("""
            QLabel {
                font-family: 'Consolas', monospace;
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 5px 10px;
                background: #ecf0f1;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self._time_label)
        
        # 状态指示
        self._status_label = QLabel("就绪")
        self._status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(self._status_label)
        
        layout.addStretch()
        
    def _get_button_style(self, color: str) -> str:
        """获取按钮样式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
            QPushButton:disabled {{
                background-color: #bdc3c7;
            }}
            QPushButton:checked {{
                background-color: #27ae60;
            }}
        """
        
    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep
        
    def _setup_timer(self):
        """设置计时器"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        
    def _update_time(self):
        """更新时间显示"""
        if self._is_recording and not self._is_paused:
            self._elapsed_time = time.time() - self._start_time
            
        hours = int(self._elapsed_time // 3600)
        minutes = int((self._elapsed_time % 3600) // 60)
        seconds = int(self._elapsed_time % 60)
        
        self._time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
    def _on_region_changed(self, index: int):
        """区域选择变化"""
        regions = ["fullscreen", "region", "window"]
        mode = regions[index]
        
        # 显示/隐藏选择按钮
        if mode in ("region", "window"):
            self._select_btn.show()
            self._select_btn.setText("选择区域" if mode == "region" else "选择窗口")
        else:
            self._select_btn.hide()
            self._region_info.hide()
            
        self.region_mode_changed.emit(mode)
        
    def _on_select_clicked(self):
        """选择按钮点击"""
        mode = ["fullscreen", "region", "window"][self._region_combo.currentIndex()]
        if mode == "region":
            self.select_region_clicked.emit()
        elif mode == "window":
            self.select_window_clicked.emit()
            
    def set_region_info(self, info: str):
        """设置区域信息显示"""
        # 已改为在主窗口标题栏显示，此处不再处理
        pass
        
    def _on_record_clicked(self):
        """录制按钮点击"""
        if not self._is_recording:
            self._is_recording = True
            self._is_paused = False
            self._start_time = time.time()
            self._elapsed_time = 0
            
            self._record_btn.setText("⏺ 录制中")
            self._record_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
            self._region_combo.setEnabled(False)
            
            self._status_label.setText("录制中...")
            self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
            
            self._timer.start(100)
            self.start_recording.emit()
            
    def _on_pause_clicked(self):
        """暂停按钮点击"""
        if self._is_paused:
            # 恢复
            self._is_paused = False
            self._start_time = time.time() - self._elapsed_time
            self._pause_btn.setText("⏸ 暂停")
            self._status_label.setText("录制中...")
            self._status_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        else:
            # 暂停
            self._is_paused = True
            self._pause_btn.setText("▶ 继续")
            self._status_label.setText("已暂停")
            self._status_label.setStyleSheet("color: #f39c12; font-size: 12px;")
            
        self.pause_recording.emit()
            
    def _on_stop_clicked(self):
        """停止按钮点击"""
        self._is_recording = False
        self._is_paused = False
        self._timer.stop()
        
        self._record_btn.setText("⏺ 开始录制")
        self._record_btn.setEnabled(True)
        self._pause_btn.setText("⏸ 暂停")
        self._pause_btn.setEnabled(False)
        self._stop_btn.setEnabled(False)
        self._region_combo.setEnabled(True)
        
        self._status_label.setText("就绪")
        self._status_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        
        self.stop_recording.emit()
        
    @property
    def is_recording(self) -> bool:
        return self._is_recording
    
    @property
    def is_paused(self) -> bool:
        return self._is_paused
