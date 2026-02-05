#!/usr/bin/env python3
"""
GodHand Monitor - 性能监控与日志分析系统

功能:
- 执行时间追踪
- 成功率统计
- 错误分析
- 性能报告生成
- 实时监控Dashboard
"""

import json
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Any
from collections import deque, defaultdict
import statistics


@dataclass
class ExecutionRecord:
    """执行记录"""
    id: str
    timestamp: str
    command: str
    intent_category: str
    execution_mode: str
    success: bool
    execution_time: float
    action_count: int
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class PerformanceMetrics:
    """性能指标"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    p95_execution_time: float
    category_stats: Dict[str, Dict]
    hourly_stats: Dict[str, Dict]


class MetricsStore:
    """指标存储 - 使用SQLite持久化"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path(__file__).parent.parent / "data" / "metrics.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    command TEXT NOT NULL,
                    intent_category TEXT,
                    execution_mode TEXT,
                    success INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    action_count INTEGER,
                    error_message TEXT,
                    screenshot_path TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON executions(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category 
                ON executions(intent_category)
            """)
            
            conn.commit()
    
    def record(self, record: ExecutionRecord):
        """记录执行"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO executions 
                   (id, timestamp, command, intent_category, execution_mode,
                    success, execution_time, action_count, error_message, 
                    screenshot_path, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.timestamp,
                    record.command,
                    record.intent_category,
                    record.execution_mode,
                    1 if record.success else 0,
                    record.execution_time,
                    record.action_count,
                    record.error_message,
                    record.screenshot_path,
                    json.dumps(record.metadata) if record.metadata else None
                )
            )
            conn.commit()
    
    def get_metrics(self, hours: int = 24) -> PerformanceMetrics:
        """获取性能指标"""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 基础统计
            cursor = conn.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                    AVG(execution_time) as avg_time,
                    MIN(execution_time) as min_time,
                    MAX(execution_time) as max_time
                   FROM executions 
                   WHERE timestamp > ?""",
                (since,)
            )
            row = cursor.fetchone()
            
            total = row[0] or 0
            successful = row[1] or 0
            
            # 计算p95
            cursor = conn.execute(
                """SELECT execution_time FROM executions 
                   WHERE timestamp > ? ORDER BY execution_time 
                   LIMIT 1 OFFSET ?""",
                (since, int(total * 0.95))
            )
            p95_row = cursor.fetchone()
            p95 = p95_row[0] if p95_row else 0
            
            # 分类统计
            category_stats = defaultdict(lambda: {'count': 0, 'success': 0})
            cursor = conn.execute(
                """SELECT intent_category, success, COUNT(*)
                   FROM executions WHERE timestamp > ?
                   GROUP BY intent_category, success""",
                (since,)
            )
            for category, success, count in cursor:
                if category:
                    category_stats[category]['count'] += count
                    if success:
                        category_stats[category]['success'] += count
            
            # 小时统计
            hourly_stats = defaultdict(lambda: {'count': 0, 'success': 0})
            cursor = conn.execute(
                """SELECT strftime('%H', timestamp) as hour, success, COUNT(*)
                   FROM executions WHERE timestamp > ?
                   GROUP BY hour, success""",
                (since,)
            )
            for hour, success, count in cursor:
                hourly_stats[hour]['count'] += count
                if success:
                    hourly_stats[hour]['success'] += count
            
            return PerformanceMetrics(
                total_executions=total,
                successful_executions=successful,
                failed_executions=total - successful,
                success_rate=successful / total if total > 0 else 0,
                avg_execution_time=row[2] or 0,
                min_execution_time=row[3] or 0,
                max_execution_time=row[4] or 0,
                p95_execution_time=p95,
                category_stats=dict(category_stats),
                hourly_stats=dict(hourly_stats)
            )
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近的错误"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT timestamp, command, error_message, execution_mode
                   FROM executions 
                   WHERE success = 0 AND error_message IS NOT NULL
                   ORDER BY timestamp DESC
                   LIMIT ?""",
                (limit,)
            )
            return [
                {
                    'timestamp': row[0],
                    'command': row[1],
                    'error': row[2],
                    'mode': row[3]
                }
                for row in cursor.fetchall()
            ]
    
    def get_top_commands(self, limit: int = 10) -> List[Dict]:
        """获取常用命令"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT command, COUNT(*) as count,
                   AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                   FROM executions 
                   GROUP BY command
                   ORDER BY count DESC
                   LIMIT ?""",
                (limit,)
            )
            return [
                {
                    'command': row[0],
                    'count': row[1],
                    'success_rate': row[2]
                }
                for row in cursor.fetchall()
            ]


class RealtimeMonitor:
    """实时监控器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.execution_times: deque = deque(maxlen=window_size)
        self.success_count = 0
        self.failure_count = 0
        self.current_tasks: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
    
    def start_task(self, task_id: str, command: str):
        """开始任务"""
        with self._lock:
            self.current_tasks[task_id] = {
                'command': command,
                'start_time': time.time(),
                'status': 'running'
            }
        self._notify('task_start', {'id': task_id, 'command': command})
    
    def end_task(self, task_id: str, success: bool, execution_time: float):
        """结束任务"""
        with self._lock:
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
            
            self.execution_times.append(execution_time)
            if success:
                self.success_count += 1
            else:
                self.failure_count += 1
        
        self._notify('task_end', {
            'id': task_id,
            'success': success,
            'execution_time': execution_time
        })
    
    def get_realtime_stats(self) -> Dict:
        """获取实时统计"""
        with self._lock:
            times = list(self.execution_times)
            
            return {
                'current_tasks': len(self.current_tasks),
                'tasks': [
                    {'id': tid, 'command': t['command'], 'elapsed': time.time() - t['start_time']}
                    for tid, t in self.current_tasks.items()
                ],
                'recent_avg_time': statistics.mean(times) if times else 0,
                'recent_success_rate': self.success_count / (self.success_count + self.failure_count)
                    if (self.success_count + self.failure_count) > 0 else 1.0,
                'total_recent': len(times)
            }
    
    def on_update(self, callback: Callable):
        """注册更新回调"""
        self._callbacks.append(callback)
    
    def _notify(self, event: str, data: Dict):
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(event, data)
            except Exception as e:
                print(f"Callback error: {e}")


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, store: MetricsStore):
        self.store = store
    
    def generate_report(self, days: int = 7) -> Dict:
        """生成性能报告"""
        metrics = self.store.get_metrics(hours=days * 24)
        errors = self.store.get_recent_errors(limit=20)
        top_commands = self.store.get_top_commands(limit=10)
        
        # 分析错误模式
        error_patterns = self._analyze_errors(errors)
        
        # 分析性能趋势
        trends = self._analyze_trends(metrics)
        
        return {
            'period': f'{days} days',
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_executions': metrics.total_executions,
                'success_rate': f'{metrics.success_rate:.1%}',
                'avg_execution_time': f'{metrics.avg_execution_time:.2f}s',
                'p95_execution_time': f'{metrics.p95_execution_time:.2f}s'
            },
            'category_breakdown': metrics.category_stats,
            'hourly_distribution': metrics.hourly_stats,
            'top_commands': top_commands,
            'error_analysis': error_patterns,
            'trends': trends,
            'recommendations': self._generate_recommendations(metrics, error_patterns)
        }
    
    def _analyze_errors(self, errors: List[Dict]) -> Dict:
        """分析错误模式"""
        patterns = defaultdict(int)
        mode_errors = defaultdict(int)
        
        for error in errors:
            # 提取错误类型
            msg = error.get('error', '')
            if 'not found' in msg.lower() or '找不到' in msg:
                patterns['NOT_FOUND'] += 1
            elif 'timeout' in msg.lower() or '超时' in msg:
                patterns['TIMEOUT'] += 1
            elif 'permission' in msg.lower() or '权限' in msg:
                patterns['PERMISSION_DENIED'] += 1
            elif 'parse' in msg.lower() or '解析' in msg:
                patterns['PARSE_ERROR'] += 1
            else:
                patterns['OTHER'] += 1
            
            mode_errors[error.get('mode', 'unknown')] += 1
        
        return {
            'type_distribution': dict(patterns),
            'mode_distribution': dict(mode_errors),
            'total_errors': len(errors)
        }
    
    def _analyze_trends(self, metrics: PerformanceMetrics) -> Dict:
        """分析趋势"""
        hourly_success_rates = {
            hour: stats['success'] / stats['count'] if stats['count'] > 0 else 0
            for hour, stats in metrics.hourly_stats.items()
        }
        
        # 找出高峰时段
        peak_hours = sorted(
            metrics.hourly_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:3]
        
        return {
            'peak_hours': [h[0] for h in peak_hours],
            'best_performance_hours': sorted(
                hourly_success_rates.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            'avg_actions_per_execution': 0  # 需要从记录计算
        }
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, 
                                   error_patterns: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if metrics.success_rate < 0.8:
            recommendations.append(
                f"成功率较低 ({metrics.success_rate:.1%})，建议检查错误日志并优化解析规则"
            )
        
        if metrics.avg_execution_time > 5:
            recommendations.append(
                f"平均执行时间较长 ({metrics.avg_execution_time:.1f}s)，建议优化执行流程"
            )
        
        if error_patterns['type_distribution'].get('PARSE_ERROR', 0) > 5:
            recommendations.append(
                "解析错误较多，建议扩充意图识别规则或使用更强大的LLM模型"
            )
        
        if error_patterns['type_distribution'].get('TIMEOUT', 0) > 3:
            recommendations.append(
                "超时错误频繁，建议增加超时处理或优化等待逻辑"
            )
        
        if not recommendations:
            recommendations.append("系统运行良好，暂无特别建议")
        
        return recommendations


class GodHandMonitor:
    """GodHand 监控主类"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.store = MetricsStore(self.data_dir / "metrics.db")
        self.realtime = RealtimeMonitor()
        self.analyzer = PerformanceAnalyzer(self.store)
        
        # 启动监控线程
        self._running = False
        self._monitor_thread = None
    
    def record_execution(self, command: str, intent_category: str,
                        execution_mode: str, success: bool,
                        execution_time: float, action_count: int = 0,
                        error_message: str = None, metadata: Dict = None):
        """记录执行"""
        record = ExecutionRecord(
            id=f"exec_{int(time.time() * 1000)}",
            timestamp=datetime.now().isoformat(),
            command=command,
            intent_category=intent_category,
            execution_mode=execution_mode,
            success=success,
            execution_time=execution_time,
            action_count=action_count,
            error_message=error_message,
            metadata=metadata
        )
        
        self.store.record(record)
    
    def get_dashboard_data(self) -> Dict:
        """获取Dashboard数据"""
        return {
            'realtime': self.realtime.get_realtime_stats(),
            'metrics': asdict(self.store.get_metrics(hours=24)),
            'recent_errors': self.store.get_recent_errors(limit=5),
            'top_commands': self.store.get_top_commands(limit=5)
        }
    
    def generate_report(self, days: int = 7) -> Dict:
        """生成报告"""
        return self.analyzer.generate_report(days)
    
    def print_summary(self):
        """打印摘要"""
        metrics = self.store.get_metrics(hours=24)
        
        print("\n" + "=" * 60)
        print("📊 GodHand Monitor - 24小时摘要")
        print("=" * 60)
        print(f"总执行次数: {metrics.total_executions}")
        print(f"成功率: {metrics.success_rate:.1%}")
        print(f"平均执行时间: {metrics.avg_execution_time:.2f}s")
        print(f"P95执行时间: {metrics.p95_execution_time:.2f}s")
        
        if metrics.category_stats:
            print("\n分类统计:")
            for category, stats in metrics.category_stats.items():
                rate = stats['success'] / stats['count'] if stats['count'] > 0 else 0
                print(f"  {category}: {stats['count']}次 (成功率: {rate:.1%})")
        
        print("=" * 60)


# 便捷函数
def get_monitor() -> GodHandMonitor:
    """获取监控器实例"""
    return GodHandMonitor()


if __name__ == "__main__":
    # 测试
    monitor = get_monitor()
    
    # 模拟一些数据
    for i in range(10):
        monitor.record_execution(
            command=f"测试命令 {i}",
            intent_category="app_launch" if i % 2 == 0 else "gui_auto",
            execution_mode="auto",
            success=i % 3 != 0,
            execution_time=1.5 + i * 0.1,
            action_count=2
        )
    
    monitor.print_summary()
    
    # 生成报告
    report = monitor.generate_report(days=1)
    print("\n报告摘要:")
    print(json.dumps(report['summary'], indent=2, ensure_ascii=False))
