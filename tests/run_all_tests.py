#!/usr/bin/env python3
"""
🧪 GodHand 完整测试套件运行器

运行所有测试并生成报告
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(title):
    """打印标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_footer(title, success=True):
    """打印页脚"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"\n  {title}: {status}")
    print("-"*70 + "\n")


def run_test_module(module_name, test_func):
    """运行测试模块"""
    print(f"🔄 运行 {module_name}...")
    try:
        test_func()
        print_footer(module_name, True)
        return True
    except Exception as e:
        print(f"❌ 错误: {e}")
        print_footer(module_name, False)
        return False


def main():
    """主函数"""
    print_header("🌌 GodHand 宇宙级测试套件 🌌")
    print("版本: v3.0.0-universe")
    print("日期: 2026-02-07")
    print("\n")

    results = {}

    # 1. Smart Parser 测试
    try:
        from test_smart_parser import run_all_tests as run_parser_tests
        results['SmartParser'] = run_test_module("SmartParser", run_parser_tests)
    except Exception as e:
        print(f"❌ SmartParser 测试加载失败: {e}")
        results['SmartParser'] = False

    # 2. Visual Engine 测试
    try:
        from test_visual_engine import run_all_tests as run_visual_tests
        results['VisualEngine'] = run_test_module("VisualEngine", run_visual_tests)
    except Exception as e:
        print(f"❌ VisualEngine 测试加载失败: {e}")
        results['VisualEngine'] = False

    # 3. Task Planner 测试
    try:
        from test_task_planner import run_all_tests as run_planner_tests
        results['TaskPlanner'] = run_test_module("TaskPlanner", run_planner_tests)
    except Exception as e:
        print(f"❌ TaskPlanner 测试加载失败: {e}")
        results['TaskPlanner'] = False

    # 4. Element Library 测试
    try:
        from test_element_library import run_all_tests as run_library_tests
        results['ElementLibrary'] = run_test_module("ElementLibrary", run_library_tests)
    except Exception as e:
        print(f"❌ ElementLibrary 测试加载失败: {e}")
        results['ElementLibrary'] = False

    # 5. Learning System 测试
    try:
        from test_learning_system import run_all_tests as run_learning_tests
        results['LearningSystem'] = run_test_module("LearningSystem", run_learning_tests)
    except Exception as e:
        print(f"❌ LearningSystem 测试加载失败: {e}")
        results['LearningSystem'] = False

    # 6. Error Recovery 测试
    try:
        from test_error_recovery import run_all_tests as run_recovery_tests
        results['ErrorRecovery'] = run_test_module("ErrorRecovery", run_recovery_tests)
    except Exception as e:
        print(f"❌ ErrorRecovery 测试加载失败: {e}")
        results['ErrorRecovery'] = False

    # 7. Performance Monitor 测试
    try:
        from test_performance_monitor import run_all_tests as run_performance_tests
        results['PerformanceMonitor'] = run_test_module("PerformanceMonitor", run_performance_tests)
    except Exception as e:
        print(f"❌ PerformanceMonitor 测试加载失败: {e}")
        results['PerformanceMonitor'] = False

    # 8. Platform Adapters 测试
    try:
        from test_platform_adapters import run_all_tests as run_platform_tests
        results['PlatformAdapters'] = run_test_module("PlatformAdapters", run_platform_tests)
    except Exception as e:
        print(f"❌ PlatformAdapters 测试加载失败: {e}")
        results['PlatformAdapters'] = False

    # 9. Cloud Sync 测试
    try:
        from test_cloud_sync import run_all_tests as run_cloud_tests
        results['CloudSync'] = run_test_module("CloudSync", run_cloud_tests)
    except Exception as e:
        print(f"❌ CloudSync 测试加载失败: {e}")
        results['CloudSync'] = False

    # 10. Plugin System 测试
    try:
        from test_plugin_system import run_all_tests as run_plugin_tests
        results['PluginSystem'] = run_test_module("PluginSystem", run_plugin_tests)
    except Exception as e:
        print(f"❌ PluginSystem 测试加载失败: {e}")
        results['PluginSystem'] = False

    # 汇总结果
    print_header("📊 测试结果汇总")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0

    for module, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {module:<25} {status}")

    print("\n" + "="*70)
    print(f"  总计: {passed}/{total} 通过 ({percentage:.0f}%)")
    print("="*70)

    if passed == total:
        print("\n  🌌 所有测试通过！宇宙级标准达成！\n")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} 个模块测试失败\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
