#!/usr/bin/env python3
"""
Office 自动化示例

展示如何使用 GodHand 自动化 Office 应用。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import TaskPlanner, VisualEngine
from PIL import Image


def example_excel_data_entry():
    """Excel 数据录入自动化"""
    print("=" * 60)
    print("Excel 数据录入自动化")
    print("=" * 60)

    planner = TaskPlanner()

    # 复杂的数据录入任务
    instruction = """
    打开Excel，创建一个新的工作表，
    在第一行输入标题：姓名、年龄、城市，
    然后输入3行示例数据，
    最后保存文件到桌面
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_word_document_creation():
    """Word 文档创建自动化"""
    print("\n" + "=" * 60)
    print("Word 文档创建自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开Word，创建一个新文档，
    输入标题：项目报告，
    输入正文：这是一个自动化测试文档，
    设置标题为加粗，
    保存到桌面
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_powerpoint_presentation():
    """PowerPoint 演示文稿自动化"""
    print("\n" + "=" * 60)
    print("PowerPoint 演示文稿自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开PowerPoint，创建新演示文稿，
    添加标题幻灯片：季度总结，
    添加第二张幻灯片：数据概览，
    保存文件
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_outlook_email():
    """Outlook 邮件自动化"""
    print("\n" + "=" * 60)
    print("Outlook 邮件自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开Outlook，创建新邮件，
    设置主题为：项目更新，
    输入正文：项目进展顺利，预计下周完成，
    添加到草稿箱
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


if __name__ == "__main__":
    print("\n📊 Office 自动化示例\n")

    example_excel_data_entry()
    example_word_document_creation()
    example_powerpoint_presentation()
    example_outlook_email()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
