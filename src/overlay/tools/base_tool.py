#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
绘图工具基类
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional
from dataclasses import dataclass, field
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


@dataclass
class DrawingItem:
    """绘图项数据类"""
    tool_type: str
    color: Tuple[int, int, int]
    width: int
    points: List[Tuple[int, int]] = field(default_factory=list)
    text: str = ""
    rect: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    extra_data: Optional[bytes] = None  # 附加二进制数据（如zoom截图缓存）
    

class BaseTool(ABC):
    """绘图工具基类"""
    
    TOOL_TYPE = "base"
    
    def __init__(self, color: Tuple[int, int, int] = (255, 0, 0), width: int = 3):
        """
        初始化工具
        
        Args:
            color: RGB颜色元组
            width: 线宽
        """
        self.color = color
        self.width = width
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_drawing = False
        
    def set_color(self, color: Tuple[int, int, int]):
        """设置颜色"""
        self.color = color
        
    def set_width(self, width: int):
        """设置线宽"""
        self.width = width
        
    def get_pen(self) -> QPen:
        """获取QPen对象"""
        pen = QPen(QColor(*self.color))
        pen.setWidth(self.width)
        return pen
    
    def get_brush(self, filled: bool = False) -> QBrush:
        """获取QBrush对象"""
        if filled:
            return QBrush(QColor(*self.color, 50))  # 半透明填充
        return QBrush()  # 无填充
        
    @abstractmethod
    def on_press(self, pos: QPoint) -> None:
        """鼠标按下事件"""
        pass
    
    @abstractmethod
    def on_move(self, pos: QPoint) -> None:
        """鼠标移动事件"""
        pass
    
    @abstractmethod
    def on_release(self, pos: QPoint) -> Optional[DrawingItem]:
        """
        鼠标释放事件
        
        Returns:
            完成的绘图项，如果未完成则返回None
        """
        pass
    
    @abstractmethod
    def draw_preview(self, painter: QPainter) -> None:
        """绘制预览（正在绘制时）"""
        pass
    
    @staticmethod
    @abstractmethod
    def draw_item(painter: QPainter, item: DrawingItem) -> None:
        """绘制已完成的项"""
        pass
    
    @property
    def is_drawing(self) -> bool:
        """是否正在绘制"""
        return self._is_drawing
    
    def cancel(self) -> None:
        """取消当前绘制"""
        self._is_drawing = False
        self._start_pos = None
        self._current_pos = None
