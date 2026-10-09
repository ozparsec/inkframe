#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Tuple


@dataclass
class Config:
    """应用配置类"""
    
    # 录制设置
    fps: int = 30
    video_format: str = "mp4"  # mp4, avi, webm
    video_codec: str = "mp4v"
    output_dir: str = ""
    record_audio: bool = True
    
    # 标注设置
    default_color: Tuple[int, int, int] = (255, 0, 0)  # RGB红色
    default_line_width: int = 3
    
    # 放大镜设置
    magnifier_scale: float = 2.0
    magnifier_size: int = 150
    
    # 快捷键
    hotkey_start_stop: str = "Ctrl+Alt+R"
    hotkey_pause: str = "Ctrl+Alt+P"
    hotkey_annotate: str = "Ctrl+Alt+D"
    
    # 窗口设置
    always_on_top: bool = True
    minimize_to_tray: bool = True
    
    # 鼠标点击高亮
    highlight_clicks: bool = True
    click_color_left: Tuple[int, int, int] = (255, 0, 0)       # 左键颜色 (纯红)
    click_color_right: Tuple[int, int, int] = (255, 0, 0)      # 右键颜色 (也用红色)
    click_ring_size: int = 20                                   # 圆的半径
    click_animation_duration: int = 400                         # 动画持续时间(ms)
    
    @classmethod
    def load(cls, path: Path = None) -> "Config":
        """从文件加载配置"""
        if path is None:
            path = Path.home() / ".screenrecorder" / "config.json"
            
        # 强制重置快捷键配置 (如果检测到旧的默认值) 
        # 或者简单地，如果从未手动修改过... 
        # 这里直接检查文件内容，如果是 F11 就忽略?
        pass
        
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 转换元组
                    if "default_color" in data:
                        data["default_color"] = tuple(data["default_color"])
                    return cls(**data)
            except Exception:
                pass
        return cls()
    
    def save(self, path: Path = None):
        """保存配置到文件"""
        if path is None:
            path = Path.home() / ".screenrecorder" / "config.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = asdict(self)
        # 转换元组为列表
        data["default_color"] = list(data["default_color"])
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
