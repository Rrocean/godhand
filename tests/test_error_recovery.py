#!/usr/bin/env python3
"""ErrorRecovery 测试"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.error_recovery import (
    ErrorRecovery, ErrorType, ErrorSeverity,
    RecoveryResult, with_error_recovery
)


class TestErrorClassification(unittest.TestCase):
    """错误分类测试"""

    def setUp(self):
        self.er = ErrorRecovery()

    def test_element_not_found(self):
        error = Exception("Element not found: 保存按钮")
        context = {"action": {"type": "click"}}

        result = self.er.handle_error(error, context, max_attempts=1)
        self.assertIsInstance(result, RecoveryResult)

    def test_timeout(self):
        error = Exception("Timeout waiting for window")
        context = {}

        result = self.er.handle_error(error, context, max_attempts=1)
        self.assertIsInstance(result, RecoveryResult)

    def test_permission_denied(self):
        error = Exception("Permission denied")
        context = {}

        result = self.er.handle_error(error, context, max_attempts=1)
        self.assertIsInstance(result, RecoveryResult)


class TestRecoveryStrategies(unittest.TestCase):
    """恢复策略测试"""

    def setUp(self):
        self.er = ErrorRecovery()

    def test_skip_action(self):
        from core.error_recovery import ErrorContext
        context = {"action": {"type": "test"}}
        error_ctx = ErrorContext(
            error_type=ErrorType.UNKNOWN,
            severity=ErrorSeverity.WARNING,
            message="test"
        )

        result = self.er._skip_action(error_ctx, context)
        self.assertTrue(result.success)

    def test_increase_timeout(self):
        from core.error_recovery import ErrorContext
        context = {"timeout": 5}
        error_ctx = ErrorContext(
            error_type=ErrorType.TIMEOUT,
            severity=ErrorSeverity.RECOVERABLE,
            message="timeout"
        )

        result = self.er._increase_timeout(error_ctx, context)
        self.assertTrue(result.success)
        self.assertEqual(result.new_state["timeout"], 10)


class TestDecorator(unittest.TestCase):
    """装饰器测试"""

    def test_with_recovery(self):
        call_count = [0]

        @with_error_recovery(max_attempts=1)
        def failing_function():
            call_count[0] += 1
            raise Exception("test error")

        with self.assertRaises(Exception):
            failing_function()

        self.assertEqual(call_count[0], 2)  # 原始调用 + 1次重试


class TestStats(unittest.TestCase):
    """统计测试"""

    def test_stats(self):
        er = ErrorRecovery()
        stats = er.get_stats()

        self.assertIn("total_errors", stats)
        self.assertIn("successful_recoveries", stats)
        self.assertIn("success_rate", stats)


if __name__ == "__main__":
    unittest.main()
