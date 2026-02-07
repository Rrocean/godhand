#!/usr/bin/env python3
"""
TaskPlanner 测试套件

测试目标：任务规划器的各项功能
"""

import unittest
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.task_planner import (
    TaskPlanner, PlanExecutor, ExecutionPlan, Step, StepType, StepStatus,
    PlanningContext, quick_plan
)


class TestStep(unittest.TestCase):
    """步骤测试"""

    def test_step_creation(self):
        """测试步骤创建"""
        step = Step(
            id="step_001",
            type=StepType.ACTION,
            description="打开记事本",
            params={"action": "open_app", "app_name": "notepad"},
            timeout=30.0
        )

        self.assertEqual(step.id, "step_001")
        self.assertEqual(step.type, StepType.ACTION)
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertEqual(step.timeout, 30.0)

    def test_step_to_dict(self):
        """测试步骤序列化"""
        step = Step(
            id="step_002",
            type=StepType.WAIT,
            description="等待2秒",
            params={"seconds": 2.0}
        )

        data = step.to_dict()
        self.assertEqual(data['id'], 'step_002')
        self.assertEqual(data['type'], 'wait')
        self.assertEqual(data['status'], 'pending')

    def test_step_dependencies(self):
        """测试步骤依赖"""
        step1 = Step(id="step_001", type=StepType.ACTION, description="第一步", params={})
        step2 = Step(
            id="step_002",
            type=StepType.ACTION,
            description="第二步",
            params={},
            depends_on=["step_001"]
        )

        self.assertEqual(step2.depends_on, ["step_001"])


class TestExecutionPlan(unittest.TestCase):
    """执行计划测试"""

    def setUp(self):
        self.steps = [
            Step(id="step_001", type=StepType.ACTION, description="第一步", params={}),
            Step(id="step_002", type=StepType.ACTION, description="第二步", params={}, depends_on=["step_001"]),
            Step(id="step_003", type=StepType.ACTION, description="第三步", params={}, depends_on=["step_002"]),
        ]
        self.plan = ExecutionPlan(
            task_id="test_task_001",
            description="测试任务",
            steps=self.steps
        )

    def test_get_step(self):
        """测试获取步骤"""
        step = self.plan.get_step("step_001")
        self.assertIsNotNone(step)
        self.assertEqual(step.description, "第一步")

        step = self.plan.get_step("non_existent")
        self.assertIsNone(step)

    def test_get_ready_steps(self):
        """测试获取就绪步骤"""
        ready = self.plan.get_ready_steps()
        # 只有 step_001 没有依赖，应该就绪
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "step_001")

        # 标记 step_001 为完成
        self.plan.get_step("step_001").status = StepStatus.COMPLETED
        ready = self.plan.get_ready_steps()
        # step_002 现在应该就绪
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "step_002")

    def test_plan_to_dict(self):
        """测试计划序列化"""
        data = self.plan.to_dict()
        self.assertEqual(data['task_id'], 'test_task_001')
        self.assertEqual(data['description'], '测试任务')
        self.assertEqual(len(data['steps']), 3)


class TestTaskPlanner(unittest.TestCase):
    """任务规划器测试"""

    def setUp(self):
        self.planner = TaskPlanner(use_llm=False)

    def test_simple_command(self):
        """测试简单命令规划"""
        instruction = "打开记事本"
        plan = self.planner.plan(instruction)

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertGreater(len(plan.steps), 0)

    def test_compound_command(self):
        """测试复合命令规划"""
        instruction = "打开记事本 输入Hello World"
        plan = self.planner.plan(instruction)

        self.assertIsInstance(plan, ExecutionPlan)
        # 应该分解为多个步骤
        self.assertGreaterEqual(len(plan.steps), 2)

    def test_template_open_and_type(self):
        """测试打开并输入模板"""
        instruction = "打开记事本 输入测试内容"
        context = PlanningContext(instruction=instruction)

        plan = self.planner._template_open_and_type(instruction, context)

        self.assertEqual(plan.description, instruction)
        # 应该包含打开、等待、输入步骤
        step_types = [s.type for s in plan.steps]
        self.assertIn(StepType.ACTION, step_types)
        self.assertIn(StepType.WAIT, step_types)

    def test_fallback_plan(self):
        """测试回退计划"""
        instruction = "一些无法识别的指令"
        plan = self.planner._create_fallback_plan(instruction)

        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].type, StepType.ACTION)

    def test_adapt_plan_on_failure(self):
        """测试失败时的计划调整"""
        plan = self.planner.plan("打开记事本")

        # 模拟失败
        feedback = {
            "failed_step": plan.steps[0].id,
            "error": "timeout"
        }

        adapted = self.planner.adapt_plan(plan, feedback)
        self.assertTrue(adapted.context.get('adapted', False))


class TestPlanExecution(unittest.TestCase):
    """计划执行测试"""

    def setUp(self):
        self.planner = TaskPlanner(use_llm=False)

    def test_execution_order(self):
        """测试执行顺序"""
        steps = [
            Step(id="s1", type=StepType.ACTION, description="步骤1", params={}),
            Step(id="s2", type=StepType.ACTION, description="步骤2", params={}, depends_on=["s1"]),
            Step(id="s3", type=StepType.ACTION, description="步骤3", params={}, depends_on=["s2"]),
        ]
        plan = ExecutionPlan(task_id="test", description="测试", steps=steps)

        # 验证初始状态
        ready = plan.get_ready_steps()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "s1")

        # 完成步骤1
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "s2")

        # 完成步骤2
        steps[1].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].id, "s3")

    def test_parallel_execution(self):
        """测试并行执行准备"""
        steps = [
            Step(id="s1", type=StepType.ACTION, description="步骤1", params={}),
            Step(id="s2", type=StepType.ACTION, description="步骤2", params={}, depends_on=["s1"]),
            Step(id="s3", type=StepType.ACTION, description="步骤3", params={}, depends_on=["s1"]),  # 与 s2 并行
        ]
        plan = ExecutionPlan(task_id="test", description="测试", steps=steps)

        # 完成步骤1
        steps[0].status = StepStatus.COMPLETED
        ready = plan.get_ready_steps()

        # s2 和 s3 都应该就绪（并行）
        self.assertEqual(len(ready), 2)
        ready_ids = [s.id for s in ready]
        self.assertIn("s2", ready_ids)
        self.assertIn("s3", ready_ids)


class TestQuickPlan(unittest.TestCase):
    """快速规划测试"""

    def test_quick_plan_open_app(self):
        """测试快速规划打开应用"""
        result = quick_plan("打开计算器")

        self.assertIn('task_id', result)
        self.assertIn('steps', result)
        self.assertGreater(len(result['steps']), 0)


class TestContextHandling(unittest.TestCase):
    """上下文处理测试"""

    def test_context_creation(self):
        """测试上下文创建"""
        context = PlanningContext(
            instruction="测试指令",
            current_app="TestApp",
            available_elements=[{"type": "button", "x": 100, "y": 100}]
        )

        self.assertEqual(context.instruction, "测试指令")
        self.assertEqual(context.current_app, "TestApp")
        self.assertEqual(len(context.available_elements), 1)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestStep))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutionPlan))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskPlanner))
    suite.addTests(loader.loadTestsFromTestCase(TestPlanExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestQuickPlan))
    suite.addTests(loader.loadTestsFromTestCase(TestContextHandling))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
