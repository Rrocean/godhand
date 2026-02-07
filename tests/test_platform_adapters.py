#!/usr/bin/env python3
"""PlatformAdapters 测试"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.platform_adapters import (
    WindowInfo, ScreenInfo,
    get_platform_adapter
)


class TestWindowInfo(unittest.TestCase):
    """窗口信息测试"""

    def test_creation(self):
        win = WindowInfo(
            handle=12345,
            title="Test Window",
            position=(100, 200),
            size=(800, 600),
            is_active=True
        )
        self.assertEqual(win.title, "Test Window")
        self.assertEqual(win.size, (800, 600))

    def test_to_dict(self):
        win = WindowInfo(
            handle=12345,
            title="Test",
            position=(0, 0),
            size=(100, 100),
            is_active=False
        )
        data = win.to_dict()
        self.assertEqual(data["title"], "Test")


class TestScreenInfo(unittest.TestCase):
    """屏幕信息测试"""

    def test_creation(self):
        screen = ScreenInfo(
            width=1920,
            height=1080,
            scale_factor=1.0
        )
        self.assertEqual(screen.width, 1920)
        self.assertEqual(screen.scale_factor, 1.0)


class TestPlatformAdapter(unittest.TestCase):
    """平台适配器测试"""

    def test_get_adapter(self):
        adapter = get_platform_adapter()
        self.assertIsNotNone(adapter)
        self.assertIn(adapter.platform_name, ["Windows", "macOS", "Linux"])

    def test_screen_info(self):
        adapter = get_platform_adapter()
        screen = adapter.get_screen_info()
        self.assertIsInstance(screen, ScreenInfo)
        self.assertGreater(screen.width, 0)
        self.assertGreater(screen.height, 0)

    def test_mouse_position(self):
        adapter = get_platform_adapter()
        pos = adapter.get_mouse_position()
        self.assertIsInstance(pos, tuple)
        self.assertEqual(len(pos), 2)


if __name__ == "__main__":
    unittest.main()
