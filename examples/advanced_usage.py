#!/usr/bin/env python3
"""
高级用法示例

展示 GodHand 的高级功能，包括学习系统、元素库等。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.learning_system import LearningSystem
from core.element_library import ElementLibrary
from core.error_recovery import ErrorRecovery
from core.performance_monitor import PerformanceMonitor


def example_1_learning_system():
    """示例1: 学习系统"""
    print("=" * 60)
    print("示例1: 学习系统")
    print("=" * 60)

    ls = LearningSystem(data_dir="./data/learning_demo")

    # 开始录制
    print("\n1. 录制演示...")
    rec_id = ls.start_recording("打开邮件并发送")

    # 模拟录制动作
    ls.record_action({"type": "open_app", "params": {"app_name": "Outlook"}})
    ls.record_action({"type": "wait", "params": {"seconds": 2}})
    ls.record_action({"type": "click", "params": {"target": "新建邮件"}})
    ls.record_action({"type": "type_text", "params": {"text": "Hello"}})
    ls.record_action({"type": "click", "params": {"target": "发送"}})

    # 停止录制
    demo = ls.stop_recording(user_rating=5)
    print(f"录制完成: {demo.id}")
    print(f"动作数: {len(demo.actions)}")

    # 查找相似演示
    print("\n2. 查找相似演示...")
    similar = ls.find_similar_demonstration("打开邮件发送")
    if similar:
        print(f"找到相似演示: {similar.task_description}")

    # 获取推荐
    print("\n3. 获取工作流推荐...")
    suggestions = ls.suggest_workflows()
    print(f"推荐工作流 ({len(suggestions)} 个):")
    for s in suggestions[:5]:
        print(f"  - {s['description']} ({s['reason']})")

    # 统计
    print("\n4. 学习统计...")
    stats = ls.get_learning_stats()
    print(f"演示记录: {stats['demonstrations']['total']}")
    print(f"学习模式: {stats['patterns']['total']}")


def example_2_element_library():
    """示例2: 元素库"""
    print("\n" + "=" * 60)
    print("示例2: 元素库")
    print("=" * 60)

    lib = ElementLibrary(data_dir="./data/elements_demo")

    # 创建模拟截图
    from PIL import Image
    test_img = Image.new('RGB', (1920, 1080), color='white')

    # 添加模板
    print("\n1. 添加模板...")
    template = lib.add_template(
        name="保存按钮",
        app_name="记事本",
        element_type="button",
        screenshot=test_img,
        bbox=(100, 100, 80, 30),
        text="保存",
        tags=["important"]
    )
    print(f"模板ID: {template.template_id}")

    # 查找模板
    print("\n2. 查找模板...")
    found = lib.find_template("保存按钮")
    if found:
        print(f"找到: {found.name} (应用: {found.app_name})")

    # 缓存元素
    print("\n3. 缓存元素...")
    cached = lib.cache_element(
        element_id="elem_001",
        x=150,
        y=150,
        width=80,
        height=30,
        confidence=0.95,
        detection_method="cv",
        template_id=template.template_id
    )
    print(f"缓存: {cached.element_id}")

    # 从缓存查找
    print("\n4. 从缓存查找...")
    from_cache = lib.find_in_cache(155, 155)
    if from_cache:
        print(f"缓存命中: {from_cache.element_id}")

    # 统计
    print("\n5. 元素库统计...")
    stats = lib.get_stats()
    print(f"模板数: {stats['templates_count']}")
    print(f"缓存大小: {stats['cache_size']}")
    print(f"缓存命中率: {stats['cache_hit_rate']*100:.1f}%")


def example_3_error_recovery():
    """示例3: 错误恢复"""
    print("\n" + "=" * 60)
    print("示例3: 错误恢复")
    print("=" * 60)

    er = ErrorRecovery()

    # 模拟各种错误
    errors = [
        Exception("Element not found: 保存按钮"),
        Exception("Timeout waiting for window"),
        Exception("Permission denied"),
    ]

    for i, error in enumerate(errors, 1):
        print(f"\n{i}. 错误: {error}")
        context = {
            "action": {"type": "click", "target": "test"},
            "app_name": "test_app"
        }

        result = er.handle_error(error, context, max_attempts=2)
        print(f"   恢复方法: {result.method_used}")
        print(f"   成功: {result.success}")
        print(f"   消息: {result.message}")

    # 统计
    print("\n错误恢复统计...")
    stats = er.get_stats()
    print(f"总错误数: {stats['total_errors']}")
    print(f"成功恢复: {stats['successful_recoveries']}")
    print(f"恢复成功率: {stats['success_rate']*100:.1f}%")


def example_4_performance_monitor():
    """示例4: 性能监控"""
    print("\n" + "=" * 60)
    print("示例4: 性能监控")
    print("=" * 60)

    pm = PerformanceMonitor(data_dir="./data/metrics_demo")

    # 模拟执行
    print("\n1. 模拟执行记录...")
    for i in range(10):
        task_id = f"task_{i}"
        pm.start_execution(task_id, f"测试指令 {i}", mode="auto")

        # 模拟执行时间
        import time
        time.sleep(0.05)

        success = i % 3 != 0  # 模拟一些失败
        pm.end_execution(
            task_id,
            success=success,
            steps_count=3,
            error_type="Timeout" if not success else None
        )

    print("记录完成")

    # 获取统计
    print("\n2. 执行统计...")
    stats = pm.get_execution_stats(days=1)
    print(f"总执行: {stats['total_executions']}")
    print(f"成功: {stats['successful']} ({stats['success_rate']*100:.1f}%)")
    print(f"平均耗时: {stats['avg_duration']:.3f}s")

    # 按模式统计
    print("\n3. 按模式统计...")
    mode_stats = pm.get_mode_stats(days=1)
    for mode, ms in mode_stats.items():
        print(f"  {mode}: {ms['total']}次 (成功率 {ms['rate']*100:.1f}%)")

    # 生成报告
    print("\n4. 生成报告...")
    report = pm.generate_report(days=1)
    print(report[:500] + "...")


if __name__ == "__main__":
    print("\n🖐️ GodHand 高级用法示例\n")

    try:
        example_1_learning_system()
    except Exception as e:
        print(f"学习系统示例失败: {e}")

    try:
        example_2_element_library()
    except Exception as e:
        print(f"元素库示例失败: {e}")

    try:
        example_3_error_recovery()
    except Exception as e:
        print(f"错误恢复示例失败: {e}")

    try:
        example_4_performance_monitor()
    except Exception as e:
        print(f"性能监控示例失败: {e}")

    print("\n" + "=" * 60)
    print("示例完成!")
    print("=" * 60)
