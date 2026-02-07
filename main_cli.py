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
    CLOSE_APP = "close_app"  # 关闭应用
    ACTIVATE_WINDOW = "activate_window"  # 激活窗口
    LIST_WINDOWS = "list_windows"  # 列出窗口
    MINIMIZE_WINDOW = "minimize_window"  # 最小化窗口
    MAXIMIZE_WINDOW = "maximize_window"  # 最大化窗口
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
    WAIT_FOR_IMAGE = "wait_for_image"  # 等待图片出现
    SCREENSHOT = "screenshot"
    SHELL = "shell"
    VISUAL_ACTION = "visual_action"  # 视觉描述类动作（如画个圆）
    SEARCH = "search"  # 搜索
    FILE_CREATE = "file_create"  # 创建文件
    FILE_DELETE = "file_delete"  # 删除文件
    FILE_OPEN = "file_open"  # 打开文件
    DIR_CREATE = "dir_create"  # 创建目录
    BROWSER_OPEN = "browser_open"  # 打开网页
    COPY = "copy"  # 复制
    PASTE = "paste"  # 粘贴
    SELECT_ALL = "select_all"  # 全选
    IMAGE_CLICK = "image_click"  # 图片识别点击
    GET_POSITION = "get_position"  # 获取鼠标位置
    GET_SCREEN_SIZE = "get_screen_size"  # 获取屏幕尺寸
    GET_PIXEL_COLOR = "get_pixel_color"  # 获取像素颜色
    LOOP = "loop"  # 循环执行
    CONDITION = "condition"  # 条件执行
    RANDOM_CLICK = "random_click"  # 随机点击
    BEEP = "beep"  # 蜂鸣提示
    NOTIFY = "notify"  # 系统通知


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

        # 关闭应用
        close_match = re.search(r'(?:关闭|退出|关掉)\s*(.+)', instruction)
        if close_match:
            app = close_match.group(1).strip()
            return Action(
                type=ActionType.CLOSE_APP,
                params={'app': app},
                description=f'关闭应用: {app}'
            )

        # 复制
        if re.search(r'(?:复制|拷贝)', instruction):
            return Action(
                type=ActionType.COPY,
                params={},
                description='复制'
            )

        # 粘贴
        if re.search(r'(?:粘贴)', instruction):
            return Action(
                type=ActionType.PASTE,
                params={},
                description='粘贴'
            )

        # 全选
        if re.search(r'(?:全选)', instruction):
            return Action(
                type=ActionType.SELECT_ALL,
                params={},
                description='全选'
            )

        # 获取鼠标位置
        if re.search(r'(?:获取|显示).*?(?:鼠标|光标).*?(?:位置|坐标)', instruction):
            return Action(
                type=ActionType.GET_POSITION,
                params={},
                description='获取鼠标位置'
            )

        # 图片识别点击
        img_match = re.search(r'(?:点击图片|找图).*?(.+\.(?:png|jpg|bmp|gif))', instruction)
        if img_match:
            image_path = img_match.group(1).strip()
            return Action(
                type=ActionType.IMAGE_CLICK,
                params={'image': image_path},
                description=f'点击图片: {image_path}'
            )

        # 循环执行
        loop_match = re.search(r'(?:循环|重复)\s*(\d+)\s*(?:次)?\s*(.+)', instruction)
        if loop_match:
            count = int(loop_match.group(1))
            sub_command = loop_match.group(2).strip()
            return Action(
                type=ActionType.LOOP,
                params={'count': count, 'command': sub_command},
                description=f'循环{count}次: {sub_command}'
            )

        # 等待图片出现
        wait_img_match = re.search(r'(?:等待|等).*?(?:图片|图像).*?(.+\.(?:png|jpg|bmp|gif))', instruction)
        if wait_img_match:
            image_path = wait_img_match.group(1).strip()
            return Action(
                type=ActionType.WAIT_FOR_IMAGE,
                params={'image': image_path, 'timeout': 30},
                description=f'等待图片: {image_path}'
            )

        # 激活窗口
        activate_match = re.search(r'(?:激活|切换到|点击窗口)\s*(.+)', instruction)
        if activate_match:
            window_title = activate_match.group(1).strip()
            return Action(
                type=ActionType.ACTIVATE_WINDOW,
                params={'title': window_title},
                description=f'激活窗口: {window_title}'
            )

        # 列出所有窗口
        if re.search(r'(?:列出|显示).*?(?:窗口|应用|程序)', instruction):
            return Action(
                type=ActionType.LIST_WINDOWS,
                params={},
                description='列出所有窗口'
            )

        # 最小化窗口
        if re.search(r'(?:最小化|最小)', instruction):
            return Action(
                type=ActionType.MINIMIZE_WINDOW,
                params={},
                description='最小化窗口'
            )

        # 最大化窗口
        if re.search(r'(?:最大化|最大)', instruction):
            return Action(
                type=ActionType.MAXIMIZE_WINDOW,
                params={},
                description='最大化窗口'
            )

        # 获取屏幕尺寸
        if re.search(r'(?:获取|显示).*?(?:屏幕|分辨率)', instruction):
            return Action(
                type=ActionType.GET_SCREEN_SIZE,
                params={},
                description='获取屏幕尺寸'
            )

        # 获取像素颜色
        pixel_match = re.search(r'(?:获取|查看).*?(?:颜色|像素).*?(\d+)\s*,\s*(\d+)', instruction)
        if pixel_match:
            x, y = int(pixel_match.group(1)), int(pixel_match.group(2))
            return Action(
                type=ActionType.GET_PIXEL_COLOR,
                params={'x': x, 'y': y},
                description=f'获取 ({x}, {y}) 像素颜色'
            )

        # 随机点击
        if re.search(r'(?:随机点击|随便点)', instruction):
            return Action(
                type=ActionType.RANDOM_CLICK,
                params={},
                description='随机点击'
            )

        # 蜂鸣提示
        if re.search(r'(?:蜂鸣|提示音|beep)', instruction):
            return Action(
                type=ActionType.BEEP,
                params={},
                description='蜂鸣提示'
            )

        # 系统通知
        notify_match = re.search(r'(?:通知|提醒)\s*(.+)', instruction)
        if notify_match:
            message = notify_match.group(1).strip()
            return Action(
                type=ActionType.NOTIFY,
                params={'message': message},
                description=f'系统通知: {message}'
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

    def execute(self, action: Action, retry=3) -> Dict:
        """执行单个动作，带重试机制"""
        if not HAS_PYAUTOGUI and action.type not in [ActionType.OPEN_APP, ActionType.SHELL]:
            return {'success': False, 'error': 'pyautogui 未安装'}

        print(f"  [执行] {action.description}")

        last_error = None
        for attempt in range(retry):
            try:
                handler = getattr(self, f'_exec_{action.type.value}', None)
                if handler:
                    result = handler(action)
                    if result.get('success'):
                        return result
                    elif attempt < retry - 1:
                        print(f"    [重试 {attempt + 1}/{retry}]...")
                        time.sleep(0.5)
                    else:
                        return result
                else:
                    return {'success': False, 'error': f'未知动作: {action.type.value}'}
            except Exception as e:
                last_error = str(e)
                if attempt < retry - 1:
                    print(f"    [重试 {attempt + 1}/{retry}]...")
                    time.sleep(0.5)

        return {'success': False, 'error': last_error}

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

        # 使用配置的截图目录
        screenshot_dir = "."
        if hasattr(self, 'config'):
            screenshot_dir = self.config.get('screenshot_dir', '.')

        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(screenshot_dir, filename)

        pyautogui.screenshot(filepath)
        return {'success': True, 'output': f'截图保存: {filepath}'}

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

    def _exec_close_app(self, action: Action) -> Dict:
        """关闭应用"""
        app = action.params.get('app', '')
        try:
            # 尝试通过 taskkill 关闭
            subprocess.run(f'taskkill /f /im {app}.exe', shell=True, capture_output=True)
            return {'success': True, 'output': f'关闭应用: {app}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_copy(self, action: Action) -> Dict:
        """复制"""
        pyautogui.hotkey('ctrl', 'c')
        return {'success': True, 'output': '复制'}

    def _exec_paste(self, action: Action) -> Dict:
        """粘贴"""
        pyautogui.hotkey('ctrl', 'v')
        return {'success': True, 'output': '粘贴'}

    def _exec_select_all(self, action: Action) -> Dict:
        """全选"""
        pyautogui.hotkey('ctrl', 'a')
        return {'success': True, 'output': '全选'}

    def _exec_get_position(self, action: Action) -> Dict:
        """获取鼠标位置"""
        x, y = pyautogui.position()
        return {'success': True, 'output': f'鼠标位置: ({x}, {y})'}

    def _exec_image_click(self, action: Action) -> Dict:
        """图片识别点击"""
        image_path = action.params.get('image', '')
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
            if location:
                pyautogui.click(location.x, location.y)
                return {'success': True, 'output': f'点击图片 {image_path} 在 ({location.x}, {location.y})'}
            else:
                return {'success': False, 'error': f'未找到图片: {image_path}'}
        except Exception as e:
            return {'success': False, 'error': f'图片识别失败: {e}'}

    def _exec_loop(self, action: Action) -> Dict:
        """循环执行"""
        count = action.params.get('count', 1)
        command = action.params.get('command', '')

        results = []
        for i in range(count):
            print(f"\n  [循环 {i+1}/{count}]")
            # 解析子命令
            sub_action = self.parser._parse_single(command.lower())
            if sub_action:
                result = self.execute(sub_action)
                results.append(result)
            else:
                results.append({'success': False, 'error': f'无法解析: {command}'})

        success_count = sum(1 for r in results if r.get('success'))
        return {'success': success_count == len(results), 'output': f'循环完成: {success_count}/{len(results)} 成功'}

    def _exec_wait_for_image(self, action: Action) -> Dict:
        """等待图片出现"""
        image_path = action.params.get('image', '')
        timeout = action.params.get('timeout', 30)
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                location = pyautogui.locateCenterOnScreen(image_path, confidence=0.9)
                if location:
                    return {'success': True, 'output': f'找到图片 {image_path} 在 ({location.x}, {location.y})'}
                time.sleep(0.5)
            return {'success': False, 'error': f'等待超时，未找到图片: {image_path}'}
        except Exception as e:
            return {'success': False, 'error': f'等待图片失败: {e}'}

    def _exec_activate_window(self, action: Action) -> Dict:
        """激活窗口"""
        title = action.params.get('title', '')
        try:
            import pygetwindow as gw
            window = None
            try:
                window = gw.getWindowsWithTitle(title)[0]
            except:
                for w in gw.getAllWindows():
                    if title.lower() in w.title.lower():
                        window = w
                        break
            if window:
                window.activate()
                return {'success': True, 'output': f'激活窗口: {window.title}'}
            else:
                return {'success': False, 'error': f'未找到窗口: {title}'}
        except Exception as e:
            return {'success': False, 'error': f'激活窗口失败: {e}'}

    def _exec_list_windows(self, action: Action) -> Dict:
        """列出所有窗口"""
        try:
            import pygetwindow as gw
            windows = [w for w in gw.getAllWindows() if w.title]
            print("\n[窗口列表]")
            for i, w in enumerate(windows[:20], 1):
                print(f"  {i}. {w.title}")
            return {'success': True, 'output': f'找到 {len(windows)} 个窗口'}
        except Exception as e:
            return {'success': False, 'error': f'获取窗口列表失败: {e}'}

    def _exec_minimize_window(self, action: Action) -> Dict:
        """最小化窗口"""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                window.minimize()
                return {'success': True, 'output': '最小化当前窗口'}
            else:
                return {'success': False, 'error': '没有活动窗口'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_maximize_window(self, action: Action) -> Dict:
        """最大化窗口"""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                window.maximize()
                return {'success': True, 'output': '最大化当前窗口'}
            else:
                return {'success': False, 'error': '没有活动窗口'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_get_screen_size(self, action: Action) -> Dict:
        """获取屏幕尺寸"""
        width, height = pyautogui.size()
        return {'success': True, 'output': f'屏幕尺寸: {width}x{height}'}

    def _exec_get_pixel_color(self, action: Action) -> Dict:
        """获取像素颜色"""
        x = action.params.get('x', 0)
        y = action.params.get('y', 0)
        try:
            color = pyautogui.pixel(x, y)
            hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
            return {'success': True, 'output': f'位置 ({x}, {y}) 的颜色: RGB{color} / {hex_color}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _exec_random_click(self, action: Action) -> Dict:
        """随机点击"""
        import random
        width, height = pyautogui.size()
        x = random.randint(100, width - 100)
        y = random.randint(100, height - 100)
        pyautogui.click(x, y)
        return {'success': True, 'output': f'随机点击: ({x}, {y})'}

    def _exec_beep(self, action: Action) -> Dict:
        """蜂鸣提示"""
        try:
            import winsound
            winsound.Beep(1000, 500)
            return {'success': True, 'output': '蜂鸣提示'}
        except:
            return {'success': False, 'error': '蜂鸣失败'}

    def _exec_notify(self, action: Action) -> Dict:
        """系统通知"""
        message = action.params.get('message', 'GodHand 通知')
        try:
            from ctypes import windll
            windll.user32.MessageBoxW(0, message, "GodHand", 0x40)
            return {'success': True, 'output': f'显示通知: {message}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


class Config:
    """配置管理系统"""

    def __init__(self, config_file="godhand_config.json"):
        self.config_file = config_file
        self.data = self._load()

    def _load(self) -> Dict:
        """加载配置"""
        default_config = {
            'click_delay': 0.1,
            'type_interval': 0.01,
            'move_duration': 0.5,
            'screenshot_dir': './screenshots',
            'log_enabled': True,
            'log_file': 'godhand.log',
            'auto_save_screenshot': True,
            'default_wait': 2.0,
            'window_timeout': 10,
            'image_confidence': 0.9,
            'aliases': {
                'calc': '计算器',
                'notepad': '记事本',
                'paint': '画图',
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    default_config.update(json.load(f))
            except Exception as e:
                print(f"[WARN] 配置文件加载失败: {e}")

        return default_config

    def save(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 配置保存失败: {e}")

    def get(self, key, default=None):
        """获取配置项"""
        return self.data.get(key, default)

    def set(self, key, value):
        """设置配置项"""
        self.data[key] = value
        self.save()


class Logger:
    """日志系统"""

    def __init__(self, log_file='godhand.log', enabled=True):
        self.log_file = log_file
        self.enabled = enabled

    def log(self, level, message):
        """记录日志"""
        if not self.enabled:
            return

        from datetime import datetime
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[ERROR] 日志写入失败: {e}")

    def info(self, message):
        self.log('INFO', message)

    def error(self, message):
        self.log('ERROR', message)

    def debug(self, message):
        self.log('DEBUG', message)


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self.tasks = []
        self.running = False

    def add(self, time_str: str, command: str):
        """添加定时任务 (time_str: HH:MM)"""
        self.tasks.append({'time': time_str, 'command': command, 'done': False})
        print(f"[调度] 添加任务 {time_str}: {command}")

    def run(self, parser, executor):
        """运行调度器"""
        import datetime
        self.running = True
        print("[调度] 任务调度器启动...")

        while self.running:
            now = datetime.datetime.now().strftime('%H:%M')
            for task in self.tasks:
                if task['time'] == now and not task['done']:
                    print(f"\n[调度] 执行任务: {task['command']}")
                    actions = parser.parse(task['command'])
                    if actions:
                        for action in actions:
                            executor.execute(action)
                    task['done'] = True

            # 重置已完成的任务（下一分钟）
            if now.endswith(':00'):
                for task in self.tasks:
                    task['done'] = False

            time.sleep(1)

    def stop(self):
        """停止调度器"""
        self.running = False


class Recorder:
    """录制和回放系统"""

    def __init__(self):
        self.recording = []
        self.is_recording = False
        self.record_file = "recorded_script.json"

    def start_recording(self):
        """开始录制"""
        self.recording = []
        self.is_recording = True
        print("[录制] 开始录制，输入 'stop' 停止")
        return True

    def stop_recording(self, filename=None):
        """停止录制并保存"""
        self.is_recording = False
        if filename:
            self.record_file = filename

        # 保存到文件
        import json
        try:
            with open(self.record_file, 'w', encoding='utf-8') as f:
                json.dump(self.recording, f, ensure_ascii=False, indent=2)
            print(f"[录制] 已保存 {len(self.recording)} 个动作到 {self.record_file}")
            return True
        except Exception as e:
            print(f"[ERROR] 保存失败: {e}")
            return False

    def add_action(self, command: str):
        """添加动作到录制"""
        if self.is_recording:
            self.recording.append({
                'command': command,
                'timestamp': time.time()
            })

    def load_script(self, filename=None):
        """加载录制的脚本"""
        if filename:
            self.record_file = filename

        import json
        try:
            with open(self.record_file, 'r', encoding='utf-8') as f:
                self.recording = json.load(f)
            return self.recording
        except Exception as e:
            print(f"[ERROR] 加载失败: {e}")
            return []

    def play(self, executor, parser, delay=1.0):
        """回放录制的脚本"""
        if not self.recording:
            print("[回放] 没有录制内容")
            return False

        print(f"[回放] 开始回放 {len(self.recording)} 个动作，间隔 {delay} 秒")

        for i, item in enumerate(self.recording, 1):
            command = item['command']
            print(f"\n[{i}/{len(self.recording)}] 执行: {command}")

            actions = parser.parse(command)
            if actions:
                for action in actions:
                    executor.execute(action)
            else:
                print(f"  [ERROR] 无法解析: {command}")

            if i < len(self.recording):
                time.sleep(delay)

        print("\n[回放] 完成")
        return True


class GodHandCLI:
    """GodHand 命令行界面"""

    def __init__(self):
        self.config = Config()
        self.logger = Logger(
            self.config.get('log_file'),
            self.config.get('log_enabled')
        )
        self.parser = SimpleParser()
        self.executor = ActionExecutor()
        self.executor.parser = self.parser  # 用于循环执行
        self.executor.config = self.config  # 配置
        self.recorder = Recorder()
        self.scheduler = TaskScheduler()
        self.running = True

        # 确保截图目录存在
        screenshot_dir = self.config.get('screenshot_dir')
        if screenshot_dir and not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        print("=" * 60)
        print("GodHand CLI v3.2 - 专业GUI自动化工具")
        print("=" * 60)
        self.logger.info("GodHand CLI 启动")

        # 加载别名
        aliases = self.config.get('aliases', {})
        self.parser.app_map.update(aliases)
        if not HAS_PYAUTOGUI:
            print("\n[WARN] pyautogui 未安装，部分功能不可用")
            print("安装: pip install pyautogui pyperclip pygetwindow opencv-python\n")
        print("\n基础指令:")
        print("  打开 [应用名]        - 打开应用程序")
        print("  关闭 [应用名]        - 关闭应用程序")
        print("  打开 XX 然后 YY      - 复合指令（支持多个然后）")
        print("  点击 X, Y           - 点击坐标")
        print("  双击                - 双击鼠标")
        print("  右键                - 右键点击")
        print("  输入 [文字]         - 输入文字")
        print("  按 [键名]           - 按键")
        print("  快捷键 ctrl+a       - 快捷键组合")
        print("  移动 X, Y           - 移动鼠标")
        print("  等待 [秒数]         - 等待")
        print("  截图                - 屏幕截图")
        print("\n窗口管理:")
        print("  列出窗口            - 显示所有窗口")
        print("  激活 [窗口名]       - 激活指定窗口")
        print("  最小化              - 最小化当前窗口")
        print("  最大化              - 最大化当前窗口")
        print("\n高级功能:")
        print("  搜索 [关键词]       - 浏览器搜索")
        print("  打开 [网址]         - 打开网页")
        print("  创建文件 [路径]     - 创建文件")
        print("  删除文件 [路径]     - 删除文件")
        print("  创建文件夹 [路径]   - 创建目录")
        print("  复制 / 粘贴 / 全选  - 剪贴板操作")
        print("  获取鼠标位置        - 显示当前鼠标坐标")
        print("  获取屏幕尺寸        - 显示分辨率")
        print("  获取颜色 X, Y       - 获取像素颜色")
        print("  点击图片 [路径]     - 图片识别并点击")
        print("  等待图片 [路径]     - 等待图片出现")
        print("  循环 N次 [指令]     - 重复执行指令")
        print("  随机点击            - 随机位置点击")
        print("  蜂鸣                - 播放提示音")
        print("  通知 [消息]         - 显示系统通知")
        print("\n其他命令: help, exit, quit, record, play, script")
        print("=" * 60)

    def run(self):
        """运行主循环"""
        while self.running:
            try:
                # 获取输入
                prompt = "\n[录制中] GodHand> " if self.recorder.is_recording else "\nGodHand> "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # 录制模式下，记录所有输入
                if self.recorder.is_recording:
                    if user_input.lower() == 'stop':
                        self.recorder.stop_recording()
                        continue
                    else:
                        self.recorder.add_action(user_input)

                # 处理特殊命令
                if user_input.lower() in ['exit', 'quit', 'q']:
                    if self.recorder.is_recording:
                        self.recorder.stop_recording()
                    print("再见!")
                    break

                if user_input.lower() in ['help', 'h', '?']:
                    self.show_help()
                    continue

                # 录制命令
                if user_input.lower() == 'record':
                    self.recorder.start_recording()
                    continue

                if user_input.lower().startswith('record '):
                    filename = user_input[7:].strip()
                    self.recorder.start_recording()
                    self.recorder.record_file = filename
                    continue

                # 回放命令
                if user_input.lower() == 'play':
                    self.recorder.load_script()
                    self.recorder.play(self.executor, self.parser)
                    continue

                if user_input.lower().startswith('play '):
                    filename = user_input[5:].strip()
                    self.recorder.load_script(filename)
                    self.recorder.play(self.executor, self.parser)
                    continue

                # 脚本执行命令
                if user_input.lower().startswith('script '):
                    script_file = user_input[7:].strip()
                    self._run_script(script_file)
                    continue

                # 配置命令
                if user_input.lower().startswith('config '):
                    parts = user_input[7:].strip().split(' ', 1)
                    if len(parts) == 2:
                        key, value = parts
                        self.config.set(key, value)
                        print(f"[配置] {key} = {value}")
                    else:
                        print("[配置] 当前配置:")
                        for k, v in self.config.data.items():
                            print(f"  {k}: {v}")
                    continue

                # 定时任务命令
                if user_input.lower().startswith('schedule '):
                    parts = user_input[9:].strip().split(' ', 1)
                    if len(parts) == 2:
                        time_str, cmd = parts
                        self.scheduler.add(time_str, cmd)
                    continue

                if user_input.lower() == 'scheduler start':
                    import threading
                    self.scheduler.running = True
                    t = threading.Thread(target=self.scheduler.run, args=(self.parser, self.executor))
                    t.daemon = True
                    t.start()
                    continue

                if user_input.lower() == 'scheduler stop':
                    self.scheduler.stop()
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

    def _run_script(self, filename: str):
        """执行脚本文件"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"\n[脚本] 执行 {filename}，共 {len(lines)} 行")
            print("=" * 60)

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                print(f"\n[{i}] {line}")
                actions = self.parser.parse(line)

                if actions:
                    for action in actions:
                        self.executor.execute(action)
                else:
                    print(f"  [ERROR] 无法解析: {line}")

            print(f"\n{'='*60}")
            print("[脚本] 执行完成")

        except Exception as e:
            print(f"[ERROR] 脚本执行失败: {e}")

    def show_help(self):
        """显示帮助"""
        print("\n" + "=" * 60)
        print("GodHand CLI v3.2 - 使用帮助")
        print("=" * 60)
        print("\n基础示例:")
        print("  打开记事本")
        print("  打开记事本 然后输入Hello World 然后按回车")
        print("  点击 500, 500")
        print("  双击")
        print("  输入 你好世界")
        print("  按 enter")
        print("  快捷键 ctrl+s")
        print("  等待 3")
        print("  截图")
        print("  获取鼠标位置")
        print("  复制 / 粘贴")
        print("  循环 3次 截图")
        print("\n录制与回放:")
        print("  record            - 开始录制")
        print("  record my.json    - 录制到指定文件")
        print("  stop              - 停止录制")
        print("  play              - 回放录制")
        print("  play my.json      - 回放指定脚本")
        print("\n脚本执行:")
        print("  script myscript.txt - 执行脚本文件")
        print("  (脚本文件每行一个命令，#开头为注释)")
        print("\n配置管理:")
        print("  config            - 显示当前配置")
        print("  config key value  - 设置配置项")
        print("\n定时任务:")
        print("  schedule HH:MM command  - 添加定时任务")
        print("  scheduler start     - 启动调度器")
        print("  scheduler stop      - 停止调度器")
        print("\n高级示例:")
        print("  打开计算器 然后输入1 然后按加号 然后输入1 然后按等于")
        print("  关闭 计算器")
        print("  点击图片 button.png")
        print("  等待图片 loading.png")
        print("  列出窗口")
        print("  激活 记事本")
        print("  通知 任务完成")
        print("=" * 60)


def main():
    """主入口"""
    cli = GodHandCLI()
    cli.run()


if __name__ == "__main__":
    main()
