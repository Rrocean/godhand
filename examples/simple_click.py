#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单点击示例 - 假设屏幕上有一个确定按钮
"""
import sys
sys.path.insert(0, '..')

from ghost import GhostHand

ghost = GhostHand()

# 让 GhostHand 找到并点击"确定"按钮
gghost.run("找到屏幕上的确定按钮并点击它")

# 或者更复杂的任务
gghost.run("打开开始菜单，搜索记事本，打开它，输入'Hello GhostHand'")
