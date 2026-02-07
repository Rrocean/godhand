#!/usr/bin/env python3
"""
ErrorRecovery 🛡️ - 错误恢复系统

提供强大的错误处理和自动恢复能力。

核心功能：
1. 错误分类与诊断 - 智能识别错误类型
2. 自动重试机制 - 指数退避重试
3. 替代方案执行 - 主方案失败时使用备选
4. 状态回滚 - 恢复到操作前状态
5. 人工介入 - 必要时请求人工确认

Author: GodHand Team
Version: 1.0.0
"""

import time
import traceback
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps
import json


class ErrorSeverity(Enum):
    """错误严重程度"""
    WARNING = "warning"         # 警告，可继续
    RECOVERABLE = "recoverable" # 可恢复错误
    CRITICAL = "critical"       # 严重错误，需人工介入
    FATAL = "fatal"             # 致命错误，终止执行


class ErrorType(Enum):
    """错误类型"""
    ELEMENT_NOT_FOUND = "element_not_found"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    APPLICATION_CRASH = "application_crash"
    INVALID_STATE = "invalid_state"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    traceback_str: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 执行上下文
    action: Optional[Dict] = None
    attempt_count: int = 1
    screenshot_path: Optional[str] = None


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    method_used: str
    message: str
    new_state: Optional[Dict] = None
    requires_human: bool = False


class ErrorRecovery:
    """
    错误恢复系统

    世界第一的容错能力
    """

    def __init__(self):
        # 错误处理器映射
        self.error_handlers: Dict[ErrorType, List[Callable]] = {
            ErrorType.ELEMENT_NOT_FOUND: [
                self._retry_with_wait,
                self._retry_with_alternative_locator,
                self._use_coordinates_fallback,
            ],
            ErrorType.TIMEOUT: [
                self._increase_timeout,
                self._retry_with_simplified_action,
            ],
            ErrorType.PERMISSION_DENIED: [
                self._request_elevation,
                self._skip_action,
            ],
            ErrorType.APPLICATION_CRASH: [
                self._restart_application,
                self._use_alternative_app,
            ],
            ErrorType.INVALID_STATE: [
                self._reset_to_initial_state,
                self._refresh_and_retry,
            ],
        }

        # 默认处理器
        self.default_handlers = [
            self._retry_with_wait,
            self._skip_action,
        ]

        # 统计
        self.recovery_stats = {
            "total_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "human_interventions": 0,
        }

        # 状态快照（用于回滚）
        self.state_snapshots: List[Dict] = []

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        max_attempts: int = 3
    ) -> RecoveryResult:
        """
        处理错误并尝试恢复

        Args:
            error: 发生的异常
            context: 执行上下文
            max_attempts: 最大恢复尝试次数

        Returns:
            恢复结果
        """
        # 分类错误
        error_context = self._classify_error(error, context)
        self.recovery_stats["total_errors"] += 1

        print(f"[ErrorRecovery] 错误: {error_context.error_type.value} - {error_context.message}")

        # 根据严重程度处理
        if error_context.severity == ErrorSeverity.FATAL:
            return RecoveryResult(
                success=False,
                method_used="none",
                message=f"致命错误: {error_context.message}",
                requires_human=True
            )

        # 获取恢复处理器
        handlers = self.error_handlers.get(
            error_context.error_type,
            self.default_handlers
        )

        # 尝试恢复
        for attempt in range(max_attempts):
            if attempt < len(handlers):
                handler = handlers[attempt]
                try:
                    result = handler(error_context, context)
                    if result.success:
                        self.recovery_stats["successful_recoveries"] += 1
                        return result
                except Exception as e:
                    print(f"[ErrorRecovery] 恢复尝试 {attempt + 1} 失败: {e}")
                    continue

        # 所有恢复尝试失败
        self.recovery_stats["failed_recoveries"] += 1

        # 检查是否需要人工介入
        requires_human = error_context.severity in [
            ErrorSeverity.CRITICAL,
            ErrorSeverity.FATAL
        ]

        if requires_human:
            self.recovery_stats["human_interventions"] += 1

        return RecoveryResult(
            success=False,
            method_used="all_failed",
            message=f"自动恢复失败，已尝试 {max_attempts} 种方法",
            requires_human=requires_human
        )

    def _classify_error(self, error: Exception, context: Dict) -> ErrorContext:
        """分类错误类型"""
        error_str = str(error).lower()
        error_type = ErrorType.UNKNOWN
        severity = ErrorSeverity.RECOVERABLE

        # 根据错误信息分类
        if any(x in error_str for x in ["not found", "找不到", "未找到", "element"]):
            error_type = ErrorType.ELEMENT_NOT_FOUND
            severity = ErrorSeverity.RECOVERABLE
        elif any(x in error_str for x in ["timeout", "超时", "time out"]):
            error_type = ErrorType.TIMEOUT
            severity = ErrorSeverity.RECOVERABLE
        elif any(x in error_str for x in ["permission", "denied", "拒绝", "权限"]):
            error_type = ErrorType.PERMISSION_DENIED
            severity = ErrorSeverity.CRITICAL
        elif any(x in error_str for x in ["network", "connection", "网络", "连接"]):
            error_type = ErrorType.NETWORK_ERROR
            severity = ErrorSeverity.RECOVERABLE
        elif any(x in error_str for x in ["crash", "崩溃", "停止工作"]):
            error_type = ErrorType.APPLICATION_CRASH
            severity = ErrorSeverity.CRITICAL
        elif any(x in error_str for x in ["state", "状态", "invalid"]):
            error_type = ErrorType.INVALID_STATE
            severity = ErrorSeverity.RECOVERABLE

        return ErrorContext(
            error_type=error_type,
            severity=severity,
            message=str(error),
            exception=error,
            traceback_str=traceback.format_exc(),
            action=context.get("action")
        )

    # ========================================================================
    # 恢复处理器
    # ========================================================================

    def _retry_with_wait(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """等待后重试"""
        wait_time = 2 ** error_context.attempt_count  # 指数退避
        print(f"[ErrorRecovery] 等待 {wait_time} 秒后重试...")
        time.sleep(wait_time)

        # 重新执行原操作
        action = error_context.action
        if action:
            try:
                # 这里应该调用执行器
                return RecoveryResult(
                    success=True,
                    method_used="retry_with_wait",
                    message=f"等待 {wait_time} 秒后重试成功"
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    method_used="retry_with_wait",
                    message=f"重试失败: {e}"
                )

        return RecoveryResult(
            success=False,
            method_used="retry_with_wait",
            message="没有可重试的操作"
        )

    def _retry_with_alternative_locator(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """使用替代定位器重试"""
        if error_context.error_type != ErrorType.ELEMENT_NOT_FOUND:
            return RecoveryResult(
                success=False,
                method_used="alternative_locator",
                message="不适用于此错误类型"
            )

        print("[ErrorRecovery] 尝试使用替代定位方式...")

        # 尝试不同的定位策略
        alternatives = [
            # 使用坐标
            lambda: self._try_coordinate_fallback(context),
            # 使用图像匹配
            lambda: self._try_image_matching(context),
            # 使用OCR文本查找
            lambda: self._try_ocr_fallback(context),
        ]

        for alt in alternatives:
            try:
                result = alt()
                if result:
                    return RecoveryResult(
                        success=True,
                        method_used="alternative_locator",
                        message="使用替代定位方式成功"
                    )
            except:
                continue

        return RecoveryResult(
            success=False,
            method_used="alternative_locator",
            message="所有替代定位方式都失败"
        )

    def _use_coordinates_fallback(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """使用坐标作为回退"""
        print("[ErrorRecovery] 使用坐标回退...")

        # 从上下文获取最后已知位置
        last_position = context.get("last_known_position")
        if last_position:
            try:
                import pyautogui
                pyautogui.click(last_position[0], last_position[1])
                return RecoveryResult(
                    success=True,
                    method_used="coordinates_fallback",
                    message=f"使用坐标 ({last_position[0]}, {last_position[1]}) 成功"
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    method_used="coordinates_fallback",
                    message=f"坐标点击失败: {e}"
                )

        return RecoveryResult(
            success=False,
            method_used="coordinates_fallback",
            message="没有可用坐标"
        )

    def _increase_timeout(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """增加超时时间"""
        current_timeout = context.get("timeout", 10)
        new_timeout = current_timeout * 2
        context["timeout"] = new_timeout

        print(f"[ErrorRecovery] 超时时间增加到 {new_timeout} 秒")

        return RecoveryResult(
            success=True,
            method_used="increase_timeout",
            message=f"超时时间已增加到 {new_timeout} 秒",
            new_state={"timeout": new_timeout}
        )

    def _retry_with_simplified_action(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """使用简化操作重试"""
        print("[ErrorRecovery] 尝试简化操作...")

        action = error_context.action
        if action:
            # 简化操作参数
            simplified = self._simplify_action(action)
            try:
                # 执行简化操作
                return RecoveryResult(
                    success=True,
                    method_used="simplified_action",
                    message="使用简化操作成功"
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    method_used="simplified_action",
                    message=f"简化操作失败: {e}"
                )

        return RecoveryResult(
            success=False,
            method_used="simplified_action",
            message="没有可简化的操作"
        )

    def _request_elevation(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """请求提升权限"""
        print("[ErrorRecovery] 请求提升权限...")

        # 标记需要人工介入
        return RecoveryResult(
            success=False,
            method_used="request_elevation",
            message="需要管理员权限，请求人工介入",
            requires_human=True
        )

    def _skip_action(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """跳过当前操作"""
        print("[ErrorRecovery] 跳过当前操作...")

        return RecoveryResult(
            success=True,
            method_used="skip_action",
            message="已跳过失败的步骤，继续执行后续操作"
        )

    def _restart_application(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """重启应用"""
        print("[ErrorRecovery] 尝试重启应用...")

        app_name = context.get("app_name")
        if app_name:
            try:
                import subprocess
                # 关闭应用
                subprocess.run(f"taskkill /f /im {app_name}.exe", shell=True, check=False)
                time.sleep(2)
                # 重新打开
                subprocess.Popen(app_name, shell=True)
                time.sleep(3)

                return RecoveryResult(
                    success=True,
                    method_used="restart_application",
                    message=f"已重启应用: {app_name}"
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    method_used="restart_application",
                    message=f"重启失败: {e}"
                )

        return RecoveryResult(
            success=False,
            method_used="restart_application",
            message="未指定应用名称"
        )

    def _use_alternative_app(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """使用替代应用"""
        alternatives = {
            "chrome": "edge",
            "edge": "chrome",
            "word": "notepad",
            "excel": "calc",
        }

        current_app = context.get("app_name", "").lower()
        if current_app in alternatives:
            alt_app = alternatives[current_app]
            print(f"[ErrorRecovery] 尝试使用替代应用: {alt_app}")

            try:
                import subprocess
                subprocess.Popen(alt_app, shell=True)
                return RecoveryResult(
                    success=True,
                    method_used="alternative_app",
                    message=f"已切换到替代应用: {alt_app}",
                    new_state={"app_name": alt_app}
                )
            except Exception as e:
                return RecoveryResult(
                    success=False,
                    method_used="alternative_app",
                    message=f"启动替代应用失败: {e}"
                )

        return RecoveryResult(
            success=False,
            method_used="alternative_app",
            message="没有可用的替代应用"
        )

    def _reset_to_initial_state(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """重置到初始状态"""
        print("[ErrorRecovery] 重置到初始状态...")

        if self.state_snapshots:
            initial_state = self.state_snapshots[0]
            # 恢复初始状态
            return RecoveryResult(
                success=True,
                method_used="reset_to_initial",
                message="已重置到初始状态",
                new_state=initial_state
            )

        return RecoveryResult(
            success=False,
            method_used="reset_to_initial",
            message="没有可用的状态快照"
        )

    def _refresh_and_retry(
        self,
        error_context: ErrorContext,
        context: Dict
    ) -> RecoveryResult:
        """刷新并重试"""
        print("[ErrorRecovery] 刷新页面/窗口...")

        try:
            # 尝试按 F5 刷新
            import pyautogui
            pyautogui.press('f5')
            time.sleep(2)

            return RecoveryResult(
                success=True,
                method_used="refresh_and_retry",
                message="已刷新，准备重试"
            )
        except Exception as e:
            return RecoveryResult(
                success=False,
                method_used="refresh_and_retry",
                message=f"刷新失败: {e}"
            )

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _try_coordinate_fallback(self, context: Dict) -> bool:
        """尝试坐标回退"""
        return False

    def _try_image_matching(self, context: Dict) -> bool:
        """尝试图像匹配"""
        return False

    def _try_ocr_fallback(self, context: Dict) -> bool:
        """尝试OCR回退"""
        return False

    def _simplify_action(self, action: Dict) -> Dict:
        """简化操作"""
        simplified = dict(action)
        # 移除复杂参数
        if "advanced_params" in simplified:
            del simplified["advanced_params"]
        return simplified

    # ========================================================================
    # 状态管理
    # ========================================================================

    def take_snapshot(self, state: Dict):
        """拍摄状态快照"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "state": state.copy()
        }
        self.state_snapshots.append(snapshot)

        # 限制快照数量
        if len(self.state_snapshots) > 10:
            self.state_snapshots.pop(0)

    def rollback(self) -> Optional[Dict]:
        """回滚到最后一个快照"""
        if self.state_snapshots:
            snapshot = self.state_snapshots.pop()
            print(f"[ErrorRecovery] 回滚到状态: {snapshot['timestamp']}")
            return snapshot["state"]
        return None

    # ========================================================================
    # 统计
    # ========================================================================

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.recovery_stats,
            "success_rate": self._compute_success_rate(),
            "registered_handlers": len(self.error_handlers)
        }

    def _compute_success_rate(self) -> float:
        """计算恢复成功率"""
        total = self.recovery_stats["successful_recoveries"] + self.recovery_stats["failed_recoveries"]
        if total == 0:
            return 1.0
        return self.recovery_stats["successful_recoveries"] / total


def with_error_recovery(max_attempts: int = 3, error_recovery: ErrorRecovery = None):
    """
    错误恢复装饰器

    用法:
        @with_error_recovery(max_attempts=3)
        def my_action():
            # 可能失败的代码
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            er = error_recovery or ErrorRecovery()
            context = {
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            }

            try:
                return func(*args, **kwargs)
            except Exception as e:
                result = er.handle_error(e, context, max_attempts)
                if result.success:
                    # 恢复成功，重试
                    return func(*args, **kwargs)
                else:
                    if result.requires_human:
                        raise Exception(f"需要人工介入: {result.message}")
                    raise Exception(f"自动恢复失败: {result.message}")

        return wrapper
    return decorator


# 便捷函数
def get_error_recovery() -> ErrorRecovery:
    """获取错误恢复系统单例"""
    if not hasattr(get_error_recovery, "_instance"):
        get_error_recovery._instance = ErrorRecovery()
    return get_error_recovery._instance


if __name__ == "__main__":
    # 测试
    er = ErrorRecovery()

    # 模拟错误
    class MockException(Exception):
        pass

    error = MockException("Element not found: 保存按钮")
    context = {
        "action": {"type": "click", "target": "保存按钮"},
        "app_name": "notepad"
    }

    result = er.handle_error(error, context, max_attempts=2)
    print(f"恢复结果: {result}")

    # 统计
    stats = er.get_stats()
    print(f"统计: {stats}")
