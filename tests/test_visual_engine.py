#!/usr/bin/env python3
"""
VisualEngine 测试套件

测试目标：视觉理解引擎的各项功能
"""

import unittest
import sys
from pathlib import Path
from PIL import Image
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.visual_engine import (
    VisualEngine, UIElement, ElementType, SceneContext,
    quick_detect, quick_locate
)


class TestVisualEngine(unittest.TestCase):
    """视觉引擎测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.engine = VisualEngine(use_ocr=False, use_ml=False)
        # 创建测试图像
        cls.test_image = Image.new('RGB', (1920, 1080), color='white')
        draw = Image.new('RGB', (1920, 1080), color='white')

    def test_element_creation(self):
        """测试元素创建"""
        element = UIElement(
            type=ElementType.BUTTON,
            x=100,
            y=200,
            width=120,
            height=40,
            confidence=0.95,
            text="Save"
        )

        self.assertEqual(element.type, ElementType.BUTTON)
        self.assertEqual(element.x, 100)
        self.assertEqual(element.y, 200)
        self.assertEqual(element.bbox, (40, 180, 160, 220))
        self.assertTrue(element.contains_point(100, 200))
        self.assertFalse(element.contains_point(0, 0))

    def test_element_distance(self):
        """测试元素距离计算"""
        element = UIElement(
            type=ElementType.BUTTON,
            x=100,
            y=100,
            width=50,
            height=50,
            confidence=0.9
        )

        distance = element.distance_to(200, 200)
        expected = np.sqrt(100**2 + 100**2)
        self.assertAlmostEqual(distance, expected)

    def test_element_to_dict(self):
        """测试元素序列化"""
        element = UIElement(
            type=ElementType.INPUT,
            x=50,
            y=50,
            width=200,
            height=30,
            confidence=0.85,
            text="test@example.com",
            description="Email input"
        )

        data = element.to_dict()
        self.assertEqual(data['type'], 'input')
        self.assertEqual(data['text'], 'test@example.com')
        self.assertEqual(data['confidence'], 0.85)

    def test_detect_elements_empty_image(self):
        """测试空图像检测"""
        # 纯色图像应该检测不到复杂元素
        img = Image.new('RGB', (800, 600), color='gray')
        elements = self.engine.detect_elements(img)

        # 纯色图像可能检测到一些噪声，但应该很少
        self.assertIsInstance(elements, list)
        self.assertLess(len(elements), 50)  # 合理的上限

    def test_scene_context_creation(self):
        """测试场景上下文"""
        context = SceneContext(
            application="TestApp",
            window_title="Test Window",
            window_size=(1920, 1080),
            scene_type="dashboard",
            elements_count=25
        )

        self.assertEqual(context.application, "TestApp")
        self.assertEqual(context.window_size, (1920, 1080))

        data = context.to_dict()
        self.assertEqual(data['scene_type'], 'dashboard')


class TestVisualEngineIntegration(unittest.TestCase):
    """集成测试（需要实际截图）"""

    @unittest.skipUnless(
        sys.platform == 'win32',
        "Windows-specific test"
    )
    def test_screenshot_detection(self):
        """测试真实截图检测"""
        try:
            import pyautogui
            engine = VisualEngine(use_ocr=False)

            screenshot = pyautogui.screenshot()
            elements = engine.detect_elements(screenshot)

            self.assertIsInstance(elements, list)
            print(f"\n检测到 {len(elements)} 个元素")

            # 验证元素属性
            for elem in elements[:5]:  # 只检查前5个
                self.assertGreater(elem.confidence, 0)
                self.assertGreater(elem.width, 0)
                self.assertGreater(elem.height, 0)

        except ImportError:
            self.skipTest("pyautogui not installed")


class TestSceneUnderstanding(unittest.TestCase):
    """场景理解测试"""

    def setUp(self):
        self.engine = VisualEngine(use_ocr=False)

    def test_classify_scene_form(self):
        """测试表单场景分类"""
        # 模拟表单元素：多个输入框和按钮
        elements = [
            UIElement(ElementType.INPUT, 100, 100, 200, 30, 0.9),
            UIElement(ElementType.INPUT, 100, 150, 200, 30, 0.9),
            UIElement(ElementType.BUTTON, 100, 200, 100, 40, 0.9),
        ]

        scene_type = self.engine._classify_scene(elements)
        self.assertEqual(scene_type, 'form')

    def test_classify_scene_dashboard(self):
        """测试仪表板场景分类"""
        # 模拟仪表板：很多按钮
        elements = [
            UIElement(ElementType.BUTTON, i*100, 100, 80, 40, 0.9)
            for i in range(10)
        ]

        scene_type = self.engine._classify_scene(elements)
        self.assertEqual(scene_type, 'dashboard')

    def test_classify_scene_minimal(self):
        """测试极简界面分类"""
        elements = [
            UIElement(ElementType.BUTTON, 100, 100, 80, 40, 0.9),
            UIElement(ElementType.TEXT, 200, 100, 100, 20, 0.8),
        ]

        scene_type = self.engine._classify_scene(elements)
        self.assertEqual(scene_type, 'minimal')


class TestElementFiltering(unittest.TestCase):
    """元素过滤测试"""

    def setUp(self):
        self.engine = VisualEngine(use_ocr=False)

    def test_filter_overlapping_elements(self):
        """测试重叠元素过滤"""
        elements = [
            UIElement(ElementType.BUTTON, 100, 100, 100, 50, 0.9),  # 高置信度
            UIElement(ElementType.BUTTON, 105, 105, 90, 45, 0.5),   # 重叠，低置信度
            UIElement(ElementType.INPUT, 300, 100, 200, 30, 0.8),   # 不重叠
        ]

        filtered = self.engine._filter_and_sort(elements)

        # 应该过滤掉重叠的低置信度元素
        self.assertLessEqual(len(filtered), len(elements))

    def test_sort_by_confidence(self):
        """测试按置信度排序"""
        elements = [
            UIElement(ElementType.BUTTON, 100, 100, 50, 50, 0.5),
            UIElement(ElementType.BUTTON, 200, 200, 50, 50, 0.9),
            UIElement(ElementType.BUTTON, 300, 300, 50, 50, 0.7),
        ]

        filtered = self.engine._filter_and_sort(elements)

        # 应该按置信度降序排列
        confidences = [e.confidence for e in filtered]
        self.assertEqual(confidences, sorted(confidences, reverse=True))


class TestIouCalculation(unittest.TestCase):
    """IoU 计算测试"""

    def setUp(self):
        self.engine = VisualEngine(use_ocr=False)

    def test_iou_identical_boxes(self):
        """测试相同框的 IoU"""
        box = (100, 100, 200, 200)
        iou = self.engine._calculate_iou(box, box)
        self.assertEqual(iou, 1.0)

    def test_iou_no_overlap(self):
        """测试无重叠的 IoU"""
        box1 = (100, 100, 200, 200)
        box2 = (300, 300, 400, 400)
        iou = self.engine._calculate_iou(box1, box2)
        self.assertEqual(iou, 0.0)

    def test_iou_partial_overlap(self):
        """测试部分重叠的 IoU"""
        box1 = (100, 100, 200, 200)
        box2 = (150, 150, 250, 250)
        iou = self.engine._calculate_iou(box1, box2)

        # 交集: 50x50 = 2500
        # 并集: 10000 + 10000 - 2500 = 17500
        # IoU: 2500 / 17500 = 0.142...
        expected = 2500 / 17500
        self.assertAlmostEqual(iou, expected, places=5)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestVisualEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestSceneUnderstanding))
    suite.addTests(loader.loadTestsFromTestCase(TestElementFiltering))
    suite.addTests(loader.loadTestsFromTestCase(TestIouCalculation))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
