#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
窗口枚举模块 - 获取系统中的窗口列表
"""

import ctypes
from ctypes import wintypes
from typing import List, Tuple, Optional
from dataclasses import dataclass


# Windows API 定义
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
GetClassName = user32.GetClassNameW
IsIconic = user32.IsIconic  # 是否最小化


@dataclass
class WindowInfo:
    """窗口信息"""
    hwnd: int
    title: str
    class_name: str
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    
    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]
    
    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]
    
    @property
    def region(self) -> Tuple[int, int, int, int]:
        """返回 (left, top, width, height) 格式"""
        return (self.rect[0], self.rect[1], self.width, self.height)
    
    def __str__(self) -> str:
        return f"{self.title} ({self.width}x{self.height})"


def get_window_title(hwnd: int) -> str:
    """获取窗口标题"""
    length = GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def get_window_class(hwnd: int) -> str:
    """获取窗口类名"""
    buffer = ctypes.create_unicode_buffer(256)
    GetClassName(hwnd, buffer, 256)
    return buffer.value


def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """获取窗口矩形区域"""
    rect = wintypes.RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)


def enumerate_windows(include_minimized: bool = False) -> List[WindowInfo]:
    """
    枚举所有可见窗口
    
    Args:
        include_minimized: 是否包含最小化的窗口
        
    Returns:
        窗口信息列表
    """
    windows = []
    
    # 要排除的窗口类名
    excluded_classes = {
        'Progman',           # 桌面
        'WorkerW',           # 桌面工作区
        'Shell_TrayWnd',     # 任务栏
        'Windows.UI.Core.CoreWindow',  # UWP 弹窗
        'Notification Area', # 通知区域
    }
    
    def enum_callback(hwnd, lparam):
        # 检查窗口是否可见
        if not IsWindowVisible(hwnd):
            return True
            
        # 检查是否最小化
        if not include_minimized and IsIconic(hwnd):
            return True
            
        # 获取窗口信息
        title = get_window_title(hwnd)
        if not title:
            return True
            
        class_name = get_window_class(hwnd)
        if class_name in excluded_classes:
            return True
            
        rect = get_window_rect(hwnd)
        
        # 排除太小的窗口
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width < 100 or height < 100:
            return True
            
        windows.append(WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            rect=rect
        ))
        
        return True
    
    EnumWindows(EnumWindowsProc(enum_callback), 0)
    
    # 按标题排序
    windows.sort(key=lambda w: w.title.lower())
    
    return windows


def get_window_by_hwnd(hwnd: int) -> Optional[WindowInfo]:
    """根据句柄获取窗口信息"""
    if not IsWindowVisible(hwnd):
        return None
        
    title = get_window_title(hwnd)
    if not title:
        return None
        
    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=get_window_class(hwnd),
        rect=get_window_rect(hwnd)
    )


def bring_window_to_front(hwnd: int):
    """将窗口置于前台"""
    user32.SetForegroundWindow(hwnd)
