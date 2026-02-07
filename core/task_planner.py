#!/usr/bin/env python3
"""
TaskPlanner 🧠 - 智能任务规划器

将复杂的自然语言指令分解为可执行的动作序列。
支持条件分支、循环、错误恢复等高级特性。

Author: GodHand Team
Version: 1.0.0
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union, Callable
from enum import Enum, auto
from abc import ABC, abstractmethod


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class StepType(Enum):
    """步骤类型"""
    ACTION = "action"           # 普通动作
    CONDITION = "condition"     # 条件判断
    LOOP = "loop"               # 循环
    WAIT = "wait"               # 等待
    PARALLEL = "parallel"       # 并行执行
    CALLBACK = "callback"       # 回调/人工确认


@dataclass
class Step:
    """执行步骤"""
    id: str
    type: StepType
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    depends_on: List[str] = field(default_factory=list)  # 依赖的步骤ID
    on_success: Optional[str] = None  # 成功后的下一步
    on_failure: Optional[str] = None  # 失败后的下一步
    timeout: float = 30.0  # 超时时间（秒）

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "depends_on": self.depends_on,
            "timeout": self.timeout
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    task_id: str
    description: str
    steps: List[Step]
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())

    def get_step(self, step_id: str) -> Optional[Step]:
        """获取指定步骤"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self) -> List[Step]:
        """获取可以执行的步骤（依赖已满足）"""
        ready = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue

            # 检查依赖
            deps_satisfied = all(
                self.get_step(dep_id).status == StepStatus.COMPLETED
                for dep_id in step.depends_on
            )
            if deps_satisfied:
                ready.append(step)
        return ready

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
            "created_at": self.created_at
        }


@dataclass
class PlanningContext:
    """规划上下文"""
    instruction: str
    current_app: Optional[str] = None
    available_elements: List[Dict] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)


class TaskPlanner:
    """
    智能任务规划器

    世界第一的任务规划能力：
    - 复杂指令自动分解
    - 智能错误恢复
    - 自适应执行策略
    """

    def __init__(self, llm_client=None, use_llm: bool = True):
        self.llm = llm_client
        self.use_llm = use_llm
        self.step_counter = 0

        # 内置的任务模板
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Callable]:
        """加载任务模板"""
        return {
            "open_and_type": self._template_open_and_type,
            "search_and_extract": self._template_search_and_extract,
            "file_organization": self._template_file_organization,
            "data_entry": self._template_data_entry,
        }

    def plan(self, instruction: str, context: Optional[PlanningContext] = None) -> ExecutionPlan:
        """
        根据指令生成执行计划

        Args:
            instruction: 自然语言指令
            context: 规划上下文（可选）

        Returns:
            ExecutionPlan 执行计划
        """
        if context is None:
            context = PlanningContext(instruction=instruction)

        # 1. 尝试模板匹配
        plan = self._try_template_match(instruction, context)
        if plan:
            return plan

        # 2. 尝试 LLM 规划
        if self.use_llm and self.llm:
            plan = self._plan_with_llm(instruction, context)
            if plan:
                return plan

        # 3. 规则-based 规划
        plan = self._plan_with_rules(instruction, context)
        if plan:
            return plan

        # 4. 无法规划，返回单步计划
        return self._create_fallback_plan(instruction)

    def _try_template_match(self, instruction: str, context: PlanningContext) -> Optional[ExecutionPlan]:
        """尝试匹配预设模板"""
        instruction_lower = instruction.lower()

        # 模板1: 打开应用并输入
        if any(x in instruction_lower for x in ["打开", "输入"]):
            return self._template_open_and_type(instruction, context)

        # 模板2: 搜索并提取
        if "搜索" in instruction_lower and ("提取" in instruction_lower or "保存" in instruction_lower):
            return self._template_search_and_extract(instruction, context)

        # 模板3: 文件整理
        if any(x in instruction_lower for x in ["整理文件", "移动文件", "分类"]):
            return self._template_file_organization(instruction, context)

        return None

    def _template_open_and_type(self, instruction: str, context: PlanningContext) -> ExecutionPlan:
        """模板：打开应用并输入"""
        # 解析应用名和输入内容
        # 格式: "打开XXX 输入YYY" 或 "打开XXX，输入YYY"

        parts = re.split(r'[，,;；]\s*|\s+然后\s+|\s+再\s+', instruction)

        steps = []
        current_app = None

        for part in parts:
            part = part.strip()

            # 打开应用
            if part.startswith("打开") or part.startswith("启动"):
                app_name = part.replace("打开", "").replace("启动", "").strip()
                current_app = app_name
                steps.append(Step(
                    id=self._next_step_id(),
                    type=StepType.ACTION,
                    description=f"打开应用: {app_name}",
                    params={"action": "open_app", "app_name": app_name}
                ))
                # 等待应用启动
                steps.append(Step(
                    id=self._next_step_id(),
                    type=StepType.WAIT,
                    description="等待应用启动",
                    params={"seconds": 2.0},
                    depends_on=[steps[-1].id]
                ))

            # 输入文本
            elif part.startswith("输入") or part.startswith("填写"):
                text = part.replace("输入", "").replace("填写", "").strip()
                depends = [steps[-1].id] if steps else []
                steps.append(Step(
                    id=self._next_step_id(),
                    type=StepType.ACTION,
                    description=f"输入文本: {text[:20]}...",
                    params={"action": "type_text", "text": text},
                    depends_on=depends
                ))

            # 按键
            elif part.startswith("按") or part.startswith("按下"):
                key = part.replace("按下", "").replace("按", "").strip()
                depends = [steps[-1].id] if steps else []
                steps.append(Step(
                    id=self._next_step_id(),
                    type=StepType.ACTION,
                    description=f"按键: {key}",
                    params={"action": "press_key", "key": key},
                    depends_on=depends
                ))

        return ExecutionPlan(
            task_id=self._generate_task_id(),
            description=instruction,
            steps=steps,
            context={"template": "open_and_type", "app": current_app}
        )

    def _template_search_and_extract(self, instruction: str, context: PlanningContext) -> ExecutionPlan:
        """模板：搜索并提取信息"""
        steps = []

        # 解析搜索关键词
        search_match = re.search(r'搜索["\']?([^"\']+)["\']?', instruction)
        query = search_match.group(1) if search_match else ""

        # 1. 打开浏览器
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.ACTION,
            description="打开浏览器",
            params={"action": "open_app", "app_name": "browser"}
        ))

        # 2. 等待
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.WAIT,
            description="等待浏览器启动",
            params={"seconds": 2.0},
            depends_on=[steps[-1].id]
        ))

        # 3. 执行搜索
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.ACTION,
            description=f"搜索: {query}",
            params={"action": "search", "query": query},
            depends_on=[steps[-1].id]
        ))

        # 4. 等待结果加载
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.WAIT,
            description="等待搜索结果",
            params={"seconds": 3.0},
            depends_on=[steps[-1].id]
        ))

        # 5. 提取信息（需要人工确认或AI辅助）
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.CALLBACK,
            description="提取搜索结果信息",
            params={"action": "extract_info", "query": query},
            depends_on=[steps[-1].id]
        ))

        return ExecutionPlan(
            task_id=self._generate_task_id(),
            description=instruction,
            steps=steps,
            context={"template": "search_and_extract", "query": query}
        )

    def _template_file_organization(self, instruction: str, context: PlanningContext) -> ExecutionPlan:
        """模板：文件整理"""
        steps = []

        # 解析文件夹和规则
        folder_match = re.search(r'["\']?([^"\']+?)["\']?\s*文件夹', instruction)
        folder = folder_match.group(1) if folder_match else "当前文件夹"

        # 检测是按类型还是按日期
        by_type = any(x in instruction for x in ["类型", "格式", "扩展名"])
        by_date = any(x in instruction for x in ["日期", "时间", "年月"])

        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.ACTION,
            description=f"扫描文件夹: {folder}",
            params={"action": "scan_folder", "folder": folder}
        ))

        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.ACTION,
            description="分析文件并分类",
            params={
                "action": "classify_files",
                "folder": folder,
                "by_type": by_type,
                "by_date": by_date
            },
            depends_on=[steps[-1].id]
        ))

        # 添加确认步骤
        steps.append(Step(
            id=self._next_step_id(),
            type=StepType.CALLBACK,
            description="确认整理方案",
            params={"action": "confirm", "message": "是否执行文件整理？"},
            depends_on=[steps[-1].id],
            on_success=steps[-1].id + "_exec"  # 确认后执行
        ))

        # 执行整理
        steps.append(Step(
            id=steps[-1].id + "_exec",
            type=StepType.ACTION,
            description="执行文件整理",
            params={"action": "organize_files", "folder": folder},
            depends_on=[steps[-2].id]
        ))

        return ExecutionPlan(
            task_id=self._generate_task_id(),
            description=instruction,
            steps=steps,
            context={"template": "file_organization", "folder": folder}
        )

    def _template_data_entry(self, instruction: str, context: PlanningContext) -> ExecutionPlan:
        """模板：数据录入"""
        # TODO: 实现数据录入模板
        return None

    def _plan_with_llm(self, instruction: str, context: PlanningContext) -> Optional[ExecutionPlan]:
        """使用 LLM 进行智能规划"""
        if not self.llm:
            return None

        prompt = f"""你是一个智能任务规划器。请将用户的指令分解为详细的执行步骤。

用户指令: "{instruction}"

当前应用: {context.current_app or "未知"}
可用元素: {len(context.available_elements)} 个

请将指令分解为以下格式的 JSON 执行计划：

{{
    "steps": [
        {{
            "id": "step_1",
            "type": "action",
            "description": "步骤描述",
            "params": {{"action": "动作类型", "参数": "值"}},
            "depends_on": [],
            "timeout": 30
        }}
    ],
    "context": {{
        "key": "value"
    }}
}}

步骤类型: action, condition, loop, wait, callback
动作类型: open_app, click, type_text, press_key, scroll, screenshot, find_element

注意事项:
1. 每个步骤要有明确的描述和参数
2. 使用 depends_on 建立步骤依赖关系
3. 打开应用后要等待2秒
4. 复杂操作前添加确认步骤(callback)
5. 只返回JSON，不要其他内容
"""

        try:
            response = self.llm.generate(prompt)

            # 提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())

                steps = []
                for step_data in data.get("steps", []):
                    steps.append(Step(
                        id=step_data.get("id", self._next_step_id()),
                        type=StepType(step_data.get("type", "action")),
                        description=step_data.get("description", ""),
                        params=step_data.get("params", {}),
                        depends_on=step_data.get("depends_on", []),
                        timeout=step_data.get("timeout", 30.0)
                    ))

                return ExecutionPlan(
                    task_id=self._generate_task_id(),
                    description=instruction,
                    steps=steps,
                    context=data.get("context", {})
                )

        except Exception as e:
            print(f"[TaskPlanner] LLM planning failed: {e}")

        return None

    def _plan_with_rules(self, instruction: str, context: PlanningContext) -> Optional[ExecutionPlan]:
        """使用规则进行基础规划"""
        instruction_lower = instruction.lower()
        steps = []

        # 简单规则匹配
        if "截图" in instruction_lower:
            steps.append(Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description="截取屏幕",
                params={"action": "screenshot"}
            ))

        elif instruction_lower.startswith("打开"):
            app_name = instruction.replace("打开", "").strip()
            steps.append(Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"打开应用: {app_name}",
                params={"action": "open_app", "app_name": app_name}
            ))

        elif instruction_lower.startswith("输入"):
            text = instruction.replace("输入", "").strip()
            steps.append(Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"输入文本",
                params={"action": "type_text", "text": text}
            ))

        elif "搜索" in instruction_lower:
            query = instruction.replace("搜索", "").strip()
            steps.append(Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"搜索: {query}",
                params={"action": "search", "query": query}
            ))

        if steps:
            return ExecutionPlan(
                task_id=self._generate_task_id(),
                description=instruction,
                steps=steps,
                context={"source": "rule_based"}
            )

        return None

    def _create_fallback_plan(self, instruction: str) -> ExecutionPlan:
        """创建回退计划（单步执行）"""
        return ExecutionPlan(
            task_id=self._generate_task_id(),
            description=instruction,
            steps=[
                Step(
                    id=self._next_step_id(),
                    type=StepType.ACTION,
                    description=f"执行: {instruction}",
                    params={"action": "execute", "instruction": instruction}
                )
            ],
            context={"source": "fallback"}
        )

    def adapt_plan(self, plan: ExecutionPlan, feedback: Dict[str, Any]) -> ExecutionPlan:
        """
        根据执行反馈调整计划

        Args:
            plan: 原执行计划
            feedback: 执行反馈（包含失败的步骤、错误信息等）

        Returns:
            调整后的执行计划
        """
        failed_step_id = feedback.get("failed_step")
        error_message = feedback.get("error", "")

        if not failed_step_id:
            return plan

        failed_step = plan.get_step(failed_step_id)
        if not failed_step:
            return plan

        # 创建调整后的计划
        new_steps = list(plan.steps)

        # 如果还有重试次数，添加重试步骤
        if failed_step.retries < failed_step.max_retries:
            retry_step = Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"重试: {failed_step.description}",
                params={**failed_step.params, "retry": True},
                depends_on=failed_step.depends_on,
                retries=failed_step.retries + 1,
                max_retries=failed_step.max_retries
            )
            new_steps.append(retry_step)
        else:
            # 重试耗尽，尝试替代方案
            alt_step = self._create_alternative_step(failed_step, error_message)
            if alt_step:
                new_steps.append(alt_step)

        return ExecutionPlan(
            task_id=plan.task_id,
            description=f"{plan.description} (adapted)",
            steps=new_steps,
            context={**plan.context, "adapted": True, "feedback": feedback}
        )

    def _create_alternative_step(self, failed_step: Step, error_message: str) -> Optional[Step]:
        """为失败的步骤创建替代方案"""
        action = failed_step.params.get("action", "")

        # 元素未找到的替代方案
        if "not found" in error_message.lower() or "找不到" in error_message:
            return Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"替代方案: 使用坐标执行 {failed_step.description}",
                params={**failed_step.params, "fallback": "use_coordinates"},
                depends_on=failed_step.depends_on
            )

        # 超时的替代方案
        if "timeout" in error_message.lower() or "超时" in error_message:
            return Step(
                id=self._next_step_id(),
                type=StepType.ACTION,
                description=f"替代方案: 跳过 {failed_step.description}",
                params={"action": "skip", "original": failed_step.params},
                depends_on=failed_step.depends_on
            )

        return None

    def _next_step_id(self) -> str:
        """生成步骤 ID"""
        self.step_counter += 1
        return f"step_{self.step_counter:03d}"

    def _generate_task_id(self) -> str:
        """生成任务 ID"""
        import time
        return f"task_{int(time.time() * 1000)}"


class PlanExecutor:
    """执行计划执行器"""

    def __init__(self, action_executor: Optional[Callable] = None):
        self.action_executor = action_executor
        self.current_plan: Optional[ExecutionPlan] = None

    async def execute(self, plan: ExecutionPlan, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        执行计划

        Args:
            plan: 执行计划
            callback: 执行回调函数(step, result) -> None

        Returns:
            执行结果统计
        """
        self.current_plan = plan

        results = {
            "task_id": plan.task_id,
            "total_steps": len(plan.steps),
            "completed": 0,
            "failed": 0,
            "skipped": 0,
            "results": []
        }

        while True:
            # 获取可以执行的步骤
            ready_steps = plan.get_ready_steps()

            if not ready_steps:
                # 检查是否全部完成
                pending = [s for s in plan.steps if s.status == StepStatus.PENDING]
                running = [s for s in plan.steps if s.status == StepStatus.RUNNING]

                if not pending and not running:
                    break  # 全部完成

                # 等待依赖完成
                await __import__('asyncio').sleep(0.1)
                continue

            # 执行就绪的步骤
            for step in ready_steps:
                step.status = StepStatus.RUNNING

                try:
                    result = await self._execute_step(step)
                    step.status = StepStatus.COMPLETED
                    step.result = result
                    results["completed"] += 1

                except Exception as e:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    results["failed"] += 1

                    # 检查是否有失败处理路径
                    if step.on_failure:
                        # TODO: 处理失败路径
                        pass

                if callback:
                    callback(step, step.result)

        return results

    async def _execute_step(self, step: Step) -> Any:
        """执行单个步骤"""
        if step.type == StepType.WAIT:
            await __import__('asyncio').sleep(step.params.get("seconds", 1.0))
            return {"waited": step.params.get("seconds", 1.0)}

        elif step.type == StepType.ACTION:
            if self.action_executor:
                return await self.action_executor(step.params)
            else:
                return {"mock": step.params}

        elif step.type == StepType.CALLBACK:
            # 需要人工介入
            return {"callback_required": True, "params": step.params}

        else:
            return {"unsupported_type": step.type.value}


# 便捷函数
def quick_plan(instruction: str, context: Optional[Dict] = None) -> Dict:
    """快速规划"""
    planner = TaskPlanner(use_llm=False)
    ctx = PlanningContext(instruction=instruction)
    if context:
        ctx.current_app = context.get("current_app")
        ctx.available_elements = context.get("available_elements", [])

    plan = planner.plan(instruction, ctx)
    return plan.to_dict()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python task_planner.py '打开记事本 输入Hello World'")
        print("\n支持的指令示例:")
        print("  - 打开记事本 输入Hello 然后保存")
        print("  - 搜索Python教程")
        print("  - 整理桌面文件夹按类型")
        sys.exit(1)

    instruction = sys.argv[1]

    planner = TaskPlanner(use_llm=False)
    plan = planner.plan(instruction)

    print(f"\n📋 任务: {plan.description}")
    print(f"🆔 任务ID: {plan.task_id}")
    print(f"\n📌 执行计划 ({len(plan.steps)} 个步骤):")
    print("-" * 60)

    for i, step in enumerate(plan.steps, 1):
        deps = f" [依赖: {', '.join(step.depends_on)}]" if step.depends_on else ""
        print(f"\n{i}. [{step.type.value.upper()}] {step.description}{deps}")
        print(f"   参数: {step.params}")

    print("-" * 60)
    print("\n✅ 规划完成!")
