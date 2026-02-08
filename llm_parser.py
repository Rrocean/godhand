#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM智能解析器 - 让AI理解任意指令
不需要硬编码规则，直接让LLM理解用户意图
"""

import os
import sys
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# 尝试导入Google Gemini
try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("[WARN] Google Gemini未安装: pip install google-genai")


class ActionType(Enum):
    """动作类型"""
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    MOVE = "move"
    DRAG = "drag"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    SEARCH = "search"
    BROWSER_OPEN = "browser_open"
    GET_POSITION = "get_position"
    GET_SCREEN_SIZE = "get_screen_size"
    ACTIVATE_WINDOW = "activate_window"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"
    COPY = "copy"
    PASTE = "paste"
    SELECT_ALL = "select_all"
    UNKNOWN = "unknown"


@dataclass
class Action:
    """动作定义"""
    type: ActionType
    params: Dict
    description: str = ""


class LLMParser:
    """LLM智能解析器 - 直接让AI理解用户指令"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = None
        self.history = []  # 对话历史

        if HAS_GEMINI and self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return HAS_GEMINI and self.client is not None

    def parse(self, instruction: str) -> List[Action]:
        """
        使用LLM解析用户指令
        让AI直接理解意图并生成动作序列
        """
        if not self.is_available():
            print("[WARN] LLM不可用，使用规则解析")
            return self._fallback_parse(instruction)

        # 构建系统提示词
        system_prompt = self._get_system_prompt()

        # 构建用户消息
        user_message = f"用户指令: {instruction}"

        try:
            # 调用LLM
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[system_prompt, user_message],
                config=types.GenerateContentConfig(
                    temperature=0.1,  # 低温度，更确定性的输出
                    max_output_tokens=2048,
                )
            )

            # 解析LLM输出
            actions = self._parse_llm_response(response.text)

            # 保存到历史
            self.history.append({
                "instruction": instruction,
                "actions": [self._action_to_dict(a) for a in actions]
            })

            return actions

        except Exception as e:
            print(f"[ERROR] LLM解析失败: {e}")
            return self._fallback_parse(instruction)

    def _get_system_prompt(self) -> str:
        """获取系统提示词 - 告诉LLM如何生成动作"""
        return """你是一个Windows自动化助手。请将用户的自然语言指令转换为可执行的动作序列。

## 可用动作类型

1. **open_app** - 打开应用程序
   - params: {"app": "应用名称或命令"}
   - 示例: {"type": "open_app", "params": {"app": "notepad"}, "description": "打开记事本"}

2. **close_app** - 关闭应用程序
   - params: {"app": "应用名称"}

3. **click** - 鼠标点击
   - params: {"x": 100, "y": 200} 或 {} (点击当前位置)

4. **double_click** - 双击
   - params: {}

5. **right_click** - 右键点击
   - params: {}

6. **type** - 输入文字
   - params: {"text": "要输入的内容"}

7. **press_key** - 按单个键
   - params: {"key": "键名"}
   - 常用键: enter, space, esc, tab, backspace, delete, up, down, left, right

8. **hotkey** - 快捷键组合
   - params: {"keys": ["ctrl", "a"]}
   - 常用: ctrl+a(全选), ctrl+c(复制), ctrl+v(粘贴), ctrl+s(保存), alt+f4(关闭), ctrl+f(搜索)

9. **move** - 移动鼠标
   - params: {"x": 100, "y": 200}

10. **wait** - 等待
    - params: {"seconds": 2.0}

11. **screenshot** - 截图
    - params: {}

12. **search** - 网页搜索
    - params: {"query": "搜索关键词"}

13. **browser_open** - 打开网页
    - params: {"url": "https://..."}

14. **activate_window** - 激活窗口
    - params: {"title": "窗口标题"}

15. **minimize_window** / **maximize_window** - 最小化/最大化窗口
    - params: {}

16. **copy** / **paste** / **select_all** - 复制/粘贴/全选
    - params: {}

## 常见应用命令
- 记事本: notepad
- 计算器: calc
- 画图: mspaint
- 浏览器: msedge
- Chrome: chrome
- Word: winword
- Excel: excel
- VSCode: code
- 微信: WeChat.exe
- 文件资源管理器: explorer

## 输出格式
请输出JSON数组，每个元素是一个动作对象：

```json
[
  {"type": "open_app", "params": {"app": "notepad"}, "description": "打开记事本"},
  {"type": "wait", "params": {"seconds": 1.5}, "description": "等待应用启动"},
  {"type": "type", "params": {"text": "Hello World"}, "description": "输入文字"}
]
```

## 规则
1. 必须输出有效的JSON格式
2. 每个动作都要有description字段说明用途
3. 动作之间要添加适当的wait等待
4. 对于复合指令（多个步骤），拆分为多个动作
5. 如果不确定如何执行，返回空数组 []

现在请解析用户的指令。"""

    def _parse_llm_response(self, response: str) -> List[Action]:
        """解析LLM的JSON响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                # 尝试找代码块
                json_match = re.search(r'```json\s*(\[.*?\])\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    return []
            else:
                json_str = json_match.group()

            data = json.loads(json_str)
            actions = []

            for item in data:
                action_type_str = item.get('type', 'unknown')
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    action_type = ActionType.UNKNOWN

                actions.append(Action(
                    type=action_type,
                    params=item.get('params', {}),
                    description=item.get('description', '')
                ))

            return actions

        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析失败: {e}")
            print(f"[DEBUG] 原始响应: {response[:200]}")
            return []

    def _action_to_dict(self, action: Action) -> Dict:
        """将Action转换为字典"""
        return {
            'type': action.type.value,
            'params': action.params,
            'description': action.description
        }

    def _fallback_parse(self, instruction: str) -> List[Action]:
        """LLM不可用时的回退解析 - 简单规则匹配"""
        instruction_lower = instruction.lower().strip()

        # 简单的规则匹配
        if '打开' in instruction_lower:
            app = instruction_lower.replace('打开', '').strip()
            return [Action(ActionType.OPEN_APP, {"app": app}, f"打开 {app}")]

        if '点击' in instruction_lower:
            return [Action(ActionType.CLICK, {}, "点击")]

        if '输入' in instruction_lower:
            text = instruction_lower.replace('输入', '').strip()
            return [Action(ActionType.TYPE, {"text": text}, f"输入 {text}")]

        if '等待' in instruction_lower:
            return [Action(ActionType.WAIT, {"seconds": 2}, "等待")]

        if '截图' in instruction_lower:
            return [Action(ActionType.SCREENSHOT, {}, "截图")]

        return [Action(ActionType.UNKNOWN, {}, f"无法理解: {instruction}")]


# 兼容旧版接口
class SmartParser(LLMParser):
    """兼容旧版SmartParser接口"""
    pass


if __name__ == "__main__":
    # 测试LLM解析器
    parser = LLMParser()

    if not parser.is_available():
        print("LLM不可用，请设置 GOOGLE_API_KEY 环境变量")
        sys.exit(1)

    test_commands = [
        "打开记事本输入Hello World",
        "发送消息给张三说你好",
        "打开浏览器搜索Python教程",
        "截图然后等待3秒再点击",
    ]

    for cmd in test_commands:
        print(f"\n{'='*60}")
        print(f"指令: {cmd}")
        print('='*60)

        actions = parser.parse(cmd)
        print(f"\n解析结果 ({len(actions)} 个动作):")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. {action.type.value}")
            print(f"     描述: {action.description}")
            print(f"     参数: {action.params}")
