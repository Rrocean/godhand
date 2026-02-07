#!/usr/bin/env python3
"""ElementLibrary 测试"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.element_library import (
    ElementLibrary, ElementTemplate, CachedElement
)


class TestElementTemplate(unittest.TestCase):
    """元素模板测试"""

    def test_creation(self):
        template = ElementTemplate(
            template_id="tpl_001",
            name="保存按钮",
            app_name="记事本",
            element_type="button",
            image_hash="abc123"
        )
        self.assertEqual(template.name, "保存按钮")
        self.assertEqual(template.hit_count, 0)

    def test_to_dict(self):
        template = ElementTemplate(
            template_id="tpl_002",
            name="测试",
            app_name="App",
            element_type="input",
            image_hash="xyz",
            hit_count=5
        )
        data = template.to_dict()
        self.assertEqual(data["hit_count"], 5)


class TestCachedElement(unittest.TestCase):
    """缓存元素测试"""

    def test_is_valid(self):
        cached = CachedElement(
            element_id="elem_001",
            template_id=None,
            x=100, y=200,
            width=50, height=30,
            confidence=0.9,
            detection_method="cv",
            timestamp=__import__('time').time(),
            ttl=300
        )
        self.assertTrue(cached.is_valid())

    def test_is_expired(self):
        cached = CachedElement(
            element_id="elem_002",
            template_id=None,
            x=100, y=200,
            width=50, height=30,
            confidence=0.9,
            detection_method="cv",
            timestamp=0,  # 很久以前
            ttl=1
        )
        self.assertFalse(cached.is_valid())


class TestElementLibrary(unittest.TestCase):
    """元素库测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.lib = ElementLibrary(data_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_template(self):
        img = Image.new('RGB', (100, 100), color='red')
        template = self.lib.add_template(
            name="测试按钮",
            app_name="TestApp",
            element_type="button",
            screenshot=img,
            bbox=(10, 10, 50, 30)
        )
        self.assertIsNotNone(template.template_id)
        self.assertEqual(template.name, "测试按钮")

    def test_find_template(self):
        img = Image.new('RGB', (100, 100))
        self.lib.add_template(
            name="保存按钮",
            app_name="App",
            element_type="button",
            screenshot=img,
            bbox=(10, 10, 50, 30)
        )

        found = self.lib.find_template("保存按钮")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "保存按钮")

    def test_cache_element(self):
        cached = self.lib.cache_element(
            element_id="elem_001",
            x=100, y=200,
            width=50, height=30,
            confidence=0.95,
            detection_method="cv"
        )
        self.assertEqual(cached.element_id, "elem_001")

        retrieved = self.lib.get_cached_element("elem_001")
        self.assertIsNotNone(retrieved)

    def test_find_in_cache(self):
        self.lib.cache_element(
            element_id="elem_001",
            x=150, y=250,
            width=50, height=30,
            confidence=0.95
        )

        found = self.lib.find_in_cache(155, 255)
        self.assertIsNotNone(found)

    def test_clear_expired(self):
        # 添加一个过期的元素
        self.lib.cache_element(
            element_id="elem_expired",
            x=100, y=100,
            width=50, height=30,
            confidence=0.9,
            ttl=-1  # 已过期
        )

        cleared = self.lib.clear_expired_cache()
        self.assertGreaterEqual(cleared, 1)

    def test_stats(self):
        stats = self.lib.get_stats()
        self.assertIn("templates_count", stats)
        self.assertIn("cache_size", stats)
        self.assertIn("cache_hit_rate", stats)


if __name__ == "__main__":
    unittest.main()
