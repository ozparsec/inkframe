#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文本绘图工具
"""

from typing import Optional
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QInputDialog, QWidget
from .base_tool import BaseTool, DrawingItem


class TextTool(BaseTool):
    """文本工具"""
    
    TOOL_TYPE = "text"
    DEFAULT_FONT_SIZE = 16
    
    def __init__(self, color=(255, 0, 0), width=3, parent: QWidget = None):
        super().__init__(color, width)
        self._parent = parent
        self._text_pos: Optional[QPoint] = None
        self._pending_text: str = ""
        
    def set_parent(self, parent: QWidget):
        """设置父窗口用于显示对话框"""
        self._parent = parent
        
    def on_press(self, pos: QPoint) -> None:
        self._text_pos = pos
        self._is_drawing = True
        
    def on_move(self, pos: QPoint) -> None:
        pass  # 文本工具不需要处理移动
            
    def on_release(self, pos: QPoint) -> Optional[DrawingItem]:
        if not self._is_drawing or self._text_pos is None:
            return None
            
        self._is_drawing = False
        
        # 弹出文本输入对话框
        text, ok = QInputDialog.getText(
            self._parent,
            "输入文本",
            "请输入标注文字:",
            text=""
        )
        
        if ok and text.strip():
            item = DrawingItem(
                tool_type=self.TOOL_TYPE,
                color=self.color,
                width=self.width,
                points=[(self._text_pos.x(), self._text_pos.y())],
                text=text.strip()
            )
            self._text_pos = None
            return item
            
        self._text_pos = None
        return None
        
    def draw_preview(self, painter: QPainter) -> None:
        # 文本工具显示光标位置指示
        if self._text_pos:
            painter.setPen(self.get_pen())
            # 绘制一个小十字表示文本位置
            size = 10
            painter.drawLine(
                self._text_pos.x() - size, self._text_pos.y(),
                self._text_pos.x() + size, self._text_pos.y()
            )
            painter.drawLine(
                self._text_pos.x(), self._text_pos.y() - size,
                self._text_pos.x(), self._text_pos.y() + size
            )
            
    @staticmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        if not item.text or not item.points:
            return
            
        # 设置字体
        font = QFont("Microsoft YaHei", TextTool.DEFAULT_FONT_SIZE)
        font.setBold(True)
        painter.setFont(font)
        
        # 设置颜色
        painter.setPen(QColor(*item.color))
        
        # 绘制文本背景（半透明）
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(item.text)
        x, y = item.points[0]
        
        bg_rect = text_rect.translated(x, y - text_rect.height())
        bg_rect.adjust(-4, -2, 4, 2)
        
        painter.fillRect(bg_rect, QColor(255, 255, 255, 180))
        
        # 绘制文本
        painter.drawText(x, y, item.text)
