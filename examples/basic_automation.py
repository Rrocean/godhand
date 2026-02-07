#!/usr/bin/env python3
"""
基础自动化示例

展示 GodHand 的基础自动化功能。
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.smart_parser import SmartParser, ActionExecutor
from core.visual_engine import VisualEngine
from core.task_planner import TaskPlanner


def example_1_simple_command():
    """示例1: 简单命令执行"""
    print("=" * 60)
    print("示例1: 简单命令")
    print("=" * 60)

    parser = SmartParser()
    executor = ActionExecutor()

    commands = [
        "打开计算器",
        "打开记事本",
        "截图",
        "搜索Python教程",
    ]

    for cmd in commands:
        print(f"\n指令: {cmd}")
        actions = parser.parse(cmd)
        print(f"解析结果: {len(actions)} 个动作")

        for i, action in enumerate(actions, 1):
            print(f"  {i}. [{action.type.value}] {action.description}")


def example_2_compound_command():
    """示例2: 复合指令"""
    print("\n" + "=" * 60)
    print("示例2: 复合指令")
    print("=" * 60)

    planner = TaskPlanner(use_llm=False)

    instructions = [
        "打开记事本 输入Hello World",
        "打开计算器 计算1+1",
        "截图 保存到桌面",
    ]

    for instruction in instructions:
        print(f"\n指令: {instruction}")
        plan = planner.plan(instruction)
        print(f"执行计划 ({len(plan.steps)} 个步骤):")

        for i, step in enumerate(plan.steps, 1):
            deps = f" (依赖: {step.depends_on})" if step.depends_on else ""
            print(f"  {i}. [{step.type.value}] {step.description}{deps}")


def example_3_visual_detection():
    """示例3: 视觉检测"""
    print("\n" + "=" * 60)
    print("示例3: 视觉检测")
    print("=" * 60)

    try:
        import pyautogui
        engine = VisualEngine(use_ocr=False)

        print("\n正在截取屏幕并检测元素...")
        screenshot = pyautogui.screenshot()
        elements = engine.detect_elements(screenshot)

        print(f"检测到 {len(elements)} 个元素:")

        # 按类型分组
        by_type = {}
        for elem in elements:
            t = elem.type.value
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(elem)

        for elem_type, elems in sorted(by_type.items()):
            print(f"\n  {elem_type.upper()}: {len(elems)} 个")
            for elem in elems[:3]:  # 只显示前3个
                print(f"    - {elem.description} at ({elem.x}, {elem.y})")

    except ImportError:
        print("需要安装 pyautogui 才能运行此示例")


def example_4_element_location():
    """示例4: 元素定位"""
    print("\n" + "=" * 60)
    print("示例4: 元素定位")
    print("=" * 60)

    try:
        import pyautogui
        engine = VisualEngine(use_ocr=False)

        # 截图
        screenshot = pyautogui.screenshot()

        # 尝试定位一些常见元素
        queries = [
            "开始按钮",
            "任务栏",
            "搜索框",
        ]

        for query in queries:
            print(f"\n查找: {query}")
            element = engine.locate_element(query, screenshot)

            if element:
                print(f"  找到! 位置: ({element.x}, {element.y})")
                print(f"  大小: {element.width}x{element.height}")
                print(f"  置信度: {element.confidence:.2f}")
            else:
                print(f"  未找到")

    except ImportError:
        print("需要安装 pyautogui 才能运行此示例")


if __name__ == "__main__":
    print("\n🖐️ GodHand 基础自动化示例\n")

    example_1_simple_command()
    example_2_compound_command()

    # 尝试视觉示例
    try:
        example_3_visual_detection()
        example_4_element_location()
    except Exception as e:
        print(f"\n视觉示例失败: {e}")

    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)
