#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础用法示例
"""
import sys
sys.path.insert(0, '..')

from ghost import GhostHand, Config

# 方法1: 使用配置文件
ghost = GhostHand(config=Config('../config.json'))
ghost.run("打开计算器并计算 123+456")

# 方法2: 直接传入 API Key（覆盖配置文件）
# ghost = GhostHand(api_key="your-api-key-here")
# ghost.run("打开记事本并输入你好世界")
