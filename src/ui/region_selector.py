#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
区域选择器 - 拖拽选择录制区域
"""

from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QScreen
from PySide6.QtWidgets import QWidget, QApplication, QLabel


class RegionSelector(QWidget):
    """区域选择器"""
    
    # 选择完成信号 (left, top, width, height)
    region_selected = Signal(tuple)
    # 取消选择信号
    selection_cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置全屏透明窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # 选择状态
        self._selecting = False
        self._start_pos = QPoint()
        self._current_pos = QPoint()
        
        # 提示标签
        self._hint_label = QLabel("拖拽选择录制区域，按 ESC 取消", self)
        self._hint_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self._hint_label.adjustSize()
        
    def show_fullscreen(self, screen: QScreen = None):
        """全屏显示选择器"""
        if screen is None:
            screen = QApplication.primaryScreen()
            
        geometry = screen.geometry()
        self.setGeometry(geometry)
        
        # 居中显示提示
        self._hint_label.move(
            (geometry.width() - self._hint_label.width()) // 2,
            50
        )
        
        self.show()
        self.activateWindow()
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        
        # 绘制半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self._selecting:
            # 计算选择区域
            rect = self._get_selection_rect()
            
            if rect.isValid():
                # 清除选中区域的遮罩（使其透明）
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
                painter.fillRect(rect, Qt.GlobalColor.transparent)
                
                # 绘制边框
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                pen = QPen(QColor(65, 105, 225), 2)  # 皇家蓝边框
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.drawRect(rect)
                
                # 显示尺寸信息
                size_text = f"{rect.width()} x {rect.height()}"
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(rect.x() + 5, rect.y() - 5, size_text)
        
    def _get_selection_rect(self) -> QRect:
        """获取选择矩形"""
        return QRect(self._start_pos, self._current_pos).normalized()
        
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._selecting = True
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._hint_label.hide()
            self.update()
            
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        if self._selecting:
            self._current_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = self._get_selection_rect()
            
            # 检查选择区域是否有效（至少100x100）
            if rect.width() >= 100 and rect.height() >= 100:
                # 转换为全局坐标
                global_pos = self.mapToGlobal(rect.topLeft())
                region = (
                    global_pos.x(),
                    global_pos.y(),
                    rect.width(),
                    rect.height()
                )
                self.hide()
                self.region_selected.emit(region)
            else:
                # 区域太小，重新选择
                self._hint_label.setText("区域太小，请重新选择（至少 100x100）")
                self._hint_label.adjustSize()
                self._hint_label.show()
                self.update()
                
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.selection_cancelled.emit()
