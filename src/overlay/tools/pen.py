#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
画笔绘图工具
"""

from typing import Optional, List
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
from .base_tool import BaseTool, DrawingItem


class PenTool(BaseTool):
    """画笔工具 - 自由绘制"""
    
    TOOL_TYPE = "pen"
    
    def __init__(self, color=(255, 0, 0), width=3):
        super().__init__(color, width)
        self._points: List[QPoint] = []
        
    def on_press(self, pos: QPoint) -> None:
        self._is_drawing = True
        self._points.append(pos)
        
    def on_move(self, pos: QPoint) -> None:
        if self._is_drawing:
            self._points.append(pos)
            
    def on_release(self, pos: QPoint) -> Optional[DrawingItem]:
        if not self._is_drawing or len(self._points) < 2:
            self.cancel()
            return None
            
        item = DrawingItem(
            tool_type=self.TOOL_TYPE,
            points=[(p.x(), p.y()) for p in self._points],
            color=self.color,
            width=self.width
        )
        self.cancel()
        return item
        
    def draw_preview(self, painter: QPainter) -> None:
        if not self._is_drawing or len(self._points) < 2:
            return
            
        painter.setPen(self.get_pen())
        self._draw_path(painter, self._points)
        
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        if len(item.points) < 2:
            return
            
        pen = QPen(QColor(*item.color))
        pen.setWidth(item.width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        points = [QPoint(p[0], p[1]) for p in item.points]
        PenTool._draw_path(painter, points)
    
    @staticmethod
    def _draw_path(painter: QPainter, points: List[QPoint]) -> None:
        """绘制平滑路径"""
        if len(points) < 2:
            return
            
        path = QPainterPath()
        path.moveTo(points[0])
        
        # 使用贝塞尔曲线平滑
        for i in range(1, len(points)):
            path.lineTo(points[i])
            
        painter.drawPath(path)
    
    def cancel(self) -> None:
        super().cancel()
        self._points = []
