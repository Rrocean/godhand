#!/usr/bin/env python3
"""
AIAgent 🤖 - 自主AI代理系统

具备自主决策、长期记忆、复杂任务规划的AI Agent。
能够理解用户意图，自主分解任务，执行并适应环境变化。

Author: GodHand Team
Version: 1.0.0
"""

import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import hashlib


class AgentState(Enum):
    """代理状态"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    WAITING = "waiting"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Memory:
    """记忆单元"""
    content: str
    memory_type: str  # "observation", "action", "reflection", "plan"
    timestamp: float
    importance: float = 1.0
    embedding: Optional[List[float]] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "content": self.content,
            "type": self.memory_type,
            "timestamp": self.timestamp,
            "importance": self.importance
        }


@dataclass
class Goal:
    """目标"""
    id: str
    description: str
    priority: TaskPriority
    subgoals: List["Goal"] = field(default_factory=list)
    status: str = "pending"  # pending, active, completed, failed
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    deadline: Optional[float] = None


class LongTermMemory:
    """
    长期记忆系统

    存储Agent的观察、行动和反思
    """

    def __init__(self, max_memories: int = 1000):
        self.memories: List[Memory] = []
        self.max_memories = max_memories
        self._memory_index: Dict[str, List[int]] = {}  # 类型索引

    def add(self, memory: Memory):
        """添加记忆"""
        self.memories.append(memory)

        # 更新索引
        if memory.memory_type not in self._memory_index:
            self._memory_index[memory.memory_type] = []
        self._memory_index[memory.memory_type].append(len(self.memories) - 1)

        # 遗忘旧记忆
        if len(self.memories) > self.max_memories:
            self._forget_least_important()

    def _forget_least_important(self):
        """遗忘最不重要的记忆"""
        if not self.memories:
            return

        # 找到重要性最低且不是反思的记忆
        min_importance = float('inf')
        min_idx = -1

        for i, mem in enumerate(self.memories):
            if mem.memory_type != "reflection" and mem.importance < min_importance:
                min_importance = mem.importance
                min_idx = i

        if min_idx >= 0:
            del self.memories[min_idx]
            self._rebuild_index()

    def _rebuild_index(self):
        """重建索引"""
        self._memory_index.clear()
        for i, mem in enumerate(self.memories):
            if mem.memory_type not in self._memory_index:
                self._memory_index[mem.memory_type] = []
            self._memory_index[mem.memory_type].append(i)

    def retrieve(self, query: str, k: int = 5) -> List[Memory]:
        """检索相关记忆"""
        # 简化的检索：基于关键词匹配
        # 实际应该使用向量相似度
        keywords = set(query.lower().split())

        scored_memories = []
        for mem in self.memories:
            score = 0
            mem_words = set(mem.content.lower().split())
            score += len(keywords & mem_words)
            score += mem.importance * 0.1
            score -= (time.time() - mem.timestamp) / 86400 * 0.01  # 时间衰减

            scored_memories.append((mem, score))

        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_memories[:k]]

    def get_recent(self, n: int = 10, memory_type: str = None) -> List[Memory]:
        """获取最近的记忆"""
        if memory_type:
            indices = self._memory_index.get(memory_type, [])
            memories = [self.memories[i] for i in indices]
        else:
            memories = self.memories

        return sorted(memories, key=lambda x: x.timestamp, reverse=True)[:n]

    def summarize(self) -> str:
        """总结记忆"""
        recent = self.get_recent(20)
        observations = [m.content for m in recent if m.memory_type == "observation"]
        actions = [m.content for m in recent if m.memory_type == "action"]

        summary = f"最近观察:\n" + "\n".join(f"- {o}" for o in observations[:5])
        summary += f"\n\n最近行动:\n" + "\n".join(f"- {a}" for a in actions[:5])

        return summary


class AIAgent:
    """
    AI Agent

    宇宙第一的自主AI代理
    """

    def __init__(self, name: str = "GodHand Agent", llm_client=None):
        self.name = name
        self.llm = llm_client
        self.state = AgentState.IDLE

        # 记忆系统
        self.memory = LongTermMemory()
        self.working_memory: Dict[str, Any] = {}  # 工作记忆

        # 目标管理
        self.goals: List[Goal] = []
        self.current_goal: Optional[Goal] = None

        # 执行历史
        self.action_history: List[Dict] = []

        # 技能注册
        self.skills: Dict[str, Callable] = {}

        # 反思计数
        self.action_count_since_reflection = 0
        self.reflection_interval = 5

        print(f"🤖 [AIAgent] {name} 初始化完成")

    def register_skill(self, name: str, func: Callable):
        """注册技能"""
        self.skills[name] = func
        print(f"✅ 技能已注册: {name}")

    def perceive(self, observation: str, importance: float = 1.0):
        """感知环境"""
        memory = Memory(
            content=observation,
            memory_type="observation",
            timestamp=time.time(),
            importance=importance
        )
        self.memory.add(memory)
        print(f"👁️  [感知] {observation[:100]}...")

    def set_goal(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Goal:
        """设置目标"""
        goal_id = hashlib.md5(f"{description}{time.time()}".encode()).hexdigest()[:8]

        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority
        )

        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority.value, reverse=True)

        # 记录到记忆
        self.memory.add(Memory(
            content=f"设定目标: {description}",
            memory_type="plan",
            timestamp=time.time(),
            importance=priority.value
        ))

        print(f"🎯 [目标] {description} (优先级: {priority.name})")
        return goal

    def plan(self, goal: Goal = None) -> List[Dict]:
        """制定计划"""
        self.state = AgentState.PLANNING

        target = goal or self.current_goal
        if not target:
            return []

        # 获取相关记忆
        relevant_memories = self.memory.retrieve(target.description, k=10)
        memory_context = "\n".join([m.content for m in relevant_memories])

        # 使用LLM制定计划（如果有）
        if self.llm:
            plan = self._plan_with_llm(target, memory_context)
        else:
            plan = self._plan_with_rules(target)

        # 记录计划
        self.memory.add(Memory(
            content=f"制定计划: {len(plan)} 个步骤",
            memory_type="plan",
            timestamp=time.time(),
            importance=target.priority.value
        ))

        self.state = AgentState.IDLE
        return plan

    def _plan_with_llm(self, goal: Goal, context: str) -> List[Dict]:
        """使用LLM制定计划"""
        # 这里应该调用LLM API
        # 简化实现
        return [
            {"step": 1, "action": "analyze", "description": f"分析目标: {goal.description}"},
            {"step": 2, "action": "execute", "description": "执行主要任务"},
            {"step": 3, "action": "verify", "description": "验证结果"}
        ]

    def _plan_with_rules(self, goal: Goal) -> List[Dict]:
        """使用规则制定计划"""
        description = goal.description.lower()

        if "打开" in description:
            app = description.replace("打开", "").strip()
            return [
                {"step": 1, "action": "open_app", "target": app},
                {"step": 2, "action": "wait", "duration": 2},
                {"step": 3, "action": "verify", "description": f"确认 {app} 已打开"}
            ]

        return [
            {"step": 1, "action": "analyze", "description": "分析任务"},
            {"step": 2, "action": "execute", "description": "执行任务"}
        ]

    def execute(self, action: Dict) -> Dict:
        """执行动作"""
        self.state = AgentState.EXECUTING

        action_type = action.get("action", "unknown")
        print(f"⚡ [执行] {action_type}: {action.get('description', '')}")

        result = {"success": False, "output": ""}

        # 执行技能
        if action_type in self.skills:
            try:
                skill_func = self.skills[action_type]
                result = skill_func(**{k: v for k, v in action.items() if k != "action"})
                result["success"] = True
            except Exception as e:
                result["error"] = str(e)
        else:
            result["output"] = f"未知动作: {action_type}"

        # 记录行动
        self.action_history.append({
            "action": action,
            "result": result,
            "timestamp": time.time()
        })

        self.memory.add(Memory(
            content=f"执行: {action_type} - 结果: {result.get('output', '')[:100]}",
            memory_type="action",
            timestamp=time.time(),
            importance=2.0 if result["success"] else 3.0
        ))

        self.action_count_since_reflection += 1

        # 触发反思
        if self.action_count_since_reflection >= self.reflection_interval:
            self.reflect()

        self.state = AgentState.IDLE
        return result

    def reflect(self):
        """反思"""
        self.state = AgentState.REFLECTING
        print("🤔 [反思] 分析最近的表现...")

        # 获取最近的行动
        recent_actions = self.action_history[-self.reflection_interval:]

        successes = sum(1 for a in recent_actions if a["result"].get("success"))
        failures = len(recent_actions) - successes

        reflection_content = f"最近 {len(recent_actions)} 个行动: "
        reflection_content += f"成功 {successes} 次, 失败 {failures} 次"

        if failures > 0:
            reflection_content += ". 需要改进策略。"
        else:
            reflection_content += ". 表现良好。"

        self.memory.add(Memory(
            content=reflection_content,
            memory_type="reflection",
            timestamp=time.time(),
            importance=2.5
        ))

        print(f"💭 {reflection_content}")

        self.action_count_since_reflection = 0
        self.state = AgentState.IDLE

    def run(self, instruction: str) -> Dict:
        """运行完整循环"""
        print(f"\n{'='*60}")
        print(f"🚀 [运行] {instruction}")
        print('='*60)

        # 1. 感知
        self.perceive(f"收到指令: {instruction}", importance=2.0)

        # 2. 设定目标
        goal = self.set_goal(instruction, TaskPriority.HIGH)
        self.current_goal = goal

        # 3. 制定计划
        plan = self.plan(goal)
        print(f"\n📋 计划: {len(plan)} 个步骤")

        # 4. 执行
        results = []
        for step in plan:
            result = self.execute(step)
            results.append(result)

            if not result.get("success"):
                print(f"❌ 步骤失败: {step}")
                # 可以尝试恢复或重规划

        # 5. 总结
        success_count = sum(1 for r in results if r.get("success"))
        print(f"\n✅ 完成: {success_count}/{len(results)} 个步骤成功")

        return {
            "goal": goal.description,
            "plan": plan,
            "results": results,
            "success_rate": success_count / len(results) if results else 0
        }

    def chat(self, message: str) -> str:
        """对话模式"""
        # 检索相关记忆
        relevant = self.memory.retrieve(message, k=5)
        context = self.memory.summarize()

        # 这里应该使用LLM生成回复
        response = f"我理解了: {message}\n"
        response += f"根据我的记忆，{context[:200]}..."

        # 记录对话
        self.memory.add(Memory(
            content=f"用户: {message}",
            memory_type="observation",
            timestamp=time.time()
        ))
        self.memory.add(Memory(
            content=f"助手: {response[:100]}",
            memory_type="action",
            timestamp=time.time()
        ))

        return response

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "name": self.name,
            "state": self.state.value,
            "memory_count": len(self.memory.memories),
            "goals_count": len(self.goals),
            "skills_count": len(self.skills),
            "action_history_count": len(self.action_history)
        }


# 便捷函数
def create_agent(name: str = "Agent", llm_client=None) -> AIAgent:
    """创建AI Agent"""
    return AIAgent(name, llm_client)


if __name__ == "__main__":
    # 测试
    agent = AIAgent("Test Agent")

    # 注册一些测试技能
    agent.register_skill("open_app", lambda target: {"output": f"打开 {target}"})
    agent.register_skill("wait", lambda duration: {"output": f"等待 {duration} 秒"})
    agent.register_skill("analyze", lambda **kwargs: {"output": "分析完成"})
    agent.register_skill("verify", lambda **kwargs: {"output": "验证通过"})

    # 运行测试
    result = agent.run("打开计算器")
    print(f"\n结果: {result}")

    # 查看状态
    print(f"\n状态: {agent.get_status()}")
