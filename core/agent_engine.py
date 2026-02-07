#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Agent Engine - AI智能决策引擎
实现类似Clawdbot的智能任务规划、推理和执行
"""

import json
import os
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class TaskPlan:
    """任务计划"""
    task_id: str
    description: str
    steps: List[Dict]
    estimated_time: int  # 估计执行时间(秒)
    dependencies: List[str]
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = ""
    completed_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Memory:
    """记忆单元"""
    memory_id: str
    content: str
    memory_type: str  # fact, preference, task_history, error
    importance: float  # 0-1
    created_at: str
    last_accessed: str
    access_count: int = 0


class MemorySystem:
    """持久化记忆系统 - 类似Clawdbot的记忆功能"""

    def __init__(self, memory_file="memory.json"):
        self.memory_file = memory_file
        self.memories: List[Memory] = []
        self.short_term: List[str] = []  # 短期记忆（当前会话）
        self.load()

    def load(self):
        """加载记忆"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = [Memory(**m) for m in data]
            except Exception as e:
                print(f"[Memory] 加载失败: {e}")

    def save(self):
        """保存记忆"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(m) for m in self.memories], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Memory] 保存失败: {e}")

    def add(self, content: str, memory_type: str = "fact", importance: float = 0.5):
        """添加记忆"""
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.memories)}"
        now = datetime.now().isoformat()

        memory = Memory(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            created_at=now,
            last_accessed=now
        )
        self.memories.append(memory)
        self.save()
        return memory_id

    def search(self, query: str, limit: int = 5) -> List[Memory]:
        """搜索相关记忆"""
        # 简单的关键词匹配
        query_lower = query.lower()
        matches = []

        for memory in self.memories:
            if query_lower in memory.content.lower():
                memory.access_count += 1
                memory.last_accessed = datetime.now().isoformat()
                matches.append(memory)

        # 按重要性和访问次数排序
        matches.sort(key=lambda m: (m.importance * 0.7 + m.access_count * 0.3), reverse=True)
        return matches[:limit]

    def get_context(self, query: str) -> str:
        """获取相关记忆上下文"""
        memories = self.search(query)
        if not memories:
            return ""

        context_parts = [f"- {m.content}" for m in memories]
        return "\n".join(context_parts)

    def add_short_term(self, content: str):
        """添加到短期记忆"""
        self.short_term.append(content)
        if len(self.short_term) > 10:  # 保持最近10条
            self.short_term.pop(0)

    def get_conversation_context(self) -> str:
        """获取对话上下文"""
        return "\n".join(self.short_term)


class TaskPlanner:
    """任务规划器 - 将自然语言转换为执行计划"""

    def __init__(self, memory_system: MemorySystem = None):
        self.memory = memory_system or MemorySystem()
        self.plans: List[TaskPlan] = []

    def analyze_intent(self, user_input: str) -> Dict:
        """分析用户意图"""
        intent = {
            'action': 'unknown',
            'target': None,
            'parameters': {},
            'complexity': 'simple'
        }

        # 分析复杂度
        steps_count = len(re.findall(r'(然后|接着|再|之后)', user_input))
        if steps_count > 3:
            intent['complexity'] = 'complex'
        elif steps_count > 0:
            intent['complexity'] = 'medium'

        # 识别主要动作
        action_patterns = [
            (r'(打开|启动|运行)', 'open_app'),
            (r'(关闭|退出)', 'close_app'),
            (r'(点击|按|输入)', 'interact'),
            (r'(搜索|查找)', 'search'),
            (r'(创建|新建)', 'create'),
            (r'(删除|移除)', 'delete'),
            (r'(截图|拍照)', 'screenshot'),
            (r'(等待|延时|暂停)', 'wait'),
        ]

        for pattern, action in action_patterns:
            if re.search(pattern, user_input):
                intent['action'] = action
                break

        # 提取目标
        target_match = re.search(r'(?:打开|启动|运行|关闭)\s*(\S+)', user_input)
        if target_match:
            intent['target'] = target_match.group(1)

        return intent

    def create_plan(self, user_input: str) -> TaskPlan:
        """创建任务计划"""
        intent = self.analyze_intent(user_input)

        # 生成计划ID
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 解析步骤
        steps = self._parse_steps(user_input)

        # 估计时间
        estimated_time = self._estimate_time(steps)

        # 创建计划
        plan = TaskPlan(
            task_id=plan_id,
            description=user_input,
            steps=steps,
            estimated_time=estimated_time,
            dependencies=[]
        )

        # 保存到记忆
        self.memory.add(f"创建了任务计划: {user_input}", "task_history", importance=0.6)

        return plan

    def _parse_steps(self, user_input: str) -> List[Dict]:
        """解析执行步骤"""
        steps = []

        # 分割复合指令
        parts = re.split(r'(?:然后|接着|再|之后)', user_input)

        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue

            step = {
                'step_id': i + 1,
                'action': self._identify_action(part),
                'params': self._extract_params(part),
                'description': part,
                'can_fail': False,
                'retry': 3
            }
            steps.append(step)

        return steps

    def _identify_action(self, text: str) -> str:
        """识别动作类型"""
        patterns = {
            'open_app': r'(打开|启动|运行)\s*(.+)',
            'close_app': r'(关闭|退出)\s*(.+)',
            'click': r'(点击|单击)',
            'type': r'(输入|打字)',
            'press_key': r'(按|按键)',
            'wait': r'(等待|延时|暂停)\s*(\d+)',
            'screenshot': r'(截图|拍照)',
            'search': r'(搜索|查找)',
        }

        for action, pattern in patterns.items():
            if re.search(pattern, text):
                return action

        return 'unknown'

    def _extract_params(self, text: str) -> Dict:
        """提取参数"""
        params = {}

        # 提取坐标
        coord_match = re.search(r'(\d+)\s*,\s*(\d+)', text)
        if coord_match:
            params['x'] = int(coord_match.group(1))
            params['y'] = int(coord_match.group(2))

        # 提取时间
        time_match = re.search(r'(\d+)\s*(?:秒|s)', text)
        if time_match:
            params['seconds'] = int(time_match.group(1))

        # 提取应用名
        app_match = re.search(r'(?:打开|关闭|启动)\s*(\S+)', text)
        if app_match:
            params['app'] = app_match.group(1)

        return params

    def _estimate_time(self, steps: List[Dict]) -> int:
        """估计执行时间"""
        total = 0
        for step in steps:
            if step['action'] == 'wait':
                total += step['params'].get('seconds', 1)
            elif step['action'] == 'open_app':
                total += 3  # 打开应用默认等待3秒
            else:
                total += 1  # 其他操作默认1秒
        return total


class AgentEngine:
    """智能代理引擎 - 核心AI控制器"""

    def __init__(self):
        self.memory = MemorySystem()
        self.planner = TaskPlanner(self.memory)
        self.current_plan: Optional[TaskPlan] = None
        self.execution_history: List[Dict] = []

    def process(self, user_input: str) -> Dict:
        """处理用户输入 - 主入口"""
        # 添加上下文记忆
        self.memory.add_short_term(user_input)

        # 检索相关记忆
        context = self.memory.get_context(user_input)
        conversation = self.memory.get_conversation_context()

        # 分析意图
        intent = self.planner.analyze_intent(user_input)

        # 创建执行计划
        plan = self.planner.create_plan(user_input)
        self.current_plan = plan

        return {
            'intent': intent,
            'plan': plan,
            'context': context,
            'conversation': conversation,
            'estimated_time': plan.estimated_time
        }

    def learn_from_result(self, plan: TaskPlan, results: List[Dict]):
        """从执行结果中学习"""
        success_count = sum(1 for r in results if r.get('success'))
        total = len(results)

        # 记录成功/失败模式
        if success_count == total:
            self.memory.add(
                f"任务成功: {plan.description}",
                "task_history",
                importance=0.5
            )
        else:
            self.memory.add(
                f"任务部分失败: {plan.description}, 成功率 {success_count}/{total}",
                "error",
                importance=0.7
            )

        # 更新计划状态
        plan.status = "completed" if success_count == total else "partial"
        plan.completed_at = datetime.now().isoformat()

        # 保存执行历史
        self.execution_history.append({
            'plan_id': plan.task_id,
            'success': success_count == total,
            'results': results
        })

    def get_suggestions(self, partial_input: str) -> List[str]:
        """获取命令建议"""
        suggestions = []

        # 基于历史记忆提供建议
        if '打开' in partial_input:
            recent_apps = [m.content for m in self.memory.search("打开")[:3]]
            suggestions.extend(recent_apps)

        # 常用命令模板
        templates = [
            "打开 {app} 然后输入{text}",
            "点击 {x}, {y} 然后等待 {秒}",
            "搜索 {关键词}",
            "循环 {次数}次 {动作}",
        ]

        return suggestions[:5]


# 便捷函数
def create_agent() -> AgentEngine:
    """创建智能代理实例"""
    return AgentEngine()


if __name__ == "__main__":
    # 测试
    agent = create_agent()

    test_inputs = [
        "打开记事本 然后输入Hello World",
        "打开计算器 然后输入1 然后按加号 然后输入1 然后按等于",
        "搜索 Python教程",
    ]

    for user_input in test_inputs:
        print(f"\n{'='*60}")
        print(f"[输入] {user_input}")
        result = agent.process(user_input)
        print(f"[意图] {result['intent']}")
        print(f"[计划] {result['plan'].task_id}, 估计时间: {result['plan'].estimated_time}s")
        print(f"[步骤]")
        for step in result['plan'].steps:
            print(f"  {step['step_id']}. {step['action']}: {step['description']}")
