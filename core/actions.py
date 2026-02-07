#!/usr/bin/env python3
"""Actions - 动作定义与执行器"""

import os
import sys
import time
import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import logging

# Windows 特定功能
if sys.platform == 'win32':
    import ctypes
    try:
        import win32gui
        import win32con
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
else:
    HAS_WIN32 = False

# 图像处理
try:
    import pyautogui
    import pyperclip
    HAS_PYAUTO = True
except ImportError:
    HAS_PYAUTO = False

try:
    from PIL import Image, ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """动作类型枚举"""
    # 应用控制
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    FOCUS_WINDOW = "focus_window"
    MINIMIZE_WINDOW = "minimize_window"
    MAXIMIZE_WINDOW = "maximize_window"
    LIST_WINDOWS = "list_windows"
    
    # 鼠标操作
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_RIGHT_CLICK = "mouse_right_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    
    # 键盘操作
    TYPE_TEXT = "type_text"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    
    # 文件操作
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    FILE_COPY = "file_copy"
    FILE_MOVE = "file_move"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    DIR_CREATE = "dir_create"
    DIR_DELETE = "dir_delete"
    DIR_LIST = "dir_list"
    
    # 系统操作
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_RESTART = "system_restart"
    SYSTEM_SLEEP = "system_sleep"
    SYSTEM_LOCK = "system_lock"
    SYSTEM_VOLUME = "system_volume"
    SYSTEM_SCREENSHOT = "system_screenshot"
    SYSTEM_CLIPBOARD = "system_clipboard"
    
    # 浏览器
    BROWSER_OPEN = "browser_open"
    BROWSER_SEARCH = "browser_search"
    
    # 流程控制
    WAIT = "wait"
    
    # 其他
    UNKNOWN = "unknown"


@dataclass
class Action:
    """动作定义"""
    type: ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type.value,
            'params': self.params,
            'description': self.description,
            'confidence': self.confidence
        }


class ActionExecutor:
    """动作执行器"""
    
    def __init__(self):
        self.results: List[Dict] = []
    
    def execute(self, action: Action) -> Dict:
        """执行单个动作"""
        start_time = time.time()
        
        result = {
            'success': False,
            'action': action.to_dict(),
            'output': '',
            'error': None,
            'execution_time': 0.0
        }
        
        # 简单的动作处理
        handlers = {
            ActionType.OPEN_APP: self._exec_open_app,
            ActionType.TYPE_TEXT: self._exec_type_text,
            ActionType.PRESS_KEY: self._exec_press_key,
            ActionType.HOTKEY: self._exec_hotkey,
            ActionType.WAIT: self._exec_wait,
            ActionType.MOUSE_CLICK: self._exec_mouse_click,
            ActionType.MOUSE_MOVE: self._exec_mouse_move,
            ActionType.SYSTEM_SCREENSHOT: self._exec_screenshot,
            ActionType.BROWSER_SEARCH: self._exec_browser_search,
        }
        
        try:
            handler = handlers.get(action.type)
            if handler:
                result = handler(action, result)
            else:
                result['output'] = f"演示模式: {action.description}"
                result['success'] = True
        except Exception as e:
            result['error'] = str(e)
        
        result['execution_time'] = time.time() - start_time
        return result
    
    def execute_batch(self, actions: List[Action]) -> List[Dict]:
        """批量执行"""
        return [self.execute(a) for a in actions]
    
    def _exec_open_app(self, action: Action, result: Dict) -> Dict:
        app = action.params.get('app', '')
        try:
            if sys.platform == 'win32':
                app_map = {
                    '计算器': 'calc.exe',
                    '记事本': 'notepad.exe',
                    '画图': 'mspaint.exe',
                    'cmd': 'cmd.exe',
                    '任务管理器': 'taskmgr.exe',
                }
                cmd = app_map.get(app, app)
                subprocess.Popen(f'start "" {cmd}', shell=True)
            result['success'] = True
            result['output'] = f"已启动: {app}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_type_text(self, action: Action, result: Dict) -> Dict:
        if not HAS_PYAUTO:
            result['error'] = 'pyautogui 未安装'
            return result
        try:
            text = action.params.get('text', '')
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            result['success'] = True
            result['output'] = f"已输入: {text[:30]}{'...' if len(text) > 30 else ''}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_press_key(self, action: Action, result: Dict) -> Dict:
        if not HAS_PYAUTO:
            result['error'] = 'pyautogui 未安装'
            return result
        try:
            key = action.params.get('key', '')
            pyautogui.press(key)
            result['success'] = True
            result['output'] = f"按键: {key}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_hotkey(self, action: Action, result: Dict) -> Dict:
        if not HAS_PYAUTO:
            result['error'] = 'pyautogui 未安装'
            return result
        try:
            keys = action.params.get('keys', [])
            pyautogui.hotkey(*keys)
            result['success'] = True
            result['output'] = f"快捷键: {'+'.join(keys)}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_wait(self, action: Action, result: Dict) -> Dict:
        try:
            seconds = action.params.get('seconds', 1.0)
            time.sleep(seconds)
            result['success'] = True
            result['output'] = f"等待 {seconds} 秒"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_mouse_click(self, action: Action, result: Dict) -> Dict:
        if not HAS_PYAUTO:
            result['error'] = 'pyautogui 未安装'
            return result
        try:
            x = action.params.get('x')
            y = action.params.get('y')
            if x is not None and y is not None:
                pyautogui.click(x, y)
                result['output'] = f"点击 ({x}, {y})"
            else:
                pyautogui.click()
                result['output'] = "点击"
            result['success'] = True
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_mouse_move(self, action: Action, result: Dict) -> Dict:
        if not HAS_PYAUTO:
            result['error'] = 'pyautogui 未安装'
            return result
        try:
            x = action.params.get('x', 0)
            y = action.params.get('y', 0)
            pyautogui.moveTo(x, y, duration=0.5)
            result['success'] = True
            result['output'] = f"移动鼠标到 ({x}, {y})"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_screenshot(self, action: Action, result: Dict) -> Dict:
        try:
            if HAS_PIL:
                screenshot = ImageGrab.grab()
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot.save(filename)
                result['success'] = True
                result['output'] = f"截图保存: {filename}"
            else:
                result['error'] = 'PIL 未安装'
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _exec_browser_search(self, action: Action, result: Dict) -> Dict:
        try:
            query = action.params.get('query', '')
            encoded = urllib.parse.quote(query)
            url = f'https://www.bing.com/search?q={encoded}'
            subprocess.Popen(f'start msedge "{url}"', shell=True)
            result['success'] = True
            result['output'] = f"搜索: {query}"
        except Exception as e:
            result['error'] = str(e)
        return result


if __name__ == "__main__":
    print("Actions module ready!")
