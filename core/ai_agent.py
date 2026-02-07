#!/usr/bin/env python3
"""
AIAgent [emoji] - [emoji]AI[emoji]

[emoji]AI Agent[emoji]
[emoji]

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
    """[emoji]"""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    WAITING = "waiting"


class TaskPriority(Enum):
    """[emoji]"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Memory:
    """[emoji]"""
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
    """[emoji]"""
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
    [emoji]

    [emoji]Agent[emoji]
    """

    def __init__(self, max_memories: int = 1000):
        self.memories: List[Memory] = []
        self.max_memories = max_memories
        self._memory_index: Dict[str, List[int]] = {}  # [emoji]

    def add(self, memory: Memory):
        """[emoji]"""
        self.memories.append(memory)

        # [emoji]
        if memory.memory_type not in self._memory_index:
            self._memory_index[memory.memory_type] = []
        self._memory_index[memory.memory_type].append(len(self.memories) - 1)

        # [emoji]
        if len(self.memories) > self.max_memories:
            self._forget_least_important()

    def _forget_least_important(self):
        """[emoji]"""
        if not self.memories:
            return

        # [emoji]
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
        """[emoji]"""
        self._memory_index.clear()
        for i, mem in enumerate(self.memories):
            if mem.memory_type not in self._memory_index:
                self._memory_index[mem.memory_type] = []
            self._memory_index[mem.memory_type].append(i)

    def retrieve(self, query: str, k: int = 5) -> List[Memory]:
        """[emoji]"""
        # [emoji]
        # [emoji]
        keywords = set(query.lower().split())

        scored_memories = []
        for mem in self.memories:
            score = 0
            mem_words = set(mem.content.lower().split())
            score += len(keywords & mem_words)
            score += mem.importance * 0.1
            score -= (time.time() - mem.timestamp) / 86400 * 0.01  # [emoji]

            scored_memories.append((mem, score))

        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_memories[:k]]

    def get_recent(self, n: int = 10, memory_type: str = None) -> List[Memory]:
        """[emoji]"""
        if memory_type:
            indices = self._memory_index.get(memory_type, [])
            memories = [self.memories[i] for i in indices]
        else:
            memories = self.memories

        return sorted(memories, key=lambda x: x.timestamp, reverse=True)[:n]

    def summarize(self) -> str:
        """[emoji]"""
        recent = self.get_recent(20)
        observations = [m.content for m in recent if m.memory_type == "observation"]
        actions = [m.content for m in recent if m.memory_type == "action"]

        summary = f"[emoji]:\n" + "\n".join(f"- {o}" for o in observations[:5])
        summary += f"\n\n[emoji]:\n" + "\n".join(f"- {a}" for a in actions[:5])

        return summary


class AIAgent:
    """
    AI Agent

    [emoji]AI[emoji]
    """

    def __init__(self, name: str = "GodHand Agent", llm_client=None):
        self.name = name
        self.llm = llm_client
        self.state = AgentState.IDLE

        # [emoji]
        self.memory = LongTermMemory()
        self.working_memory: Dict[str, Any] = {}  # [emoji]

        # [emoji]
        self.goals: List[Goal] = []
        self.current_goal: Optional[Goal] = None

        # [emoji]
        self.action_history: List[Dict] = []

        # [emoji]
        self.skills: Dict[str, Callable] = {}

        # [emoji]
        self.action_count_since_reflection = 0
        self.reflection_interval = 5

        print(f"[emoji] [AIAgent] {name} [emoji]")

    def register_skill(self, name: str, func: Callable):
        """[emoji]"""
        self.skills[name] = func
        print(f"[emoji] [emoji]: {name}")

    def perceive(self, observation: str, importance: float = 1.0):
        """[emoji]"""
        memory = Memory(
            content=observation,
            memory_type="observation",
            timestamp=time.time(),
            importance=importance
        )
        self.memory.add(memory)
        print(f"[emoji]  [[emoji]] {observation[:100]}...")

    def set_goal(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Goal:
        """[emoji]"""
        goal_id = hashlib.md5(f"{description}{time.time()}".encode()).hexdigest()[:8]

        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority
        )

        self.goals.append(goal)
        self.goals.sort(key=lambda g: g.priority.value, reverse=True)

        # [emoji]
        self.memory.add(Memory(
            content=f"[emoji]: {description}",
            memory_type="plan",
            timestamp=time.time(),
            importance=priority.value
        ))

        print(f"[emoji] [[emoji]] {description} ([emoji]: {priority.name})")
        return goal

    def plan(self, goal: Goal = None) -> List[Dict]:
        """[emoji]"""
        self.state = AgentState.PLANNING

        target = goal or self.current_goal
        if not target:
            return []

        # [emoji]
        relevant_memories = self.memory.retrieve(target.description, k=10)
        memory_context = "\n".join([m.content for m in relevant_memories])

        # [emoji]LLM[emoji]
        if self.llm:
            plan = self._plan_with_llm(target, memory_context)
        else:
            plan = self._plan_with_rules(target)

        # [emoji]
        self.memory.add(Memory(
            content=f"[emoji]: {len(plan)} [emoji]",
            memory_type="plan",
            timestamp=time.time(),
            importance=target.priority.value
        ))

        self.state = AgentState.IDLE
        return plan

    def _plan_with_llm(self, goal: Goal, context: str) -> List[Dict]:
        """[emoji]LLM[emoji]"""
        # [emoji]LLM API
        # [emoji]
        return [
            {"step": 1, "action": "analyze", "description": f"[emoji]: {goal.description}"},
            {"step": 2, "action": "execute", "description": "[emoji]"},
            {"step": 3, "action": "verify", "description": "[emoji]"}
        ]

    def _plan_with_rules(self, goal: Goal) -> List[Dict]:
        """[emoji]"""
        description = goal.description.lower()

        if "[emoji]" in description:
            app = description.replace("[emoji]", "").strip()
            return [
                {"step": 1, "action": "open_app", "target": app},
                {"step": 2, "action": "wait", "duration": 2},
                {"step": 3, "action": "verify", "description": f"[emoji] {app} [emoji]"}
            ]

        return [
            {"step": 1, "action": "analyze", "description": "[emoji]"},
            {"step": 2, "action": "execute", "description": "[emoji]"}
        ]

    def execute(self, action: Dict) -> Dict:
        """[emoji]"""
        self.state = AgentState.EXECUTING

        action_type = action.get("action", "unknown")
        print(f"[emoji] [[emoji]] {action_type}: {action.get('description', '')}")

        result = {"success": False, "output": ""}

        # [emoji]
        if action_type in self.skills:
            try:
                skill_func = self.skills[action_type]
                result = skill_func(**{k: v for k, v in action.items() if k != "action"})
                result["success"] = True
            except Exception as e:
                result["error"] = str(e)
        else:
            result["output"] = f"[emoji]: {action_type}"

        # [emoji]
        self.action_history.append({
            "action": action,
            "result": result,
            "timestamp": time.time()
        })

        self.memory.add(Memory(
            content=f"[emoji]: {action_type} - [emoji]: {result.get('output', '')[:100]}",
            memory_type="action",
            timestamp=time.time(),
            importance=2.0 if result["success"] else 3.0
        ))

        self.action_count_since_reflection += 1

        # [emoji]
        if self.action_count_since_reflection >= self.reflection_interval:
            self.reflect()

        self.state = AgentState.IDLE
        return result

    def reflect(self):
        """[emoji]"""
        self.state = AgentState.REFLECTING
        print("[[emoji]] [[emoji]] [emoji]...")

        # [emoji]
        recent_actions = self.action_history[-self.reflection_interval:]

        successes = sum(1 for a in recent_actions if a["result"].get("success"))
        failures = len(recent_actions) - successes

        reflection_content = f"[emoji] {len(recent_actions)} [emoji]: "
        reflection_content += f"[emoji] {successes} [emoji], [emoji] {failures} [emoji]"

        if failures > 0:
            reflection_content += ". [emoji]"
        else:
            reflection_content += ". [emoji]"

        self.memory.add(Memory(
            content=reflection_content,
            memory_type="reflection",
            timestamp=time.time(),
            importance=2.5
        ))

        print(f"[emoji] {reflection_content}")

        self.action_count_since_reflection = 0
        self.state = AgentState.IDLE

    def run(self, instruction: str) -> Dict:
        """[emoji]"""
        print(f"\n{'='*60}")
        print(f"[emoji] [[emoji]] {instruction}")
        print('='*60)

        # 1. [emoji]
        self.perceive(f"[emoji]: {instruction}", importance=2.0)

        # 2. [emoji]
        goal = self.set_goal(instruction, TaskPriority.HIGH)
        self.current_goal = goal

        # 3. [emoji]
        plan = self.plan(goal)
        print(f"\n[emoji] [emoji]: {len(plan)} [emoji]")

        # 4. [emoji]
        results = []
        for step in plan:
            result = self.execute(step)
            results.append(result)

            if not result.get("success"):
                print(f"[emoji] [emoji]: {step}")
                # [emoji]

        # 5. [emoji]
        success_count = sum(1 for r in results if r.get("success"))
        print(f"\n[emoji] [emoji]: {success_count}/{len(results)} [emoji]")

        return {
            "goal": goal.description,
            "plan": plan,
            "results": results,
            "success_rate": success_count / len(results) if results else 0
        }

    def chat(self, message: str) -> str:
        """[emoji]"""
        # [emoji]
        relevant = self.memory.retrieve(message, k=5)
        context = self.memory.summarize()

        # [emoji]LLM[emoji]
        response = f"[emoji]: {message}\n"
        response += f"[emoji]{context[:200]}..."

        # [emoji]
        self.memory.add(Memory(
            content=f"[emoji]: {message}",
            memory_type="observation",
            timestamp=time.time()
        ))
        self.memory.add(Memory(
            content=f"[emoji]: {response[:100]}",
            memory_type="action",
            timestamp=time.time()
        ))

        return response

    def get_status(self) -> Dict:
        """[emoji]"""
        return {
            "name": self.name,
            "state": self.state.value,
            "memory_count": len(self.memory.memories),
            "goals_count": len(self.goals),
            "skills_count": len(self.skills),
            "action_history_count": len(self.action_history)
        }


# [emoji]
def create_agent(name: str = "Agent", llm_client=None) -> AIAgent:
    """[emoji]AI Agent"""
    return AIAgent(name, llm_client)


if __name__ == "__main__":
    # [emoji]
    agent = AIAgent("Test Agent")

    # [emoji]
    agent.register_skill("open_app", lambda target: {"output": f"[emoji] {target}"})
    agent.register_skill("wait", lambda duration: {"output": f"[emoji] {duration} [emoji]"})
    agent.register_skill("analyze", lambda **kwargs: {"output": "[emoji]"})
    agent.register_skill("verify", lambda **kwargs: {"output": "[emoji]"})

    # [emoji]
    result = agent.run("[emoji]")
    print(f"\n[emoji]: {result}")

    # [emoji]
    print(f"\n[emoji]: {agent.get_status()}")
