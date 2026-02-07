#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand v4.0 AI Agent 演示
展示智能决策引擎的能力
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent_engine import create_agent


def demo():
    """AI Agent演示"""
    print("=" * 60)
    print("GodHand v4.0 - AI智能引擎演示")
    print("=" * 60)

    agent = create_agent()

    test_cases = [
        "打开记事本 然后输入Hello World",
        "打开计算器 然后输入1 然后按加号 然后输入1 然后按等于",
        "截图 然后获取鼠标位置",
        "循环 3次 点击 500, 500",
    ]

    for user_input in test_cases:
        print(f"\n{'='*60}")
        print(f"[用户输入] {user_input}")
        print("-" * 60)

        # AI处理
        result = agent.process(user_input)

        print(f"[🧠 意图分析]")
        print(f"  动作: {result['intent']['action']}")
        print(f"  目标: {result['intent'].get('target', 'N/A')}")
        print(f"  复杂度: {result['intent']['complexity']}")

        print(f"\n[📋 执行计划] {result['plan'].task_id}")
        print(f"  预计执行时间: {result['plan'].estimated_time}秒")
        print(f"  步骤数: {len(result['plan'].steps)}")

        for step in result['plan'].steps:
            print(f"    {step['step_id']}. [{step['action']}] {step['description']}")

        if result['context']:
            print(f"\n[💡 相关记忆]")
            print(result['context'])

    print(f"\n{'='*60}")
    print("演示完成！GodHand v4.0 AI引擎已准备就绪")
    print("=" * 60)


if __name__ == "__main__":
    demo()
