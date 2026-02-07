#!/usr/bin/env python3
"""
Platform Adapters 🖥️ - 跨平台适配器

为 GodHand 提供统一的跨平台 GUI 自动化接口。
支持 Windows、macOS、Linux。

Author: GodHand Team
Version: 1.0.0
"""

import sys
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import time


@dataclass
class WindowInfo:
    """窗口信息"""
    handle: Any              # 平台相关的窗口句柄
    title: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    is_active: bool
    process_name: str = ""

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "position": self.position,
            "size": self.size,
            "is_active": self.is_active,
            "process_name": self.process_name
        }


@dataclass
class ScreenInfo:
    """屏幕信息"""
    width: int
    height: int
    scale_factor: float = 1.0  # 用于 Retina/HiDPI 屏幕


class PlatformAdapter(ABC):
    """
    平台适配器抽象基类

    定义所有平台需要实现的统一接口。
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass

    @abstractmethod
    def take_screenshot(self, region: Tuple[int, int, int, int] = None) -> Any:
        """
        截取屏幕

        Args:
            region: (x, y, width, height) 可选区域

        Returns:
            PIL Image 或 numpy array
        """
        pass

    @abstractmethod
    def get_mouse_position(self) -> Tuple[int, int]:
        """获取鼠标当前位置"""
        pass

    @abstractmethod
    def move_mouse(self, x: int, y: int, duration: float = 0.0):
        """移动鼠标到指定位置"""
        pass

    @abstractmethod
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """
        点击鼠标

        Args:
            x, y: 坐标
            button: "left", "right", "middle"
            clicks: 点击次数
        """
        pass

    @abstractmethod
    def scroll(self, amount: int, x: int = None, y: int = None):
        """
        滚动鼠标

        Args:
            amount: 正数向上，负数向下
            x, y: 可选的滚动位置
        """
        pass

    @abstractmethod
    def type_text(self, text: str, interval: float = 0.01):
        """输入文本"""
        pass

    @abstractmethod
    def press_key(self, key: str):
        """按下单个按键"""
        pass

    @abstractmethod
    def hotkey(self, *keys: str):
        """按下组合键"""
        pass

    @abstractmethod
    def get_window_list(self) -> List[WindowInfo]:
        """获取所有窗口列表"""
        pass

    @abstractmethod
    def get_active_window(self) -> Optional[WindowInfo]:
        """获取当前活动窗口"""
        pass

    @abstractmethod
    def activate_window(self, window_handle: Any) -> bool:
        """激活指定窗口"""
        pass

    @abstractmethod
    def find_window(self, title_pattern: str) -> Optional[WindowInfo]:
        """根据标题查找窗口"""
        pass

    @abstractmethod
    def get_screen_info(self) -> ScreenInfo:
        """获取屏幕信息"""
        pass

    @abstractmethod
    def open_application(self, app_name: str) -> bool:
        """
        打开应用程序

        Args:
            app_name: 应用名称或路径
        """
        pass

    @abstractmethod
    def execute_shell_command(self, command: str, wait: bool = False) -> tuple:
        """
        执行 shell 命令

        Returns:
            (returncode, stdout, stderr)
        """
        pass

    def delay(self, seconds: float):
        """延迟"""
        time.sleep(seconds)


class WindowsAdapter(PlatformAdapter):
    """
    Windows 平台适配器

    使用 pyautogui + pywin32 + ctypes
    """

    def __init__(self):
        self._init_platform()

    def _init_platform(self):
        """初始化 Windows 特定模块"""
        try:
            import pyautogui
            self.pyautogui = pyautogui
            pyautogui.FAILSAFE = True  # 鼠标移到角落停止
        except ImportError:
            raise RuntimeError("pyautogui is required on Windows")

        try:
            import win32gui
            import win32con
            self.win32gui = win32gui
            self.win32con = win32con
            self._has_win32 = True
        except ImportError:
            print("[Warn] pywin32 not installed, window management limited")
            self._has_win32 = False

    @property
    def platform_name(self) -> str:
        return "Windows"

    def take_screenshot(self, region: Tuple[int, int, int, int] = None):
        if region:
            return self.pyautogui.screenshot(region=region)
        return self.pyautogui.screenshot()

    def get_mouse_position(self) -> Tuple[int, int]:
        return self.pyautogui.position()

    def move_mouse(self, x: int, y: int, duration: float = 0.0):
        self.pyautogui.moveTo(x, y, duration=duration)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        self.pyautogui.click(x, y, button=button, clicks=clicks)

    def scroll(self, amount: int, x: int = None, y: int = None):
        if x is not None and y is not None:
            self.pyautogui.scroll(amount, x, y)
        else:
            self.pyautogui.scroll(amount)

    def type_text(self, text: str, interval: float = 0.01):
        self.pyautogui.typewrite(text, interval=interval)

    def press_key(self, key: str):
        self.pyautogui.press(key)

    def hotkey(self, *keys: str):
        self.pyautogui.hotkey(*keys)

    def get_window_list(self) -> List[WindowInfo]:
        if not self._has_win32:
            return []

        windows = []

        def callback(hwnd, extra):
            if self.win32gui.IsWindowVisible(hwnd):
                title = self.win32gui.GetWindowText(hwnd)
                if title:
                    rect = self.win32gui.GetWindowRect(hwnd)
                    x, y = rect[0], rect[1]
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]

                    # 检查是否活动
                    active = self.win32gui.GetForegroundWindow() == hwnd

                    windows.append(WindowInfo(
                        handle=hwnd,
                        title=title,
                        position=(x, y),
                        size=(width, height),
                        is_active=active
                    ))
            return True

        self.win32gui.EnumWindows(callback, None)
        return windows

    def get_active_window(self) -> Optional[WindowInfo]:
        if not self._has_win32:
            return None

        hwnd = self.win32gui.GetForegroundWindow()
        if hwnd:
            title = self.win32gui.GetWindowText(hwnd)
            rect = self.win32gui.GetWindowRect(hwnd)
            return WindowInfo(
                handle=hwnd,
                title=title,
                position=(rect[0], rect[1]),
                size=(rect[2] - rect[0], rect[3] - rect[1]),
                is_active=True
            )
        return None

    def activate_window(self, window_handle) -> bool:
        if not self._has_win32:
            return False

        try:
            self.win32gui.SetForegroundWindow(window_handle)
            return True
        except Exception as e:
            print(f"[Error] Failed to activate window: {e}")
            return False

    def find_window(self, title_pattern: str) -> Optional[WindowInfo]:
        windows = self.get_window_list()
        import re
        pattern = re.compile(title_pattern, re.IGNORECASE)

        for window in windows:
            if pattern.search(window.title):
                return window
        return None

    def get_screen_info(self) -> ScreenInfo:
        size = self.pyautogui.size()
        return ScreenInfo(width=size[0], height=size[1], scale_factor=1.0)

    def open_application(self, app_name: str) -> bool:
        """打开 Windows 应用"""
        # 常见应用映射
        app_map = {
            "计算器": "calc.exe",
            "记事本": "notepad.exe",
            "画图": "mspaint.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "浏览器": "msedge",
            "edge": "msedge",
            "chrome": "chrome",
            "word": "winword",
            "excel": "excel",
            "vscode": "code",
        }

        # 查找应用命令
        cmd = app_map.get(app_name, app_name)

        try:
            subprocess.Popen(cmd, shell=True)
            return True
        except Exception as e:
            print(f"[Error] Failed to open {app_name}: {e}")
            return False

    def execute_shell_command(self, command: str, wait: bool = False) -> tuple:
        try:
            if wait:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                return (result.returncode, result.stdout, result.stderr)
            else:
                subprocess.Popen(command, shell=True)
                return (0, "", "")
        except Exception as e:
            return (-1, "", str(e))


class MacOSAdapter(PlatformAdapter):
    """
    macOS 平台适配器

    使用 AppleScript + pyautogui
    """

    def __init__(self):
        self._init_platform()

    def _init_platform(self):
        """初始化 macOS 特定模块"""
        try:
            import pyautogui
            self.pyautogui = pyautogui
            pyautogui.FAILSAFE = True
        except ImportError:
            raise RuntimeError("pyautogui is required on macOS")

    @property
    def platform_name(self) -> str:
        return "macOS"

    def take_screenshot(self, region: Tuple[int, int, int, int] = None):
        if region:
            return self.pyautogui.screenshot(region=region)
        return self.pyautogui.screenshot()

    def get_mouse_position(self) -> Tuple[int, int]:
        return self.pyautogui.position()

    def move_mouse(self, x: int, y: int, duration: float = 0.0):
        self.pyautogui.moveTo(x, y, duration=duration)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        self.pyautogui.click(x, y, button=button, clicks=clicks)

    def scroll(self, amount: int, x: int = None, y: int = None):
        if x is not None and y is not None:
            self.pyautogui.scroll(amount, x, y)
        else:
            self.pyautogui.scroll(amount)

    def type_text(self, text: str, interval: float = 0.01):
        self.pyautogui.typewrite(text, interval=interval)

    def press_key(self, key: str):
        self.pyautogui.press(key)

    def hotkey(self, *keys: str):
        self.pyautogui.hotkey(*keys)

    def get_window_list(self) -> List[WindowInfo]:
        """使用 AppleScript 获取窗口列表"""
        try:
            script = '''
            tell application "System Events"
                set windowList to {}
                repeat with proc in (get processes whose background only is false)
                    set procName to name of proc
                    repeat with win in (get windows of proc)
                        set winName to name of win
                        set winPos to position of win
                        set winSize to size of win
                        set end of windowList to {procName, winName, winPos, winSize}
                    end repeat
                end repeat
                return windowList
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )

            # 解析结果（简化处理）
            windows = []
            # TODO: 解析 AppleScript 输出
            return windows

        except Exception as e:
            print(f"[Error] Failed to get window list: {e}")
            return []

    def get_active_window(self) -> Optional[WindowInfo]:
        """获取活动窗口"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set frontAppName to name of frontApp
                set win to first window of frontApp
                set winName to name of win
                set winPos to position of win
                set winSize to size of win
                return {frontAppName, winName, winPos, winSize}
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # 解析结果
                # TODO: 解析输出
                return None
            return None

        except Exception as e:
            print(f"[Error] Failed to get active window: {e}")
            return None

    def activate_window(self, window_handle: Any) -> bool:
        """激活窗口"""
        # macOS 使用 window_handle 作为标题
        try:
            script = f'''
            tell application "System Events"
                tell process "{window_handle}"
                    set frontmost to true
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception as e:
            print(f"[Error] Failed to activate window: {e}")
            return False

    def find_window(self, title_pattern: str) -> Optional[WindowInfo]:
        """查找窗口"""
        windows = self.get_window_list()
        import re
        pattern = re.compile(title_pattern, re.IGNORECASE)

        for window in windows:
            if pattern.search(window.title):
                return window
        return None

    def get_screen_info(self) -> ScreenInfo:
        """获取屏幕信息"""
        size = self.pyautogui.size()
        # macOS 可能有 Retina 屏幕
        return ScreenInfo(width=size[0], height=size[1], scale_factor=2.0)

    def open_application(self, app_name: str) -> bool:
        """打开 macOS 应用"""
        app_map = {
            "计算器": "Calculator",
            "文本编辑": "TextEdit",
            "终端": "Terminal",
            "safari": "Safari",
            "chrome": "Google Chrome",
            "vscode": "Visual Studio Code",
        }

        app = app_map.get(app_name, app_name)

        try:
            script = f'tell application "{app}" to activate'
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception as e:
            print(f"[Error] Failed to open {app_name}: {e}")
            return False

    def execute_shell_command(self, command: str, wait: bool = False) -> tuple:
        """执行 shell 命令"""
        try:
            if wait:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    executable="/bin/bash"
                )
                return (result.returncode, result.stdout, result.stderr)
            else:
                subprocess.Popen(command, shell=True, executable="/bin/bash")
                return (0, "", "")
        except Exception as e:
            return (-1, "", str(e))


class LinuxAdapter(PlatformAdapter):
    """
    Linux 平台适配器

    使用 X11 (xlib) 或 Wayland
    """

    def __init__(self):
        self.display_server = self._detect_display_server()
        self._init_platform()

    def _detect_display_server(self) -> str:
        """检测显示服务器类型"""
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        elif os.environ.get("DISPLAY"):
            return "x11"
        return "unknown"

    def _init_platform(self):
        """初始化 Linux 特定模块"""
        try:
            import pyautogui
            self.pyautogui = pyautogui
            pyautogui.FAILSAFE = True
        except ImportError:
            raise RuntimeError("pyautogui is required on Linux")

        if self.display_server == "x11":
            try:
                import Xlib
                self.Xlib = Xlib
                self._has_xlib = True
            except ImportError:
                print("[Warn] python-xlib not installed, window management limited")
                self._has_xlib = False
        else:
            self._has_xlib = False

    @property
    def platform_name(self) -> str:
        return f"Linux ({self.display_server})"

    def take_screenshot(self, region: Tuple[int, int, int, int] = None):
        if region:
            return self.pyautogui.screenshot(region=region)
        return self.pyautogui.screenshot()

    def get_mouse_position(self) -> Tuple[int, int]:
        return self.pyautogui.position()

    def move_mouse(self, x: int, y: int, duration: float = 0.0):
        self.pyautogui.moveTo(x, y, duration=duration)

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        self.pyautogui.click(x, y, button=button, clicks=clicks)

    def scroll(self, amount: int, x: int = None, y: int = None):
        if x is not None and y is not None:
            self.pyautogui.scroll(amount, x, y)
        else:
            self.pyautogui.scroll(amount)

    def type_text(self, text: str, interval: float = 0.01):
        self.pyautogui.typewrite(text, interval=interval)

    def press_key(self, key: str):
        self.pyautogui.press(key)

    def hotkey(self, *keys: str):
        self.pyautogui.hotkey(*keys)

    def get_window_list(self) -> List[WindowInfo]:
        """获取窗口列表"""
        if self.display_server == "x11" and self._has_xlib:
            return self._get_x11_window_list()

        # 使用 wmctrl 作为备选
        return self._get_window_list_wmctrl()

    def _get_x11_window_list(self) -> List[WindowInfo]:
        """使用 Xlib 获取窗口列表"""
        try:
            display = self.Xlib.display.Display()
            root = display.screen().root

            window_ids = root.get_full_property(
                display.intern_atom('_NET_CLIENT_LIST'),
                self.Xlib.X.AnyPropertyType
            ).value

            windows = []
            for window_id in window_ids:
                window = display.create_resource_object('window', window_id)

                try:
                    name = window.get_wm_name()
                    geom = window.get_geometry()

                    windows.append(WindowInfo(
                        handle=window_id,
                        title=name or "",
                        position=(geom.x, geom.y),
                        size=(geom.width, geom.height),
                        is_active=False  # TODO: 检查活动状态
                    ))
                except:
                    pass

            return windows

        except Exception as e:
            print(f"[Error] Failed to get window list: {e}")
            return []

    def _get_window_list_wmctrl(self) -> List[WindowInfo]:
        """使用 wmctrl 获取窗口列表"""
        try:
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True
            )

            windows = []
            for line in result.stdout.split('\n'):
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    window_id = int(parts[0], 16)
                    title = parts[3]
                    windows.append(WindowInfo(
                        handle=window_id,
                        title=title,
                        position=(0, 0),  # wmctrl -l 不返回位置
                        size=(0, 0),
                        is_active=False
                    ))

            return windows

        except Exception as e:
            print(f"[Error] Failed to get window list: {e}")
            return []

    def get_active_window(self) -> Optional[WindowInfo]:
        """获取活动窗口"""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                title = result.stdout.strip()
                return WindowInfo(
                    handle=None,
                    title=title,
                    position=(0, 0),
                    size=(0, 0),
                    is_active=True
                )
            return None

        except Exception as e:
            print(f"[Error] Failed to get active window: {e}")
            return None

    def activate_window(self, window_handle: Any) -> bool:
        """激活窗口"""
        try:
            subprocess.run(
                ["xdotool", "windowactivate", str(window_handle)],
                check=True
            )
            return True
        except Exception as e:
            print(f"[Error] Failed to activate window: {e}")
            return False

    def find_window(self, title_pattern: str) -> Optional[WindowInfo]:
        """查找窗口"""
        windows = self.get_window_list()
        import re
        pattern = re.compile(title_pattern, re.IGNORECASE)

        for window in windows:
            if pattern.search(window.title):
                return window
        return None

    def get_screen_info(self) -> ScreenInfo:
        """获取屏幕信息"""
        size = self.pyautogui.size()
        return ScreenInfo(width=size[0], height=size[1], scale_factor=1.0)

    def open_application(self, app_name: str) -> bool:
        """打开 Linux 应用"""
        try:
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[Error] Failed to open {app_name}: {e}")
            return False

    def execute_shell_command(self, command: str, wait: bool = False) -> tuple:
        """执行 shell 命令"""
        try:
            if wait:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    executable="/bin/bash"
                )
                return (result.returncode, result.stdout, result.stderr)
            else:
                subprocess.Popen(command, shell=True, executable="/bin/bash")
                return (0, "", "")
        except Exception as e:
            return (-1, "", str(e))


class PlatformAdapterFactory:
    """
    平台适配器工厂

    自动检测当前平台并返回相应的适配器。
    """

    _instance: Optional[PlatformAdapter] = None

    @classmethod
    def get_adapter(cls) -> PlatformAdapter:
        """
        获取当前平台的适配器（单例）
        """
        if cls._instance is None:
            cls._instance = cls._create_adapter()
        return cls._instance

    @classmethod
    def _create_adapter(cls) -> PlatformAdapter:
        """创建适配器"""
        system = sys.platform

        if system == "win32":
            print("[PlatformAdapter] 使用 Windows 适配器")
            return WindowsAdapter()
        elif system == "darwin":
            print("[PlatformAdapter] 使用 macOS 适配器")
            return MacOSAdapter()
        elif system == "linux":
            print("[PlatformAdapter] 使用 Linux 适配器")
            return LinuxAdapter()
        else:
            raise RuntimeError(f"不支持的平台: {system}")

    @classmethod
    def reset(cls):
        """重置适配器（用于测试）"""
        cls._instance = None


# 便捷函数
def get_platform_adapter() -> PlatformAdapter:
    """获取平台适配器"""
    return PlatformAdapterFactory.get_adapter()


def take_screenshot(region: Tuple[int, int, int, int] = None):
    """便捷截图"""
    return get_platform_adapter().take_screenshot(region)


def get_mouse_pos() -> Tuple[int, int]:
    """便捷获取鼠标位置"""
    return get_platform_adapter().get_mouse_position()


def move_mouse(x: int, y: int, duration: float = 0.0):
    """便捷移动鼠标"""
    return get_platform_adapter().move_mouse(x, y, duration)


def click(x: int, y: int, button: str = "left"):
    """便捷点击"""
    return get_platform_adapter().click(x, y, button)


def type_text(text: str):
    """便捷输入文本"""
    return get_platform_adapter().type_text(text)


def press(key: str):
    """便捷按键"""
    return get_platform_adapter().press_key(key)


def hotkey(*keys: str):
    """便捷组合键"""
    return get_platform_adapter().hotkey(*keys)


if __name__ == "__main__":
    # 测试适配器
    adapter = get_platform_adapter()

    print(f"\n平台: {adapter.platform_name}")
    print("=" * 50)

    # 屏幕信息
    screen = adapter.get_screen_info()
    print(f"屏幕尺寸: {screen.width}x{screen.height}")

    # 鼠标位置
    pos = adapter.get_mouse_position()
    print(f"鼠标位置: {pos}")

    # 窗口列表
    print("\n窗口列表:")
    windows = adapter.get_window_list()
    for i, win in enumerate(windows[:10]):
        print(f"  {i+1}. {win.title[:50]} ({win.size[0]}x{win.size[1]})")

    # 活动窗口
    active = adapter.get_active_window()
    if active:
        print(f"\n活动窗口: {active.title}")
