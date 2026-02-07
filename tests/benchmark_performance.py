#!/usr/bin/env python3
"""
性能基准测试 - 测量核心模块性能
"""

import sys
import time
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

from core import (
    VisualEngine, TaskPlanner, LearningSystem,
    ElementLibrary, SmartParser
)
from core.visual_engine import UIElement, ElementType


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.results = {}

    def benchmark_visual_engine(self, iterations=100):
        """基准测试视觉引擎"""
        print("\n📊 基准测试: VisualEngine")

        engine = VisualEngine(use_ocr=False, use_ml=False)
        screenshot = Image.new('RGB', (1920, 1080), color='white')

        # 测试元素检测性能
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            elements = engine.detect_buttons(screenshot)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        self.results['visual_engine'] = {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'min_ms': min(times),
            'max_ms': max(times),
            'stdev_ms': statistics.stdev(times) if len(times) > 1 else 0
        }

        print(f"   平均: {self.results['visual_engine']['mean_ms']:.2f}ms")
        print(f"   中位数: {self.results['visual_engine']['median_ms']:.2f}ms")
        print(f"   最小: {self.results['visual_engine']['min_ms']:.2f}ms")
        print(f"   最大: {self.results['visual_engine']['max_ms']:.2f}ms")

        return self.results['visual_engine']['mean_ms'] < 100  # 目标 < 100ms

    def benchmark_task_planner(self, iterations=50):
        """基准测试任务规划器"""
        print("\n📊 基准测试: TaskPlanner")

        planner = TaskPlanner(use_llm=False)
        instructions = [
            "打开记事本",
            "打开计算器并计算1+1",
            "打开浏览器搜索Python教程",
            "点击保存按钮然后关闭窗口",
            "输入用户名和密码然后点击登录"
        ]

        times = []
        for instruction in instructions * (iterations // len(instructions)):
            start = time.perf_counter()
            plan = planner.plan(instruction)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        self.results['task_planner'] = {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times),
            'min_ms': min(times),
            'max_ms': max(times)
        }

        print(f"   平均: {self.results['task_planner']['mean_ms']:.2f}ms")
        print(f"   中位数: {self.results['task_planner']['median_ms']:.2f}ms")

        return self.results['task_planner']['mean_ms'] < 50  # 目标 < 50ms

    def benchmark_smart_parser(self, iterations=100):
        """基准测试智能解析器"""
        print("\n📊 基准测试: SmartParser")

        parser = SmartParser()
        commands = [
            "打开记事本",
            "输入Hello World",
            "截图保存到桌面",
            "打开计算器计算1+1",
            "点击确定按钮"
        ]

        times = []
        for command in commands * (iterations // len(commands)):
            start = time.perf_counter()
            result = parser.parse(command)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        self.results['smart_parser'] = {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times)
        }

        print(f"   平均: {self.results['smart_parser']['mean_ms']:.2f}ms")
        print(f"   中位数: {self.results['smart_parser']['median_ms']:.2f}ms")

        return self.results['smart_parser']['mean_ms'] < 10  # 目标 < 10ms

    def benchmark_element_library(self, iterations=1000):
        """基准测试元素库"""
        print("\n📊 基准测试: ElementLibrary")

        with tempfile.TemporaryDirectory() as tmpdir:
            library = ElementLibrary(cache_dir=tmpdir)

            # 添加一些测试数据
            for i in range(100):
                library.add_template(
                    name=f"button_{i}",
                    element_type="button",
                    image=None,
                    text=f"Button {i}",
                    app_name="TestApp"
                )

            # 测试查找性能
            times = []
            for i in range(iterations):
                start = time.perf_counter()
                results = library.find_by_text(f"Button {i % 100}", app_name="TestApp")
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)

            self.results['element_library'] = {
                'mean_ms': statistics.mean(times),
                'median_ms': statistics.median(times)
            }

            print(f"   平均: {self.results['element_library']['mean_ms']:.2f}ms")
            print(f"   中位数: {self.results['element_library']['median_ms']:.2f}ms")

            return self.results['element_library']['mean_ms'] < 5  # 目标 < 5ms

    def benchmark_learning_system(self, iterations=50):
        """基准测试学习系统"""
        print("\n📊 基准测试: LearningSystem")

        learning = LearningSystem()

        # 测试工作流学习性能
        times = []
        for i in range(iterations):
            start = time.perf_counter()
            demo = learning.start_demonstration(f"workflow_{i}", f"Test workflow {i}")

            for j in range(10):  # 10个动作
                learning.record_action(demo.id, {
                    "action": "click",
                    "target": f"button_{j}"
                })

            learning.end_demonstration(demo.id)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        self.results['learning_system'] = {
            'mean_ms': statistics.mean(times),
            'median_ms': statistics.median(times)
        }

        print(f"   平均: {self.results['learning_system']['mean_ms']:.2f}ms")
        print(f"   中位数: {self.results['learning_system']['median_ms']:.2f}ms")

        return self.results['learning_system']['mean_ms'] < 100  # 目标 < 100ms

    def benchmark_concurrent_operations(self, workers=4, iterations_per_worker=25):
        """基准测试并发操作"""
        print("\n📊 基准测试: 并发操作")

        parser = SmartParser()
        commands = ["打开记事本", "输入Hello", "截图", "点击确定"] * iterations_per_worker

        def parse_batch(batch):
            results = []
            for cmd in batch:
                start = time.perf_counter()
                result = parser.parse(cmd)
                elapsed = (time.perf_counter() - start) * 1000
                results.append(elapsed)
            return results

        # 分割任务
        batch_size = len(commands) // workers
        batches = [commands[i:i+batch_size] for i in range(0, len(commands), batch_size)]

        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            all_results = list(executor.map(parse_batch, batches))
        total_elapsed = (time.perf_counter() - start) * 1000

        all_times = [t for batch in all_results for t in batch]

        self.results['concurrent'] = {
            'total_ms': total_elapsed,
            'mean_ms': statistics.mean(all_times),
            'throughput': len(commands) / (total_elapsed / 1000)  # ops/sec
        }

        print(f"   总时间: {self.results['concurrent']['total_ms']:.2f}ms")
        print(f"   平均: {self.results['concurrent']['mean_ms']:.2f}ms")
        print(f"   吞吐量: {self.results['concurrent']['throughput']:.2f} ops/sec")

        return self.results['concurrent']['throughput'] > 100  # 目标 > 100 ops/sec

    def generate_report(self):
        """生成性能报告"""
        print("\n" + "="*70)
        print("📈 性能基准测试报告")
        print("="*70)

        for name, metrics in self.results.items():
            print(f"\n{name}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"   {metric}: {value:.3f}")
                else:
                    print(f"   {metric}: {value}")

        # 保存报告
        report_path = Path(__file__).parent / "benchmark_report.json"
        import json
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\n💾 报告已保存: {report_path}")

    def run_all_benchmarks(self):
        """运行所有基准测试"""
        print("\n" + "🚀"*35)
        print("\n  GodHand 性能基准测试")
        print("\n" + "🚀"*35)

        results = []

        results.append(("VisualEngine", self.benchmark_visual_engine()))
        results.append(("TaskPlanner", self.benchmark_task_planner()))
        results.append(("SmartParser", self.benchmark_smart_parser()))
        results.append(("ElementLibrary", self.benchmark_element_library()))
        results.append(("LearningSystem", self.benchmark_learning_system()))
        results.append(("Concurrent", self.benchmark_concurrent_operations()))

        self.generate_report()

        print("\n" + "="*70)
        print("测试结果汇总:")
        print("="*70)

        passed = sum(1 for _, r in results if r)
        for name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {name:<20} {status}")

        print(f"\n总计: {passed}/{len(results)} 通过")
        print("="*70 + "\n")

        return passed == len(results)


def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    success = benchmark.run_all_benchmarks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
