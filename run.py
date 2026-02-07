#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Runner - 直接执行命令行指令
用法: python run.py "打开记事本 然后输入Hello World"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_cli import SimpleParser, ActionExecutor, HAS_PYAUTOGUI

def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("GodHand Runner - 直接执行GUI自动化指令")
        print("=" * 60)
        print("\n用法:")
        print('  python run.py "打开记事本"')
        print('  python run.py "打开画图 然后画个圆"')
        print('  python run.py "点击 500, 500"')
        print('  python run.py "输入 Hello World"')
        print('  python run.py "截图"')
        print("\n支持指令:")
        print("  打开 [应用名]        - 打开应用程序")
        print("  打开 XX 然后 YY      - 复合指令")
        print("  点击 X, Y           - 点击坐标")
        print("  双击                - 双击鼠标")
        print("  右键                - 右键点击")
        print("  输入 [文字]         - 输入文字")
        print("  按 [键名]           - 按键")
        print("  快捷键 ctrl+a       - 快捷键组合")
        print("  移动 X, Y           - 移动鼠标")
        print("  等待 [秒数]         - 等待")
        print("  截图                - 屏幕截图")
        print("  搜索 [关键词]       - 浏览器搜索")
        print("  打开 [网址]         - 打开网页")
        print("  创建文件 [路径]     - 创建文件")
        print("  删除文件 [路径]     - 删除文件")
        print("  创建文件夹 [路径]   - 创建目录")
        print("=" * 60)

        if not HAS_PYAUTOGUI:
            print("\n[WARN] pyautogui 未安装")
            print("安装: pip install pyautogui pyperclip")
        return

    # 获取命令
    command = ' '.join(sys.argv[1:])

    print(f"=" * 60)
    print(f"[指令] {command}")
    print(f"=" * 60)

    # 解析
    parser = SimpleParser()
    actions = parser.parse(command)

    if not actions:
        print("[ERROR] 无法解析指令")
        return

    print(f"\n解析到 {len(actions)} 个动作:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action.type.value}: {action.description}")

    # 执行
    print(f"\n{'='*60}")
    print("开始执行...")
    print(f"{'='*60}")

    executor = ActionExecutor()
    results = executor.execute_batch(actions)

    # 结果
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\n{'='*60}")
    print(f"[完成] {success_count}/{len(results)} 个动作成功")
    print(f"{'='*60}")

    # 退出码
    sys.exit(0 if success_count == len(results) else 1)

if __name__ == "__main__":
    main()
