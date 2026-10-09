#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
箭头绘图工具
"""

import math
from typing import Optional
from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from .base_tool import BaseTool, DrawingItem


class ArrowTool(BaseTool):
    """箭头工具"""
    
    TOOL_TYPE = "arrow"
    ARROW_HEAD_LENGTH = 20  # 箭头长度
    ARROW_HEAD_ANGLE = 30   # 箭头角度（度）
    
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
            
        self._draw_arrow(
            painter, 
            self._start_pos, 
            self._current_pos,
            self.color,
            self.width
        )
            
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        if len(item.points) >= 2:
            start = QPoint(item.points[0][0], item.points[0][1])
            end = QPoint(item.points[1][0], item.points[1][1])
            ArrowTool._draw_arrow(painter, start, end, item.color, item.width)
    
    @staticmethod
    def _draw_arrow(
        painter: QPainter, 
        start: QPoint, 
        end: QPoint,
        color: tuple,
        width: int
    ) -> None:
        """绘制箭头"""
        pen = QPen(QColor(*color))
        pen.setWidth(width)
        painter.setPen(pen)
        
        # 画线
        painter.drawLine(start, end)
        
        # 计算箭头
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)
        
        if length < 1:
            return
            
        # 单位向量
        ux = dx / length
        uy = dy / length
        
        # 箭头长度（根据线宽调整）
        arrow_length = ArrowTool.ARROW_HEAD_LENGTH + width * 2
        angle = math.radians(ArrowTool.ARROW_HEAD_ANGLE)
        
        # 箭头两个点
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # 左侧点
        lx = end.x() - arrow_length * (ux * cos_a + uy * sin_a)
        ly = end.y() - arrow_length * (uy * cos_a - ux * sin_a)
        
        # 右侧点
        rx = end.x() - arrow_length * (ux * cos_a - uy * sin_a)
        ry = end.y() - arrow_length * (uy * cos_a + ux * sin_a)
        
        # 绘制箭头
        arrow_head = QPolygonF([
            QPointF(end.x(), end.y()),
            QPointF(lx, ly),
            QPointF(rx, ry)
        ])
        
        painter.setBrush(QColor(*color))
        painter.drawPolygon(arrow_head)
