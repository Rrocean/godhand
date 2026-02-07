#!/usr/bin/env python3
"""
Web 自动化示例

展示如何使用 GodHand 自动化浏览器操作。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import TaskPlanner


def example_search_and_extract():
    """搜索并提取信息"""
    print("=" * 60)
    print("搜索并提取信息")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开浏览器，
    搜索 Python 教程，
    打开第一个结果，
    提取页面标题和主要内容
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_form_filling():
    """表单填写自动化"""
    print("\n" + "=" * 60)
    print("表单填写自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开浏览器访问示例网站，
    在姓名字段输入：张三，
    在邮箱字段输入：zhangsan@example.com，
    选择城市：北京，
    点击提交按钮
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_data_scraping():
    """数据抓取自动化"""
    print("\n" + "=" * 60)
    print("数据抓取自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开浏览器访问新闻网站，
    提取首页所有新闻标题，
    保存到文本文件
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_social_media():
    """社交媒体自动化"""
    print("\n" + "=" * 60)
    print("社交媒体自动化")
    print("=" * 60)

    planner = TaskPlanner()

    instruction = """
    打开浏览器访问社交媒体网站，
    搜索指定话题，
    收集前10条帖子内容，
    保存到文档
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


if __name__ == "__main__":
    print("\n🌐 Web 自动化示例\n")

    example_search_and_extract()
    example_form_filling()
    example_data_scraping()
    example_social_media()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
