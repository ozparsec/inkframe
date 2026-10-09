#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
矩形绘图工具
"""

from typing import Optional
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QColor, QPen
from .base_tool import BaseTool, DrawingItem


class RectangleTool(BaseTool):
    """矩形工具"""
    
    TOOL_TYPE = "rectangle"
    
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
        
        # 创建绘图项
        rect = self._get_rect()
        item = DrawingItem(
            tool_type=self.TOOL_TYPE,
            color=self.color,
            width=self.width,
            rect=(rect.x(), rect.y(), rect.width(), rect.height())
        )
        
        self._start_pos = None
        self._current_pos = None
        
        return item
        
    def _get_rect(self) -> QRect:
        """获取矩形区域"""
        if self._start_pos and self._current_pos:
            return QRect(self._start_pos, self._current_pos).normalized()
        return QRect()
        
    def draw_preview(self, painter: QPainter) -> None:
        if not self._is_drawing:
            return
            
        rect = self._get_rect()
        if rect.isValid():
            painter.setPen(self.get_pen())
            painter.setBrush(self.get_brush(filled=False))  # 不填充
            painter.drawRect(rect)
            
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        if item.rect:
            pen = QPen(QColor(*item.color))
            pen.setWidth(item.width)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)  # 不填充
            painter.drawRect(*item.rect)
