#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSystemTrayIcon,
    QMenu, QMessageBox, QFileDialog, QApplication, QPushButton, QLabel
)

from .control_panel import ControlPanel
from .toolbar import ToolBar
from ..utils.config import Config
from pathlib import Path



class CompactWidget(QWidget):
    """精简模式界面"""
    
    # 信号
    expand_clicked = Signal()
    start_clicked = Signal()
    stop_clicked = Signal()
    annotate_clicked = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._annotate_on = False
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # 展开按钮
        self._expand_btn = QPushButton("⬜")
        self._expand_btn.setFixedSize(30, 30)
        self._expand_btn.setToolTip("展开完整界面 (Ctrl+M)")
        self._expand_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background: #2980b9; }
        """)
        self._expand_btn.clicked.connect(self.expand_clicked.emit)
        layout.addWidget(self._expand_btn)
        
        # 录制按钮
        self._record_btn = QPushButton("⏺ 开始")
        self._record_btn.setFixedSize(70, 30)
        self._record_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c0392b; }
        """)
        self._record_btn.clicked.connect(self._on_record_clicked)
        layout.addWidget(self._record_btn)
        
        # 标注按钮
        self._annotate_btn = QPushButton("✏")
        self._annotate_btn.setFixedSize(30, 30)
        self._annotate_btn.setCheckable(True)
        self._annotate_btn.setToolTip("标注模式 (Ctrl+Alt+D)")
        self._annotate_btn.setStyleSheet("""
            QPushButton {
                background: #9b59b6;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover { background: #8e44ad; }
            QPushButton:checked { background: #27ae60; }
        """)
        self._annotate_btn.toggled.connect(self.annotate_clicked.emit)
        layout.addWidget(self._annotate_btn)
        
        # 时长显示
        self._time_label = QLabel("00:00")
        self._time_label.setStyleSheet("color: #333; font-weight: bold;")
        layout.addWidget(self._time_label)
        
    def _on_record_clicked(self):
        if self._is_recording:
            self.stop_clicked.emit()
        else:
            self.start_clicked.emit()
            
    def set_recording(self, recording: bool):
        self._is_recording = recording
        if recording:
            self._record_btn.setText("⏹ 停止")
            self._record_btn.setStyleSheet("""
                QPushButton {
                    background: #27ae60;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #229954; }
            """)
        else:
            self._record_btn.setText("⏺ 开始")
            self._record_btn.setStyleSheet("""
                QPushButton {
                    background: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #c0392b; }
            """)
            
    def update_time(self, seconds: int):
        mins = seconds // 60
        secs = seconds % 60
        self._time_label.setText(f"{mins:02d}:{secs:02d}")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._compact_mode = False
        self._setup_ui()
        self._setup_tray()
        
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("InkFrame")
        self.setMinimumSize(800, 120)
        self.setMaximumHeight(150)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
        """)
        
        # 中心部件
        central = QWidget()
        self.setCentralWidget(central)
        
        self._main_layout = QVBoxLayout(central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 控制面板（正常模式）
        self._control_panel = ControlPanel()
        self._main_layout.addWidget(self._control_panel)
        
        # 工具栏（正常模式）
        self._toolbar = ToolBar()
        self._main_layout.addWidget(self._toolbar)
        
        # 精简面板（精简模式）
        self._compact_widget = CompactWidget()
        self._compact_widget.hide()
        self._compact_widget.expand_clicked.connect(self._toggle_compact_mode)
        self._compact_widget.start_clicked.connect(self._control_panel._on_record_clicked)
        self._compact_widget.stop_clicked.connect(self._control_panel._on_stop_clicked)
        self._compact_widget.annotate_clicked.connect(self._control_panel.toggle_annotation.emit)
        self._main_layout.addWidget(self._compact_widget)
        
        # 同步录制状态
        self._control_panel.start_recording.connect(lambda: self._compact_widget.set_recording(True))
        self._control_panel.stop_recording.connect(lambda: self._compact_widget.set_recording(False))
        
        # 创建菜单栏
        self._setup_menu()
        
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        open_action = QAction("打开输出目录(&O)", self)
        open_action.triggered.connect(self._open_output_dir)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        self._compact_action = QAction("精简模式(&C)", self)
        self._compact_action.setCheckable(True)
        self._compact_action.setShortcut("Ctrl+M")
        self._compact_action.triggered.connect(self._toggle_compact_mode)
        view_menu.addAction(self._compact_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")
        
        output_action = QAction("输出设置(&O)...", self)
        output_action.triggered.connect(self._show_output_settings)
        settings_menu.addAction(output_action)
        
        hotkey_action = QAction("快捷键设置(&H)...", self)
        hotkey_action.triggered.connect(self._show_hotkey_settings)
        settings_menu.addAction(hotkey_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _toggle_compact_mode(self):
        """切换精简模式"""
        self._compact_mode = not self._compact_mode
        self._compact_action.setChecked(self._compact_mode)
        
        if self._compact_mode:
            # 精简模式
            self._control_panel.hide()
            self._toolbar.hide()
            self.menuBar().hide()
            self._compact_widget.show()
            self.setMinimumSize(220, 50)
            self.setMaximumSize(300, 60)
            self.resize(220, 50)
            self.setWindowTitle("InkFrame (精简模式)")
        else:
            # 正常模式
            self._compact_widget.hide()
            self._control_panel.show()
            self._toolbar.show()
            self.menuBar().show()
            self.setMinimumSize(800, 120)
            self.setMaximumSize(16777215, 150)
            self.resize(800, 140)
            self.setWindowTitle("InkFrame")
        
    def _setup_tray(self):
        """设置系统托盘"""
        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("InkFrame")
        
        # 托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        compact_action = QAction("精简模式", self)
        compact_action.triggered.connect(self._toggle_compact_mode)
        tray_menu.addAction(compact_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(exit_action)
        
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        
    def _on_tray_activated(self, reason):
        """托盘图标激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
            
    def _open_output_dir(self):
        """打开输出目录"""
        import os
        import subprocess
        from pathlib import Path
        
        output_dir = Path.home() / "Videos"
        output_dir.mkdir(exist_ok=True)
        
        if os.name == 'nt':
            os.startfile(str(output_dir))
        else:
            subprocess.run(['xdg-open', str(output_dir)])
            
    def _show_output_settings(self):
        """显示输出设置"""
        from PySide6.QtWidgets import (
            QDialog, QFormLayout, QLineEdit, QHBoxLayout, 
            QSpinBox, QComboBox, QDialogButtonBox, QCheckBox
        )
        
        dialog = QDialog(self)
        dialog.setWindowTitle("输出设置")
        dialog.setFixedWidth(400)
        
        layout = QFormLayout(dialog)
        
        # 加载配置
        config = Config.load()
        
        # 输出目录
        path_layout = QHBoxLayout()
        path_edit = QLineEdit(config.output_dir or str(Path.home() / "Videos"))
        path_edit.setReadOnly(True)
        path_layout.addWidget(path_edit)
        
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        
        def browse_path():
            path = QFileDialog.getExistingDirectory(dialog, "选择输出目录", path_edit.text())
            if path:
                path_edit.setText(path)
                
        browse_btn.clicked.connect(browse_path)
        path_layout.addWidget(browse_btn)
        layout.addRow("输出目录:", path_layout)
        
        # 帧率
        fps_spin = QSpinBox()
        fps_spin.setRange(10, 60)
        fps_spin.setValue(config.fps)
        fps_spin.setSuffix(" fps")
        layout.addRow("帧率:", fps_spin)
        
        # 视频格式
        fmt_combo = QComboBox()
        fmt_combo.addItems(["mp4", "avi", "webm"])
        fmt_combo.setCurrentText(config.video_format)
        layout.addRow("视频格式:", fmt_combo)
        
        # 窗口设置
        ontop_check = QCheckBox("窗口置顶")
        ontop_check.setChecked(config.always_on_top)
        layout.addRow("", ontop_check)
        # 最小化到托盘
        tray_check = QCheckBox("关闭时最小化到系统托盘")
        tray_check.setChecked(config.minimize_to_tray)
        layout.addRow(tray_check)
        
        # 快捷键设置 (分隔线)
        layout.addRow(QLabel("<b>快捷键设置</b>"))
        
        # 开始/停止
        hotkey_start_stop = QLineEdit(config.hotkey_start_stop)
        layout.addRow("开始/停止录制:", hotkey_start_stop)
        
        # 暂停/恢复
        hotkey_pause = QLineEdit(config.hotkey_pause)
        layout.addRow("暂停/恢复录制:", hotkey_pause)
        
        # 标注模式
        hotkey_annotate = QLineEdit(config.hotkey_annotate)
        layout.addRow("切换标注模式:", hotkey_annotate)
        
        # 提示
        tip_label = QLabel("提示: 修改快捷键后需重启生效")
        tip_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow(tip_label)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec():
            # 保存配置
            config.output_dir = path_edit.text()
            config.fps = fps_spin.value()
            config.video_format = fmt_combo.currentText()
            config.always_on_top = ontop_check.isChecked()
            config.minimize_to_tray = tray_check.isChecked()
            
            # 保存快捷键
            config.hotkey_start_stop = hotkey_start_stop.text()
            config.hotkey_pause = hotkey_pause.text()
            config.hotkey_annotate = hotkey_annotate.text()
            
            config.save()
            
            # 更新运行时配置
            if hasattr(self, '_config'):
                self._config = config
                
                # 更新录制帧率
                if hasattr(self, '_screen_capture'):
                    self._screen_capture.set_fps(config.fps)
            
            # 应用设置
            if config.always_on_top:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            else:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

        
    def _show_hotkey_settings(self):
        """显示快捷键设置"""
        shortcuts = """
<h3>快捷键列表</h3>
<table border="1" cellpadding="5">
<tr><th>快捷键</th><th>功能</th></tr>
<tr><td>Ctrl+Alt+D</td><td>切换标注模式</td></tr>
<tr><td>Ctrl+Alt+R</td><td>开始/停止录制</td></tr>
<tr><td>Ctrl+Alt+P</td><td>暂停/恢复录制</td></tr>
<tr><td>Ctrl+M</td><td>切换精简模式</td></tr>
<tr><td>R</td><td>矩形工具</td></tr>
<tr><td>E</td><td>椭圆工具</td></tr>
<tr><td>L</td><td>直线工具</td></tr>
<tr><td>A</td><td>箭头工具</td></tr>
<tr><td>P</td><td>画笔工具</td></tr>
<tr><td>T</td><td>文本工具</td></tr>
<tr><td>Z</td><td>放大工具</td></tr>
<tr><td>Delete</td><td>清除标注</td></tr>
<tr><td>Ctrl+Z</td><td>撤销</td></tr>
<tr><td>Ctrl+Y</td><td>重做</td></tr>
<tr><td>ESC</td><td>退出标注模式</td></tr>
</table>
"""
        QMessageBox.information(self, "快捷键设置", shortcuts)
        
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 InkFrame",
            "<h3>InkFrame</h3>"
            "<p>版本: 1.0.0</p>"
            "<p>功能特性:</p>"
            "<ul>"
            "<li>屏幕录制（全屏/区域/窗口）</li>"
            "<li>实时标注（矩形/椭圆/直线/箭头/画笔/文本/放大）</li>"
            "<li>颜色和线宽自定义</li>"
            "<li>局部放大功能</li>"
            "</ul>"
            "<p>开发: InkFrame Contributors</p>"
        )
        
    def closeEvent(self, event):
        """关闭事件"""
        if self._control_panel.is_recording:
            reply = QMessageBox.question(
                self,
                "确认退出",
                "正在录制中，是否停止录制并退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
                
        event.accept()
        
    @property
    def control_panel(self) -> ControlPanel:
        return self._control_panel
    
    @property
    def toolbar(self) -> ToolBar:
        return self._toolbar
    
    @property
    def compact_widget(self) -> CompactWidget:
        return self._compact_widget
