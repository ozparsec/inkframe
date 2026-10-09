#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直线绘图工具
"""

from typing import Optional
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QColor, QPen
from .base_tool import BaseTool, DrawingItem


class LineTool(BaseTool):
    """直线工具"""
    
    TOOL_TYPE = "line"
    
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
        
        item = DrawingItem(
            tool_type=self.TOOL_TYPE,
            color=self.color,
            width=self.width,
            points=[
                (self._start_pos.x(), self._start_pos.y()),
                (self._current_pos.x(), self._current_pos.y())
            ]
        )
        
        self._start_pos = None
        self._current_pos = None
        
        return item
        
    def draw_preview(self, painter: QPainter) -> None:
        if not self._is_drawing or not self._start_pos or not self._current_pos:
            return
            
        painter.setPen(self.get_pen())
        painter.drawLine(self._start_pos, self._current_pos)
            
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        if len(item.points) >= 2:
            pen = QPen(QColor(*item.color))
            pen.setWidth(item.width)
            painter.setPen(pen)
            painter.drawLine(
                item.points[0][0], item.points[0][1],
                item.points[1][0], item.points[1][1]
            )
