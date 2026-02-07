#!/usr/bin/env python3
"""Advanced Parser - 高级指令解析器"""

import re
from typing import List, Optional
from actions import Action, ActionType


class AdvancedParser:
    """高级自然语言指令解析器 - 支持复合指令"""

    def __init__(self):
        self.app_map = {
            '计算器': 'calc.exe',
            '记事本': 'notepad.exe',
            '画图': 'mspaint.exe',
            'cmd': 'cmd.exe',
            '命令行': 'cmd.exe',
            'powershell': 'powershell.exe',
            '任务管理器': 'taskmgr.exe',
            '设置': 'ms-settings:',
            '浏览器': 'msedge',
            'edge': 'msedge',
            'chrome': 'chrome',
        }

        self.key_map = {
            '回车': 'enter', 'enter': 'enter',
            '空格': 'space', 'space': 'space',
            '退格': 'backspace', 'backspace': 'backspace',
            '删除': 'delete', 'delete': 'delete', 'del': 'delete',
            'esc': 'escape', 'escape': 'escape',
            '上': 'up', '下': 'down', '左': 'left', '右': 'right',
            'tab': 'tab',
            'ctrl': 'ctrl', 'control': 'ctrl',
            'alt': 'alt',
            'shift': 'shift',
        }

    def parse(self, instruction: str) -> List[Action]:
        """解析指令，返回动作列表"""
        instruction = instruction.strip()
        if not instruction:
            return []

        # 尝试解析复合指令
        composite = self._parse_composite(instruction)
        if composite:
            return composite

        # 尝试解析单一指令
        action = self._parse_single(instruction)
        if action:
            return [action]

        return []

    def _parse_composite(self, instruction: str) -> Optional[List[Action]]:
        """解析复合指令（包含多个动作的指令）"""
        actions = []

        # 模式1: 打开/启动/运行 X 然后/再/接着 做Y
        # 示例：打开记事本 然后输入Hello World
        pattern1 = r'(?:打开|启动|运行)\s*(.+?)\s*(?:然后|再|接着)\s*(.+)'
        match = re.search(pattern1, instruction, re.IGNORECASE)

        if match:
            app_part = match.group(1).strip()
            follow_up = match.group(2).strip()

            # 清理应用名称（去掉可能的后缀）
            app_name = re.sub(r'[然后|再|接着]$', '', app_part).strip()

            actions.append(Action(
                type=ActionType.OPEN_APP,
                params={'app': self._resolve_app(app_name)},
                description=f'打开应用: {app_name}',
                confidence=0.95
            ))

            actions.append(Action(
                type=ActionType.WAIT,
                params={'seconds': 2.0},
                description='等待应用启动',
                confidence=1.0
            ))

            # 解析后续动作
            follow_action = self._parse_single(follow_up)
            if follow_action:
                actions.append(follow_action)
            else:
                # 如果无法解析，作为视觉动作处理
                actions.append(Action(
                    type=ActionType.VISUAL_ACTION,
                    params={'instruction': follow_up},
                    description=f'视觉动作: {follow_up}',
                    confidence=0.7
                ))

            return actions

        # 模式2: 使用标点符号分隔的多个指令
        separators = ['，然后', ',然后', '；', ';']
        if any(sep in instruction for sep in separators):
            parts = re.split('|'.join(separators), instruction)
            for part in parts:
                part = part.strip()
                if part:
                    action = self._parse_single(part)
                    if action:
                        actions.append(action)

            if actions:
                return actions

        return None

    def _parse_single(self, instruction: str) -> Optional[Action]:
        """解析单一指令"""
        inst_lower = instruction.lower().strip()

        # 打开应用
        match = re.search(r'(?:打开|启动|运行)\s*(.+)', inst_lower)
        if match:
            app = match.group(1).strip()
            return Action(
                type=ActionType.OPEN_APP,
                params={'app': self._resolve_app(app)},
                description=f'打开应用: {app}',
                confidence=0.95
            )

        # 关闭应用
        match = re.search(r'(?:关闭|退出|杀掉)\s*(.+)', inst_lower)
        if match:
            app = match.group(1).strip()
            return Action(
                type=ActionType.CLOSE_APP,
                params={'app_name': app},
                description=f'关闭应用: {app}',
                confidence=0.9
            )

        # 最小化窗口
        if re.search(r'(?:最小化|缩小)', inst_lower):
            return Action(
                type=ActionType.MINIMIZE_WINDOW,
                params={},
                description='最小化窗口',
                confidence=1.0
            )

        # 最大化窗口
        if re.search(r'(?:最大化|全屏)', inst_lower):
            return Action(
                type=ActionType.MAXIMIZE_WINDOW,
                params={},
                description='最大化窗口',
                confidence=1.0
            )

        # 列出窗口
        if re.search(r'(?:列出|显示).*窗口', inst_lower):
            return Action(
                type=ActionType.LIST_WINDOWS,
                params={},
                description='列出所有窗口',
                confidence=1.0
            )

        # 点击坐标
        match = re.search(r'(?:点击|单击).*?(\d+)\s*,\s*(\d+)', inst_lower)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return Action(
                type=ActionType.MOUSE_CLICK,
                params={'x': x, 'y': y},
                description=f'点击坐标 ({x}, {y})',
                confidence=0.95
            )

        # 点击当前位置
        if re.search(r'^(?:点击|单击)$', inst_lower):
            return Action(
                type=ActionType.MOUSE_CLICK,
                params={},
                description='点击当前位置',
                confidence=0.9
            )

        # 双击
        if re.search(r'(?:双击|double)', inst_lower):
            return Action(
                type=ActionType.MOUSE_DOUBLE_CLICK,
                params={},
                description='双击鼠标',
                confidence=0.9
            )

        # 右键点击
        if re.search(r'(?:右击|右键|right)', inst_lower):
            return Action(
                type=ActionType.MOUSE_RIGHT_CLICK,
                params={},
                description='右键点击',
                confidence=0.9
            )

        # 移动鼠标
        match = re.search(r'(?:移动|移到).*?(\d+)\s*,\s*(\d+)', inst_lower)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            return Action(
                type=ActionType.MOUSE_MOVE,
                params={'x': x, 'y': y},
                description=f'移动鼠标到 ({x}, {y})',
                confidence=0.95
            )

        # 拖拽
        match = re.search(r'(?:拖拽|拖动).*?(\d+)\s*,\s*(\d+).*?(\d+)\s*,\s*(\d+)', inst_lower)
        if match:
            x1, y1, x2, y2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            return Action(
                type=ActionType.MOUSE_DRAG,
                params={'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2},
                description=f'从 ({x1}, {y1}) 拖拽到 ({x2}, {y2})',
                confidence=0.95
            )

        # 滚动
        match = re.search(r'(?:滚动|滚轮).*?(\d+)', inst_lower)
        if match:
            amount = int(match.group(1))
            return Action(
                type=ActionType.MOUSE_SCROLL,
                params={'amount': amount},
                description=f'滚动 {amount}',
                confidence=0.9
            )

        # 输入文字
        match = re.search(r'(?:输入|打字|填写|写入)\s*(.+)', inst_lower)
        if match:
            text = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.TYPE_TEXT,
                params={'text': text},
                description=f'输入文字: {text[:30]}{"..." if len(text) > 30 else ""}',
                confidence=0.95
            )

        # 按键
        match = re.search(r'(?:按下|按键|按)\s*(.+)', inst_lower)
        if match:
            key = match.group(1).strip().lower()
            actual_key = self.key_map.get(key, key)
            return Action(
                type=ActionType.PRESS_KEY,
                params={'key': actual_key},
                description=f'按键: {key}',
                confidence=0.95
            )

        # 快捷键
        match = re.search(r'(?:快捷键|热键)\s*(.+)', inst_lower)
        if match:
            keys = match.group(1).strip().split('+')
            return Action(
                type=ActionType.HOTKEY,
                params={'keys': [k.strip() for k in keys]},
                description=f'快捷键: {"+".join(keys)}',
                confidence=0.9
            )

        # 创建文件
        match = re.search(r'(?:创建|新建).*?文件\s*(.+)', inst_lower)
        if match:
            path = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.FILE_CREATE,
                params={'path': path},
                description=f'创建文件: {path}',
                confidence=0.9
            )

        # 删除文件
        match = re.search(r'(?:删除|移除).*?文件\s*(.+)', inst_lower)
        if match:
            path = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.FILE_DELETE,
                params={'path': path},
                description=f'删除文件: {path}',
                confidence=0.9
            )

        # 创建目录
        match = re.search(r'(?:创建|新建).*?(?:文件夹|目录|dir)\s*(.+)', inst_lower)
        if match:
            path = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.DIR_CREATE,
                params={'path': path},
                description=f'创建目录: {path}',
                confidence=0.9
            )

        # 列出目录
        match = re.search(r'(?:列出|显示).*?(?:文件夹|目录|dir)\s*(.+)', inst_lower)
        if match:
            path = match.group(1).strip().strip('"\'')
            return Action(
                type=ActionType.DIR_LIST,
                params={'path': path},
                description=f'列出目录: {path}',
                confidence=0.9
            )

        # 截图
        if re.search(r'(?:截图|快照|snapshot)', inst_lower):
            return Action(
                type=ActionType.SYSTEM_SCREENSHOT,
                params={},
                description='截取屏幕',
                confidence=1.0
            )

        # 设置音量
        match = re.search(r'音量.*?(\d+)', inst_lower)
        if match:
            level = int(match.group(1))
            return Action(
                type=ActionType.SYSTEM_VOLUME,
                params={'level': level},
                description=f'设置音量: {level}%',
                confidence=0.9
            )

        # 锁定系统
        if re.search(r'(?:锁定|锁屏)', inst_lower):
            return Action(
                type=ActionType.SYSTEM_LOCK,
                params={},
                description='锁定系统',
                confidence=1.0
            )

        # 睡眠
        if re.search(r'(?:睡眠|休眠)', inst_lower):
            return Action(
                type=ActionType.SYSTEM_SLEEP,
                params={},
                description='系统睡眠',
                confidence=1.0
            )

        # 关机
        if re.search(r'(?:关机|关闭电脑)', inst_lower):
            return Action(
                type=ActionType.SYSTEM_SHUTDOWN,
                params={'delay': 60},
                description='系统关机 (60秒)',
                confidence=1.0
            )

        # 获取剪贴板
        if re.search(r'(?:获取|显示).*?剪贴板', inst_lower):
            return Action(
                type=ActionType.SYSTEM_CLIPBOARD,
                params={'operation': 'get'},
                description='获取剪贴板内容',
                confidence=0.9
            )

        if re.search(r'(?:清空|清除).*?剪贴板', inst_lower):
            return Action(
                type=ActionType.SYSTEM_CLIPBOARD,
                params={'operation': 'clear'},
                description='清空剪贴板',
                confidence=0.9
            )

        # 打开URL
        match = re.search(r'(?:打开|访问).*?(https?://\S+)', inst_lower)
        if match:
            url = match.group(1)
            return Action(
                type=ActionType.BROWSER_OPEN,
                params={'url': url},
                description=f'打开URL: {url}',
                confidence=0.95
            )

        # 搜索 - 支持"搜索XXX"或"百度XXX"或"google XXX"
        # 修改：只有当明确说"搜索"时才触发，普通文字不触发
        search_patterns = [
            (r'(?:搜索|查找)\s*(.+)', 'bing'),  # 搜索/查找 关键词
            (r'^百度\s*(.+)', 'baidu'),  # 百度 关键词
            (r'^google\s*(.+)', 'google'),  # google 关键词
        ]
        for pattern, engine in search_patterns:
            match = re.search(pattern, inst_lower)
            if match:
                query = match.group(1).strip()
                return Action(
                    type=ActionType.BROWSER_SEARCH,
                    params={'query': query, 'engine': engine},
                    description=f'搜索: {query}',
                    confidence=0.95
                )

        # 等待
        match = re.search(r'(?:等待|延时|wait)\s*(\d+)', inst_lower)
        if match:
            seconds = int(match.group(1))
            return Action(
                type=ActionType.WAIT,
                params={'seconds': seconds},
                description=f'等待 {seconds} 秒',
                confidence=1.0
            )

        return None

    def _resolve_app(self, app_name: str) -> str:
        """解析应用名称到命令"""
        app_lower = app_name.lower()

        if app_lower in self.app_map:
            return self.app_map[app_lower]

        for name, cmd in self.app_map.items():
            if name in app_lower or app_lower in name:
                return cmd

        return app_name


# 便捷函数
def parse_instruction(instruction: str) -> List[Action]:
    """解析指令的便捷函数"""
    parser = AdvancedParser()
    return parser.parse(instruction)


if __name__ == "__main__":
    # 测试解析器
    test_cases = [
        "打开画图 然后画个圆",
        "打开记事本 然后输入Hello World",
        "点击 500, 500",
        "输入 Hello World",
        "截图",
        "搜索 Python教程",
    ]

    parser = AdvancedParser()

    for test in test_cases:
        print(f"\n测试: {test}")
        actions = parser.parse(test)
        for action in actions:
            print(f"  -> {action.type.value}: {action.description}")
