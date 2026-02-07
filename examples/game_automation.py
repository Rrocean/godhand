#!/usr/bin/env python3
"""
游戏自动化示例

展示如何使用 GodHand 自动化游戏操作。
⚠️ 警告：请仅在单机游戏或允许自动化的游戏中使用
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import TaskPlanner, VisualEngine
from core.visual_engine import ElementType


def example_fishing_bot():
    """钓鱼助手示例 - 自动检测钓鱼提示并点击"""
    print("=" * 60)
    print("🎣 钓鱼助手示例")
    print("=" * 60)
    print("""
    功能：
    1. 检测屏幕上的钓鱼提示（如浮标变化）
    2. 自动点击收杆
    3. 重复钓鱼流程
    """)

    planner = TaskPlanner()

    instruction = """
    持续监控屏幕中央区域，
    当检测到浮标下沉时立即点击，
    等待3秒后重复
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_auto_grind():
    """自动刷怪示例"""
    print("\n" + "=" * 60)
    print("⚔️ 自动战斗示例")
    print("=" * 60)
    print("""
    功能：
    1. 检测敌人血条
    2. 自动释放技能组合
    3. 自动拾取掉落物品
    """)

    planner = TaskPlanner()

    instruction = """
    循环执行：
    1. 检测屏幕上的敌人血条
    2. 按顺序释放技能：1 → 2 → 3
    3. 检测掉落物品并点击拾取
    4. 寻找下一个敌人
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_crafting_automation():
    """自动制作物品示例"""
    print("\n" + "=" * 60)
    print("🔨 自动制作示例")
    print("=" * 60)
    print("""
    功能：
    1. 打开制作界面
    2. 选择配方
    3. 批量制作物品
    """)

    planner = TaskPlanner()

    instruction = """
    打开制作界面，
    选择配方：生命药水，
    设置数量：20，
    点击制作按钮，
    等待制作完成
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_screen_detection():
    """屏幕元素检测示例"""
    print("\n" + "=" * 60)
    print("👁️ 游戏界面元素检测")
    print("=" * 60)

    try:
        from PIL import Image
        import numpy as np

        # 创建模拟游戏截图
        screenshot = Image.new('RGB', (1920, 1080), color='#2c3e50')

        engine = VisualEngine(use_ocr=False)

        # 检测血条、蓝条等游戏UI元素
        print("\n检测游戏UI元素：")
        print("  - 血条 (Health Bar)")
        print("  - 蓝条 (Mana/Energy Bar)")
        print("  - 技能图标")
        print("  - 小地图")
        print("  - 背包按钮")

        elements = engine.detect_buttons(screenshot)
        print(f"\n检测到 {len(elements)} 个可交互元素")

    except Exception as e:
        print(f"演示需要实际游戏画面: {e}")


if __name__ == "__main__":
    print("\n🎮 游戏自动化示例")
    print("⚠️  警告：请遵守游戏服务条款，仅在允许的情况下使用")
    print("=" * 60)

    example_fishing_bot()
    example_auto_grind()
    example_crafting_automation()
    example_screen_detection()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
