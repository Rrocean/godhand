#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand CLI Enhanced v4.0 - 增强版命令行界面
新增功能:
- 自由问答模式: 用自然语言与系统对话
- 功能自检: 自动检测所有功能是否可用
- 智能帮助: 随时询问如何使用
- 对话记忆: 记住上下文和偏好
- 完善的错误处理与恢复
"""

import sys
import os
import json
import time
import re
import subprocess
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from datetime import datetime
from pathlib import Path

# 添加核心模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入依赖
try:
    import pyautogui
    import pyperclip
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

# 禁用智能解析器导入（有依赖问题）
HAS_SMART_PARSER = False


class ActionType(Enum):
    """动作类型枚举"""
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
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    DIR_CREATE = "dir_create"
    BROWSER_OPEN = "browser_open"
    COPY = "copy"
    PASTE = "paste"
    SELECT_ALL = "select_all"
    GET_POSITION = "get_position"
    GET_SCREEN_SIZE = "get_screen_size"
    GET_PIXEL_COLOR = "get_pixel_color"
    IMAGE_CLICK = "image_click"
    ACTIVATE_WINDOW = "activate_window"
    LIST_WINDOWS = "list_windows"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"
    LOOP = "loop"
    VISUAL_ACTION = "visual_action"
    BEEP = "beep"
    NOTIFY = "notify"
    RANDOM_CLICK = "random_click"
    QUESTION = "question"  # 问答模式
    HELP = "help"  # 帮助请求


@dataclass
class Action:
    """动作定义"""
    type: ActionType
    params: Dict
    description: str = ""


class KnowledgeBase:
    """知识库 - 存储如何使用系统的知识"""

    def __init__(self):
        self.knowledge = {
            "基础操作": {
                "如何打开应用": "输入 '打开 [应用名]'，例如: 打开记事本、打开计算器、打开画图",
                "如何输入文字": "输入 '输入 [文字]'，例如: 输入 Hello World",
                "如何点击鼠标": "输入 '点击 X,Y' 指定坐标，或 '点击' 点击当前位置",
                "如何按键": "输入 '按 [键名]'，例如: 按 enter、按 space、按 esc",
                "如何快捷键": "输入 '快捷键 [组合键]'，例如: 快捷键 ctrl+s、快捷键 alt+f4",
                "如何等待": "输入 '等待 [秒数]'，例如: 等待 3",
                "如何截图": "输入 '截图'",
                "如何获取鼠标位置": "输入 '获取鼠标位置'",
            },
            "复合指令": {
                "什么是复合指令": "复合指令是一次执行多个操作，用'然后'、'再'、'接着'连接",
                "如何打开并输入": "输入 '打开 [应用] 然后输入 [文字]'，例如: 打开记事本 然后输入 Hello",
                "如何在浏览器搜索": "输入 '搜索 [关键词]'，例如: 搜索 Python教程",
                "如何打开画图并画圆": "输入 '打开画图 然后画个圆'",
            },
            "窗口管理": {
                "如何列出窗口": "输入 '列出窗口' 显示所有打开的窗口",
                "如何激活窗口": "输入 '激活 [窗口名]'，例如: 激活 记事本",
                "如何最小化": "输入 '最小化'",
                "如何最大化": "输入 '最大化'",
                "如何关闭应用": "输入 '关闭 [应用名]'，例如: 关闭 记事本",
            },
            "文件操作": {
                "如何创建文件": "输入 '创建文件 [路径]'，例如: 创建文件 test.txt",
                "如何创建文件夹": "输入 '创建文件夹 [路径]'，例如: 创建文件夹 myfolder",
                "如何删除文件": "输入 '删除文件 [路径]'，例如: 删除文件 test.txt",
            },
            "高级功能": {
                "如何录制操作": "输入 'record' 开始录制，输入 'stop' 停止",
                "如何回放录制": "输入 'play' 回放录制的内容",
                "如何执行脚本": "输入 'script [文件名]'，例如: script myscript.txt",
                "如何定时任务": "输入 'schedule [时间] [命令]'，例如: schedule 09:00 打开记事本",
                "如何循环执行": "输入 '循环 [次数]次 [指令]'，例如: 循环 3次 截图",
            },
            "系统状态": {
                "检查系统": "输入 'check' 或 '自检' 检查所有功能状态",
                "查看版本": "输入 'version' 或 '版本'",
                "查看帮助": "输入 'help' 或 '帮助'",
            }
        }

        # 问答模式的关键词匹配
        self.question_patterns = {
            r"(?:如何|怎么|怎样).*?(?:打开|启动|运行).*?(\S+)": "打开 {0}",
            r"(?:如何|怎么|怎样).*?(?:输入|打字|写)": "输入 [你的文字]",
            r"(?:如何|怎么|怎样).*?(?:点击|按).*?(?:鼠标|左键)": "点击 X,Y 或直接输入 点击",
            r"(?:如何|怎么|怎样).*?(?:右键)": "右键",
            r"(?:如何|怎么|怎样).*?(?:双击)": "双击",
            r"(?:如何|怎么|怎样).*?(?:截图|截屏)": "截图",
            r"(?:如何|怎么|怎样).*?(?:等待|延时)": "等待 3",
            r"(?:你能做什么|你有什么功能|你会什么|功能列表|help|帮助)": "__HELP__",
            r"(?:检查|自检|测试|状态|check|status)": "__CHECK__",
            r"(?:打开|启动|运行)\s*(.+?)\s*(?:然后|再|接着|并)": "__COMPOSITE__",
        }

    def answer(self, question: str) -> Optional[str]:
        """回答用户问题"""
        question = question.lower().strip()

        # 检查是否是特定模式
        for pattern, template in self.question_patterns.items():
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                if template == "__HELP__":
                    return self.get_full_help()
                elif template == "__CHECK__":
                    return "__CHECK__"  # 特殊标记，让系统执行自检
                elif template == "__COMPOSITE__":
                    return self._explain_composite(match.group(1))
                else:
                    # 填充模板
                    groups = match.groups()
                    if groups:
                        return f"你可以输入: '{template.format(*groups)}'"
                    else:
                        return f"你可以输入: '{template}'"

        # 搜索知识库
        for category, items in self.knowledge.items():
            for keyword, answer in items.items():
                if any(word in question for word in keyword.lower().split()):
                    return answer

        # 模糊匹配
        for category, items in self.knowledge.items():
            for keyword, answer in items.items():
                # 计算相似度 - 简单实现
                keyword_words = set(keyword.lower().split())
                question_words = set(question.split())
                if keyword_words & question_words:  # 有交集
                    return answer

        return None

    def _explain_composite(self, app: str) -> str:
        return f"这是复合指令。我会先打开 {app}，然后执行后续操作。复合指令支持多个'然后'连接。"

    def get_full_help(self) -> str:
        """获取完整帮助信息"""
        lines = ["\n" + "=" * 60, "GodHand CLI v4.0 - 功能列表", "=" * 60]

        for category, items in self.knowledge.items():
            lines.append(f"\n【{category}】")
            for keyword, answer in items.items():
                lines.append(f"  • {keyword}: {answer}")

        lines.append("\n" + "=" * 60)
        lines.append("提示: 可以直接用自然语言问我，比如'怎么打开记事本'")
        lines.append("=" * 60 + "\n")
        return "\n".join(lines)

    def get_examples(self) -> List[str]:
        """获取示例命令列表"""
        return [
            "打开记事本 然后输入Hello World",
            "打开计算器 然后输入1+1 然后按等于",
            "搜索 Python教程",
            "点击 500,500 然后等待 2 然后截图",
            "打开画图 然后画个圆",
            "循环 3次 获取鼠标位置",
            "创建文件夹 test_folder",
            "获取屏幕尺寸",
        ]


class FunctionChecker:
    """功能自检器"""

    def __init__(self):
        self.results = []

    def check_all(self) -> Dict[str, Any]:
        """检查所有功能"""
        print("\n" + "=" * 60)
        print("系统自检中...")
        print("=" * 60)

        checks = [
            ("Python版本", self._check_python),
            ("pyautogui (GUI自动化)", self._check_pyautogui),
            ("pyperclip (剪贴板)", self._check_pyperclip),
            ("pygetwindow (窗口管理)", self._check_pygetwindow),
            ("SmartParser (智能解析)", self._check_smart_parser),
            ("屏幕访问权限", self._check_screen_access),
            ("文件系统访问", self._check_filesystem),
            ("网络连接", self._check_network),
        ]

        results = {}
        for name, check_func in checks:
            try:
                status, message = check_func()
                results[name] = {"status": status, "message": message}
                icon = "[OK]" if status else "[FAIL]"
                print(f"  {icon} {name}: {message}")
            except Exception as e:
                results[name] = {"status": False, "message": str(e)}
                print(f"  [ERROR] {name}: {e}")

        # 统计
        passed = sum(1 for r in results.values() if r["status"])
        total = len(results)
        print(f"\n自检结果: {passed}/{total} 项通过")

        if passed < total:
            print("\n建议安装缺失依赖:")
            print("  pip install pyautogui pyperclip pygetwindow")

        print("=" * 60 + "\n")
        return results

    def _check_python(self) -> Tuple[bool, str]:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return True, version

    def _check_pyautogui(self) -> Tuple[bool, str]:
        if HAS_PYAUTOGUI:
            size = pyautogui.size()
            return True, f"已安装 (屏幕: {size[0]}x{size[1]})"
        return False, "未安装"

    def _check_pyperclip(self) -> Tuple[bool, str]:
        try:
            import pyperclip
            return True, "已安装"
        except:
            return False, "未安装"

    def _check_pygetwindow(self) -> Tuple[bool, str]:
        if HAS_PYGETWINDOW:
            return True, "已安装"
        return False, "未安装 (窗口管理功能受限)"

    def _check_smart_parser(self) -> Tuple[bool, str]:
        if HAS_SMART_PARSER:
            return True, "已加载"
        return False, "未加载 (使用基础解析器)"

    def _check_screen_access(self) -> Tuple[bool, str]:
        if not HAS_PYAUTOGUI:
            return False, "无法检测 (pyautogui未安装)"
        try:
            # 尝试获取屏幕尺寸
            size = pyautogui.size()
            return True, f"可以访问 ({size[0]}x{size[1]})"
        except Exception as e:
            return False, f"访问失败: {e}"

    def _check_filesystem(self) -> Tuple[bool, str]:
        try:
            test_file = "_test_write_temp.txt"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return True, "读写正常"
        except Exception as e:
            return False, f"访问失败: {e}"

    def _check_network(self) -> Tuple[bool, str]:
        try:
            import urllib.request
            urllib.request.urlopen("https://www.bing.com", timeout=3)
            return True, "连接正常"
        except:
            return False, "连接失败 (搜索功能受限)"


class ConversationMemory:
    """对话记忆系统"""

    def __init__(self, memory_file="conversation_memory.json"):
        self.memory_file = memory_file
        self.data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "conversations": [],
            "frequent_commands": {},
            "user_preferences": {},
            "last_session": None
        }

    def save(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 记忆保存失败: {e}")

    def add_conversation(self, user_input: str, system_response: str, success: bool):
        self.data["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "system": system_response,
            "success": success
        })
        # 只保留最近100条
        if len(self.data["conversations"]) > 100:
            self.data["conversations"] = self.data["conversations"][-100:]

        # 统计常用命令
        if user_input not in ["exit", "quit", "help", "check"]:
            self.data["frequent_commands"][user_input] = \
                self.data["frequent_commands"].get(user_input, 0) + 1

    def get_frequent_commands(self, n: int = 5) -> List[Tuple[str, int]]:
        items = sorted(self.data["frequent_commands"].items(),
                      key=lambda x: x[1], reverse=True)
        return items[:n]

    def set_preference(self, key: str, value: Any):
        self.data["user_preferences"][key] = value
        self.save()

    def get_preference(self, key: str, default=None):
        return self.data["user_preferences"].get(key, default)


class EnhancedParser:
    """增强版解析器 - 继承基础或智能解析器"""

    def __init__(self):
        self.knowledge = KnowledgeBase()

    def parse(self, instruction: str) -> Tuple[List[Action], Optional[str]]:
        """
        解析指令，返回 (动作列表, 问答回复)
        如果第二个返回值不为空，表示这是一个问答请求
        """
        instruction = instruction.strip()
        if not instruction:
            return [], None

        instruction_lower = instruction.lower()

        # 先检查是否是问句（以疑问词开头）- 优先作为问答
        question_prefixes = ['如何', '怎么', '怎样', '什么', '哪里', '为什么', '你能']
        if any(instruction_lower.startswith(p) for p in question_prefixes):
            answer = self.knowledge.answer(instruction)
            if answer and not answer.startswith("__"):
                return [Action(ActionType.QUESTION, {"answer": answer}, "问答")], None

        # 检查是否是复合指令（包含连接词）- 优先解析为动作
        composite_markers = ['然后', '再', '接着', '并', '，', ',', '；', ';']
        if any(m in instruction_lower for m in composite_markers):
            return self._basic_parse(instruction), None

        # 检查是否是明确的动作指令（以动作关键词开头）
        action_keywords = ['点击', '双击', '右键', '输入', '按', '快捷键',
                          '移动', '等待', '截图', '搜索', '获取', '创建', '删除',
                          '列出', '激活', '最小化', '最大化', '复制', '粘贴', '全选',
                          '关闭']
        if any(instruction_lower.startswith(kw) for kw in action_keywords):
            return self._basic_parse(instruction), None

        # "打开" 开头需要特殊处理 - 检查是否是疑问句形式
        if instruction_lower.startswith('打开'):
            # 如果包含疑问词，可能是问句
            if any(q in instruction_lower for q in ['吗', '？', '?', '如何', '怎么']):
                answer = self.knowledge.answer(instruction)
                if answer and not answer.startswith("__"):
                    return [Action(ActionType.QUESTION, {"answer": answer}, "问答")], None
            return self._basic_parse(instruction), None

        # 检查是否是问答
        answer = self.knowledge.answer(instruction)
        if answer:
            if answer == "__CHECK__":
                return [Action(ActionType.QUESTION, {"operation": "check"}, "系统自检")], None
            elif answer.startswith("__"):
                pass
            else:
                return [Action(ActionType.QUESTION, {"answer": answer}, "问答")], None

        # 使用基础规则解析
        return self._basic_parse(instruction), None

    def _basic_parse(self, instruction: str) -> List[Action]:
        """基础解析规则"""
        instruction_lower = instruction.lower().strip()

        # 帮助
        if instruction_lower in ["help", "?", "帮助"]:
            return [Action(ActionType.HELP, {}, "显示帮助")]

        # 版本
        if instruction_lower in ["version", "版本", "v"]:
            return [Action(ActionType.QUESTION, {"answer": "GodHand CLI v4.0 Enhanced"}, "版本信息")]

        # 自检
        if instruction_lower in ["check", "自检", "测试", "test"]:
            return [Action(ActionType.QUESTION, {"operation": "check"}, "系统自检")]

        # 复合指令: 打开X 然后Y
        if "然后" in instruction_lower or "再" in instruction_lower or "接着" in instruction_lower:
            return self._parse_composite(instruction_lower)

        # 打开应用
        match = re.search(r'(?:打开|启动|运行)\s*(.+)', instruction_lower)
        if match:
            app = match.group(1).strip()
            return [Action(ActionType.OPEN_APP, {"app": app}, f"打开 {app}")]

        # 关闭应用
        match = re.search(r'(?:关闭|退出|关掉)\s*(.+)', instruction_lower)
        if match:
            app = match.group(1).strip()
            return [Action(ActionType.CLOSE_APP, {"app": app}, f"关闭 {app}")]

        # 点击坐标
        match = re.search(r'(?:点击|单击).*?(\d+)\s*[,，]\s*(\d+)', instruction_lower)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return [Action(ActionType.CLICK, {"x": x, "y": y}, f"点击 ({x}, {y})")]

        # 普通点击
        if "点击" in instruction_lower or "单击" in instruction_lower:
            return [Action(ActionType.CLICK, {}, "点击当前位置")]

        # 双击
        if "双击" in instruction_lower:
            return [Action(ActionType.DOUBLE_CLICK, {}, "双击")]

        # 右键
        if "右键" in instruction_lower:
            return [Action(ActionType.RIGHT_CLICK, {}, "右键点击")]

        # 输入文字
        match = re.search(r'(?:输入|打字|写)\s*(.+)', instruction_lower)
        if match:
            text = match.group(1).strip().strip('"\'')
            return [Action(ActionType.TYPE, {"text": text}, f'输入 "{text[:20]}..."' if len(text) > 20 else f'输入 "{text}"')]

        # 按键
        match = re.search(r'(?:按|按键|按下)\s*(.+)', instruction_lower)
        if match:
            key = match.group(1).strip()
            return [Action(ActionType.PRESS_KEY, {"key": key}, f"按 {key}")]

        # 快捷键
        match = re.search(r'(?:快捷键|热键)\s*(.+)', instruction_lower)
        if match:
            keys = [k.strip() for k in match.group(1).split('+')]
            return [Action(ActionType.HOTKEY, {"keys": keys}, f"快捷键 {'+'.join(keys)}")]

        # 移动鼠标
        match = re.search(r'(?:移动|移到).*?(\d+)\s*[,，]\s*(\d+)', instruction_lower)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return [Action(ActionType.MOVE, {"x": x, "y": y}, f"移动鼠标到 ({x}, {y})")]

        # 等待
        match = re.search(r'(?:等待|延时|wait)\s*(\d+(?:\.\d+)?)', instruction_lower)
        if match:
            seconds = float(match.group(1))
            return [Action(ActionType.WAIT, {"seconds": seconds}, f"等待 {seconds} 秒")]

        # 截图
        if "截图" in instruction_lower or "截屏" in instruction_lower:
            return [Action(ActionType.SCREENSHOT, {}, "截图")]

        # 搜索
        match = re.search(r'(?:搜索|查找|百度|google)\s*(.+)', instruction_lower)
        if match:
            query = match.group(1).strip()
            return [Action(ActionType.SEARCH, {"query": query}, f"搜索: {query}")]

        # 获取鼠标位置
        if "鼠标位置" in instruction_lower or "鼠标坐标" in instruction_lower:
            return [Action(ActionType.GET_POSITION, {}, "获取鼠标位置")]

        # 获取屏幕尺寸
        if "屏幕" in instruction_lower and ("尺寸" in instruction_lower or "大小" in instruction_lower or "分辨率" in instruction_lower):
            return [Action(ActionType.GET_SCREEN_SIZE, {}, "获取屏幕尺寸")]

        # 创建文件夹
        match = re.search(r'(?:创建|新建).*?(?:文件夹|目录)\s*(.+)', instruction_lower)
        if match:
            path = match.group(1).strip()
            return [Action(ActionType.DIR_CREATE, {"path": path}, f"创建文件夹: {path}")]

        # 创建文件
        match = re.search(r'(?:创建|新建).*?文件\s*(.+)', instruction_lower)
        if match:
            path = match.group(1).strip()
            return [Action(ActionType.FILE_CREATE, {"path": path}, f"创建文件: {path}")]

        # 删除文件
        match = re.search(r'(?:删除|移除).*?文件\s*(.+)', instruction_lower)
        if match:
            path = match.group(1).strip()
            return [Action(ActionType.FILE_DELETE, {"path": path}, f"删除文件: {path}")]

        # 列出窗口
        if "列出" in instruction_lower and "窗口" in instruction_lower:
            return [Action(ActionType.LIST_WINDOWS, {}, "列出窗口")]

        # 激活窗口
        match = re.search(r'(?:激活|切换到|点击窗口)\s*(.+)', instruction_lower)
        if match:
            title = match.group(1).strip()
            return [Action(ActionType.ACTIVATE_WINDOW, {"title": title}, f"激活窗口: {title}")]

        # 最小化
        if "最小化" in instruction_lower:
            return [Action(ActionType.MINIMIZE_WINDOW, {}, "最小化窗口")]

        # 最大化
        if "最大化" in instruction_lower:
            return [Action(ActionType.MAXIMIZE_WINDOW, {}, "最大化窗口")]

        # 复制
        if "复制" in instruction_lower or "拷贝" in instruction_lower:
            return [Action(ActionType.COPY, {}, "复制")]

        # 粘贴
        if "粘贴" in instruction_lower:
            return [Action(ActionType.PASTE, {}, "粘贴")]

        # 全选
        if "全选" in instruction_lower:
            return [Action(ActionType.SELECT_ALL, {}, "全选")]

        # 浏览器打开
        match = re.search(r'(?:打开|访问|浏览)\s*(https?://\S+)', instruction_lower)
        if match:
            url = match.group(1)
            return [Action(ActionType.BROWSER_OPEN, {"url": url}, f"打开网页: {url}")]

        # 循环
        match = re.search(r'(?:循环|重复)\s*(\d+)\s*(?:次|遍)?\s*(.+)', instruction_lower)
        if match:
            count = int(match.group(1))
            sub_cmd = match.group(2).strip()
            return [Action(ActionType.LOOP, {"count": count, "command": sub_cmd}, f"循环{count}次: {sub_cmd}")]

        # 画个圆/画圆 (视觉动作)
        if "画" in instruction_lower and ("圆" in instruction_lower or "矩形" in instruction_lower or "方" in instruction_lower):
            return [Action(ActionType.VISUAL_ACTION, {"description": instruction_lower}, f"视觉动作: {instruction_lower}")]

        # 未知指令
        return [Action(ActionType.TYPE, {"text": instruction}, f"输入: {instruction}")]

    def _parse_composite(self, instruction: str) -> List[Action]:
        """解析复合指令"""
        actions = []

        # 分割指令
        parts = re.split(r'(?:然后|再|接着|，|,)', instruction)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # 检查是否是"打开X"
            open_match = re.match(r'^(?:打开|启动|运行)\s*(.+)$', part)
            if open_match:
                app = open_match.group(1).strip()
                actions.append(Action(ActionType.OPEN_APP, {"app": app}, f"打开 {app}"))
                actions.append(Action(ActionType.WAIT, {"seconds": 2}, "等待应用启动"))
                continue

            # 检查是否是"输入X"
            type_match = re.match(r'^(?:输入|打字|写)\s*(.+)$', part)
            if type_match:
                text = type_match.group(1).strip().strip('"\'')
                actions.append(Action(ActionType.TYPE, {"text": text}, f"输入: {text[:20]}"))
                continue

            # 检查是否是"按X"
            press_match = re.match(r'^(?:按|按键|按下)\s*(.+)$', part)
            if press_match:
                key = press_match.group(1).strip()
                actions.append(Action(ActionType.PRESS_KEY, {"key": key}, f"按 {key}"))
                continue

            # 其他指令
            sub_actions = self._basic_parse(part)
            if sub_actions and sub_actions[0].type != ActionType.TYPE:
                actions.extend(sub_actions)
            else:
                # 如果无法解析，作为视觉动作
                actions.append(Action(ActionType.VISUAL_ACTION, {"description": part}, f"视觉动作: {part}"))

        return actions


class EnhancedExecutor:
    """增强版执行器"""

    def __init__(self):
        self.app_map = {
            '计算器': 'calc.exe',
            '记事本': 'notepad.exe',
            '画图': 'mspaint.exe',
            'cmd': 'cmd.exe',
            '命令行': 'cmd.exe',
            'powershell': 'powershell.exe',
            '浏览器': 'msedge',
            'edge': 'msedge',
            'chrome': 'chrome',
            '任务管理器': 'taskmgr.exe',
            '设置': 'ms-settings:',
            'word': 'winword',
            'excel': 'excel',
            'vscode': 'code',
            '文件资源管理器': 'explorer.exe',
            '资源管理器': 'explorer.exe',
        }
        self.key_map = {
            '回车': 'enter',
            '空格': 'space',
            '退格': 'backspace',
            '删除': 'delete',
            '上': 'up',
            '下': 'down',
            '左': 'left',
            '右': 'right',
            'esc': 'esc',
            'tab': 'tab',
            '等于': '=',
            '等号': '=',
            '加号': '+',
            '加': '+',
            '减号': '-',
            '减': '-',
            '乘号': '*',
            '乘': '*',
            '除号': '/',
            '除': '/',
            '点': '.',
            '句号': '.',
        }

    def execute(self, action: Action) -> Dict:
        """执行动作，带错误处理"""
        result = {"success": False, "output": "", "error": None}

        try:
            handler = getattr(self, f'_exec_{action.type.value}', None)
            if handler:
                result = handler(action)
            else:
                result["error"] = f"未实现的执行器: {action.type.value}"
        except Exception as e:
            result["error"] = str(e)

        return result

    def execute_batch(self, actions: List[Action]) -> List[Dict]:
        """批量执行"""
        results = []
        for i, action in enumerate(actions, 1):
            print(f"  [{i}/{len(actions)}] {action.description}")
            result = self.execute(action)
            results.append(result)

            if result.get("success"):
                print(f"      [OK] {result.get('output', '完成')}")
            else:
                print(f"      [FAIL] {result.get('error', '未知错误')}")

            # 动作间短暂延迟
            time.sleep(0.1)

        return results

    def _resolve_app(self, app_name: str) -> str:
        """解析应用名称为命令"""
        app_lower = app_name.lower()
        if app_lower in self.app_map:
            return self.app_map[app_lower]
        for name, cmd in self.app_map.items():
            if name in app_lower or app_lower in name:
                return cmd
        return app_name

    def _resolve_key(self, key: str) -> str:
        """解析按键名称"""
        return self.key_map.get(key, key.lower())

    def _exec_open_app(self, action: Action) -> Dict:
        app = action.params.get("app", "")
        cmd = self._resolve_app(app)
        try:
            subprocess.Popen(f'start "" {cmd}', shell=True)
            return {"success": True, "output": f"已启动: {app}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_close_app(self, action: Action) -> Dict:
        app = action.params.get("app", "")
        try:
            subprocess.run(f'taskkill /f /im {app}.exe', shell=True, capture_output=True)
            return {"success": True, "output": f"已关闭: {app}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_click(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        x = action.params.get("x")
        y = action.params.get("y")
        if x is not None and y is not None:
            pyautogui.click(x, y)
            return {"success": True, "output": f"点击 ({x}, {y})"}
        else:
            pyautogui.click()
            return {"success": True, "output": "点击当前位置"}

    def _exec_double_click(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        pyautogui.doubleClick()
        return {"success": True, "output": "双击"}

    def _exec_right_click(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        pyautogui.rightClick()
        return {"success": True, "output": "右键点击"}

    def _exec_type(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        text = action.params.get("text", "")
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        return {"success": True, "output": f"输入: {text[:30]}{'...' if len(text) > 30 else ''}"}

    def _exec_press_key(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        key = self._resolve_key(action.params.get("key", ""))
        pyautogui.press(key)
        return {"success": True, "output": f"按 {key}"}

    def _exec_hotkey(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        keys = action.params.get("keys", [])
        keys_lower = [k.lower() for k in keys]
        pyautogui.hotkey(*keys_lower)
        return {"success": True, "output": f"快捷键: {'+'.join(keys)}"}

    def _exec_move(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        x = action.params.get("x", 0)
        y = action.params.get("y", 0)
        pyautogui.moveTo(x, y)
        return {"success": True, "output": f"移动鼠标到 ({x}, {y})"}

    def _exec_wait(self, action: Action) -> Dict:
        seconds = action.params.get("seconds", 1.0)
        time.sleep(seconds)
        return {"success": True, "output": f"等待 {seconds} 秒"}

    def _exec_screenshot(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        return {"success": True, "output": f"截图保存: {filename}"}

    def _exec_search(self, action: Action) -> Dict:
        query = action.params.get("query", "")
        import urllib.parse
        encoded = urllib.parse.quote(query)
        url = f'https://www.bing.com/search?q={encoded}'
        subprocess.Popen(f'start msedge "{url}"', shell=True)
        return {"success": True, "output": f"搜索: {query}"}

    def _exec_get_position(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        x, y = pyautogui.position()
        return {"success": True, "output": f"鼠标位置: ({x}, {y})"}

    def _exec_get_screen_size(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        w, h = pyautogui.size()
        return {"success": True, "output": f"屏幕尺寸: {w}x{h}"}

    def _exec_dir_create(self, action: Action) -> Dict:
        path = action.params.get("path", "")
        try:
            os.makedirs(path, exist_ok=True)
            return {"success": True, "output": f"创建文件夹: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_file_create(self, action: Action) -> Dict:
        path = action.params.get("path", "")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('')
            return {"success": True, "output": f"创建文件: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_file_delete(self, action: Action) -> Dict:
        path = action.params.get("path", "")
        try:
            os.remove(path)
            return {"success": True, "output": f"删除文件: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_list_windows(self, action: Action) -> Dict:
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow未安装"}
        try:
            windows = [w for w in gw.getAllWindows() if w.title]
            print("\n[窗口列表]")
            for i, w in enumerate(windows[:15], 1):
                print(f"  {i}. {w.title}")
            return {"success": True, "output": f"共 {len(windows)} 个窗口"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_activate_window(self, action: Action) -> Dict:
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow未安装"}
        title = action.params.get("title", "")
        try:
            windows = gw.getWindowsWithTitle(title)
            if windows:
                windows[0].activate()
                return {"success": True, "output": f"激活窗口: {windows[0].title}"}
            else:
                # 模糊匹配
                for w in gw.getAllWindows():
                    if title.lower() in w.title.lower():
                        w.activate()
                        return {"success": True, "output": f"激活窗口: {w.title}"}
                return {"success": False, "error": f"未找到窗口: {title}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_minimize_window(self, action: Action) -> Dict:
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow未安装"}
        try:
            w = gw.getActiveWindow()
            if w:
                w.minimize()
                return {"success": True, "output": "最小化当前窗口"}
            return {"success": False, "error": "没有活动窗口"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_maximize_window(self, action: Action) -> Dict:
        if not HAS_PYGETWINDOW:
            return {"success": False, "error": "pygetwindow未安装"}
        try:
            w = gw.getActiveWindow()
            if w:
                w.maximize()
                return {"success": True, "output": "最大化当前窗口"}
            return {"success": False, "error": "没有活动窗口"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _exec_copy(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        pyautogui.hotkey('ctrl', 'c')
        return {"success": True, "output": "复制"}

    def _exec_paste(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        pyautogui.hotkey('ctrl', 'v')
        return {"success": True, "output": "粘贴"}

    def _exec_select_all(self, action: Action) -> Dict:
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装"}
        pyautogui.hotkey('ctrl', 'a')
        return {"success": True, "output": "全选"}

    def _exec_browser_open(self, action: Action) -> Dict:
        url = action.params.get("url", "")
        subprocess.Popen(f'start msedge "{url}"', shell=True)
        return {"success": True, "output": f"打开网页: {url}"}

    def _exec_loop(self, action: Action) -> Dict:
        """循环执行 - 需要在主循环中处理"""
        return {"success": False, "error": "循环指令需要在主循环中处理"}

    def _exec_visual_action(self, action: Action) -> Dict:
        """视觉动作 - 尝试执行"""
        description = action.params.get("description", "")

        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui未安装，无法执行视觉动作"}

        # 尝试解析画图相关的动作
        if "圆" in description:
            # 在画图中画圆
            try:
                # 尝试点击椭圆工具位置 (基于常见布局)
                pyautogui.click(100, 100)
                time.sleep(0.2)
                # 拖拽画圆
                pyautogui.moveTo(400, 300)
                pyautogui.dragTo(600, 500, duration=0.5)
                return {"success": True, "output": "尝试画圆"}
            except Exception as e:
                return {"success": False, "error": f"画圆失败: {e}"}

        if "方" in description or "矩形" in description:
            try:
                pyautogui.click(70, 100)
                time.sleep(0.2)
                pyautogui.moveTo(400, 300)
                pyautogui.dragTo(600, 500, duration=0.5)
                return {"success": True, "output": "尝试画矩形"}
            except Exception as e:
                return {"success": False, "error": f"画矩形失败: {e}"}

        return {"success": False, "output": f"视觉动作: {description} (需要手动执行)"}

    def _exec_question(self, action: Action) -> Dict:
        """问答动作 - 只是显示答案"""
        answer = action.params.get("answer", "")
        print(f"\n{answer}")
        return {"success": True, "output": "已显示答案"}

    def _exec_help(self, action: Action) -> Dict:
        kb = KnowledgeBase()
        print(kb.get_full_help())
        return {"success": True, "output": "已显示帮助"}


class GodHandCLIEnhanced:
    """增强版CLI主类"""

    def __init__(self):
        self.parser = EnhancedParser()
        self.executor = EnhancedExecutor()
        self.checker = FunctionChecker()
        self.memory = ConversationMemory()
        self.knowledge = KnowledgeBase()
        self.running = True
        self.show_banner()

    def show_banner(self):
        """显示启动横幅"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   GodHand CLI Enhanced v4.0                               ║
║   智能GUI自动化平台 - 自由问答版                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

[功能特点]
• 自由问答: 用自然语言询问如何使用，例如"怎么打开记事本"
• 复合指令: 支持"打开XX然后输入YY"等多步骤操作
• 功能自检: 输入'check'检查系统状态
• 对话记忆: 记住您的使用习惯和常用命令

[快速开始]
• 输入 'help' 查看所有功能
• 输入 'check' 检查系统状态
• 直接输入命令，如'打开记事本'
• 问问题，如'如何截图'

[提示] 输入 'exit' 退出程序
"""
        print(banner)

    def run(self):
        """运行主循环"""
        while self.running:
            try:
                user_input = input("\nGodHand> ").strip()

                if not user_input:
                    continue

                # 退出命令
                if user_input.lower() in ["exit", "quit", "q", "退出"]:
                    print("\n感谢使用 GodHand CLI Enhanced! 再见!")
                    self.memory.save()
                    break

                # 特殊命令处理
                if user_input.lower() in ["check", "自检", "test"]:
                    self.checker.check_all()
                    continue

                if user_input.lower() in ["help", "?", "帮助"]:
                    print(self.knowledge.get_full_help())
                    continue

                if user_input.lower() in ["examples", "示例", "例子"]:
                    self.show_examples()
                    continue

                if user_input.lower() in ["history", "历史"]:
                    self.show_history()
                    continue

                # 解析指令
                actions, _ = self.parser.parse(user_input)

                if not actions:
                    print("[提示] 无法解析指令，尝试用自然语言描述您想做什么")
                    print("       例如: '我想打开记事本输入一些文字'")
                    continue

                # 处理问答
                if actions[0].type == ActionType.QUESTION:
                    self.executor.execute(actions[0])
                    continue

                # 执行动作
                print(f"\n解析到 {len(actions)} 个动作:")
                for i, action in enumerate(actions, 1):
                    print(f"  {i}. {action.description}")

                print("\n开始执行...")
                results = self.executor.execute_batch(actions)

                # 统计结果
                success_count = sum(1 for r in results if r.get("success"))
                print(f"\n[结果] {success_count}/{len(results)} 个动作成功")

                # 保存对话记忆
                response = f"执行了 {len(actions)} 个动作，{success_count} 个成功"
                self.memory.add_conversation(user_input, response, success_count == len(actions))

            except KeyboardInterrupt:
                print("\n\n再见!")
                self.memory.save()
                break
            except Exception as e:
                print(f"\n[错误] {e}")
                import traceback
                traceback.print_exc()

    def show_examples(self):
        """显示示例"""
        print("\n" + "=" * 60)
        print("常用示例")
        print("=" * 60)
        examples = self.knowledge.get_examples()
        for i, ex in enumerate(examples, 1):
            print(f"  {i}. {ex}")
        print("=" * 60 + "\n")

    def show_history(self):
        """显示历史记录"""
        print("\n" + "=" * 60)
        print("常用命令")
        print("=" * 60)
        frequent = self.memory.get_frequent_commands(10)
        if frequent:
            for cmd, count in frequent:
                print(f"  • {cmd} (使用{count}次)")
        else:
            print("  暂无历史记录")
        print("=" * 60 + "\n")


def main():
    """主入口"""
    cli = GodHandCLIEnhanced()
    cli.run()


if __name__ == "__main__":
    main()
