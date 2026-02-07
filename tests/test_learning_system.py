#!/usr/bin/env python3
"""LearningSystem 测试"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.learning_system import (
    LearningSystem, Demonstration, LearnedPattern,
    PlanningContext, quick_plan
)


class TestDemonstration(unittest.TestCase):
    """演示记录测试"""

    def test_creation(self):
        demo = Demonstration(
            id="test_001",
            task_description="打开记事本",
            actions=[{"type": "open_app"}],
            context={}
        )
        self.assertEqual(demo.task_description, "打开记事本")
        self.assertEqual(len(demo.actions), 1)

    def test_to_dict(self):
        demo = Demonstration(
            id="test_002",
            task_description="测试",
            actions=[],
            context={},
            success_count=5
        )
        data = demo.to_dict()
        self.assertEqual(data["success_count"], 5)


class TestLearningSystem(unittest.TestCase):
    """学习系统测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ls = LearningSystem(data_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_recording(self):
        # 开始录制
        rec_id = self.ls.start_recording("测试任务")
        self.assertIn("rec_", rec_id)

        # 记录动作
        self.ls.record_action({"type": "click", "x": 100, "y": 200})
        self.ls.record_action({"type": "type", "text": "hello"})

        # 停止录制
        demo = self.ls.stop_recording(user_rating=5)
        self.assertEqual(demo.task_description, "测试任务")
        self.assertEqual(len(demo.actions), 2)

    def test_find_similar(self):
        # 先录制一个演示
        self.ls.start_recording("打开记事本")
        self.ls.record_action({"type": "open_app", "app": "notepad"})
        self.ls.stop_recording()

        # 查找相似的
        similar = self.ls.find_similar_demonstration("打开notepad")
        self.assertIsNotNone(similar)

    def test_suggest_workflows(self):
        # 添加一些演示记录
        for i in range(3):
            self.ls.command_frequency[f"command_{i}"] = i + 1

        suggestions = self.ls.suggest_workflows()
        self.assertIsInstance(suggestions, list)

    def test_feedback(self):
        self.ls.record_feedback(
            task_id="task_001",
            instruction="测试指令",
            result={"success": True},
            rating=5,
            comments="很好"
        )

        self.assertEqual(len(self.ls.feedback_records), 1)

    def test_stats(self):
        stats = self.ls.get_learning_stats()
        self.assertIn("demonstrations", stats)
        self.assertIn("patterns", stats)


if __name__ == "__main__":
    unittest.main()
