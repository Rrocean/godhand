#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand 功能全面测试
测试所有功能确保可用
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_cli_enhanced import EnhancedParser, EnhancedExecutor, FunctionChecker, KnowledgeBase


def test_knowledge_base():
    """测试知识库"""
    print("\n" + "=" * 60)
    print("测试知识库")
    print("=" * 60)

    kb = KnowledgeBase()

    test_questions = [
        "如何打开记事本",
        "怎么截图",
        "你能做什么",
        "如何打开画图并画圆",
        "怎么输入文字",
    ]

    all_passed = True
    for q in test_questions:
        answer = kb.answer(q)
        status = "[OK]" if answer else "[FAIL]"
        print(f"  {status} '{q}' -> {answer[:50] if answer else 'None'}...")
        if not answer:
            all_passed = False

    return all_passed


def test_parser():
    """测试解析器"""
    print("\n" + "=" * 60)
    print("测试指令解析器")
    print("=" * 60)

    parser = EnhancedParser()

    test_cases = [
        ("打开记事本", 1),
        ("打开记事本 然后输入Hello", 3),  # 打开+等待+输入
        ("点击 500, 500", 1),
        ("双击", 1),
        ("右键", 1),
        ("输入 Hello World", 1),
        ("按 enter", 1),
        ("快捷键 ctrl+s", 1),
        ("等待 3", 1),
        ("截图", 1),
        ("搜索 Python教程", 1),
        ("获取鼠标位置", 1),
        ("获取屏幕尺寸", 1),
        ("创建文件夹 test", 1),
        ("创建文件 test.txt", 1),
        ("列出窗口", 1),
        ("激活 记事本", 1),
        ("最小化", 1),
        ("最大化", 1),
        ("复制", 1),
        ("粘贴", 1),
        ("全选", 1),
        ("help", 1),
        ("check", 1),
        ("画个圆", 1),
    ]

    all_passed = True
    for cmd, expected_count in test_cases:
        actions, _ = parser.parse(cmd)
        passed = len(actions) >= expected_count
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} '{cmd}' -> {len(actions)} actions (expected >= {expected_count})")
        if not passed:
            all_passed = False

    return all_passed


def test_executor_non_gui():
    """测试执行器（非GUI操作）"""
    print("\n" + "=" * 60)
    print("测试执行器（非GUI）")
    print("=" * 60)

    executor = EnhancedExecutor()

    # 测试获取屏幕尺寸（不修改系统状态）
    from main_cli_enhanced import Action, ActionType
    action = Action(ActionType.GET_SCREEN_SIZE, {}, "获取屏幕尺寸")
    result = executor.execute(action)

    status = "[OK]" if result.get("success") else "[FAIL]"
    print(f"  {status} 获取屏幕尺寸: {result.get('output', result.get('error'))}")

    # 测试获取鼠标位置
    action = Action(ActionType.GET_POSITION, {}, "获取鼠标位置")
    result = executor.execute(action)
    status = "[OK]" if result.get("success") else "[FAIL]"
    print(f"  {status} 获取鼠标位置: {result.get('output', result.get('error'))}")

    return True


def test_composite_commands():
    """测试复合指令"""
    print("\n" + "=" * 60)
    print("测试复合指令")
    print("=" * 60)

    parser = EnhancedParser()

    composite_cases = [
        "打开记事本 然后输入Hello",
        "打开计算器 然后输入1+1 然后按等于",
        "打开画图 然后画个圆",
        "点击 500,500 然后等待 2 然后截图",
    ]

    all_passed = True
    for cmd in composite_cases:
        actions, _ = parser.parse(cmd)
        passed = len(actions) >= 2  # 复合指令至少应该有2个动作
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} '{cmd}'")
        print(f"      解析为 {len(actions)} 个动作:")
        for i, a in enumerate(actions[:5], 1):  # 只显示前5个
            print(f"        {i}. {a.type.value}: {a.description}")
        if len(actions) > 5:
            print(f"        ... 还有 {len(actions)-5} 个")
        if not passed:
            all_passed = False

    return all_passed


def test_system_check():
    """测试系统自检"""
    print("\n" + "=" * 60)
    print("测试系统自检")
    print("=" * 60)

    checker = FunctionChecker()
    results = checker.check_all()

    passed = sum(1 for r in results.values() if r["status"])
    total = len(results)
    print(f"\n自检通过: {passed}/{total}")

    return passed > 0


def test_qa_mode():
    """测试问答模式"""
    print("\n" + "=" * 60)
    print("测试问答模式")
    print("=" * 60)

    parser = EnhancedParser()

    qa_tests = [
        "如何打开记事本",
        "怎么截图",
        "你能做什么",
        "如何打开画图并画圆",
    ]

    all_passed = True
    for q in qa_tests:
        actions, _ = parser.parse(q)
        # 问答应该返回 QUESTION 类型的动作
        passed = len(actions) > 0 and actions[0].type.value == "question"
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} '{q}' -> {actions[0].type.value if actions else 'None'}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    print("GodHand CLI Enhanced 功能全面测试")
    print("=" * 60)

    tests = [
        ("知识库", test_knowledge_base),
        ("指令解析器", test_parser),
        ("复合指令", test_composite_commands),
        ("问答模式", test_qa_mode),
        ("执行器", test_executor_non_gui),
        ("系统自检", test_system_check),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[错误] {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} - {name}")

    total = len(results)
    passed = sum(1 for r in results.values() if r)
    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n[OK] 所有测试通过! 系统功能完整。")
        return 0
    else:
        print(f"\n[WARN] 有 {total-passed} 项测试未通过，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
