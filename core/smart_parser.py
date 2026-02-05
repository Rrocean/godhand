#!/usr/bin/env python3
"""
Smart Parser - 智能指令解析器
支持开放式自然语言，复合指令理解
"""

import os
import sys
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# 尝试导入 LLM
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from ghost_v2 import LLMClient
    HAS_LLM = True
except Exception as e:
    HAS_LLM = False
    print(f"[Warn] LLM not available: {e}")


class ActionType(Enum):
    """动作类型"""
    OPEN_APP = "open_app"           # 打开应用
    TYPE_TEXT = "type_text"         # 输入文字
    CLICK = "click"                 # 点击
    PRESS_KEY = "press_key"         # 按键
    HOTKEY = "hotkey"               # 快捷键
    WAIT = "wait"                   # 等待
    SEARCH = "search"               # 搜索
    FILE_OPERATION = "file"         # 文件操作
    SYSTEM = "system"               # 系统命令
    SCRIPT = "script"               # 执行脚本
    UNKNOWN = "unknown"             # 未知


@dataclass
class Action:
    """动作"""
    type: ActionType
    params: Dict[str, Any]          # 动作参数
    description: str                # 描述
    reason: str = ""                # 执行原因
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.value,
            'params': self.params,
            'description': self.description,
            'reason': self.reason
        }


class SmartParser:
    """
    智能解析器
    支持复合指令、上下文理解、开放式自然语言
    """
    
    # 应用名称映射
    APP_ALIASES = {
        # 计算器
        '计算器': ['calc', 'calculator'],
        'calc': ['计算器'],
        # 记事本
        '记事本': ['notepad', 'txt', '文本编辑器'],
        'notepad': ['记事本'],
        'txt': ['记事本'],
        # 画图
        '画图': ['mspaint', 'paint', '绘图'],
        'paint': ['画图'],
        # 浏览器
        '浏览器': ['edge', 'chrome', 'browser'],
        'edge': ['浏览器'],
        'chrome': ['谷歌浏览器', 'chrome浏览器'],
        # 其他
        'cmd': ['命令提示符', '终端', '命令行'],
        'powershell': ['ps', 'power shell'],
        'word': ['word', '文档'],
        'excel': ['excel', '表格'],
    }
    
    # 常见应用执行命令
    APP_COMMANDS = {
        '计算器': 'calc.exe',
        '记事本': 'notepad.exe',
        '画图': 'mspaint.exe',
        'cmd': 'cmd.exe',
        'powershell': 'powershell.exe',
        '浏览器': 'msedge',
        'edge': 'msedge',
        'chrome': 'chrome',
        'word': 'winword',
        'excel': 'excel',
        'vscode': 'code',
        '设置': 'ms-settings:',
        '任务管理器': 'taskmgr.exe',
        '文件资源管理器': 'explorer.exe',
    }
    
    def __init__(self, llm_client=None, config_path: str = None):
        self.llm = llm_client
        self.config = self._load_config(config_path)
        
        # 如果没有传入llm但配置可用，尝试初始化
        if self.llm is None and HAS_LLM and config_path:
            try:
                self.llm = LLMClient(self.config)
            except Exception as e:
                print(f"[Warn] LLM初始化失败: {e}")
    
    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        default = {
            'provider': 'google',
            'google': {'api_key': os.getenv('GOOGLE_API_KEY', ''), 'model': 'gemini-2.0-flash'}
        }
        
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except:
                pass
        
        return default
    
    def parse(self, instruction: str, use_llm: bool = True) -> List[Action]:
        """
        解析指令为动作列表
        
        Args:
            instruction: 用户输入的自然语言指令
            use_llm: 是否尝试使用LLM解析
        
        Returns:
            动作列表
        """
        instruction = instruction.strip()
        if not instruction:
            return []
        
        # 1. 尝试智能规则解析（处理常见复合指令）
        actions = self._smart_rule_parse(instruction)
        if actions:
            return actions
        
        # 2. 尝试LLM解析
        if use_llm and HAS_LLM and self.llm:
            try:
                actions = self._llm_parse(instruction)
                if actions:
                    return actions
            except Exception as e:
                print(f"[Warn] LLM解析失败: {e}")
        
        # 3. 基础规则解析
        actions = self._basic_rule_parse(instruction)
        if actions:
            return actions
        
        # 4. 无法解析
        return [Action(
            type=ActionType.UNKNOWN,
            params={'raw': instruction},
            description=f"无法解析: {instruction}",
            reason="指令格式不支持"
        )]
    
    def _smart_rule_parse(self, instruction: str) -> Optional[List[Action]]:
        """
        智能规则解析 - 处理复合指令
        例如："打开记事本 输入123" "打开计算器 计算1+1"
        """
        actions = []
        remaining = instruction.lower()
        
        # 模式1: 打开X 输入Y
        # 匹配：打开记事本 输入123、打开计算器输入1+1
        open_type_pattern = r'(打开|启动|运行)\s*(.+?)(?:\s+然后\s+|\s+再\s+|\s+|，|,|;|；)\s*(输入|填写|写入|键入)(.+?)$'
        match = re.search(open_type_pattern, instruction.lower())
        if match:
            app_name = match.group(2).strip()
            text_to_type = match.group(4).strip()
            
            # 添加打开应用动作
            app_cmd = self._resolve_app(app_name)
            actions.append(Action(
                type=ActionType.OPEN_APP,
                params={'command': app_cmd, 'app_name': app_name},
                description=f"打开应用: {app_name}",
                reason="用户要求打开应用"
            ))
            
            # 添加等待动作（等待应用启动）
            actions.append(Action(
                type=ActionType.WAIT,
                params={'seconds': 1.0},
                description="等待应用启动",
                reason="等待应用窗口出现"
            ))
            
            # 添加输入动作
            actions.append(Action(
                type=ActionType.TYPE_TEXT,
                params={'text': text_to_type},
                description=f"输入文字: {text_to_type[:20]}{'...' if len(text_to_type) > 20 else ''}",
                reason="用户要求输入内容"
            ))
            
            return actions
        
        # 模式2: 打开X 搜索Y
        # 例如：打开浏览器 搜索Python教程
        search_pattern = r'(打开|启动)\s*(.+?)(?:\s+然后\s+|\s+再\s+|\s+|，|,|;|；)\s*(搜索|查找|百度|google)(.+?)$'
        match = re.search(search_pattern, instruction.lower())
        if match:
            app_name = match.group(2).strip()
            search_query = match.group(4).strip()
            
            # 如果是浏览器相关
            if any(x in app_name for x in ['浏览器', 'edge', 'chrome']):
                actions.append(Action(
                    type=ActionType.SEARCH,
                    params={'query': search_query, 'engine': 'bing'},
                    description=f"搜索: {search_query}",
                    reason="用户要求搜索"
                ))
                return actions
        
        # 模式3: 创建文件并写入内容
        # 例如：创建文件test.txt 写入Hello World
        file_pattern = r'(创建|新建)\s*文件\s*(.+?)(?:\s+然后\s+|\s+再\s+|\s+|，|,|;|；)\s*(写入|输入|填写)(.+?)$'
        match = re.search(file_pattern, instruction.lower())
        if match:
            filename = match.group(2).strip()
            content = match.group(4).strip()
            
            actions.append(Action(
                type=ActionType.FILE_OPERATION,
                params={'operation': 'create', 'filename': filename, 'content': content},
                description=f"创建文件 {filename} 并写入内容",
                reason="用户要求创建文件并写入"
            ))
            return actions
        
        # 模式4: 多个动作链
        # 例如：截图 保存到桌面
        if '然后' in instruction or '再' in instruction:
            parts = re.split(r'(?:然后|再|，|,|;|；)', instruction)
            for part in parts:
                part = part.strip()
                if part:
                    part_actions = self._basic_rule_parse(part)
                    if part_actions:
                        actions.extend(part_actions)
            
            if actions:
                return actions
        
        return None
    
    def _basic_rule_parse(self, instruction: str) -> Optional[List[Action]]:
        """基础规则解析 - 单条指令"""
        instruction_lower = instruction.lower().strip()
        
        # 1. 打开应用
        open_patterns = [
            r'^打开\s*(.+?)$',
            r'^启动\s*(.+?)$',
            r'^运行\s*(.+?)$',
            r'^开\s*(.+?)$',
        ]
        
        for pattern in open_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                app_name = match.group(1).strip()
                app_cmd = self._resolve_app(app_name)
                return [Action(
                    type=ActionType.OPEN_APP,
                    params={'command': app_cmd, 'app_name': app_name},
                    description=f"打开应用: {app_name}",
                    reason="用户要求打开应用"
                )]
        
        # 2. 输入文字
        type_patterns = [
            r'^输入\s*(.+?)$',
            r'^填写\s*(.+?)$',
            r'^写入\s*(.+?)$',
            r'^键入\s*(.+?)$',
            r'^打\s*(.+?)$',
        ]
        
        for pattern in type_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                text = match.group(1).strip()
                return [Action(
                    type=ActionType.TYPE_TEXT,
                    params={'text': text},
                    description=f"输入: {text[:30]}{'...' if len(text) > 30 else ''}",
                    reason="用户要求输入文字"
                )]
        
        # 3. 按键 - 使用更简单的匹配方式
        if instruction_lower.startswith('按') or instruction_lower.startswith('按下') or instruction_lower.startswith('按键'):
            # 提取按键名
            key = instruction_lower
            for prefix in ['按键', '按下', '按']:
                if key.startswith(prefix):
                    key = key[len(prefix):].strip()
                    break
            
            if key:
                # 映射常用按键
                key_map = {
                    '回车': 'enter', 'enter': 'enter',
                    '空格': 'space', 'space': 'space',
                    '退格': 'backspace', 'backspace': 'backspace',
                    '删除': 'delete', 'delete': 'delete', 'del': 'delete',
                    'esc': 'escape', 'escape': 'escape',
                    '上': 'up', 'up': 'up',
                    '下': 'down', 'down': 'down',
                    '左': 'left', 'left': 'left',
                    '右': 'right', 'right': 'right',
                    'tab': 'tab',
                    'ctrl': 'ctrl', 'control': 'ctrl',
                    'alt': 'alt',
                    'shift': 'shift',
                }
                actual_key = key_map.get(key.lower(), key.lower())
                return [Action(
                    type=ActionType.PRESS_KEY,
                    params={'key': actual_key},
                    description=f"按键: {key}",
                    reason="用户要求按键"
                )]
        
        # 4. 搜索
        search_patterns = [
            r'^搜索\s*(.+?)$',
            r'^查找\s*(.+?)$',
            r'^百度\s*(.+?)$',
            r'^google\s*(.+?)$',
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                query = match.group(1).strip()
                return [Action(
                    type=ActionType.SEARCH,
                    params={'query': query, 'engine': 'bing'},
                    description=f"搜索: {query}",
                    reason="用户要求搜索"
                )]
        
        # 5. 等待
        wait_patterns = [
            r'^等待\s*(\d+)\s*秒$',
            r'^等\s*(\d+)\s*秒$',
            r'^wait\s*(\d+)\s*s$',
        ]
        
        for pattern in wait_patterns:
            match = re.search(pattern, instruction_lower)
            if match:
                seconds = float(match.group(1))
                return [Action(
                    type=ActionType.WAIT,
                    params={'seconds': seconds},
                    description=f"等待 {seconds} 秒",
                    reason="用户要求等待"
                )]
        
        # 6. 截图
        if any(x in instruction_lower for x in ['截图', '截屏', 'snapshot', 'screenshot']):
            return [Action(
                type=ActionType.SYSTEM,
                params={'operation': 'screenshot'},
                description="截取屏幕",
                reason="用户要求截图"
            )]
        
        # 7. 创建文件夹
        folder_pattern = r'(?:创建|新建)\s*(?:文件夹|目录)\s*(.+?)$'
        match = re.search(folder_pattern, instruction_lower)
        if match:
            folder_name = match.group(1).strip()
            full_path = os.path.join(os.getcwd(), folder_name)
            return [Action(
                type=ActionType.FILE_OPERATION,
                params={'operation': 'mkdir', 'path': full_path},
                description=f"创建文件夹: {folder_name}",
                reason="用户要求创建文件夹"
            )]
        
        return None
    
    def _llm_parse(self, instruction: str) -> Optional[List[Action]]:
        """使用LLM解析复杂指令"""
        prompt = f"""你是一个智能助手，需要将用户的自然语言指令解析为可执行的动作序列。

用户指令: "{instruction}"

请分析这个指令，并将其解析为以下格式的JSON动作序列：

```json
[
  {{
    "type": "动作类型",
    "params": {{参数}},
    "description": "动作描述",
    "reason": "为什么执行这个动作"
  }}
]
```

支持的动作类型:
- "open_app": 打开应用，参数: {{"command": "应用命令", "app_name": "应用名"}}
- "type_text": 输入文字，参数: {{"text": "要输入的文字"}}
- "press_key": 按键，参数: {{"key": "按键名"}}
- "hotkey": 快捷键，参数: {{"keys": ["ctrl", "c"]}}
- "click": 点击，参数: {{"x": 100, "y": 200}} 或 {{"element": "元素描述"}}
- "wait": 等待，参数: {{"seconds": 1.0}}
- "search": 搜索，参数: {{"query": "搜索词", "engine": "bing"}}
- "file": 文件操作，参数: {{"operation": "create/mkdir", "path": "路径", "content": "内容"}}
- "system": 系统命令，参数: {{"command": "命令"}}

重要规则:
1. 复合指令要拆分为多个步骤
2. 打开应用后要等待1-2秒
3. 使用Windows命令时，GUI程序用"start"前缀避免阻塞
4. 只返回JSON数组，不要其他内容

示例:
用户: "打开记事本输入Hello"
输出: [
  {{"type": "open_app", "params": {{"command": "notepad.exe", "app_name": "记事本"}}, "description": "打开记事本", "reason": "用户要求打开记事本"}},
  {{"type": "wait", "params": {{"seconds": 1.0}}, "description": "等待应用启动", "reason": "等待窗口出现"}},
  {{"type": "type_text", "params": {{"text": "Hello"}}, "description": "输入Hello", "reason": "用户要求输入内容"}}
]
"""

        try:
            response = self.llm.generate(prompt)
            
            # 提取JSON
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                actions = []
                for item in data:
                    action_type = ActionType(item.get('type', 'unknown'))
                    actions.append(Action(
                        type=action_type,
                        params=item.get('params', {}),
                        description=item.get('description', ''),
                        reason=item.get('reason', '')
                    ))
                
                return actions
            
            return None
            
        except Exception as e:
            print(f"[Error] LLM解析错误: {e}")
            return None
    
    def _resolve_app(self, app_name: str) -> str:
        """解析应用名称到命令"""
        app_name = app_name.lower().strip()
        
        # 直接匹配
        if app_name in self.APP_COMMANDS:
            return self.APP_COMMANDS[app_name]
        
        # 检查别名
        for main_name, aliases in self.APP_ALIASES.items():
            if app_name == main_name.lower() or app_name in [a.lower() for a in aliases]:
                if main_name in self.APP_COMMANDS:
                    return self.APP_COMMANDS[main_name]
        
        # 模糊匹配
        for name, cmd in self.APP_COMMANDS.items():
            if name in app_name or app_name in name:
                return cmd
        
        # 未知应用，尝试直接运行
        return app_name


class ActionExecutor:
    """动作执行器"""
    
    def __init__(self):
        self.results = []
    
    def execute(self, action: Action) -> Dict:
        """执行单个动作"""
        result = {
            'success': False,
            'action': action.to_dict(),
            'output': '',
            'error': None
        }
        
        try:
            if action.type == ActionType.OPEN_APP:
                result = self._execute_open_app(action)
            elif action.type == ActionType.TYPE_TEXT:
                result = self._execute_type_text(action)
            elif action.type == ActionType.PRESS_KEY:
                result = self._execute_press_key(action)
            elif action.type == ActionType.HOTKEY:
                result = self._execute_hotkey(action)
            elif action.type == ActionType.WAIT:
                result = self._execute_wait(action)
            elif action.type == ActionType.SEARCH:
                result = self._execute_search(action)
            elif action.type == ActionType.FILE_OPERATION:
                result = self._execute_file_operation(action)
            elif action.type == ActionType.SYSTEM:
                result = self._execute_system(action)
            else:
                result['error'] = f"未实现的动作类型: {action.type}"
            
        except Exception as e:
            result['error'] = str(e)
        
        self.results.append(result)
        return result
    
    def execute_batch(self, actions: List[Action]) -> List[Dict]:
        """批量执行动作"""
        results = []
        for action in actions:
            result = self.execute(action)
            results.append(result)
            if not result['success']:
                print(f"[Warn] 动作失败: {action.description}")
        return results
    
    def _execute_open_app(self, action: Action) -> Dict:
        """执行打开应用"""
        import subprocess
        
        cmd = action.params.get('command', '')
        if not cmd:
            return {'success': False, 'error': '未指定应用命令'}
        
        # GUI程序使用start避免阻塞
        if not cmd.startswith('start ') and not cmd.endswith('.exe'):
            cmd = f'start "" {cmd}'
        
        try:
            subprocess.Popen(cmd, shell=True)
            return {
                'success': True,
                'output': f"已启动: {action.params.get('app_name', cmd)}",
                'action': action.to_dict()
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'action': action.to_dict()}
    
    def _execute_type_text(self, action: Action) -> Dict:
        """执行输入文字"""
        try:
            import pyautogui
            import pyperclip
            
            text = action.params.get('text', '')
            
            # 使用剪贴板支持中文
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            
            return {
                'success': True,
                'output': f"已输入: {text[:50]}{'...' if len(text) > 50 else ''}",
                'action': action.to_dict()
            }
        except ImportError:
            return {'success': False, 'error': '缺少pyautogui或pyperclip', 'action': action.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e), 'action': action.to_dict()}
    
    def _execute_press_key(self, action: Action) -> Dict:
        """执行按键"""
        try:
            import pyautogui
            
            key = action.params.get('key', '')
            pyautogui.press(key)
            
            return {
                'success': True,
                'output': f"已按键: {key}",
                'action': action.to_dict()
            }
        except ImportError:
            return {'success': False, 'error': '缺少pyautogui', 'action': action.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e), 'action': action.to_dict()}
    
    def _execute_hotkey(self, action: Action) -> Dict:
        """执行快捷键"""
        try:
            import pyautogui
            
            keys = action.params.get('keys', [])
            pyautogui.hotkey(*keys)
            
            return {
                'success': True,
                'output': f"快捷键: {'+'.join(keys)}",
                'action': action.to_dict()
            }
        except ImportError:
            return {'success': False, 'error': '缺少pyautogui', 'action': action.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e), 'action': action.to_dict()}
    
    def _execute_wait(self, action: Action) -> Dict:
        """执行等待"""
        import time
        
        seconds = action.params.get('seconds', 1.0)
        time.sleep(seconds)
        
        return {
            'success': True,
            'output': f"等待了 {seconds} 秒",
            'action': action.to_dict()
        }
    
    def _execute_search(self, action: Action) -> Dict:
        """执行搜索"""
        import subprocess
        
        query = action.params.get('query', '')
        engine = action.params.get('engine', 'bing')
        
        # URL编码
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        
        if engine == 'bing':
            url = f"https://www.bing.com/search?q={encoded_query}"
        elif engine == 'google':
            url = f"https://www.google.com/search?q={encoded_query}"
        else:
            url = f"https://www.bing.com/search?q={encoded_query}"
        
        cmd = f'start msedge "{url}"'
        subprocess.Popen(cmd, shell=True)
        
        return {
            'success': True,
            'output': f"搜索: {query}",
            'action': action.to_dict()
        }
    
    def _execute_file_operation(self, action: Action) -> Dict:
        """执行文件操作"""
        import os
        
        operation = action.params.get('operation', '')
        
        try:
            if operation == 'mkdir':
                path = action.params.get('path', '')
                os.makedirs(path, exist_ok=True)
                return {
                    'success': True,
                    'output': f"创建文件夹: {path}",
                    'action': action.to_dict()
                }
            elif operation == 'create':
                filename = action.params.get('filename', '')
                content = action.params.get('content', '')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                return {
                    'success': True,
                    'output': f"创建文件: {filename}",
                    'action': action.to_dict()
                }
            else:
                return {'success': False, 'error': f'未知文件操作: {operation}', 'action': action.to_dict()}
        except Exception as e:
            return {'success': False, 'error': str(e), 'action': action.to_dict()}
    
    def _execute_system(self, action: Action) -> Dict:
        """执行系统命令"""
        import subprocess
        
        operation = action.params.get('operation', '')
        
        if operation == 'screenshot':
            try:
                import pyautogui
                from datetime import datetime
                
                screenshot = pyautogui.screenshot()
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot.save(filename)
                
                return {
                    'success': True,
                    'output': f"截图保存: {filename}",
                    'action': action.to_dict()
                }
            except Exception as e:
                return {'success': False, 'error': str(e), 'action': action.to_dict()}
        
        command = action.params.get('command', '')
        if command:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {
                'success': result.returncode == 0,
                'output': result.stdout if result.returncode == 0 else result.stderr,
                'action': action.to_dict()
            }
        
        return {'success': False, 'error': '未指定系统命令', 'action': action.to_dict()}


# 便捷函数
def parse_and_execute(instruction: str, config_path: str = None) -> List[Dict]:
    """解析并执行指令"""
    parser = SmartParser(config_path=config_path)
    executor = ActionExecutor()
    
    print(f"\n[Parse] 解析指令: {instruction}")
    actions = parser.parse(instruction)
    
    print(f"[Parse] 解析为 {len(actions)} 个动作:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. [{action.type.value}] {action.description}")
    
    print(f"\n[Execute] 开始执行...")
    results = executor.execute_batch(actions)
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python smart_parser.py '打开记事本 输入123'")
        print("\n支持的指令示例:")
        print("  - 打开记事本 输入Hello World")
        print("  - 打开计算器")
        print("  - 搜索Python教程")
        print("  - 截图")
        print("  - 创建文件夹Test")
        sys.exit(1)
    
    instruction = sys.argv[1]
    results = parse_and_execute(instruction)
    
    print("\n[Result] 执行结果:")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {result['action']['description']}: {result.get('output', result.get('error', ''))}")
