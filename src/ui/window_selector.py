#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
窗口选择对话框 - 带预览功能
"""

import ctypes
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QCheckBox, QSplitter, QFrame
)

from ..core.window_enum import WindowInfo, enumerate_windows

# Windows API for window capture
# Windows API for window capture
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

# Win32 Constants and Structures
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
PW_RENDERFULLCONTENT = 0x00000002

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.c_uint32),
        ('biWidth', ctypes.c_int32),
        ('biHeight', ctypes.c_int32),
        ('biPlanes', ctypes.c_uint16),
        ('biBitCount', ctypes.c_uint16),
        ('biCompression', ctypes.c_uint32),
        ('biSizeImage', ctypes.c_uint32),
        ('biXPelsPerMeter', ctypes.c_int32),
        ('biYPelsPerMeter', ctypes.c_int32),
        ('biClrUsed', ctypes.c_uint32),
        ('biClrImportant', ctypes.c_uint32),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', ctypes.c_ulong * 3),
    ]

def capture_window_native(hwnd: int) -> Optional[QImage]:
    """使用Win32 PrintWindow API捕获窗口"""
    try:
        # 获取窗口大小
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        if width <= 0 or height <= 0:
            return None
            
        # 创建设备上下文
        hwnd_dc = user32.GetDC(hwnd)
        mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        save_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        
        # 创建位图
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        gdi32.SelectObject(save_dc, bitmap)
        
        # PrintWindow 尝试捕获
        result = user32.PrintWindow(hwnd, save_dc, PW_RENDERFULLCONTENT)
        
        # 如果失败，尝试使用 BitBlt (虽然可能也黑屏，但值得一试)
        if not result:
            result = gdi32.BitBlt(save_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)
            
        if result:
            # 获取位图数据
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # 负值表示自上而下
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0
            
            total_bytes = width * height * 4
            buffer = ctypes.create_string_buffer(total_bytes)
            
            gdi32.GetDIBits(save_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS)
            
            # 转换为QImage
            # 注意：Win32 API返回的是BGRA格式
            image = QImage(buffer, width, height, QImage.Format.Format_ARGB32)
            image = image.copy() # 深拷贝，脱离buffer引用
            
        else:
            image = None
            
        # 清理资源
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(save_dc)
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)
        
        return image
        
    except Exception as e:
        print(f"Native capture failed: {e}")
        return None



def capture_window_thumbnail(hwnd: int, max_size: int = 300) -> Optional[QPixmap]:
    """
    捕获窗口缩略图
    
    Args:
        hwnd: 窗口句柄
        max_size: 最大尺寸
        
    Returns:
        QPixmap缩略图
    """
    try:
        # 优先尝试使用 Native PrintWindow 方法 (解决黑屏问题)
        native_image = capture_window_native(hwnd)
        
        if native_image and not native_image.isNull():
            pixmap = QPixmap.fromImage(native_image)
        else:
            # 回退到 Qt 的 grabWindow
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            pixmap = screen.grabWindow(hwnd)
        
        if pixmap.isNull():
            return None
            
        # 缩放到合适大小
        scaled = pixmap.scaled(
            max_size, max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        return scaled
    except Exception as e:
        print(f"捕获窗口缩略图失败: {e}")
        return None


class WindowSelector(QDialog):
    """窗口选择对话框 - 带预览功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_window: Optional[WindowInfo] = None
        self._setup_ui()
        self._refresh_windows()
        
    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("选择录制窗口")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        
        # 提示
        hint = QLabel("请选择要录制的窗口（点击窗口可预览）：")
        layout.addWidget(hint)
        
        # 分割器：左边列表，右边预览
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：窗口列表
        left_widget = QFrame()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self._window_list = QListWidget()
        self._window_list.setMinimumWidth(300)
        self._window_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #4a90d9;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        self._window_list.itemClicked.connect(self._on_item_clicked)
        self._window_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_layout.addWidget(self._window_list)
        
        # 选项
        options_layout = QHBoxLayout()
        
        self._include_minimized = QCheckBox("包含最小化窗口")
        self._include_minimized.stateChanged.connect(self._refresh_windows)
        options_layout.addWidget(self._include_minimized)
        
        options_layout.addStretch()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_windows)
        options_layout.addWidget(refresh_btn)
        
        left_layout.addLayout(options_layout)
        
        splitter.addWidget(left_widget)
        
        # 右侧：预览区域
        right_widget = QFrame()
        right_widget.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        right_layout = QVBoxLayout(right_widget)
        
        preview_title = QLabel("窗口预览")
        preview_title.setStyleSheet("font-weight: bold; color: #333;")
        preview_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_title)
        
        self._preview_label = QLabel("选择窗口以预览")
        self._preview_label.setMinimumSize(300, 250)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                color: #888;
            }
        """)
        right_layout.addWidget(self._preview_label, 1)
        
        # 窗口信息
        self._info_label = QLabel("")
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setStyleSheet("color: #666; font-size: 12px;")
        right_layout.addWidget(self._info_label)
        
        splitter.addWidget(right_widget)
        
        # 设置分割比例
        splitter.setSizes([350, 350])
        
        layout.addWidget(splitter)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        ok_btn.clicked.connect(self._on_ok_clicked)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
    def _refresh_windows(self):
        """刷新窗口列表"""
        self._window_list.clear()
        self._preview_label.setText("选择窗口以预览")
        self._preview_label.setPixmap(QPixmap())
        self._info_label.setText("")
        
        include_minimized = self._include_minimized.isChecked()
        windows = enumerate_windows(include_minimized)
        
        for window in windows:
            item = QListWidgetItem(f"📋 {window.title}")
            item.setData(Qt.ItemDataRole.UserRole, window)
            item.setToolTip(f"{window.title}\n尺寸: {window.width}x{window.height}")
            self._window_list.addItem(item)
            
        # 选中第一项
        if self._window_list.count() > 0:
            self._window_list.setCurrentRow(0)
            self._update_preview(self._window_list.item(0))
            
    def _on_item_clicked(self, item: QListWidgetItem):
        """点击项目 - 显示预览"""
        self._update_preview(item)
        
    def _update_preview(self, item: QListWidgetItem):
        """更新预览"""
        window = item.data(Qt.ItemDataRole.UserRole)
        if not window:
            return
            
        # 捕获窗口缩略图
        thumbnail = capture_window_thumbnail(window.hwnd, 280)
        
        if thumbnail and not thumbnail.isNull():
            self._preview_label.setPixmap(thumbnail)
        else:
            self._preview_label.setText("无法预览\n(窗口可能已最小化)")
            
        # 更新信息
        self._info_label.setText(
            f"尺寸: {window.width} × {window.height}\n"
            f"位置: ({window.rect[0]}, {window.rect[1]})"
        )
            
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击项目"""
        self._selected_window = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
        
    def _on_ok_clicked(self):
        """确定按钮点击"""
        current = self._window_list.currentItem()
        if current:
            self._selected_window = current.data(Qt.ItemDataRole.UserRole)
            self.accept()
            
    def get_selected_window(self) -> Optional[WindowInfo]:
        """获取选中的窗口"""
        return self._selected_window
    
    @staticmethod
    def select_window(parent=None) -> Optional[WindowInfo]:
        """
        显示对话框并返回选中的窗口
        
        Returns:
            选中的窗口信息，取消返回None
        """
        dialog = WindowSelector(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_window()
        return None
