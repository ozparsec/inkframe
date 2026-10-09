#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
录屏软件 - 程序入口
支持屏幕录制、实时标注、局部放大
"""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.app import ScreenRecorderApp


def main():
    """程序主入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("InkFrame")
    app.setOrganizationName("InkFrame Contributors")
    
    # 设置应用图标
    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = ScreenRecorderApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
