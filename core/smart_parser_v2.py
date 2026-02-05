#!/usr/bin/env python3
"""
Smart Parser v2 - 智能指令解析器
新增功能:
- 上下文记忆
- 意图置信度
- 模式学习
- 复合指令优化
"""

import os
import sys
import json
import re
import time
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
from datetime import datetime

# 尝试导入 LLM
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from ghost_v3 import LLMClient, ExecutionMode
    HAS_LLM = True
except Exception as e:
    HAS_LLM = False
    print(f"[Warn] LLM not available: {e}")


class ActionType(Enum):
    """动作类型"""
    OPEN_APP = "open_app"
    TYPE_TEXT = "type_text"
    CLICK = "click"
    PRESS_KEY = "press_key"
    HOTKEY = "hotkey"
    WAIT = "wait"
    SEARCH = "search"
    FILE_OPERATION = "file"
    SYSTEM = "system"
    SCRIPT = "script"
    GUI_ACTION = "gui"
    UNKNOWN = "unknown"


class IntentCategory(Enum):
    """意图类别"""
    APP_LAUNCH = "app_launch"
    FILE_MANAGE = "file_manage"
    WEB_SEARCH = "web_search"
    GUI_AUTOMATION = "gui_auto"
    SYSTEM_CMD = "system_cmd"
    COMPOSITE = "composite"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """解析的意图"""
    category: IntentCategory
    confidence: float
    primary_action: str
    parameters: Dict[str, Any]
    suggested_mode: ExecutionMode


@dataclass
class Action:
    """动作"""
    type: ActionType
    params: Dict[str, Any]
    description: str
    reason: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.value,
            'params': self.params,
            'description': self.description,
            'reason': self.reason,
            'confidence': self.confidence
        }


@dataclass
class ContextMemory:
    """上下文记忆"""
    recent_commands: List[str] = field(default_factory=list)
    frequent_apps: Dict[str, int] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    last_execution_time: Optional[datetime] = None
    
    def add_command(self, command: str):
        self.recent_commands.append(command)
        if len(self.recent_commands) > 20:
            self.recent_commands.pop(0)
        self.last_execution_time = datetime.now()
    
    def record_app_usage(self, app_name: str):
        self.frequent_apps[app_name] = self.frequent_apps.get(app_name, 0) + 1
    
    def get_frequent_apps(self, n: int = 5) -> List[Tuple[str, int]]:
        return sorted(self.frequent_apps.items(), key=lambda x: x[1], reverse=True)[:n]


class SmartParserV2:
    """智能解析器 v2"""
    
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
    
    INTENT_PATTERNS = {
        IntentCategory.APP_LAUNCH: [r'打开|启动|运行'],
        IntentCategory.FILE_MANAGE: [r'创建|新建|删除|复制|移动'],
        IntentCategory.WEB_SEARCH: [r'搜索|查找'],
        IntentCategory.GUI_AUTOMATION: [r'点击|输入|按键|截图'],
        IntentCategory.SYSTEM_CMD: [r'关机|重启|睡眠'],
    }
    
    def __init__(self, llm_client=None, config_path: str = None):
        self.llm = llm_client
        self.config = self._load_config(config_path)
        self.context = ContextMemory()
        
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        self.learning_file = self.data_dir / "parser_learning.json"
        self.corrections: Dict[str, str] = {}
        self._load_learning_data()
    
    def _load_config(self, path: str) -> Dict:
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
    
    def _load_learning_data(self):
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.corrections = data.get('corrections', {})
            except:
                pass
    
    def save_learning_data(self):
        try:
            with open(self.learning_file, 'w', encoding='utf-8') as f:
                json.dump({'corrections': self.corrections}, f, ensure_ascii=False)
        except:
            pass
    
    def parse(self, instruction: str, use_context: bool = True) -> Tuple[List[Action], ParsedIntent]:
        instruction = instruction.strip()
        if not instruction:
            return [], ParsedIntent(IntentCategory.UNKNOWN, 0.0, "", {}, ExecutionMode.AUTO)
        
        # 检查用户纠正历史
        if instruction in self.corrections:
            instruction = self.corrections[instruction]
        
        # 识别意图
        intent = self._classify_intent(instruction)
        
        # 根据意图选择解析策略
        actions = []
        
        if intent.category == IntentCategory.COMPOSITE:
            actions = self._parse_composite(instruction)
        elif intent.category == IntentCategory.GUI_AUTOMATION:
            actions = self._parse_gui_actions(instruction)
        elif intent.category == IntentCategory.APP_LAUNCH:
            actions = self._parse_app_launch(instruction)
        else:
            actions = self._smart_rule_parse(instruction)
        
        # 如果规则解析失败，尝试LLM
        if not actions and HAS_LLM and self.llm:
            actions = self._llm_parse(instruction)
            intent.confidence = 0.85
        
        # 基础规则兜底
        if not actions:
            actions = self._basic_rule_parse(instruction)
        
        # 最终fallback
        if not actions:
            actions = [Action(
                type=ActionType.UNKNOWN,
                params={'raw': instruction},
                description=f"无法解析: {instruction}",
                reason="指令格式不支持",
                confidence=0.0
            )]
            intent.confidence = 0.0
        
        # 更新上下文
        if use_context:
            self.context.add_command(instruction)
            for action in actions:
                if action.type == ActionType.OPEN_APP:
                    app_name = action.params.get('app_name', '')
                    if app_name:
                        self.context.record_app_usage(app_name)
        
        return actions, intent
    
    def _classify_intent(self, instruction: str) -> ParsedIntent:
        instruction_lower = instruction.lower()
        
        # 检查是否复合指令
        composite_markers = ['然后', '再', '接着', '之后', ',', '，', ';', '；']
        if any(m in instruction for m in composite_markers):
            return ParsedIntent(
                category=IntentCategory.COMPOSITE,
                confidence=0.9,
                primary_action="composite",
                parameters={'raw': instruction},
                suggested_mode=ExecutionMode.AUTO
            )
        
        # 匹配各类意图
        scores = {}
        for category, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, instruction_lower):
                    score += 1
            scores[category] = score
        
        if scores:
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]
            
            if best_score > 0:
                confidence = min(0.6 + 0.1 * best_score, 0.95)
                suggested_mode = self._get_mode_for_category(best_category)
                
                return ParsedIntent(
                    category=best_category,
                    confidence=confidence,
                    primary_action=best_category.value,
                    parameters={},
                    suggested_mode=suggested_mode
                )
        
        return ParsedIntent(
            category=IntentCategory.UNKNOWN,
            confidence=0.3,
            primary_action="unknown",
            parameters={},
            suggested_mode=ExecutionMode.AUTO
        )
    
    def _get_mode_for_category(self, category: IntentCategory) -> ExecutionMode:
        mapping = {
            IntentCategory.APP_LAUNCH: ExecutionMode.COMMAND,
            IntentCategory.FILE_MANAGE: ExecutionMode.COMMAND,
            IntentCategory.WEB_SEARCH: ExecutionMode.COMMAND,
            IntentCategory.GUI_AUTOMATION: ExecutionMode.GUI,
            IntentCategory.SYSTEM_CMD: ExecutionMode.COMMAND,
            IntentCategory.COMPOSITE: ExecutionMode.AUTO,
        }
        return mapping.get(category, ExecutionMode.AUTO)
    
    def _parse_composite(self, instruction: str) -> List[Action]:
        """解析复合指令 - 改进版"""
        actions = []
        instruction_clean = instruction.strip()
        
        # 模式1: 打开X 然后/再/接着 输入Y
        # 支持多种连接词和标点
        open_type_pattern = r'(?:打开|启动|运行)\s*(\S+?)\s*(?:然后|再|接着|，|,)?\s*(?:输入|填写|写入|键入)\s*(.+?)$'
        match = re.search(open_type_pattern, instruction_clean, re.IGNORECASE)
        
        if match:
            app_name = match.group(1).strip()
            text_to_type = match.group(2).strip()
            
            # 添加打开应用
            app_cmd = self._resolve_app(app_name)
            actions.append(Action(
                type=ActionType.OPEN_APP,
                params={'command': app_cmd, 'app_name': app_name},
                description=f"打开应用: {app_name}",
                reason="用户要求打开应用",
                confidence=0.95
            ))
            
            # 等待
            actions.append(Action(
                type=ActionType.WAIT,
                params={'seconds': 1.5},
                description="等待应用启动",
                reason="等待应用窗口出现",
                confidence=1.0
            ))
            
            # 输入
            actions.append(Action(
                type=ActionType.TYPE_TEXT,
                params={'text': text_to_type},
                description=f"输入文字: {text_to_type[:20]}{'...' if len(text_to_type) > 20 else ''}",
                reason="用户要求输入内容",
                confidence=0.9
            ))
            
            return actions
        
        # 模式2: 智能分割处理
        if any(sep in instruction_clean for sep in ['然后', '再', '接着', '，', ',', '；', ';']):
            parts = re.split(r'\s*(?:然后|再|接着|，|,|；|;)\s*', instruction_clean)
            
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # 检查是否是"打开X"格式
                open_match = re.match(r'^(?:打开|启动|运行)\s*(.+)$', part)
                if open_match:
                    app_name = open_match.group(1).strip()
                    app_cmd = self._resolve_app(app_name)
                    actions.append(Action(
                        type=ActionType.OPEN_APP,
                        params={'command': app_cmd, 'app_name': app_name},
                        description=f"打开应用: {app_name}",
                        reason="用户要求打开应用",
                        confidence=0.95
                    ))
                    continue
                
                # 检查是否是"输入X"格式
                type_match = re.match(r'^(?:输入|填写|写入|键入|打)\s*(.+)$', part)
                if type_match:
                    text = type_match.group(1).strip()
                    actions.append(Action(
                        type=ActionType.TYPE_TEXT,
                        params={'text': text},
                        description=f"输入文字: {text[:20]}{'...' if len(text) > 20 else ''}",
                        reason="用户要求输入内容",
                        confidence=0.9
                    ))
                    continue
                
                # 其他基础解析
                other_actions = self._basic_rule_parse(part)
                if other_actions:
                    actions.extend(other_actions)
            
            if actions:
                return actions
        
        return None
    
    def _parse_gui_actions(self, instruction: str) -> List[Action]:
        actions = []
        instruction_lower = instruction.lower()
        
        if any(k in instruction_lower for k in ['截图', '截屏', 'screenshot']):
            actions.append(Action(
                type=ActionType.SYSTEM,
                params={'operation': 'screenshot'},
                description="截取屏幕",
                reason="用户要求截图",
                confidence=0.95
            ))
            return actions
        
        return actions
    
    def _parse_app_launch(self, instruction: str) -> List[Action]:
        patterns = [
            r'^打开\s*(.+?)$',
            r'^启动\s*(.+?)$',
            r'^运行\s*(.+?)$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                app_name = match.group(1).strip()
                app_cmd = self._resolve_app(app_name)
                return [Action(
                    type=ActionType.OPEN_APP,
                    params={'command': app_cmd, 'app_name': app_name},
                    description=f"打开应用: {app_name}",
                    reason="用户要求打开应用",
                    confidence=0.95
                )]
        
        return []
    
    def _smart_rule_parse(self, instruction: str) -> Optional[List[Action]]:
        # 搜索
        search_patterns = [
            (r'^搜索\s*(.+?)$', 'bing'),
            (r'^查找\s*(.+?)$', 'bing'),
        ]
        
        for pattern, engine in search_patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                query = match.group(1).strip()
                return [Action(
                    type=ActionType.SEARCH,
                    params={'query': query, 'engine': engine},
                    description=f"搜索: {query}",
                    reason="用户要求搜索",
                    confidence=0.9
                )]
        
        return None
    
    def _basic_rule_parse(self, instruction: str) -> Optional[List[Action]]:
        instruction_lower = instruction.lower().strip()
        
        # 等待
        wait_match = re.search(r'^等待?\s*(\d+)\s*秒?$', instruction_lower)
        if wait_match:
            seconds = float(wait_match.group(1))
            return [Action(
                type=ActionType.WAIT,
                params={'seconds': seconds},
                description=f"等待 {seconds} 秒",
                reason="用户要求等待",
                confidence=1.0
            )]
        
        # 创建文件夹
        folder_match = re.search(r'(?:创建|新建)\s*(?:文件夹|目录)\s*(.+?)$', instruction_lower)
        if folder_match:
            folder_name = folder_match.group(1).strip()
            full_path = os.path.join(os.getcwd(), folder_name)
            return [Action(
                type=ActionType.FILE_OPERATION,
                params={'operation': 'mkdir', 'path': full_path},
                description=f"创建文件夹: {folder_name}",
                reason="用户要求创建文件夹",
                confidence=0.9
            )]
        
        return []
    
    def _resolve_app(self, app_name: str) -> str:
        app_name = app_name.lower().strip()
        
        if app_name in self.APP_COMMANDS:
            return self.APP_COMMANDS[app_name]
        
        for name, cmd in self.APP_COMMANDS.items():
            if name in app_name or app_name in name:
                return cmd
        
        return f'start "" "{app_name}"'
    
    def _llm_parse(self, instruction: str) -> Optional[List[Action]]:
        prompt = f"""将用户的自然语言指令解析为可执行的动作序列。

用户指令: "{instruction}"

输出JSON格式:
```json
[
  {{
    "type": "动作类型",
    "params": {{参数}},
    "description": "动作描述",
    "reason": "执行原因",
    "confidence": 0.9
  }}
]
```

支持类型: open_app, type_text, press_key, hotkey, click, wait, search, file, system"""

        try:
            response = self.llm.generate(prompt, temperature=0.3)
            
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                actions = []
                for item in data:
                    action_type = ActionType(item.get('type', 'unknown'))
                    actions.append(Action(
                        type=action_type,
                        params=item.get('params', {}),
                        description=item.get('description', ''),
                        reason=item.get('reason', ''),
                        confidence=item.get('confidence', 0.8)
                    ))
                
                return actions
        except Exception as e:
            print(f"[Error] LLM解析失败: {e}")
        
        return None
    
    def record_correction(self, original: str, corrected: str):
        self.corrections[original] = corrected
        self.save_learning_data()


class ActionExecutorV2:
    """增强版动作执行器"""
    
    def __init__(self):
        self.results = []
        self.execution_log = []
    
    def execute(self, action: Action) -> Dict:
        start_time = time.time()
        
        result = {
            'success': False,
            'action': action.to_dict(),
            'output': '',
            'error': None,
            'execution_time': 0.0
        }
        
        try:
            handler = getattr(self, f'_execute_{action.type.value}', None)
            if handler:
                result = handler(action, result)
            else:
                result['error'] = f"未实现的动作类型: {action.type}"
        except Exception as e:
            result['error'] = str(e)
        
        result['execution_time'] = time.time() - start_time
        self.results.append(result)
        
        self.execution_log.append({
            'timestamp': datetime.now().isoformat(),
            'action': action.to_dict(),
            'result': result
        })
        
        return result
    
    def execute_batch(self, actions: List[Action]) -> List[Dict]:
        return [self.execute(a) for a in actions]
    
    def _execute_open_app(self, action: Action, result: Dict) -> Dict:
        import subprocess
        
        cmd = action.params.get('command', '')
        if not cmd:
            result['error'] = '未指定应用命令'
            return result
        
        if not cmd.startswith('start '):
            cmd = f'start "" {cmd}'
        
        try:
            subprocess.Popen(cmd, shell=True)
            result['success'] = True
            result['output'] = f"已启动: {action.params.get('app_name', cmd)}"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _execute_type_text(self, action: Action, result: Dict) -> Dict:
        try:
            import pyautogui
            import pyperclip
            
            text = action.params.get('text', '')
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            
            result['success'] = True
            result['output'] = f"已输入: {text[:50]}{'...' if len(text) > 50 else ''}"
        except ImportError:
            result['error'] = '缺少 pyautogui 或 pyperclip'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _execute_press_key(self, action: Action, result: Dict) -> Dict:
        try:
            import pyautogui
            key = action.params.get('key', '')
            pyautogui.press(key)
            result['success'] = True
            result['output'] = f"已按键: {key}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _execute_hotkey(self, action: Action, result: Dict) -> Dict:
        try:
            import pyautogui
            keys = action.params.get('keys', [])
            pyautogui.hotkey(*keys)
            result['success'] = True
            result['output'] = f"快捷键: {'+'.join(keys)}"
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def _execute_wait(self, action: Action, result: Dict) -> Dict:
        seconds = action.params.get('seconds', 1.0)
        time.sleep(seconds)
        result['success'] = True
        result['output'] = f"等待了 {seconds} 秒"
        return result
    
    def _execute_search(self, action: Action, result: Dict) -> Dict:
        import subprocess
        import urllib.parse
        
        query = action.params.get('query', '')
        engine = action.params.get('engine', 'bing')
        
        encoded = urllib.parse.quote(query)
        urls = {
            'bing': f'https://www.bing.com/search?q={encoded}',
            'google': f'https://www.google.com/search?q={encoded}',
            'baidu': f'https://www.baidu.com/s?wd={encoded}'
        }
        
        url = urls.get(engine, urls['bing'])
        subprocess.Popen(f'start msedge "{url}"', shell=True)
        
        result['success'] = True
        result['output'] = f"搜索: {query} ({engine})"
        return result
    
    def _execute_file_operation(self, action: Action, result: Dict) -> Dict:
        import os
        
        operation = action.params.get('operation', '')
        
        try:
            if operation == 'mkdir':
                path = action.params.get('path', '')
                os.makedirs(path, exist_ok=True)
                result['success'] = True
                result['output'] = f"创建文件夹: {path}"
            elif operation == 'create':
                filename = action.params.get('filename', '')
                content = action.params.get('content', '')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                result['success'] = True
                result['output'] = f"创建文件: {filename}"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _execute_system(self, action: Action, result: Dict) -> Dict:
        operation = action.params.get('operation', '')
        
        if operation == 'screenshot':
            try:
                import pyautogui
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot = pyautogui.screenshot()
                screenshot.save(filename)
                result['success'] = True
                result['output'] = f"截图保存: {filename}"
            except Exception as e:
                result['error'] = str(e)
        else:
            result['error'] = f"未知系统操作: {operation}"
        
        return result


def parse_and_execute(instruction: str, config_path: str = None) -> Tuple[List[Dict], ParsedIntent]:
    parser = SmartParserV2(config_path=config_path)
    executor = ActionExecutorV2()
    
    actions, intent = parser.parse(instruction)
    results = executor.execute_batch(actions)
    
    return results, intent


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python smart_parser_v2.py '打开记事本然后输入123'")
        sys.exit(1)
    
    instruction = sys.argv[1]
    results, intent = parse_and_execute(instruction)
    
    print(f"\n意图: {intent.category.value} (置信度: {intent.confidence:.2f})")
    print("执行结果:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['action']['description']}: {r.get('output', r.get('error', ''))}")
