#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
音频录制模块 - 使用sounddevice捕获系统音频
"""

import threading
import wave
import time
import queue
import numpy as np
import sounddevice as sd
import soundfile as sf
import subprocess
import os
import sys
from pathlib import Path

class AudioRecorder:
    """音频录制类"""
    
    def __init__(self, output_path: str, channels: int = 2, sample_rate: int = 44100):
        self.output_path = output_path
        self.channels = channels
        self.sample_rate = sample_rate
        
        self.input_device = None
        self._running = False
        self._stream = None
        self._frames = []
        self._start_time = 0
        self._audio_queue = queue.Queue()
        self._thread = None
        
        # 查找默认输入设备（立体声混音/麦克风）
        self._find_default_device()
        
    def _find_default_device(self):
        """查找合适的输入设备（优先立体声混音）"""
        try:
            # 获取默认输入设备
            default_input = sd.query_devices(kind='input')
            self.input_device = default_input['index']
            
            # 尝试查找立体声混音 (Windows Loopback)
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if 'Loopback' in dev['name'] or '立体声混音' in dev['name']:
                    self.input_device = i
                    break
        except Exception as e:
            print(f"Error finding audio device: {e}")
            
    def start(self):
        """开始录制"""
        if self._running:
            return
            
        self._running = True
        self._start_time = time.time()
        self._frames = []
        
        def callback(indata, frames, time, status):
            if status:
                print(status)
            self._audio_queue.put(indata.copy())
            
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                device=self.input_device,
                channels=self.channels,
                callback=callback
            )
            self._stream.start()
            
            self._thread = threading.Thread(target=self._record_loop)
            self._thread.start()
        except Exception as e:
            print(f"Failed to start audio stream: {e}")
            self._running = False
            
    def _record_loop(self):
        """录制循环"""
        while self._running:
            try:
                data = self._audio_queue.get(timeout=1)
                self._frames.append(data)
            except queue.Empty:
                continue
                
    def stop(self):
        """停止录制并保存"""
        self._running = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            
        if self._thread:
            self._thread.join()
            
        # 保存wav文件
        if self._frames:
            audio_data = np.concatenate(self._frames, axis=0)
            sf.write(self.output_path, audio_data, self.sample_rate)
            return True
        return False
        
    @staticmethod
    def _get_ffmpeg_path() -> str:
        """获取ffmpeg路径，支持打包环境"""
        if getattr(sys, 'frozen', False):
            if hasattr(sys, '_MEIPASS'):
                bundle_ffmpeg = Path(sys._MEIPASS) / "ffmpeg.exe"
                if bundle_ffmpeg.exists():
                    return str(bundle_ffmpeg)
            local_ffmpeg = Path(sys.executable).parent / "ffmpeg.exe"
            if local_ffmpeg.exists():
                return str(local_ffmpeg)
        else:
            root_dir = Path(__file__).parent.parent.parent
            local_ffmpeg = root_dir / "ffmpeg.exe"
            if local_ffmpeg.exists():
                return str(local_ffmpeg)
        return "ffmpeg"

    @staticmethod
    def merge_audio_video(video_path: str, audio_path: str, output_path: str):
        """合并音视频（使用ffmpeg）"""
        if not os.path.exists(audio_path):
            return False
            
        ffmpeg_cmd = AudioRecorder._get_ffmpeg_path()
            
        cmd = [
            ffmpeg_cmd, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError:
            return False