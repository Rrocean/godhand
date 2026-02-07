#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test CLI parser and executor without interactive input"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_cli import SimpleParser, ActionExecutor, ActionType

def test_parser():
    """Test parser with various commands"""
    parser = SimpleParser()

    test_cases = [
        "打开记事本",
        "打开画图 然后画个圆",
        "打开计算器 然后输入123",
        "点击 500, 500",
        "双击",
        "右键",
        "输入 Hello World",
        "按 enter",
        "快捷键 ctrl+s",
        "移动 100, 200",
        "等待 3",
        "截图",
        "搜索 Python教程",
        "打开 https://www.bing.com",
        "创建文件 test.txt",
        "创建文件夹 my_folder",
    ]

    print("=" * 60)
    print("Testing Parser")
    print("=" * 60)

    for cmd in test_cases:
        print(f"\n[Input] {cmd}")
        actions = parser.parse(cmd)
        if actions:
            print(f"  -> Parsed {len(actions)} action(s):")
            for i, action in enumerate(actions, 1):
                print(f"     {i}. {action.type.value}: {action.description}")
                print(f"        Params: {action.params}")
        else:
            print("  -> No actions parsed!")

    print("\n" + "=" * 60)
    print("Parser test complete")
    print("=" * 60)

if __name__ == "__main__":
    test_parser()
