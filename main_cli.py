#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand CLI - 简单可用的命令行版本
实现基础GUI自动化功能
"""

import sys
import os
import subprocess
import time
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 添加核心模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入 pyautogui
try:
    import pyautogui
    import pyperclip
    HAS_PYAUTOGUI = True
    pyautogui.FAILSAFE = True  # 启用安全模式，鼠标移到角落会停止
except ImportError:
    HAS_PYAUTOGUI = False
    print("[WARN] pyautogui 未安装，GUI功能不可用")
    print("  安装: pip install pyautogui pyperclip")


class ActionType(Enum):
    """动作类型"""
    OPEN_APP = "open_app"
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
    SHELL = "shell"
    VISUAL_ACTION = "visual_action"  # 视觉描述类动作（如画个圆）
    SEARCH = "search"  # 搜索
    FILE_CREATE = "file_create"  # 创建文件
    FILE_DELETE = "file_delete"  # 删除文件
    FILE_OPEN = "file_open"  # 打开文件
    DIR_CREATE = "dir_create"  # 创建目录
    BROWSER_OPEN = "browser_open"  # 打开网页


@dataclass
class Action:
    """动作定义"""
    type: ActionType
    params: Dict
    description: str = ""


class SimpleParser:
    """简化版指令解析器"""

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
        }

        # 中文按键名称映射
        self.key_map = {
            # 计算器专用
            '加号': '+',
            '加': '+',
            '减号': '-',
            '减': '-',
            '乘号': '*',
            '乘': '*',
            '除号': '/',
            '除': '/',
            '等于': '=',
            '等号': '=',
            '等': '=',
            '点': '.',
            '小数点': '.',
            # 功能键
            '回车': 'enter',
            '空格': 'space',
            '退格': 'backspace',
            '删除': 'delete',
            '删除键': 'delete',
            '上': 'up',
            '下': 'down',
            '左': 'left',
            '右': 'right',
            'ESC': 'esc',
            'Tab': 'tab',
            # 数字
            '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
            '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
        }

    def parse(self, instruction: str) -> List[Action]:
        """解析指令"""
        instruction = instruction.strip().lower()
        if not instruction:
            return []

        # 复合指令：打开X 然后Y
        if '然后' in instruction or '再' in instruction:
            return self._parse_composite(instruction)

        # 单一指令
        action = self._parse_single(instruction)
        return [action] if action else []

    def _parse_composite(self, instruction: str) -> List[Action]:
        """解析复合指令 - 支持多个\"然后\""""
        actions = []

        # 先检查是否是\"打开XX 然后...\"模式
        open_match = re.search(r'^(?:打开|启动|运行)\s*(.+?)\s*(?:然后|再|接着)\s*(.+)', instruction)
        if open_match:
            app_name = open_match.group(1).strip()
            rest = open_match.group(2).strip()

            # 添加打开应用动作
            actions.append(Action(
                type=ActionType.OPEN_APP,
                params={'app': self._resolve_app(app_name)},
                description=f'打开 {app_name}'
            ))

            # 添加等待动作
            actions.append(Action(
                type=ActionType.WAIT,
                params={'seconds': 2.0},
                description='等待2秒'
            ))

            # 处理剩余部分（可能还有多个\"然后\"）
            parts = re.split(r'(?:然后|再|接着)', rest)
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                action = self._parse_single(part)
                if action:
                    actions.append(action)
                else:
                    # 如果无法解析，作为视觉描述动作
                    actions.append(Action(
                        type=ActionType.VISUAL_ACTION,
                        params={'description': part},
                        description=f'视觉动作: {part}'
                    ))

            return actions

        # 其他复合指令（没有\"打开\"开头的）
        if '然后' in instruction or '再' in instruction:
            parts = re.split(r'(?:然后|再|接着)', instruction)
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                action = self._parse_single(part)
                if action:
                    actions.append(action)
                else:
                    actions.append(Action(
                        type=ActionType.VISUAL_ACTION,
                        params={'description': part},
                        description=f'视觉动作: {part}'
                    ))
            return actions

        return []

    def _parse_single(self, instruction: str) -> Optional[Action]:
        """解析单一指令"""

        # 打开应用
        match = re.search(r'(?:打开|启动|运行)\s*(.+)', instruction)
        if match:
            app = match.group(1).strip()
            return Action(
                type=ActionType.OPEN_APP,
                params={'app': self._resolve_app(app)},
                description=f'打开 {app}'
            )

        # 点击坐标
        match = re.search(r'(?:点击|单击).*?(\d+)\s*,\s*(\d+)', instruction)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return Action(
                type=ActionType.CLICK,
                params={'x': x, 'y': y},
                description=f'点击 ({x}, {y})'
            )

        # 双击
        if '双击' in instruction:
            return Action(
                type=ActionType.DOUBLE_CLICK,
                params={},
                description='双击鼠标'
            )

        # 右键
        if '右键' in instruction:
            return Action(
                type=ActionType.RIGHT_CLICK,
                params={},
                description='右键点击'
            )

        # 输入文字
        match = re.search(r'(?:输入|打字)\s*(.+)', instruction)
        if match:
            text = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.TYPE,
                params={'text': text},
                description=f'输入 "{text}"'
            )

        # 按键
        match = re.search(r'(?:按|按键)\s*(.+)', instruction)
        if match:
            key = match.group(1).strip()
            # 使用 key_map 映射中文按键名称
            actual_key = self.key_map.get(key, key.lower())
            return Action(
                type=ActionType.PRESS_KEY,
                params={'key': actual_key},
                description=f'按 {key}'
            )

        # 快捷键
        match = re.search(r'(?:快捷键)\s*(.+)', instruction)
        if match:
            keys = match.group(1).strip().split('+')
            return Action(
                type=ActionType.HOTKEY,
                params={'keys': [k.strip() for k in keys]},
                description=f'快捷键 {"+".join(keys)}'
            )

        # 等待
        match = re.search(r'(?:等待|延时)\s*(\d+)', instruction)
        if match:
            seconds = int(match.group(1))
            return Action(
                type=ActionType.WAIT,
                params={'seconds': seconds},
                description=f'等待 {seconds} 秒'
            )

        # 截图
        if '截图' in instruction:
            return Action(
                type=ActionType.SCREENSHOT,
                params={},
                description='截图'
            )

        # 移动鼠标
        match = re.search(r'(?:移动|移到).*?(\d+)\s*,\s*(\d+)', instruction)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return Action(
                type=ActionType.MOVE,
                params={'x': x, 'y': y},
                description=f'移动鼠标到 ({x}, {y})'
            )

        # 搜索 - 打开浏览器搜索
        search_match = re.search(r'(?:搜索|查找|百度|google)\s*(.+)', instruction)
        if search_match:
            query = search_match.group(1).strip()
            return Action(
                type=ActionType.SEARCH,
                params={'query': query},
                description=f'搜索: {query}'
            )

        # 创建目录 (优先于文件，避免"创建文件夹"被文件匹配)
        dir_match = re.search(r'(?:创建|新建).*?(?:文件夹|目录)\s*(.+)', instruction)
        if dir_match:
            path = dir_match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.DIR_CREATE,
                params={'path': path},
                description=f'创建目录: {path}'
            )

        # 创建文件
        file_match = re.search(r'(?:创建|新建).*?文件\s*(.+)', instruction)
        if file_match:
            path = file_match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.FILE_CREATE,
                params={'path': path},
                description=f'创建文件: {path}'
            )

        # 删除文件
        del_match = re.search(r'(?:删除|移除).*?文件\s*(.+)', instruction)
        if del_match:
            path = del_match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.FILE_DELETE,
                params={'path': path},
                description=f'删除文件: {path}'
            )

        # 打开网页
        url_match = re.search(r'(?:打开|访问).*?(https?://\S+)', instruction)
        if url_match:
            url = url_match.group(1)
            return Action(
                type=ActionType.BROWSER_OPEN,
                params={'url': url},
                description=f'打开网页: {url}'
            )

        return None

    def _resolve_app(self, app_name: str) -> str:
        """解析应用名称"""
        app_lower = app_name.lower()
        if app_lower in self.app_map:
            return self.app_map[app_lower]
        for name, cmd in self.app_map.items():
            if name in app_lower or app_lower in name:
                return cmd
        return app_name


class ActionExecutor:
    """动作执行器"""

    def __init__(self):
        self.results = []

    def execute(self, action: Action) -> Dict:
        """执行单个动作"""
        if not HAS_PYAUTOGUI and action.type not in [ActionType.OPEN_APP, ActionType.SHELL]:
            return {'success': False, 'error': 'pyautogui 未安装'}

        print(f"  [执行] {action.description}")

        try:
            handler = getattr(self, f'_exec_{action.type.value}', None)
            if handler:
                return handler(action)
            else:
                return {'success': False, 'error': f'未知动作: {action.type.value}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def execute_batch(self, actions: List[Action]) -> List[Dict]:
        """批量执行动作"""
        results = []
        for i, action in enumerate(actions, 1):
            print(f"\n[{i}/{len(actions)}] {action.description}")
            result = self.execute(action)
            results.append(result)
            if not result.get('success'):
                print(f"  [FAIL] {result.get('error')}")
            else:
                print(f"  [OK] {result.get('output', '完成')}")
        return results

    def _exec_open_app(self, action: Action) -> Dict:
        """打开应用"""
        app = action.params.get('app', '')
        subprocess.Popen(f'start "" {app}', shell=True)
        return {'success': True, 'output': f'已启动: {app}'}

    def _exec_click(self, action: Action) -> Dict:
        """点击"""
        x = action.params.get('x')
        y = action.params.get('y')
        if x is not None and y is not None:
            pyautogui.click(x, y)
            return {'success': True, 'output': f'点击 ({x}, {y})'}
        else:
            pyautogui.click()
            return {'success': True, 'output': '点击当前位置'}

    def _exec_double_click(self, action: Action) -> Dict:
        """双击"""
        pyautogui.doubleClick()
        return {'success': True, 'output': '双击'}

    def _exec_right_click(self, action: Action) -> Dict:
        """右键点击"""
        pyautogui.rightClick()
        return {'success': True, 'output': '右键点击'}

    def _exec_type(self, action: Action) -> Dict:
        """输入文字"""
        text = action.params.get('text', '')
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        return {'success': True, 'output': f'输入: {text[:30]}'}

    def _exec_press_key(self, action: Action) -> Dict:
        """按键"""
        key = action.params.get('key', '')
        pyautogui.press(key)
        return {'success': True, 'output': f'按键: {key}'}

    def _exec_hotkey(self, action: Action) -> Dict:
        """快捷键"""
        keys = action.params.get('keys', [])
        pyautogui.hotkey(*keys)
        return {'success': True, 'output': f'快捷键: {"+".join(keys)}'}

    def _exec_move(self, action: Action) -> Dict:
        """移动鼠标"""
        x = action.params.get('x', 0)
        y = action.params.get('y', 0)
        pyautogui.moveTo(x, y)
        return {'success': True, 'output': f'移动到 ({x}, {y})'}

    def _exec_wait(self, action: Action) -> Dict:
        """等待"""
        seconds = action.params.get('seconds', 1.0)
        time.sleep(seconds)
        return {'success': True, 'output': f'等待 {seconds} 秒'}

    def _exec_screenshot(self, action: Action) -> Dict:
        """截图"""
        from datetime import datetime
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot(filename)
        return {'success': True, 'output': f'截图保存: {filename}'}

    def _exec_visual_action(self, action: Action) -> Dict:
        """视觉描述动作 - 尝试模拟执行"""
        description = action.params.get('description', '')

        # 根据描述尝试执行相应操作
        if '画' in description or 'draw' in description.lower():
            # 画图相关的操作
            if '圆' in description or 'circle' in description.lower():
                # 在画图中画圆：使用椭圆工具
                # 1. 点击椭圆工具 (通常在工具栏)
                # 2. 拖拽画圆
                pyautogui.click(100, 100)  # 假设椭圆工具位置
                pyautogui.moveTo(400, 300)
                pyautogui.dragTo(600, 500, duration=0.5)
                return {'success': True, 'output': f'尝试画圆: {description}'}
            elif '方' in description or 'rect' in description.lower():
                pyautogui.click(70, 100)  # 假设矩形工具位置
                pyautogui.moveTo(400, 300)
                pyautogui.dragTo(600, 500, duration=0.5)
                return {'success': True, 'output': f'尝试画矩形: {description}'}
            else:
                return {'success': True, 'output': f'画图操作: {description}'}
        elif '点击' in description or 'click' in description.lower():
            pyautogui.click()
            return {'success': True, 'output': f'点击操作: {description}'}
        elif '输入' in description or 'type' in description.lower():
            # 提取要输入的文本
            text = description.replace('输入', '').strip()
            if text:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                return {'success': True, 'output': f'输入文本: {text}'}

        return {'success': True, 'output': f'视觉动作描述: {description} (需要手动执行)'}

    def _exec_search(self, action: Action) -> Dict:
        """搜索 - 打开浏览器"""
        query = action.params.get('query', '')
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f'https://www.bing.com/search?q={encoded_query}'
        subprocess.Popen(f'start msedge "{url}"', shell=True)
        return {'success': True, 'output': f'搜索: {query}'}

    def _exec_file_create(self, action: Action) -> Dict:
        """创建文件"""
        path = action.params.get('path', '')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('')
            return {'success': True, 'output': f'创建文件: {path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_file_delete(self, action: Action) -> Dict:
        """删除文件"""
        path = action.params.get('path', '')
        try:
            os.remove(path)
            return {'success': True, 'output': f'删除文件: {path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_dir_create(self, action: Action) -> Dict:
        """创建目录"""
        path = action.params.get('path', '')
        try:
            os.makedirs(path, exist_ok=True)
            return {'success': True, 'output': f'创建目录: {path}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_browser_open(self, action: Action) -> Dict:
        """打开网页"""
        url = action.params.get('url', '')
        subprocess.Popen(f'start msedge "{url}"', shell=True)
        return {'success': True, 'output': f'打开网页: {url}'}


class GodHandCLI:
    """GodHand 命令行界面"""

    def __init__(self):
        self.parser = SimpleParser()
        self.executor = ActionExecutor()
        self.running = True

        print("=" * 60)
        print("GodHand CLI v3.0 - 简单可用的GUI自动化工具")
        print("=" * 60)
        if not HAS_PYAUTOGUI:
            print("\n[WARN] pyautogui 未安装，部分功能不可用")
            print("安装: pip install pyautogui pyperclip\n")
        print("\n支持的指令:")
        print("  打开 [应用名]        - 打开应用程序")
        print("  打开 XX 然后 YY      - 复合指令")
        print("  点击 X, Y           - 点击坐标")
        print("  双击                - 双击鼠标")
        print("  右键                - 右键点击")
        print("  输入 [文字]         - 输入文字")
        print("  按 [键名]           - 按键 (enter, space, esc等)")
        print("  快捷键 ctrl+a       - 快捷键组合")
        print("  移动 X, Y           - 移动鼠标")
        print("  等待 [秒数]         - 等待")
        print("  截图                - 屏幕截图")
        print("  搜索 [关键词]       - 浏览器搜索")
        print("  打开 [网址]         - 打开网页")
        print("  创建文件 [路径]     - 创建文件")
        print("  删除文件 [路径]     - 删除文件")
        print("  创建文件夹 [路径]   - 创建目录")
        print("\n其他命令: help, exit, quit")
        print("=" * 60)

    def run(self):
        """运行主循环"""
        while self.running:
            try:
                # 获取输入
                user_input = input("\nGodHand> ").strip()

                if not user_input:
                    continue

                # 处理特殊命令
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("再见!")
                    break

                if user_input.lower() in ['help', 'h', '?']:
                    self.show_help()
                    continue

                # 解析并执行
                actions = self.parser.parse(user_input)

                if not actions:
                    print("[ERROR] 无法解析指令，请检查格式")
                    continue

                print(f"\n解析到 {len(actions)} 个动作")
                results = self.executor.execute_batch(actions)

                # 显示结果
                success_count = sum(1 for r in results if r.get('success'))
                print(f"\n[完成] {success_count}/{len(results)} 个动作成功")

            except KeyboardInterrupt:
                print("\n\n再见!")
                break
            except Exception as e:
                print(f"[ERROR] {e}")

    def show_help(self):
        """显示帮助"""
        print("\n" + "=" * 60)
        print("使用示例:")
        print("  打开记事本")
        print("  打开记事本 然后输入Hello World")
        print("  点击 500, 500")
        print("  双击")
        print("  输入 你好世界")
        print("  按 enter")
        print("  快捷键 ctrl+s")
        print("  等待 3")
        print("  截图")
        print("=" * 60)


def main():
    """主入口"""
    cli = GodHandCLI()
    cli.run()


if __name__ == "__main__":
    main()
