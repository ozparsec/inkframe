#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具栏组件
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QColorDialog,
    QSpinBox, QLabel, QButtonGroup, QSlider, QFrame
)


class ToolBar(QWidget):
    """标注工具栏"""
    
    # 信号
    tool_selected = Signal(str)
    color_changed = Signal(tuple)
    width_changed = Signal(int)
    zoom_scale_changed = Signal(float)  # 放大倍数变化
    undo_clicked = Signal()
    redo_clicked = Signal()
    clear_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_color = (255, 0, 0)
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # 绘图工具按钮组
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        
        # 工具列表：(id, tooltip, icon)
        tools = [
            ("rectangle", "矩形 (R)", "▭"),
            ("ellipse", "椭圆 (E)", "○"),
            ("line", "直线 (L)", "╱"),
            ("arrow", "箭头 (A)", "→"),
            ("pen", "画笔 (P)", "✎"),
            ("text", "文本 (T)", "T"),
            ("zoom", "局部放大 (Z)", "🔍"),
        ]
        
        for tool_id, tooltip, icon_text in tools:
            btn = self._create_tool_button(icon_text, tooltip)
            btn.setCheckable(True)
            btn.setProperty("tool_id", tool_id)
            btn.clicked.connect(lambda checked, t=tool_id: self._on_tool_clicked(t))
            self._tool_group.addButton(btn)
            layout.addWidget(btn)
            
            if tool_id == "rectangle":
                btn.setChecked(True)
                
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 颜色选择按钮
        self._color_btn = QToolButton()
        self._color_btn.setFixedSize(32, 32)
        self._color_btn.setToolTip("选择颜色")
        self._update_color_button()
        self._color_btn.clicked.connect(self._on_color_clicked)
        layout.addWidget(self._color_btn)
        
        # 线宽选择
        layout.addWidget(QLabel("线宽:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 20)
        self._width_spin.setValue(3)
        self._width_spin.setFixedWidth(50)
        self._width_spin.valueChanged.connect(self._on_width_changed)
        layout.addWidget(self._width_spin)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 放大倍数（用于放大工具）
        layout.addWidget(QLabel("放大:"))
        self._scale_slider = QSlider(Qt.Orientation.Horizontal)
        self._scale_slider.setRange(15, 40)  # 1.5x - 4.0x
        self._scale_slider.setValue(20)
        self._scale_slider.setFixedWidth(60)
        self._scale_slider.setToolTip("放大倍数 (+/- 调节)")
        self._scale_slider.valueChanged.connect(self._on_scale_changed)
        layout.addWidget(self._scale_slider)
        
        self._scale_label = QLabel("2.0x")
        self._scale_label.setFixedWidth(35)
        layout.addWidget(self._scale_label)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 撤销/重做/清除
        undo_btn = self._create_tool_button("↩", "撤销 (Ctrl+Z)")
        undo_btn.clicked.connect(self.undo_clicked.emit)
        layout.addWidget(undo_btn)
        
        redo_btn = self._create_tool_button("↪", "重做 (Ctrl+Y)")
        redo_btn.clicked.connect(self.redo_clicked.emit)
        layout.addWidget(redo_btn)
        
        clear_btn = self._create_tool_button("🗑", "清除全部 (Del)")
        clear_btn.clicked.connect(self.clear_clicked.emit)
        layout.addWidget(clear_btn)
        
        layout.addStretch()
        
    def _create_tool_button(self, text: str, tooltip: str) -> QToolButton:
        """创建工具按钮"""
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 32)
        btn.setStyleSheet("""
            QToolButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
                font-size: 14px;
            }
            QToolButton:hover {
                background: #e0e0e0;
            }
            QToolButton:checked {
                background: #4a90d9;
                color: white;
                border-color: #357abd;
            }
        """)
        return btn
        
    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep
        
    def _update_color_button(self):
        """更新颜色按钮显示"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(QColor(*self._current_color))
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 0))
        painter.drawRect(0, 0, 23, 23)
        painter.end()
        self._color_btn.setIcon(QIcon(pixmap))
        
    def _on_tool_clicked(self, tool_id: str):
        """工具点击"""
        self.tool_selected.emit(tool_id)
        
    def _on_color_clicked(self):
        """颜色按钮点击"""
        color = QColorDialog.getColor(
            QColor(*self._current_color),
            self,
            "选择标注颜色"
        )
        if color.isValid():
            self._current_color = (color.red(), color.green(), color.blue())
            self._update_color_button()
            self.color_changed.emit(self._current_color)
            
    def _on_width_changed(self, value: int):
        """线宽变化"""
        self.width_changed.emit(value)
        
    def _on_scale_changed(self, value: int):
        """放大倍数变化"""
        scale = value / 10.0
        self._scale_label.setText(f"{scale:.1f}x")
        self.zoom_scale_changed.emit(scale)
