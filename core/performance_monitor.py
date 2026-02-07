#!/usr/bin/env python3
"""
PerformanceMonitor 📊 - 性能监控系统

全面监控 GodHand 的性能指标，提供详细的执行统计和分析。

核心功能：
1. 执行时间追踪 - 记录每个操作的耗时
2. 成功率统计 - 分析各类操作的成功率
3. 资源使用监控 - CPU、内存、网络等
4. 性能报告生成 - 生成详细的性能报告

Author: GodHand Team
Version: 1.0.0
"""

import time
import json
import sqlite3
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import contextmanager
import threading


@dataclass
class ExecutionMetrics:
    """执行指标"""
    task_id: str
    instruction: str
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0
    success: bool = False
    error_type: Optional[str] = None
    steps_count: int = 0
    mode: str = "auto"  # auto, visual, plan

    def finalize(self, success: bool, error_type: str = None):
        """完成记录"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_type = error_type


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    network_io_sent: int
    network_io_recv: int
    disk_io_read: int
    disk_io_write: int


class PerformanceMonitor:
    """
    性能监控系统

    世界级的性能追踪能力
    """

    def __init__(self, data_dir: str = "./data/metrics"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # SQLite 数据库
        self.db_path = self.data_dir / "metrics.db"
        self._init_database()

        # 运行时指标
        self.active_executions: Dict[str, ExecutionMetrics] = {}
        self.current_session_id: Optional[str] = None

        # 缓存统计（用于快速查询）
        self._stats_cache: Dict[str, Any] = {}
        self._cache_timestamp: float = 0

        # 系统监控线程
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._system_metrics: List[SystemMetrics] = []

        print(f"[PerformanceMonitor] 初始化完成，数据库: {self.db_path}")

    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    session_id TEXT,
                    instruction TEXT,
                    mode TEXT,
                    start_time REAL,
                    end_time REAL,
                    duration REAL,
                    success INTEGER,
                    error_type TEXT,
                    steps_count INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    memory_used_mb REAL,
                    network_sent INTEGER,
                    network_recv INTEGER
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_time
                ON executions(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_task
                ON executions(task_id)
            """)

            conn.commit()

    # ========================================================================
    # 执行监控
    # ========================================================================

    def start_execution(self, task_id: str, instruction: str, mode: str = "auto") -> ExecutionMetrics:
        """开始监控执行"""
        metrics = ExecutionMetrics(
            task_id=task_id,
            instruction=instruction,
            start_time=time.time(),
            mode=mode
        )
        self.active_executions[task_id] = metrics
        return metrics

    def end_execution(
        self,
        task_id: str,
        success: bool,
        steps_count: int = 0,
        error_type: str = None
    ):
        """结束执行监控"""
        if task_id not in self.active_executions:
            return

        metrics = self.active_executions[task_id]
        metrics.finalize(success, error_type)
        metrics.steps_count = steps_count

        # 保存到数据库
        self._save_execution_metrics(metrics)

        # 从活跃列表移除
        del self.active_executions[task_id]

    def _save_execution_metrics(self, metrics: ExecutionMetrics):
        """保存执行指标到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO executions
                (task_id, session_id, instruction, mode, start_time, end_time,
                 duration, success, error_type, steps_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.task_id,
                self.current_session_id,
                metrics.instruction[:200],  # 限制长度
                metrics.mode,
                metrics.start_time,
                metrics.end_time,
                metrics.duration,
                1 if metrics.success else 0,
                metrics.error_type,
                metrics.steps_count
            ))
            conn.commit()

    @contextmanager
    def track_execution(self, task_id: str, instruction: str, mode: str = "auto"):
        """上下文管理器追踪执行"""
        self.start_execution(task_id, instruction, mode)
        try:
            yield
            self.end_execution(task_id, success=True)
        except Exception as e:
            self.end_execution(task_id, success=False, error_type=type(e).__name__)
            raise

    # ========================================================================
    # 系统监控
    # ========================================================================

    def start_system_monitoring(self, interval: float = 5.0):
        """启动系统监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_system,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        print(f"[PerformanceMonitor] 系统监控已启动 (间隔: {interval}s)")

    def stop_system_monitoring(self):
        """停止系统监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        print("[PerformanceMonitor] 系统监控已停止")

    def _monitor_system(self, interval: float):
        """系统监控循环"""
        while self._monitoring:
            try:
                # 获取系统指标
                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                net_io = psutil.net_io_counters()

                metrics = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu,
                    memory_percent=memory.percent,
                    memory_used_mb=memory.used / 1024 / 1024,
                    network_io_sent=net_io.bytes_sent,
                    network_io_recv=net_io.bytes_recv,
                    disk_io_read=0,
                    disk_io_write=0
                )

                self._system_metrics.append(metrics)

                # 限制内存中的指标数量
                if len(self._system_metrics) > 1000:
                    self._system_metrics = self._system_metrics[-500:]

                # 保存到数据库（每10次保存一次）
                if len(self._system_metrics) % 10 == 0:
                    self._save_system_metrics(metrics)

            except Exception as e:
                print(f"[PerformanceMonitor] 系统监控错误: {e}")

            time.sleep(interval)

    def _save_system_metrics(self, metrics: SystemMetrics):
        """保存系统指标"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_metrics
                (timestamp, cpu_percent, memory_percent, memory_used_mb,
                 network_sent, network_recv)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp,
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.memory_used_mb,
                metrics.network_io_sent,
                metrics.network_io_recv
            ))
            conn.commit()

    # ========================================================================
    # 统计查询
    # ========================================================================

    def get_execution_stats(
        self,
        days: int = 7,
        mode: str = None
    ) -> Dict[str, Any]:
        """获取执行统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 基础统计
            query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(duration) as avg_duration,
                    MIN(duration) as min_duration,
                    MAX(duration) as max_duration
                FROM executions
                WHERE timestamp >= datetime('now', '-{} days')
            """.format(days)

            if mode:
                query += f" AND mode = '{mode}'"

            row = conn.execute(query).fetchone()

            total = row['total'] or 0
            success = row['success_count'] or 0

            return {
                "total_executions": total,
                "successful": success,
                "failed": total - success,
                "success_rate": success / total if total > 0 else 0,
                "avg_duration": row['avg_duration'] or 0,
                "min_duration": row['min_duration'] or 0,
                "max_duration": row['max_duration'] or 0
            }

    def get_mode_stats(self, days: int = 7) -> Dict[str, Dict]:
        """按模式统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT
                    mode,
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success
                FROM executions
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY mode
            """.format(days)).fetchall()

            return {
                row['mode']: {
                    "total": row['total'],
                    "success": row['success'],
                    "rate": row['success'] / row['total'] if row['total'] > 0 else 0
                }
                for row in rows
            }

    def get_error_stats(self, days: int = 7) -> Dict[str, int]:
        """错误统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT error_type, COUNT(*) as count
                FROM executions
                WHERE timestamp >= datetime('now', '-{} days')
                AND success = 0
                AND error_type IS NOT NULL
                GROUP BY error_type
            """.format(days)).fetchall()

            return {row['error_type']: row['count'] for row in rows}

    def get_top_commands(self, days: int = 7, limit: int = 10) -> List[Dict]:
        """获取最常用的命令"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT instruction, COUNT(*) as count, AVG(duration) as avg_time
                FROM executions
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY instruction
                ORDER BY count DESC
                LIMIT {}
            """.format(days, limit)).fetchall()

            return [
                {
                    "instruction": row['instruction'],
                    "count": row['count'],
                    "avg_time": row['avg_time']
                }
                for row in rows
            ]

    # ========================================================================
    # 报告生成
    # ========================================================================

    def generate_report(self, days: int = 7) -> str:
        """生成性能报告"""
        stats = self.get_execution_stats(days)
        mode_stats = self.get_mode_stats(days)
        error_stats = self.get_error_stats(days)
        top_commands = self.get_top_commands(days)

        report = f"""
# GodHand 性能报告 ({days}天)
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 执行统计
- 总执行次数: {stats['total_executions']}
- 成功: {stats['successful']} ({stats['success_rate']*100:.1f}%)
- 失败: {stats['failed']}
- 平均执行时间: {stats['avg_duration']:.2f}s
- 最快: {stats['min_duration']:.2f}s
- 最慢: {stats['max_duration']:.2f}s

## 按模式统计
"""
        for mode, mode_stat in mode_stats.items():
            report += f"- {mode}: {mode_stat['total']}次 (成功率 {mode_stat['rate']*100:.1f}%)\n"

        report += "\n## 错误统计\n"
        if error_stats:
            for error_type, count in sorted(error_stats.items(), key=lambda x: -x[1]):
                report += f"- {error_type}: {count}次\n"
        else:
            report += "无错误记录\n"

        report += "\n## 热门指令\n"
        for i, cmd in enumerate(top_commands, 1):
            report += f"{i}. {cmd['instruction'][:50]} ({cmd['count']}次, 平均{cmd['avg_time']:.1f}s)\n"

        return report

    def export_report(self, filepath: str, days: int = 7):
        """导出报告到文件"""
        report = self.generate_report(days)
        Path(filepath).write_text(report, encoding='utf-8')
        print(f"[PerformanceMonitor] 报告已导出: {filepath}")

    # ========================================================================
    # 实时监控
    # ========================================================================

    def get_current_metrics(self) -> Dict:
        """获取当前指标"""
        return {
            "active_executions": len(self.active_executions),
            "system": {
                "cpu": psutil.cpu_percent(interval=0.5),
                "memory": psutil.virtual_memory().percent,
            } if self._monitoring else None
        }

    def print_summary(self, days: int = 1):
        """打印摘要"""
        stats = self.get_execution_stats(days)
        print(f"\n[PerformanceMonitor] 过去{days}天摘要:")
        print(f"  执行: {stats['total_executions']}次 (成功率 {stats['success_rate']*100:.1f}%)")
        print(f"  平均耗时: {stats['avg_duration']:.2f}s")


# 便捷函数
def get_performance_monitor(data_dir: str = "./data/metrics") -> PerformanceMonitor:
    """获取性能监控单例"""
    if not hasattr(get_performance_monitor, "_instance"):
        get_performance_monitor._instance = PerformanceMonitor(data_dir)
    return get_performance_monitor._instance


# 装饰器
def track_performance(mode: str = "auto"):
    """性能追踪装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            pm = get_performance_monitor()
            task_id = f"task_{int(time.time() * 1000)}"
            instruction = func.__name__

            pm.start_execution(task_id, instruction, mode)
            try:
                result = func(*args, **kwargs)
                pm.end_execution(task_id, success=True)
                return result
            except Exception as e:
                pm.end_execution(task_id, success=False, error_type=type(e).__name__)
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # 测试
    pm = PerformanceMonitor()

    # 模拟执行
    for i in range(5):
        task_id = f"test_{i}"
        pm.start_execution(task_id, f"测试指令 {i}", "auto")
        time.sleep(0.1)
        pm.end_execution(task_id, success=i % 2 == 0, steps_count=3)

    # 生成报告
    report = pm.generate_report(days=1)
    print(report)
