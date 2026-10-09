#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
放大镜组件 - 修复版
"""

from typing import Optional, Tuple
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor, QBrush
from PySide6.QtWidgets import QApplication


class Magnifier:
    """放大镜工具"""
    
    def __init__(self, size: int = 150, scale: float = 2.0):
        """
        初始化放大镜
        
        Args:
            size: 放大镜显示区域大小
            scale: 放大倍数
        """
        self.size = size
        self.scale = scale
        self._enabled = False
        self._position: Optional[QPoint] = None
        self._canvas_offset: Tuple[int, int] = (0, 0)  # 画布在屏幕上的偏移
        
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
        
    def set_scale(self, scale: float):
        """设置放大倍数"""
        self.scale = max(1.5, min(4.0, scale))
        
    def set_size(self, size: int):
        """设置放大镜大小"""
        self.size = max(100, min(300, size))
        
    def set_canvas_offset(self, x: int, y: int):
        """设置画布在屏幕上的偏移（用于区域录制时坐标转换）"""
        self._canvas_offset = (x, y)
        
    def update_position(self, pos: QPoint):
        """更新放大镜位置"""
        self._position = pos
        
    def draw(self, painter: QPainter, canvas_rect: QRect):
        """
        绘制放大镜
        
        Args:
            painter: QPainter对象
            canvas_rect: 画布区域
        """
        if not self._enabled or not self._position:
            return
            
        # 计算实际屏幕坐标
        screen_x = self._position.x() + self._canvas_offset[0]
        screen_y = self._position.y() + self._canvas_offset[1]
        
        # 获取屏幕截图
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        # 计算要截取的源区域
        source_size = int(self.size / self.scale)
        source_rect = QRect(
            screen_x - source_size // 2,
            screen_y - source_size // 2,
            source_size,
            source_size
        )
        
        # 截取屏幕区域
        screenshot = screen.grabWindow(
            0,
            source_rect.x(),
            source_rect.y(),
            source_rect.width(),
            source_rect.height()
        )
        
        if screenshot.isNull():
            return
            
        # 放大
        scaled = screenshot.scaled(
            self.size, self.size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 计算显示位置（避免超出画布边界）
        display_x = self._position.x() + 30
        display_y = self._position.y() + 30
        
        if display_x + self.size > canvas_rect.width():
            display_x = self._position.x() - self.size - 30
        if display_y + self.size > canvas_rect.height():
            display_y = self._position.y() - self.size - 30
            
        # 确保不超出左上边界
        display_x = max(5, display_x)
        display_y = max(5, display_y)
            
        display_rect = QRect(display_x, display_y, self.size, self.size)
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制白色背景圆形
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(100, 100, 100), 3))
        painter.drawEllipse(display_rect)
        
        # 绘制放大后的图像（圆形裁剪）
        # 创建圆形蒙版
        mask_pixmap = QPixmap(self.size, self.size)
        mask_pixmap.fill(Qt.GlobalColor.transparent)
        
        mask_painter = QPainter(mask_pixmap)
        mask_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        mask_painter.setBrush(QBrush(Qt.GlobalColor.white))
        mask_painter.setPen(Qt.PenStyle.NoPen)
        mask_painter.drawEllipse(0, 0, self.size, self.size)
        mask_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        mask_painter.drawPixmap(0, 0, scaled)
        mask_painter.end()
        
        # 绘制到目标位置
        painter.drawPixmap(display_rect.topLeft(), mask_pixmap)
        
        # 绘制边框
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.drawEllipse(display_rect)
        
        # 绘制十字准心
        painter.setPen(QPen(QColor(255, 0, 0, 180), 1))
        center = display_rect.center()
        cross_size = 8
        painter.drawLine(
            center.x() - cross_size, center.y(),
            center.x() + cross_size, center.y()
        )
        painter.drawLine(
            center.x(), center.y() - cross_size,
            center.x(), center.y() + cross_size
        )
        
        # 显示倍数标签（带背景）
        label_text = f"{self.scale:.1f}x"
        label_rect = QRect(display_rect.x() + 3, display_rect.y() + 3, 35, 16)
        painter.fillRect(label_rect, QColor(0, 0, 0, 150))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, label_text)
        
        painter.restore()
