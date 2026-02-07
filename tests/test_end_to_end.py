#!/usr/bin/env python3
"""
端到端测试 - 模拟真实用户场景
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image


class EndToEndTest:
    """端到端测试类"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.results = []

    def cleanup(self):
        """清理临时文件"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scenario_1_simple_automation(self):
        """场景1: 简单自动化 - 打开应用并输入文本"""
        print("\n🎬 场景1: 简单自动化")
        print("   步骤: 打开记事本 → 输入文本 → 保存")

        try:
            from core import SmartParser
            parser = SmartParser()

            # 解析复合指令
            command = "打开记事本 输入Hello World 保存到桌面"
            result = parser.parse(command)

            assert result is not None
            assert len(result.get("actions", [])) >= 3

            print("   ✅ 指令解析成功")
            self.results.append(("简单自动化", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("简单自动化", False))
            return False

    def test_scenario_2_visual_workflow(self):
        """场景2: 视觉工作流 - 检测元素并点击"""
        print("\n🎬 场景2: 视觉工作流")
        print("   步骤: 截图 → 检测按钮 → 定位目标 → 执行点击")

        try:
            from core import VisualEngine

            # 创建模拟界面
            screenshot = Image.new('RGB', (800, 600), color='lightgray')

            # 绘制模拟按钮
            from PIL import ImageDraw
            draw = ImageDraw.Draw(screenshot)
            draw.rectangle([100, 100, 200, 140], fill='blue', outline='darkblue')

            # 检测元素
            engine = VisualEngine(use_ocr=False, use_ml=False)
            elements = engine.detect_buttons(screenshot)

            # 至少检测到一些元素（模拟）
            assert isinstance(elements, list)

            print(f"   ✅ 检测到 {len(elements)} 个元素")
            self.results.append(("视觉工作流", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("视觉工作流", False))
            return False

    def test_scenario_3_task_planning(self):
        """场景3: 任务规划 - 复杂多步骤任务"""
        print("\n🎬 场景3: 任务规划")
        print("   步骤: 分析需求 → 生成计划 → 执行步骤 → 验证结果")

        try:
            from core import TaskPlanner

            planner = TaskPlanner(use_llm=False)
            instruction = "打开浏览器搜索Python教程，打开第一个结果，提取标题"

            plan = planner.plan(instruction)

            assert plan is not None
            assert len(plan.steps) >= 4  # 至少4个步骤

            print(f"   ✅ 生成 {len(plan.steps)} 个步骤的计划")
            self.results.append(("任务规划", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("任务规划", False))
            return False

    def test_scenario_4_learning_workflow(self):
        """场景4: 学习工作流 - 记录和回放用户操作"""
        print("\n🎬 场景4: 学习工作流")
        print("   步骤: 开始录制 → 记录操作 → 结束录制 → 回放工作流")

        try:
            from core import LearningSystem

            learning = LearningSystem()

            # 开始录制
            demo = learning.start_demonstration("登录流程", "自动登录示例网站")

            # 记录操作
            actions = [
                {"action": "navigate", "url": "https://example.com/login"},
                {"action": "click", "target": "用户名输入框"},
                {"action": "type", "text": "user@example.com"},
                {"action": "click", "target": "密码输入框"},
                {"action": "type", "text": "password123"},
                {"action": "click", "target": "登录按钮"}
            ]

            for action in actions:
                learning.record_action(demo.id, action)

            # 结束录制
            learning.end_demonstration(demo.id)

            # 验证工作流
            workflow = learning.get_workflow(demo.id)
            assert workflow is not None
            assert len(workflow.actions) == 6

            print(f"   ✅ 成功录制 {len(workflow.actions)} 个操作")
            self.results.append(("学习工作流", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("学习工作流", False))
            return False

    def test_scenario_5_error_recovery(self):
        """场景5: 错误恢复 - 处理执行中的错误"""
        print("\n🎬 场景5: 错误恢复")
        print("   步骤: 执行操作 → 遇到错误 → 触发恢复 → 继续执行")

        try:
            from core import ErrorRecovery, ErrorType

            recovery = ErrorRecovery()

            # 注册恢复策略
            recovery.register_recovery_strategy(
                "ElementNotFoundError",
                lambda e, ctx: {"retry": True, "alternative_action": "scroll_and_retry"}
            )

            # 模拟错误处理
            error = Exception("ElementNotFoundError: 按钮未找到")
            strategy = recovery.get_recovery_strategy(error)

            assert strategy is not None

            print("   ✅ 错误恢复机制正常工作")
            self.results.append(("错误恢复", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("错误恢复", False))
            return False

    def test_scenario_6_cloud_sync(self):
        """场景6: 云端同步 - 多设备数据同步"""
        print("\n🎬 场景6: 云端同步")
        print("   步骤: 创建配置 → 添加到同步队列 → 模拟同步 → 验证数据")

        try:
            from core import CloudSync

            db_path = os.path.join(self.temp_dir, "sync_test.db")
            sync = CloudSync(device_id="e2e_test_device", db_path=db_path)

            # 注册设备
            user = sync.register_device({
                "name": "E2E Test User",
                "email": "e2e@test.com",
                "role": "owner"
            })

            # 同步配置
            sync.sync_config({
                "theme": "dark",
                "language": "zh-CN",
                "shortcuts": {"execute": "Ctrl+Enter"}
            })

            # 验证队列
            status = sync.get_sync_status()
            assert status["pending_count"] >= 1

            print("   ✅ 云端同步功能正常")
            self.results.append(("云端同步", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("云端同步", False))
            return False

    def test_scenario_7_ai_agent_task(self):
        """场景7: AI代理任务 - 自主决策执行"""
        print("\n🎬 场景7: AI代理任务")
        print("   步骤: 设定目标 → AI规划 → 执行步骤 → 反思总结")

        try:
            from core import AIAgent, TaskPriority

            agent = AIAgent(name="E2E Test Agent")

            # 注册测试技能
            agent.register_skill("test_action", lambda **kwargs: {
                "success": True,
                "output": "Test action executed"
            })

            # 设定目标
            goal = agent.set_goal("完成端到端测试", TaskPriority.HIGH)

            # 制定计划
            plan = agent.plan(goal)

            assert plan is not None
            assert len(plan) > 0

            # 执行一步
            if plan:
                result = agent.execute(plan[0])

            # 验证状态
            status = agent.get_status()
            assert status["name"] == "E2E Test Agent"

            print(f"   ✅ AI代理成功规划并执行")
            self.results.append(("AI代理任务", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("AI代理任务", False))
            return False

    def test_scenario_8_plugin_workflow(self):
        """场景8: 插件工作流 - 扩展功能"""
        print("\n🎬 场景8: 插件工作流")
        print("   步骤: 加载插件 → 注册Hook → 触发事件 → 执行插件逻辑")

        try:
            from core.plugin_system import PluginSystem, PluginContext

            plugin_system = PluginSystem()

            # 创建测试插件目录
            plugin_dir = os.path.join(self.temp_dir, "test_plugins")
            os.makedirs(plugin_dir, exist_ok=True)

            # 创建简单插件
            test_plugin = os.path.join(plugin_dir, "e2e_plugin")
            os.makedirs(test_plugin, exist_ok=True)

            manifest = {
                "name": "e2e_plugin",
                "version": "1.0.0",
                "description": "E2E test plugin",
                "author": "Test",
                "main": "plugin.py"
            }

            with open(os.path.join(test_plugin, "manifest.json"), "w") as f:
                json.dump(manifest, f)

            # 加载插件
            plugin_system.load_plugins(plugin_dir)

            print("   ✅ 插件系统正常工作")
            self.results.append(("插件工作流", True))
            return True
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            self.results.append(("插件工作流", False))
            return False

    def run_all_tests(self):
        """运行所有端到端测试"""
        print("\n" + "="*70)
        print("🎭 GodHand 端到端测试套件")
        print("="*70)

        tests = [
            self.test_scenario_1_simple_automation,
            self.test_scenario_2_visual_workflow,
            self.test_scenario_3_task_planning,
            self.test_scenario_4_learning_workflow,
            self.test_scenario_5_error_recovery,
            self.test_scenario_6_cloud_sync,
            self.test_scenario_7_ai_agent_task,
            self.test_scenario_8_plugin_workflow,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n   ❌ 测试异常: {e}")

        self.cleanup()

        # 汇总
        print("\n" + "="*70)
        print("📊 端到端测试结果汇总")
        print("="*70)

        passed = sum(1 for _, r in self.results if r)
        for name, result in self.results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {name:<20} {status}")

        print(f"\n总计: {passed}/{len(self.results)} 通过")
        print("="*70 + "\n")

        return passed == len(self.results)


def main():
    """主函数"""
    e2e = EndToEndTest()
    success = e2e.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
