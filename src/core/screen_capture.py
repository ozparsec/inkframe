#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
屏幕捕获模块 - 使用mss进行高效屏幕截取
"""

import time
import threading
from typing import Optional, Tuple, Callable
import numpy as np
import mss
import mss.tools


class ScreenCapture:
    """屏幕捕获类"""
    
    def __init__(self, fps: int = 30):
        """
        初始化屏幕捕获
        
        Args:
            fps: 帧率
        """
        self.fps = fps
        self.frame_interval = 1.0 / fps
        
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 捕获区域 (left, top, width, height)
        self._region: Optional[Tuple[int, int, int, int]] = None
        
        # 帧回调函数
        self._frame_callback: Optional[Callable[[np.ndarray, float], None]] = None
        
        # 当前帧
        self._current_frame: Optional[np.ndarray] = None
        
    def set_region(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        设置捕获区域
        
        Args:
            region: (left, top, width, height)，None表示全屏
        """
        self._region = region
        
    def set_frame_callback(self, callback: Callable[[np.ndarray, float], None]):
        """
        设置帧回调函数
        
        Args:
            callback: 回调函数，参数为(frame, timestamp)
        """
        self._frame_callback = callback
        
    def set_fps(self, fps: int):
        """
        设置帧率
        
        Args:
            fps: 帧率
        """
        self.fps = fps
        self.frame_interval = 1.0 / fps

    def get_monitors(self) -> list:
        """获取所有显示器信息"""
        with mss.mss() as sct:
            return list(sct.monitors)
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """获取当前帧"""
        with self._lock:
            if self._current_frame is not None:
                return self._current_frame.copy()
            return None
    
    def start(self):
        """开始捕获"""
        if self._running:
            return
            
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """停止捕获"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
            
    def pause(self):
        """暂停捕获"""
        self._paused = True
        
    def resume(self):
        """恢复捕获"""
        self._paused = False
        
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    @property
    def is_paused(self) -> bool:
        """是否暂停"""
        return self._paused
        
    def _capture_loop(self):
        """捕获循环"""
        with mss.mss() as sct:
            while self._running:
                if self._paused:
                    time.sleep(0.01)
                    continue
                    
                start_time = time.perf_counter()
                timestamp = time.time()
                
                try:
                    # 确定捕获区域
                    if self._region:
                        monitor = {
                            "left": self._region[0],
                            "top": self._region[1],
                            "width": self._region[2],
                            "height": self._region[3]
                        }
                    else:
                        # 全屏捕获（所有显示器）
                        monitor = sct.monitors[0]
                    
                    # 截取屏幕
                    screenshot = sct.grab(monitor)
                    
                    # 转换为numpy数组 (BGRA -> BGR)
                    frame = np.array(screenshot)[:, :, :3]
                    
                    # 更新当前帧
                    with self._lock:
                        self._current_frame = frame
                    
                    # 调用回调
                    if self._frame_callback:
                        self._frame_callback(frame, timestamp)
                        
                except Exception as e:
                    print(f"屏幕捕获错误: {e}")
                    
                # 控制帧率
                elapsed = time.perf_counter() - start_time
                sleep_time = self.frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)


def capture_screenshot(region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
    """
    捕获单帧屏幕截图
    
    Args:
        region: (left, top, width, height)，None表示全屏
        
    Returns:
        BGR格式的numpy数组
    """
    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3]
            }
        else:
            monitor = sct.monitors[0]
            
        screenshot = sct.grab(monitor)
        return np.array(screenshot)[:, :, :3]
