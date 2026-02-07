#!/usr/bin/env python3
"""
LearningSystem 📚 - 自主学习系统

从用户行为和反馈中学习，持续改进自动化效果。

核心功能：
1. 从演示学习 (Learning from Demonstration) - 录制用户操作
2. 从反馈学习 (Learning from Feedback) - 根据用户评分改进
3. 工作流推荐 (Workflow Recommendation) - 基于上下文推荐
4. 参数优化 (Parameter Optimization) - 自动调整执行参数

Author: GodHand Team
Version: 1.0.0
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict
import hashlib
import difflib


@dataclass
class Demonstration:
    """用户演示记录"""
    id: str
    task_description: str          # 任务描述
    actions: List[Dict]            # 动作序列
    context: Dict[str, Any]        # 执行上下文
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success_count: int = 0         # 成功执行次数
    fail_count: int = 0            # 失败次数
    user_rating: Optional[float] = None  # 用户评分 1-5
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "actions": self.actions,
            "context": self.context,
            "timestamp": self.timestamp,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "user_rating": self.user_rating,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Demonstration":
        return cls(**data)


@dataclass
class FeedbackRecord:
    """反馈记录"""
    id: str
    task_id: str
    instruction: str
    result: Dict[str, Any]
    rating: float                  # 1-5 评分
    comments: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearnedPattern:
    """学习到的模式"""
    pattern_id: str
    pattern_type: str              # "element", "sequence", "timing"
    description: str
    data: Dict[str, Any]
    confidence: float              # 0-1
    occurrence_count: int = 1
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "data": self.data,
            "confidence": self.confidence,
            "occurrence_count": self.occurrence_count,
            "last_used": self.last_used
        }


class LearningSystem:
    """
    自主学习系统

    世界第一的自适应学习能力
    """

    def __init__(self, data_dir: str = "./data/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据存储
        self.demonstrations: Dict[str, Demonstration] = {}
        self.feedback_records: List[FeedbackRecord] = []
        self.patterns: Dict[str, LearnedPattern] = {}

        # 用户习惯统计
        self.user_preferences: Dict[str, Any] = defaultdict(lambda: defaultdict(int))
        self.command_frequency: Dict[str, int] = defaultdict(int)
        self.app_usage_stats: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "last_used": None})

        # 加载历史数据
        self._load_data()

        print(f"[LearningSystem] 初始化完成，已加载 {len(self.demonstrations)} 个演示记录")

    def _load_data(self):
        """加载学习数据"""
        # 加载演示记录
        demo_file = self.data_dir / "demonstrations.json"
        if demo_file.exists():
            try:
                with open(demo_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.demonstrations = {
                        k: Demonstration.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"[Warn] 加载演示记录失败: {e}")

        # 加载学习到的模式
        patterns_file = self.data_dir / "patterns.json"
        if patterns_file.exists():
            try:
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = {
                        k: LearnedPattern(**v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"[Warn] 加载模式失败: {e}")

        # 加载用户偏好
        prefs_file = self.data_dir / "user_preferences.json"
        if prefs_file.exists():
            try:
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_preferences = defaultdict(lambda: defaultdict(int), data.get("preferences", {}))
                    self.command_frequency = defaultdict(int, data.get("command_frequency", {}))
                    self.app_usage_stats = defaultdict(
                        lambda: {"count": 0, "last_used": None},
                        data.get("app_usage", {})
                    )
            except Exception as e:
                print(f"[Warn] 加载用户偏好失败: {e}")

    def _save_data(self):
        """保存学习数据"""
        # 保存演示记录
        demo_file = self.data_dir / "demonstrations.json"
        with open(demo_file, 'w', encoding='utf-8') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.demonstrations.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

        # 保存学习到的模式
        patterns_file = self.data_dir / "patterns.json"
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.patterns.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

        # 保存用户偏好
        prefs_file = self.data_dir / "user_preferences.json"
        with open(prefs_file, 'w', encoding='utf-8') as f:
            json.dump({
                "preferences": dict(self.user_preferences),
                "command_frequency": dict(self.command_frequency),
                "app_usage": dict(self.app_usage_stats)
            }, f, ensure_ascii=False, indent=2)

    # =========================================================================
    # 从演示学习
    # =========================================================================

    def start_recording(self, task_description: str, context: Dict = None) -> str:
        """
        开始录制用户操作

        Returns:
            recording_id: 录制会话ID
        """
        recording_id = f"rec_{int(time.time() * 1000)}"

        # 创建新的演示记录
        demo = Demonstration(
            id=recording_id,
            task_description=task_description,
            actions=[],
            context=context or {}
        )

        self._current_recording = demo
        print(f"[Learning] 开始录制: {task_description} (ID: {recording_id})")

        return recording_id

    def record_action(self, action: Dict):
        """记录一个动作"""
        if hasattr(self, '_current_recording') and self._current_recording:
            self._current_recording.actions.append({
                **action,
                "timestamp": datetime.now().isoformat()
            })

    def stop_recording(self, user_rating: float = None) -> Demonstration:
        """停止录制并保存"""
        if not hasattr(self, '_current_recording') or not self._current_recording:
            raise ValueError("没有正在进行的录制")

        demo = self._current_recording
        demo.user_rating = user_rating

        # 保存
        self.demonstrations[demo.id] = demo
        self._save_data()

        # 提取模式
        self._extract_patterns_from_demo(demo)

        # 更新用户偏好
        self._update_preferences_from_demo(demo)

        print(f"[Learning] 录制完成: {demo.task_description} ({len(demo.actions)} 个动作)")

        self._current_recording = None
        return demo

    def _extract_patterns_from_demo(self, demo: Demonstration):
        """从演示中提取通用模式"""
        # 提取应用打开模式
        for action in demo.actions:
            if action.get("type") == "open_app":
                app_name = action.get("params", {}).get("app_name", "")
                if app_name:
                    self._record_app_usage(app_name)

        # 提取常见动作序列模式
        if len(demo.actions) >= 2:
            sequence_key = " -> ".join([a.get("type", "unknown") for a in demo.actions[:3]])
            self._add_pattern(
                pattern_type="sequence",
                description=f"常见动作序列: {sequence_key}",
                data={"sequence": [a.get("type") for a in demo.actions[:3]]},
                confidence=0.7
            )

    def _update_preferences_from_demo(self, demo: Demonstration):
        """从演示更新用户偏好"""
        # 记录命令使用频率
        self.command_frequency[demo.task_description] += 1

        # 记录应用使用
        for action in demo.actions:
            if action.get("type") == "open_app":
                app = action.get("params", {}).get("app_name", "")
                self.app_usage_stats[app]["count"] += 1
                self.app_usage_stats[app]["last_used"] = datetime.now().isoformat()

    # =========================================================================
    # 从反馈学习
    # =========================================================================

    def record_feedback(self, task_id: str, instruction: str, result: Dict, rating: float, comments: str = None):
        """
        记录用户反馈

        Args:
            task_id: 任务ID
            instruction: 原始指令
            result: 执行结果
            rating: 1-5 评分
            comments: 用户评论
        """
        feedback = FeedbackRecord(
            id=f"fb_{int(time.time() * 1000)}",
            task_id=task_id,
            instruction=instruction,
            result=result,
            rating=rating,
            comments=comments
        )

        self.feedback_records.append(feedback)

        # 根据反馈调整
        if rating < 3:
            # 低分，记录失败模式
            self._learn_from_failure(feedback)
        elif rating >= 4:
            # 高分，强化成功模式
            self._learn_from_success(feedback)

        self._save_data()
        print(f"[Learning] 记录反馈: {instruction} -> {rating}/5")

    def _learn_from_failure(self, feedback: FeedbackRecord):
        """从失败中学习"""
        error = feedback.result.get("error", "")
        if error:
            # 记录错误模式
            self._add_pattern(
                pattern_type="failure",
                description=f"常见失败: {error[:50]}",
                data={"error": error, "instruction": feedback.instruction},
                confidence=0.5
            )

    def _learn_from_success(self, feedback: FeedbackRecord):
        """从成功中学习"""
        # 找到对应的演示并增加成功计数
        for demo in self.demonstrations.values():
            if self._is_similar_instruction(demo.task_description, feedback.instruction):
                demo.success_count += 1
                break

    # =========================================================================
    # 工作流推荐
    # =========================================================================

    def suggest_workflows(self, context: Dict = None) -> List[Dict]:
        """
        根据上下文推荐工作流

        Returns:
            推荐的工作流列表，按相关性排序
        """
        suggestions = []

        # 基于频率推荐
        frequent_commands = sorted(
            self.command_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        for cmd, freq in frequent_commands:
            suggestions.append({
                "type": "frequent",
                "description": cmd,
                "confidence": min(freq / 10, 1.0),
                "reason": f"已使用 {freq} 次"
            })

        # 基于时间推荐（例如每天早上打开邮件）
        hour = datetime.now().hour
        if 9 <= hour <= 10:
            # 早上推荐常用工作流
            morning_apps = ["邮件", "日历", "Teams"]
            for app in morning_apps:
                if self.app_usage_stats[app]["count"] > 0:
                    suggestions.append({
                        "type": "time_based",
                        "description": f"打开{app}",
                        "confidence": 0.6,
                        "reason": "早上常用"
                    })

        # 基于当前应用推荐
        current_app = context.get("current_app") if context else None
        if current_app:
            # 找到在这个应用之后常用的操作
            related = self._find_related_workflows(current_app)
            suggestions.extend(related)

        # 去重并排序
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s["description"] not in seen:
                seen.add(s["description"])
                unique_suggestions.append(s)

        return sorted(unique_suggestions, key=lambda x: x["confidence"], reverse=True)[:8]

    def find_similar_demonstration(self, instruction: str) -> Optional[Demonstration]:
        """
        查找相似的演示记录

        Args:
            instruction: 用户指令

        Returns:
            最相似的演示记录，如果没有则返回 None
        """
        best_match = None
        best_score = 0.0

        for demo in self.demonstrations.values():
            # 计算相似度
            score = self._calculate_similarity(demo.task_description, instruction)

            # 考虑评分权重
            if demo.user_rating:
                score *= (demo.user_rating / 5)

            if score > best_score and score > 0.6:  # 阈值
                best_score = score
                best_match = demo

        return best_match

    def adapt_demonstration(self, demo: Demonstration, new_context: Dict) -> List[Dict]:
        """
        根据新上下文调整演示的动作

        Args:
            demo: 原始演示记录
            new_context: 新的上下文

        Returns:
            调整后的动作列表
        """
        adapted_actions = []

        for action in demo.actions:
            adapted_action = dict(action)

            # 根据上下文调整参数
            if action.get("type") == "type_text":
                old_text = action.get("params", {}).get("text", "")
                # 如果有模板变量，替换
                if "{{" in old_text:
                    for key, value in new_context.get("variables", {}).items():
                        old_text = old_text.replace(f"{{{{{key}}}}}", str(value))
                    adapted_action["params"]["text"] = old_text

            adapted_actions.append(adapted_action)

        return adapted_actions

    # =========================================================================
    # 参数优化
    # =========================================================================

    def optimize_parameters(self, action_type: str, current_params: Dict) -> Dict:
        """
        根据历史数据优化执行参数

        Args:
            action_type: 动作类型
            current_params: 当前参数

        Returns:
            优化后的参数
        """
        optimized = dict(current_params)

        # 根据历史成功率调整等待时间
        if action_type == "wait":
            # 如果应用启动经常超时，增加等待时间
            avg_success_time = self._get_average_success_time("open_app")
            if avg_success_time:
                optimized["seconds"] = max(current_params.get("seconds", 1), avg_success_time * 1.2)

        return optimized

    def _get_average_success_time(self, action_type: str) -> Optional[float]:
        """获取某类动作的平均成功执行时间"""
        times = []
        for demo in self.demonstrations.values():
            if demo.success_count > 0:
                for action in demo.actions:
                    if action.get("type") == action_type:
                        # 这里简化处理，实际应该记录执行时间
                        times.append(1.0)

        return sum(times) / len(times) if times else None

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _record_app_usage(self, app_name: str):
        """记录应用使用"""
        self.app_usage_stats[app_name]["count"] += 1
        self.app_usage_stats[app_name]["last_used"] = datetime.now().isoformat()

    def _add_pattern(self, pattern_type: str, description: str, data: Dict, confidence: float):
        """添加学习到的模式"""
        pattern_id = hashlib.md5(f"{pattern_type}:{description}".encode()).hexdigest()[:12]

        if pattern_id in self.patterns:
            # 更新现有模式
            self.patterns[pattern_id].occurrence_count += 1
            self.patterns[pattern_id].confidence = min(
                self.patterns[pattern_id].confidence + 0.1,
                1.0
            )
        else:
            # 创建新模式
            self.patterns[pattern_id] = LearnedPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                data=data,
                confidence=confidence
            )

    def _is_similar_instruction(self, desc1: str, desc2: str) -> bool:
        """判断两个指令是否相似"""
        return self._calculate_similarity(desc1, desc2) > 0.8

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的相似度"""
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def _find_related_workflows(self, app_name: str) -> List[Dict]:
        """找到与某个应用相关的工作流"""
        related = []

        for demo in self.demonstrations.values():
            for action in demo.actions:
                if action.get("type") == "open_app":
                    action_app = action.get("params", {}).get("app_name", "")
                    if self._is_similar_instruction(action_app, app_name):
                        related.append({
                            "type": "related",
                            "description": demo.task_description,
                            "confidence": 0.5,
                            "reason": f"与 {app_name} 相关"
                        })
                        break

        return related

    # =========================================================================
    # 统计和报告
    # =========================================================================

    def get_learning_stats(self) -> Dict:
        """获取学习统计信息"""
        return {
            "demonstrations": {
                "total": len(self.demonstrations),
                "high_rated": sum(1 for d in self.demonstrations.values() if d.user_rating and d.user_rating >= 4)
            },
            "patterns": {
                "total": len(self.patterns),
                "by_type": defaultdict(int, {
                    k: sum(1 for p in self.patterns.values() if p.pattern_type == k)
                    for k in set(p.pattern_type for p in self.patterns.values())
                })
            },
            "frequent_commands": sorted(
                self.command_frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "most_used_apps": sorted(
                [(app, stats["count"]) for app, stats in self.app_usage_stats.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def reset_learning(self):
        """重置所有学习数据（谨慎使用）"""
        self.demonstrations.clear()
        self.patterns.clear()
        self.user_preferences.clear()
        self.command_frequency.clear()
        self.app_usage_stats.clear()
        self._save_data()
        print("[LearningSystem] 学习数据已重置")


# 便捷函数
def get_learning_system(data_dir: str = "./data/learning") -> LearningSystem:
    """获取学习系统单例"""
    if not hasattr(get_learning_system, "_instance"):
        get_learning_system._instance = LearningSystem(data_dir)
    return get_learning_system._instance


if __name__ == "__main__":
    # 测试
    ls = LearningSystem()

    # 模拟录制
    rec_id = ls.start_recording("打开记事本并输入内容")
    ls.record_action({"type": "open_app", "params": {"app_name": "记事本"}})
    ls.record_action({"type": "wait", "params": {"seconds": 1}})
    ls.record_action({"type": "type_text", "params": {"text": "Hello World"}})
    demo = ls.stop_recording(user_rating=5)

    print(f"\n录制完成: {demo.id}")
    print(f"动作数: {len(demo.actions)}")

    # 测试推荐
    suggestions = ls.suggest_workflows()
    print(f"\n推荐工作流:")
    for s in suggestions:
        print(f"  - {s['description']} ({s['reason']})")

    # 统计
    stats = ls.get_learning_stats()
    print(f"\n学习统计: {stats}")
