#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频编码模块 - 使用OpenCV录制 + ffmpeg转码H.264
"""

import os
import sys
import time
import threading
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from queue import Queue, Empty
import numpy as np
import cv2


class VideoEncoder:
    """视频编码器类"""
    
    def __init__(
        self,
        output_path: str,
        fps: int = 30,
        frame_size: Optional[Tuple[int, int]] = None,
        video_format: str = "mp4"
    ):
        """
        初始化视频编码器
        
        Args:
            output_path: 输出文件路径（最终MP4）
            fps: 帧率
            frame_size: 帧尺寸 (width, height)
            video_format: 视频格式
        """
        self.output_path = output_path
        self.fps = fps
        self.frame_size = frame_size
        self.video_format = video_format.lower()
        self.frame_interval = 1.0 / fps
        
        # 临时AVI文件路径（OpenCV写入用）
        self._temp_path = str(Path(output_path).with_suffix('.tmp.avi'))
        
        self._writer: Optional[cv2.VideoWriter] = None
        self._frame_queue: Queue = Queue(maxsize=120)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_count = 0
        self._start_time: Optional[float] = None
        self._last_frame_time: float = 0
        
    def start(self):
        """开始编码"""
        if self._running:
            return
            
        self._running = True
        self._frame_count = 0
        self._start_time = time.time()
        self._last_frame_time = 0
        self._thread = threading.Thread(target=self._encode_loop, daemon=True)
        self._thread.start()
        
    def stop(self) -> str:
        """
        停止编码并转码为H.264 MP4
        
        Returns:
            输出文件路径
        """
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        # 用ffmpeg将临时AVI转码为H.264 MP4
        self._convert_to_h264()
            
        return self.output_path
    
    def write_frame(self, frame: np.ndarray, overlay: Optional[np.ndarray] = None, timestamp: float = None):
        """
        写入一帧（带时间戳）
        
        Args:
            frame: BGR格式的帧
            overlay: 可选的标注覆盖层 (BGRA格式)
            timestamp: 帧时间戳
        """
        if not self._running:
            return
            
        if timestamp is None:
            timestamp = time.time()
            
        # 合成标注层
        if overlay is not None:
            frame = self._composite_overlay(frame, overlay)
            
        try:
            self._frame_queue.put_nowait((frame, timestamp))
        except:
            pass  # 队列满时丢弃帧
            
    def _composite_overlay(self, frame: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """
        合成标注覆盖层
        
        Args:
            frame: BGR格式的背景帧
            overlay: BGRA格式的覆盖层
            
        Returns:
            合成后的BGR帧
        """
        if overlay.shape[2] == 4:
            # 提取alpha通道
            alpha = overlay[:, :, 3:4] / 255.0
            overlay_bgr = overlay[:, :, :3]
            
            # Alpha混合
            result = frame * (1 - alpha) + overlay_bgr * alpha
            return result.astype(np.uint8)
        else:
            return overlay
            
    def _encode_loop(self):
        """编码循环（带时间同步）"""
        last_frame = None
        expected_time = 0
        
        while self._running or not self._frame_queue.empty():
            try:
                frame, timestamp = self._frame_queue.get(timeout=0.1)
            except Empty:
                # 队列空时，如果有最后一帧，继续填充
                if last_frame is not None and self._running and self._start_time:
                    current_time = time.time() - self._start_time
                    while expected_time < current_time:
                        if self._writer:
                            self._writer.write(last_frame)
                            self._frame_count += 1
                        expected_time += self.frame_interval
                continue
                
            # 懒初始化writer
            if self._writer is None:
                self._init_writer(frame.shape[1], frame.shape[0])
                expected_time = 0
                
            if self._writer and self._start_time:
                # 计算相对于开始时间的时间戳
                relative_time = timestamp - self._start_time
                
                # 如果落后于预期时间，写入重复帧来填补
                while expected_time < relative_time:
                    if last_frame is not None:
                        self._writer.write(last_frame)
                        self._frame_count += 1
                    expected_time += self.frame_interval
                
                # 写入当前帧
                self._writer.write(frame)
                self._frame_count += 1
                last_frame = frame.copy()
                expected_time += self.frame_interval
                
        # 释放writer
        if self._writer:
            self._writer.release()
            self._writer = None
            
    def _init_writer(self, width: int, height: int):
        """初始化VideoWriter（写入临时AVI文件）"""
        # 确保输出目录存在
        Path(self._temp_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 使用XVID编码写AVI（OpenCV原生支持好，兼容性强）
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        self._writer = cv2.VideoWriter(
            self._temp_path,
            fourcc,
            self.fps,
            (width, height)
        )
        
        if not self._writer.isOpened():
            print(f"警告: 无法创建临时视频文件 {self._temp_path}")
            self._writer = None
    
    def _get_ffmpeg_path(self) -> str:
        """获取ffmpeg可执行文件路径，支持打包环境"""
        # 1. 检查是否在 PyInstaller 打包环境下
        if getattr(sys, 'frozen', False):
            # 如果是 --onefile 模式，资源文件在 _MEIPASS 目录下
            if hasattr(sys, '_MEIPASS'):
                bundle_ffmpeg = Path(sys._MEIPASS) / "ffmpeg.exe"
                if bundle_ffmpeg.exists():
                    return str(bundle_ffmpeg)
            
            # 同时也检查 exe 同级目录
            local_ffmpeg = Path(sys.executable).parent / "ffmpeg.exe"
            if local_ffmpeg.exists():
                return str(local_ffmpeg)
        else:
            # 开发环境下，查找项目根目录
            root_dir = Path(__file__).parent.parent.parent
            local_ffmpeg = root_dir / "ffmpeg.exe"
            if local_ffmpeg.exists():
                return str(local_ffmpeg)
        
        # 2. 回退到系统 PATH 中的 ffmpeg
        return "ffmpeg"
    
    def _convert_to_h264(self):
        """将临时AVI文件转码为H.264 MP4"""
        if not os.path.exists(self._temp_path):
            return
        
        ffmpeg_cmd = self._get_ffmpeg_path()
        
        try:
            cmd = [
                ffmpeg_cmd, "-y",
                "-i", self._temp_path,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "16",
                "-tune", "animation",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                self.output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                # 转码成功，删除临时文件
                try:
                    os.remove(self._temp_path)
                except OSError:
                    pass
            else:
                print(f"ffmpeg转码失败: {result.stderr[-500:]}")
                # 转码失败时，将临时文件重命名为输出文件作为降级方案
                try:
                    if os.path.exists(self.output_path):
                        os.remove(self.output_path)
                    os.rename(self._temp_path, self.output_path)
                except OSError as e:
                    print(f"降级重命名失败: {e}")
                    
        except FileNotFoundError:
            print("未找到ffmpeg，将直接使用AVI文件")
            try:
                if os.path.exists(self.output_path):
                    os.remove(self.output_path)
                os.rename(self._temp_path, self.output_path)
            except OSError as e:
                print(f"重命名失败: {e}")
        except subprocess.TimeoutExpired:
            print("ffmpeg转码超时")
            try:
                os.rename(self._temp_path, self.output_path)
            except OSError:
                pass
            
    @property
    def frame_count(self) -> int:
        """已编码帧数"""
        return self._frame_count
    
    @property
    def duration(self) -> float:
        """录制时长（秒）"""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


def generate_output_path(output_dir: str = "", prefix: str = "recording") -> str:
    """
    生成输出文件路径
    
    Args:
        output_dir: 输出目录
        prefix: 文件名前缀
        
    Returns:
        完整的输出路径
    """
    if not output_dir:
        output_dir = str(Path.home() / "Videos")
        
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.mp4"
    
    return os.path.join(output_dir, filename)
