#!/usr/bin/env python3
"""
数据处理自动化示例

展示如何使用 GodHand 自动化数据处理任务
"""

import sys
import json
import csv
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import TaskPlanner, AIAgent


def example_excel_data_cleaning():
    """Excel数据清洗示例"""
    print("=" * 60)
    print("📊 Excel 数据清洗自动化")
    print("=" * 60)
    print("""
    功能：
    1. 打开Excel文件
    2. 删除空行和重复行
    3. 格式化日期列
    4. 保存清洗后的文件
    """)

    planner = TaskPlanner()

    instruction = """
    打开数据文件 data.xlsx，
    删除所有空行，
    删除重复的行，
    将日期列格式化为 YYYY-MM-DD，
    保存为新文件 data_cleaned.xlsx
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_csv_to_json():
    """CSV转JSON示例"""
    print("\n" + "=" * 60)
    print("🔄 CSV 转 JSON 自动化")
    print("=" * 60)

    # 创建示例CSV数据
    csv_data = """name,age,city,email
张三,28,北京,zhangsan@example.com
李四,32,上海,lisi@example.com
王五,25,深圳,wangwu@example.com"""

    print("\n示例CSV数据：")
    print(csv_data)

    # 转换为JSON
    lines = csv_data.strip().split('\n')
    headers = lines[0].split(',')

    json_data = []
    for line in lines[1:]:
        values = line.split(',')
        json_data.append(dict(zip(headers, values)))

    print("\n转换后的JSON：")
    print(json.dumps(json_data, ensure_ascii=False, indent=2))


def example_batch_rename():
    """批量重命名文件示例"""
    print("\n" + "=" * 60)
    print("📁 批量文件重命名自动化")
    print("=" * 60)
    print("""
    功能：
    1. 扫描指定目录
    2. 根据规则重命名文件
    3. 添加时间戳或序号
    """)

    planner = TaskPlanner()

    instruction = """
    打开文件夹 ./downloads，
    将所有 .jpg 文件重命名为：
    格式：photo_序号_日期.jpg，
    示例：photo_001_20240207.jpg
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_report_generation():
    """报告生成示例"""
    print("\n" + "=" * 60)
    print("📈 自动化报告生成")
    print("=" * 60)
    print("""
    功能：
    1. 收集数据
    2. 生成图表
    3. 创建报告文档
    4. 发送邮件
    """)

    planner = TaskPlanner()

    instruction = """
    打开Excel数据文件，
    读取销售数据，
    生成柱状图和折线图，
    创建Word报告包含图表，
    保存并导出为PDF
    """

    plan = planner.plan(instruction)

    print(f"\n任务分解为 {len(plan.steps)} 个步骤：")
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. [{step.type.value}] {step.description}")


def example_ai_data_analysis():
    """AI数据分析示例"""
    print("\n" + "=" * 60)
    print("🤖 AI 数据分析")
    print("=" * 60)

    agent = AIAgent(name="Data Analyst")

    # 注册数据处理技能
    agent.register_skill("load_data", lambda **kwargs: {
        "success": True,
        "output": f"加载数据文件: {kwargs.get('file', 'unknown')}"
    })
    agent.register_skill("analyze", lambda **kwargs: {
        "success": True,
        "output": "数据分析完成：发现3个关键趋势"
    })
    agent.register_skill("generate_chart", lambda **kwargs: {
        "success": True,
        "output": f"生成图表: {kwargs.get('chart_type', 'bar')}"
    })
    agent.register_skill("export_report", lambda **kwargs: {
        "success": True,
        "output": f"导出报告到: {kwargs.get('path', 'report.pdf')}"
    })

    # 执行数据分析任务
    result = agent.run("分析销售数据，生成趋势图，导出PDF报告")

    print(f"\n📊 分析结果:")
    print(f"   成功率: {result['success_rate']*100:.0f}%")
    print(f"   执行步骤: {len(result['results'])}")


def create_sample_data_files():
    """创建示例数据文件"""
    print("\n" + "=" * 60)
    print("📁 创建示例数据文件")
    print("=" * 60)

    temp_dir = Path("./sample_data")
    temp_dir.mkdir(exist_ok=True)

    # CSV文件
    csv_content = """product,category,price,quantity,sale_date
笔记本电脑,电子产品,5999,5,2024-01-15
手机,电子产品,3999,12,2024-01-16
键盘,配件,299,20,2024-01-17
鼠标,配件,159,30,2024-01-18
显示器,电子产品,1299,8,2024-01-19"""

    csv_path = temp_dir / "sales_data.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write(csv_content)

    print(f"✅ 创建: {csv_path}")

    # JSON文件
    json_data = {
        "company": "示例公司",
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "departments": [
            {"name": "销售部", "headcount": 25, "budget": 1000000},
            {"name": "技术部", "headcount": 40, "budget": 2000000},
            {"name": "市场部", "headcount": 15, "budget": 800000}
        ]
    }

    json_path = temp_dir / "company_info.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 创建: {json_path}")
    print(f"\n示例文件已保存到: {temp_dir.absolute()}")


if __name__ == "__main__":
    print("\n📊 数据处理自动化示例\n")

    example_excel_data_cleaning()
    example_csv_to_json()
    example_batch_rename()
    example_report_generation()
    example_ai_data_analysis()
    create_sample_data_files()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)
