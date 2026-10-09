#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
局部放大工具 - 推镜头模式（全画面QPainter变换）
用户框选区域后，画布以该区域中心为焦点做scale+translate变换
"""

from typing import Optional, Tuple
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QColor, QPen
from .base_tool import BaseTool, DrawingItem


class ZoomTool(BaseTool):
    """局部放大工具 - 推镜头模式"""
    
    TOOL_TYPE = "zoom"
    DEFAULT_SCALE = 2.0
    
    # 类变量：画布信息
    canvas_offset: Tuple[int, int] = (0, 0)
    canvas_size: Tuple[int, int] = (1920, 1080)
    
    def __init__(self, color=(255, 0, 0), width=2):
        super().__init__(color, width)
        self.scale = self.DEFAULT_SCALE
        
    def set_scale(self, scale: float):
        """设置放大倍数"""
        self.scale = max(1.5, min(4.0, scale))
        
    @classmethod
    def set_canvas_offset(cls, x: int, y: int):
        cls.canvas_offset = (x, y)
        
    @classmethod
    def set_canvas_size(cls, width: int, height: int):
        cls.canvas_size = (width, height)
        
    def on_press(self, pos: QPoint) -> None:
        self._start_pos = pos
        self._current_pos = pos
        self._is_drawing = True
        
    def on_move(self, pos: QPoint) -> None:
        if self._is_drawing:
            self._current_pos = pos
            
    def on_release(self, pos: QPoint) -> Optional[DrawingItem]:
        if not self._is_drawing or self._start_pos is None:
            return None
            
        self._current_pos = pos
        self._is_drawing = False
        
        rect = self._get_rect()
        if rect.width() < 20 or rect.height() < 20:
            return None
        
        # 返回一个特殊的DrawingItem，携带zoom区域信息
        # 画布会检测到这个item并激活全局zoom变换
        item = DrawingItem(
            tool_type=self.TOOL_TYPE,
            color=self.color,
            width=self.width,
            rect=(rect.x(), rect.y(), rect.width(), rect.height()),
        )
        
        # 保存放大倍数
        item.text = f"{self.scale}"
        
        self._start_pos = None
        self._current_pos = None
        
        return item
        
    def _get_rect(self) -> QRect:
        if self._start_pos and self._current_pos:
            return QRect(self._start_pos, self._current_pos).normalized()
        return QRect()
        
    def draw_preview(self, painter: QPainter) -> None:
        if not self._is_drawing:
            return
            
        rect = self._get_rect()
        if rect.isValid() and rect.width() > 10 and rect.height() > 10:
            # 绘制选择框
            pen = QPen(QColor(0, 120, 215), 2)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 120, 215, 30))
            painter.drawRect(rect)
            
            # 显示放大倍数提示
            info_text = f"🔍 {self.scale:.1f}x 推镜头放大"
            painter.setPen(QColor(255, 255, 255))
            info_rect = QRect(rect.x(), rect.y() - 22, 160, 18)
            painter.fillRect(info_rect, QColor(0, 0, 0, 180))
            painter.drawText(info_rect, Qt.AlignmentFlag.AlignCenter, info_text)
            
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        """zoom item不单独绘制，由画布全局变换处理"""
        # 仅绘制一个半透明的焦点指示框（在zoom激活状态下被画布变换覆盖时不显示）
        pass
