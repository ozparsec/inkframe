#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
透明标注画布
"""

from typing import Optional, List, Dict, Type
from dataclasses import dataclass, field
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPixmap, QScreen, QPen
from PySide6.QtWidgets import QWidget, QApplication

from .tools.base_tool import BaseTool, DrawingItem
from .tools.rectangle import RectangleTool
from .tools.ellipse import EllipseTool
from .tools.line import LineTool
from .tools.arrow import ArrowTool
from .tools.pen import PenTool
from .tools.text import TextTool
from .tools.zoom import ZoomTool


@dataclass
class FadingItem:
    """正在渐隐的绘图项"""
    item: DrawingItem
    opacity: float = 1.0  # 当前不透明度 (1.0 -> 0.0)


class AnnotationCanvas(QWidget):
    """透明标注画布"""
    
    # 信号
    annotation_changed = Signal()  # 标注发生变化
    tool_changed = Signal(str)     # 工具切换
    
    # 工具类型映射
    TOOL_CLASSES: Dict[str, Type[BaseTool]] = {
        "rectangle": RectangleTool,
        "ellipse": EllipseTool,
        "line": LineTool,
        "arrow": ArrowTool,
        "pen": PenTool,
        "text": TextTool,
        "zoom": ZoomTool,
    }
    
    # 工具快捷键映射 (使用字母)
    TOOL_SHORTCUTS = {
        Qt.Key.Key_R: "rectangle",  # R - 矩形
        Qt.Key.Key_E: "ellipse",    # E - 椭圆
        Qt.Key.Key_L: "line",       # L - 直线
        Qt.Key.Key_A: "arrow",      # A - 箭头
        Qt.Key.Key_P: "pen",        # P - 画笔
        Qt.Key.Key_T: "text",       # T - 文本
        Qt.Key.Key_Z: "zoom",       # Z - 放大
    }
    
    # 渐隐动画参数
    FADE_DURATION_MS = 500      # 渐隐总时长(毫秒)
    FADE_INTERVAL_MS = 16       # 刷新间隔(约60fps)
    
    # Zoom缩放动画参数
    ZOOM_ANIM_DURATION_MS = 200  # 缩放动画总时长(毫秒)
    ZOOM_ANIM_INTERVAL_MS = 16   # 刷新间隔(约60fps)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置透明无边框窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # 当前工具和设置
        self._current_tool_type = "rectangle"
        self._current_tool: BaseTool = RectangleTool()
        self._current_color = (255, 0, 0)
        self._current_width = 3
        
        # 放大工具的倍数
        self._zoom_scale = 2.0
        
        # 已完成的绘图项列表
        self._items: List[DrawingItem] = []
        
        # 撤销/重做栈
        self._undo_stack: List[DrawingItem] = []
        
        # 画布偏移（用于区域/窗口模式）
        self._canvas_offset = (0, 0)
        
        # 推镜头zoom状态
        self._zoom_active = False
        self._zoom_center = QPointF(0, 0)  # 焦点（画布坐标）
        self._zoom_level = 2.0             # 当前放大倍数
        self._zoom_bg: Optional[QPixmap] = None  # zoom激活时的屏幕截图背景
        
        # Zoom缩放动画状态
        self._zoom_anim_target = 1.0       # 动画目标倍数
        self._zoom_anim_elapsed = 0        # 已经过的毫秒数
        self._zoom_anim_timer = QTimer(self)
        self._zoom_anim_timer.setInterval(self.ZOOM_ANIM_INTERVAL_MS)
        self._zoom_anim_timer.timeout.connect(self._on_zoom_animate_tick)
        
        # 渐隐动画相关
        self._fading_items: List[FadingItem] = []
        self._fade_step = self.FADE_INTERVAL_MS / self.FADE_DURATION_MS  # 每帧递减量
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(self.FADE_INTERVAL_MS)
        self._fade_timer.timeout.connect(self._on_fade_tick)
        
        # 鼠标跟踪
        self.setMouseTracking(True)
        
    def set_tool(self, tool_type: str):
        """设置当前工具"""
        if tool_type not in self.TOOL_CLASSES:
            return
            
        self._current_tool_type = tool_type
        tool_class = self.TOOL_CLASSES[tool_type]
        
        if tool_type == "text":
            self._current_tool = tool_class(self._current_color, self._current_width, self)
        elif tool_type == "zoom":
            self._current_tool = tool_class(self._current_color, self._current_width)
            self._current_tool.set_scale(self._zoom_scale)
        else:
            self._current_tool = tool_class(self._current_color, self._current_width)
            
        self.tool_changed.emit(tool_type)
        
    def set_color(self, color: tuple):
        """设置颜色"""
        self._current_color = color
        self._current_tool.set_color(color)
        
    def set_line_width(self, width: int):
        """设置线宽"""
        self._current_width = width
        self._current_tool.set_width(width)
        
    def set_zoom_scale(self, scale: float):
        """设置放大倍数"""
        self._zoom_scale = max(1.5, min(4.0, scale))
        if self._current_tool_type == "zoom":
            self._current_tool.set_scale(self._zoom_scale)
        # 如果zoom已激活且不在动画中，实时更新倍数
        if self._zoom_active and not self._zoom_anim_timer.isActive():
            self._zoom_level = self._zoom_scale
            self.update()
        
    def _start_fade_out(self, items: List[DrawingItem]):
        """将项加入渐隐队列并启动动画"""
        for item in items:
            self._fading_items.append(FadingItem(item=item, opacity=1.0))
        if self._fading_items and not self._fade_timer.isActive():
            self._fade_timer.start()
    
    def _on_fade_tick(self):
        """渐隐动画每帧回调"""
        still_fading = []
        for fi in self._fading_items:
            fi.opacity -= self._fade_step
            if fi.opacity > 0.01:
                still_fading.append(fi)
        self._fading_items = still_fading
        
        if not self._fading_items:
            self._fade_timer.stop()
        
        self.update()
        
    def undo(self):
        """撤销（带渐隐）"""
        if self._items:
            item = self._items.pop()
            self._undo_stack.append(item)
            self._start_fade_out([item])
            self.annotation_changed.emit()
            self.update()
            
    def redo(self):
        """重做"""
        if self._undo_stack:
            item = self._undo_stack.pop()
            self._items.append(item)
            self.annotation_changed.emit()
            self.update()
            
    def clear(self):
        """清除所有标注（带渐隐）"""
        if self._items:
            self._start_fade_out(list(self._items))
            self._undo_stack.extend(self._items)
            self._items.clear()
            self.annotation_changed.emit()
            self.update()
        
    def get_items(self) -> List[DrawingItem]:
        """获取所有绘图项"""
        return self._items.copy()
    
    def get_overlay_pixmap(self) -> QPixmap:
        """获取标注层的pixmap（用于合成到视频）"""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_items(painter)
        painter.end()
        
        return pixmap
    
    def show_fullscreen_on_screen(self, screen: QScreen = None):
        """在指定屏幕上全屏显示"""
        if screen is None:
            screen = QApplication.primaryScreen()
            
        geometry = screen.geometry()
        self.setGeometry(geometry)
        self._canvas_offset = (0, 0)
        # 设置放大工具的画布信息
        ZoomTool.set_canvas_offset(0, 0)
        ZoomTool.set_canvas_size(geometry.width(), geometry.height())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        
    def show_on_region(self, left: int, top: int, width: int, height: int):
        """在指定区域显示标注画布"""
        self.setGeometry(left, top, width, height)
        self._canvas_offset = (left, top)
        # 设置放大工具的画布信息
        ZoomTool.set_canvas_offset(left, top)
        ZoomTool.set_canvas_size(width, height)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
                
    def _activate_zoom(self, center_x: float, center_y: float, scale: float,
                       select_rect: tuple = None):
        """激活推镜头zoom：先截取屏幕内容作为背景，再做变换
        
        Args:
            center_x, center_y: 初始焦点（选区中心）
            scale: 放大倍数
            select_rect: (x, y, w, h) 用户选中的矩形，用于钳制焦点
        """
        # 记录画布尺寸（hide前获取）
        canvas_w = self.width()
        canvas_h = self.height()
        
        # 先隐藏画布，截取干净的屏幕内容
        self.hide()
        QApplication.processEvents()  # 确保画布已隐藏
        
        screen = QApplication.primaryScreen()
        if screen:
            ox, oy = self._canvas_offset
            pixmap = screen.grabWindow(0, ox, oy, canvas_w, canvas_h)
            # 保留高DPI原始分辨率（不缩小），设置devicePixelRatio让QPainter自动适配
            dpr = screen.devicePixelRatio()
            pixmap.setDevicePixelRatio(dpr)
            self._zoom_bg = pixmap
        
        # 钳制焦点，保证选区在放大后尽量完全可见
        # 关键: 计算widget坐标系下的屏幕可见区域（DPI缩放导致widget尺寸 ≠ 屏幕尺寸）
        screen_geo = screen.geometry() if screen else None
        wg = self.geometry()
        if screen_geo:
            # 屏幕边界映射到widget坐标系
            vis_left = screen_geo.left() - wg.left()
            vis_top = screen_geo.top() - wg.top()
            vis_right = screen_geo.left() + screen_geo.width() - wg.left()
            vis_bottom = screen_geo.top() + screen_geo.height() - wg.top()
        else:
            vis_left, vis_top = 0, 0
            vis_right, vis_bottom = canvas_w, canvas_h
        
        center_x, center_y = self._clamp_zoom_center(
            center_x, center_y, scale,
            vis_left, vis_top, vis_right, vis_bottom, select_rect)
        
        self._zoom_active = True
        self._zoom_center = QPointF(center_x, center_y)
        
        # 从1.0开始，通过动画过渡到目标scale
        self._zoom_level = 1.0
        self._zoom_anim_target = scale
        self._zoom_anim_elapsed = 0
        
        # 重新显示画布
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self.update()
        
        # 启动缩放动画
        self._zoom_anim_timer.start()
        
    def _on_zoom_animate_tick(self):
        """Zoom缩放动画每帧回调（ease-out插值）"""
        self._zoom_anim_elapsed += self.ZOOM_ANIM_INTERVAL_MS
        t = min(self._zoom_anim_elapsed / self.ZOOM_ANIM_DURATION_MS, 1.0)
        # ease-out: 1 - (1 - t)^3
        t_ease = 1.0 - (1.0 - t) ** 3
        self._zoom_level = 1.0 + (self._zoom_anim_target - 1.0) * t_ease
        
        if t >= 1.0:
            self._zoom_level = self._zoom_anim_target
            self._zoom_anim_timer.stop()
        
        self.update()
    
    # zoom区域可见性边距(像素)
    ZOOM_MARGIN = 20
    
    @staticmethod
    def _clamp_zoom_center(cx: float, cy: float, s: float,
                           vis_left: float, vis_top: float,
                           vis_right: float, vis_bottom: float,
                           rect: tuple = None) -> tuple:
        """钳制zoom焦点，使选区在放大后落在屏幕可见区域内
        
        变换公式: screen_pos = s * scene_pos + center * (1 - s)
        vis_left/top/right/bottom: widget坐标系下的屏幕可见区域边界
        """
        if s <= 1.0:
            return (cx, cy)
        
        d = s - 1.0  # s > 1 保证 d > 0
        margin = AnnotationCanvas.ZOOM_MARGIN
        
        if rect:
            rx, ry, rw, rh = rect
            # 裁剪选区到可见区域
            rx2 = min(rx + rw, vis_right)
            ry2 = min(ry + rh, vis_bottom)
            rx = max(vis_left, rx)
            ry = max(vis_top, ry)
            rw = rx2 - rx
            rh = ry2 - ry
            
            if rw > 0 and rh > 0:
                # 选区右边缘在可见区域内(留margin):
                #   s*(rx+rw) + cx*(1-s) <= vis_right - margin
                #   → cx >= (s*(rx+rw) - vis_right + margin) / d
                # 选区左边缘在可见区域内(留margin):
                #   s*rx + cx*(1-s) >= vis_left + margin
                #   → cx <= (s*rx - vis_left - margin) / d
                cx_min = (s * (rx + rw) - vis_right + margin) / d
                cx_max = (s * rx - vis_left - margin) / d
                cy_min = (s * (ry + rh) - vis_bottom + margin) / d
                cy_max = (s * ry - vis_top - margin) / d
                
                # 如果带margin的区间不可行，退回到无margin
                if cx_min > cx_max:
                    cx_min = (s * (rx + rw) - vis_right) / d
                    cx_max = (s * rx - vis_left) / d
                if cy_min > cy_max:
                    cy_min = (s * (ry + rh) - vis_bottom) / d
                    cy_max = (s * ry - vis_top) / d
                
                if cx_min <= cx_max:
                    cx = max(cx_min, min(cx_max, cx))
                if cy_min <= cy_max:
                    cy = max(cy_min, min(cy_max, cy))
                
                return (cx, cy)
        
        # 无选区时：焦点限制在可见区域内
        cx = max(float(vis_left), min(float(vis_right), cx))
        cy = max(float(vis_top), min(float(vis_bottom), cy))
        
        return (cx, cy)
    
    def _deactivate_zoom(self):
        """退出推镜头zoom"""
        self._zoom_anim_timer.stop()
        self._zoom_active = False
        self._zoom_bg = None
        self.update()
        
    def _map_to_scene(self, widget_pos: QPoint) -> QPoint:
        """将widget坐标映射到zoom变换后的场景坐标"""
        if not self._zoom_active:
            return widget_pos
        # 逆变换：先反translate，再反scale
        cx = self._zoom_center.x()
        cy = self._zoom_center.y()
        s = self._zoom_level
        scene_x = (widget_pos.x() - cx * (1 - s)) / s
        scene_y = (widget_pos.y() - cy * (1 - s)) / s
        return QPoint(int(scene_x), int(scene_y))
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._zoom_active and self._zoom_bg:
            # zoom模式：先绘制缩放后的屏幕背景
            painter.save()
            cx = self._zoom_center.x()
            cy = self._zoom_center.y()
            s = self._zoom_level
            # 以焦点为中心缩放
            painter.translate(cx, cy)
            painter.scale(s, s)
            painter.translate(-cx, -cy)
            # 不使用SmoothPixmapTransform → 对屏幕内容（文字/UI）更锐利
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            # 绘制屏幕截图（devicePixelRatio已设置，QPainter自动1:1映射）
            painter.drawPixmap(0, 0, self._zoom_bg)
            
            # 在zoom变换下绘制标注
            self._draw_items(painter)
            self._draw_fading_items(painter)
            if self._current_tool.is_drawing:
                self._current_tool.draw_preview(painter)
            
            painter.restore()
            # 在变换外绘制HUD
            self._draw_zoom_hud(painter)
        else:
            # 正常模式：半透明背景
            painter.fillRect(self.rect(), QColor(0, 0, 0, 15))
            self._draw_items(painter)
            self._draw_fading_items(painter)
            if self._current_tool.is_drawing:
                self._current_tool.draw_preview(painter)
            
    def _draw_items(self, painter: QPainter):
        """绘制所有已完成的项（跳过zoom类型）"""
        for item in self._items:
            if item.tool_type == "zoom":
                continue  # zoom item由全局变换处理，不单独绘制
            tool_class = self.TOOL_CLASSES.get(item.tool_type)
            if tool_class:
                tool_class.draw_item(painter, item)
    
    def _draw_fading_items(self, painter: QPainter):
        """绘制正在渐隐的项（带透明度）"""
        for fi in self._fading_items:
            if fi.item.tool_type == "zoom":
                continue
            tool_class = self.TOOL_CLASSES.get(fi.item.tool_type)
            if tool_class:
                painter.save()
                painter.setOpacity(fi.opacity)
                tool_class.draw_item(painter, fi.item)
                painter.restore()
    
    def _draw_zoom_hud(self, painter: QPainter):
        """绘制zoom状态HUD（在变换之外绘制，始终在屏幕固定位置）"""
        # 右上角显示zoom状态提示
        hud_w, hud_h = 180, 30
        hud_x = self.width() - hud_w - 10
        hud_y = 10
        
        painter.fillRect(hud_x, hud_y, hud_w, hud_h, QColor(0, 120, 215, 220))
        painter.setPen(QColor(255, 255, 255))
        hud_rect = QRect(hud_x, hud_y, hud_w, hud_h)
        painter.drawText(hud_rect, Qt.AlignmentFlag.AlignCenter,
                         f"🔍 {self._zoom_level:.1f}x | Esc 退出")
                
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._map_to_scene(event.pos())
            self._current_tool.on_press(pos)
            self.update()
            
    def mouseMoveEvent(self, event):
        """鼠标移动"""
        pos = self._map_to_scene(event.pos())
        if self._current_tool.is_drawing:
            self._current_tool.on_move(pos)
            
        self.update()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self._map_to_scene(event.pos())
            item = self._current_tool.on_release(pos)
            if item:
                if item.tool_type == "zoom":
                    # Zoom工具：激活推镜头全局变换
                    x, y, w, h = item.rect
                    center_x = x + w / 2
                    center_y = y + h / 2
                    try:
                        scale = float(item.text)
                    except (ValueError, TypeError):
                        scale = 2.0
                    self._activate_zoom(center_x, center_y, scale,
                                        select_rect=(x, y, w, h))
                    # 不将zoom item加入items列表
                else:
                    self._items.append(item)
                    self._undo_stack.clear()
                    self.annotation_changed.emit()
            self.update()
            
    def keyPressEvent(self, event):
        """键盘事件"""
        key = event.key()
        
        # Ctrl+Z 撤销, Ctrl+Y 重做
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Z:
                self.undo()
            elif key == Qt.Key.Key_Y:
                self.redo()
            return
                
        # 数字键 1-7 切换工具
        if key in self.TOOL_SHORTCUTS:
            tool_type = self.TOOL_SHORTCUTS[key]
            self.set_tool(tool_type)
            return
                
        # Delete 或 Backspace 清除所有标注
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.clear()
            return
                
        # Escape 取消当前绘制 / 退出zoom / 关闭画布
        if key == Qt.Key.Key_Escape:
            if self._current_tool.is_drawing:
                self._current_tool.cancel()
                self.update()
            elif self._zoom_active:
                self._deactivate_zoom()
            else:
                self.hide()
            return
                
        # +/= 增加放大倍数, -/_ 减少放大倍数
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.set_zoom_scale(self._zoom_scale + 0.5)
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.set_zoom_scale(self._zoom_scale - 0.5)
