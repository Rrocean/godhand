#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claw Runner - 后台命令执行器
像 OpenClaw 一样直接执行，不操作 GUI

特点:
- 理解自然语言
- 转换为系统命令
- 后台静默执行
- 快速稳定
"""

import os
import sys
import json
import re
import subprocess
import shlex
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入 LLM
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ghost_v2 import LLMClient
    HAS_LLM = True
except Exception as e:
    HAS_LLM = False
    logger.debug(f"LLM not available: {e}")


class CommandType(Enum):
    """命令类型"""
    OPEN_APP = "open_app"          # 打开应用
    SYSTEM = "system"              # 系统命令
    FILE = "file"                  # 文件操作
    WEB = "web"                    # 网页/搜索
    SCRIPT = "script"              # 执行脚本
    UNKNOWN = "unknown"            # 未知


@dataclass
class Command:
    """命令"""
    type: CommandType
    command: str                    # 实际执行的命令
    description: str                # 描述
    working_dir: Optional[str] = None
    need_shell: bool = False


class CommandParser:
    """命令解析器 - 将自然语言转换为系统命令"""
    
    # 常见应用映射表
    APP_MAP = {
        # Windows 应用 - 使用 start 启动 GUI 程序避免阻塞
        '计算器': 'start calc.exe',
        'calc': 'start calc.exe',
        '记事本': 'start notepad.exe',
        'notepad': 'start notepad.exe',
        '画图': 'start mspaint.exe',
        'paint': 'start mspaint.exe',
        'cmd': 'start cmd.exe',
        '命令提示符': 'start cmd.exe',
        'powershell': 'start powershell.exe',
        '浏览器': 'start msedge',
        'chrome': 'start chrome',
        'edge': 'start msedge',
        '文件资源管理器': 'explorer.exe',
        'explorer': 'explorer.exe',
        '任务管理器': 'start taskmgr.exe',
        '控制面板': 'control.exe',
        '设置': 'start ms-settings:',
        
        # Office
        'word': 'start winword',
        'excel': 'start excel',
        'powerpoint': 'start powerpnt',
        
        # 开发工具
        'vscode': 'code',
        'idea': 'start idea64',
        'pycharm': 'start pycharm64',
    }
    
    # 文件操作关键词
    FILE_ACTIONS = {
        '创建': 'create',
        '新建': 'create',
        '删除': 'delete',
        '移除': 'delete',
        '打开': 'open',
        '复制': 'copy',
        '粘贴': 'paste',
        '移动': 'move',
        '重命名': 'rename',
    }
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def parse(self, instruction: str) -> List[Command]:
        """解析指令为命令列表"""
        instruction = instruction.strip().lower()
        
        commands = []
        
        # 1. 尝试规则匹配（快速路径）
        cmd = self._rule_based_parse(instruction)
        if cmd:
            commands.append(cmd)
            return commands
        
        # 2. 使用 LLM 解析（复杂指令）
        if HAS_LLM and self.llm:
            commands = self._llm_based_parse(instruction)
        else:
            # 3. 无法解析，返回未知
            commands.append(Command(
                type=CommandType.UNKNOWN,
                command="",
                description=f"无法解析指令: {instruction}"
            ))
        
        return commands
    
    def _rule_based_parse(self, instruction: str) -> Optional[Command]:
        """基于规则的解析"""
        # 模式 1: 打开应用
        # "打开计算器", "启动记事本"
        open_patterns = [
            r'打开\s*(.+?)$',
            r'启动\s*(.+?)$',
            r'运行\s*(.+?)$',
            r'开\s*(.+?)$',
        ]
        
        for pattern in open_patterns:
            match = re.search(pattern, instruction)
            if match:
                app_name = match.group(1).strip()
                return self._create_open_app_command(app_name)
        
        # 模式 2: 搜索
        # "搜索 Python 教程", "百度 Python"
        search_patterns = [
            r'搜索\s*(.+?)$',
            r'查找\s*(.+?)$',
            r'百度\s*(.+?)$',
            r'google\s*(.+?)$',
        ]
        
        for pattern in search_patterns:
            match = re.search(pattern, instruction)
            if match:
                query = match.group(1).strip()
                return Command(
                    type=CommandType.WEB,
                    command=f'start msedge "https://www.bing.com/search?q={query}"',
                    description=f"搜索: {query}"
                )
        
        # 模式 3: 创建文件/文件夹
        # "创建文件夹 Test", "新建文件 test.txt"
        create_patterns = [
            r'创建文件夹\s*(.+?)$',
            r'新建文件夹\s*(.+?)$',
            r'创建目录\s*(.+?)$',
        ]
        
        for pattern in create_patterns:
            match = re.search(pattern, instruction)
            if match:
                folder_name = match.group(1).strip()
                # 使用完整路径
                full_path = os.path.join(os.getcwd(), folder_name)
                return Command(
                    type=CommandType.FILE,
                    command=f'mkdir "{full_path}"',
                    description=f"创建文件夹: {folder_name}",
                    need_shell=True
                )
        
        # 模式 4: 系统命令
        # "关机", "重启"
        if any(word in instruction for word in ['关机', 'shutdown']):
            return Command(
                type=CommandType.SYSTEM,
                command='shutdown /s /t 60',
                description="60秒后关机"
            )
        
        if any(word in instruction for word in ['重启', 'restart', 'reboot']):
            return Command(
                type=CommandType.SYSTEM,
                command='shutdown /r /t 60',
                description="60秒后重启"
            )
        
        if any(word in instruction for word in ['取消关机', '取消重启']):
            return Command(
                type=CommandType.SYSTEM,
                command='shutdown /a',
                description="取消关机/重启"
            )
        
        return None
    
    def _create_open_app_command(self, app_name: str) -> Command:
        """创建打开应用的命令"""
        # 直接匹配
        if app_name in self.APP_MAP:
            exe = self.APP_MAP[app_name]
            return Command(
                type=CommandType.OPEN_APP,
                command=exe,
                description=f"打开应用: {app_name}",
                need_shell=True
            )
        
        # 模糊匹配
        for key, exe in self.APP_MAP.items():
            if key in app_name or app_name in key:
                return Command(
                    type=CommandType.OPEN_APP,
                    command=exe,
                    description=f"打开应用: {key}",
                    need_shell=True
                )
        
        # 未知应用，尝试直接运行
        return Command(
            type=CommandType.OPEN_APP,
            command=f'start "" {app_name}',
            description=f"尝试打开: {app_name}",
            need_shell=True
        )
    
    def _llm_based_parse(self, instruction: str) -> List[Command]:
        """使用 LLM 解析复杂指令"""
        prompt = f"""将用户的自然语言指令转换为 Windows 命令行命令。

用户指令: {instruction}

要求:
1. 返回 JSON 数组格式
2. 每个命令包含 type, command, description 字段
3. 优先使用原生 Windows 命令
4. 复杂任务拆分为多个步骤

示例输出:
[
  {{
    "type": "open_app",
    "command": "calc.exe",
    "description": "打开计算器"
  }},
  {{
    "type": "system",
    "command": "echo Hello > test.txt",
    "description": "创建测试文件"
  }}
]

只返回 JSON，不要其他内容。"""

        try:
            response = self.llm.generate(prompt)
            data = json.loads(response.strip())
            
            commands = []
            for item in data:
                cmd_type = CommandType(item.get('type', 'unknown'))
                commands.append(Command(
                    type=cmd_type,
                    command=item.get('command', ''),
                    description=item.get('description', ''),
                    need_shell=item.get('need_shell', False)
                ))
            return commands
            
        except Exception as e:
            return [Command(
                type=CommandType.UNKNOWN,
                command="",
                description=f"LLM 解析失败: {e}"
            )]


class CommandExecutor:
    """命令执行器"""
    
    def __init__(self):
        self.history: List[Dict] = []
    
    def execute(self, command: Command, dry_run: bool = False) -> Tuple[bool, str]:
        """执行命令"""
        print(f"\n[Command] {command.description}")
        print(f"[Execute] {command.command}")
        
        if dry_run:
            print("[Dry Run] 模拟执行，不实际运行")
            return True, "Dry run"
        
        try:
            # 执行命令
            if command.need_shell:
                result = subprocess.run(
                    command.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                # 安全执行，分割命令
                args = shlex.split(command.command)
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            # 记录结果
            success = result.returncode == 0
            output = result.stdout if success else result.stderr
            
            self.history.append({
                'command': command.command,
                'success': success,
                'output': output
            })
            
            if success:
                print(f"[OK] 执行成功")
                if output:
                    print(f"[Output] {output[:200]}")
            else:
                print(f"[Error] 执行失败: {output}")
            
            return success, output
            
        except subprocess.TimeoutExpired:
            print("[Error] 执行超时")
            return False, "Timeout"
        except Exception as e:
            print(f"[Error] 执行异常: {e}")
            return False, str(e)
    
    def execute_batch(self, commands: List[Command], dry_run: bool = False) -> bool:
        """批量执行命令"""
        all_success = True
        
        for i, cmd in enumerate(commands, 1):
            print(f"\n{'='*60}")
            print(f"[Step {i}/{len(commands)}]")
            success, _ = self.execute(cmd, dry_run)
            if not success:
                all_success = False
                print("[Warn] 此步骤失败，继续执行下一步...")
        
        return all_success


class ClawRunner:
    """Claw Runner - 主类"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        
        # 初始化组件
        if HAS_LLM:
            try:
                self.llm = LLMClient(self.config)
                self.parser = CommandParser(self.llm)
            except Exception as e:
                print(f"[Warn] LLM 初始化失败: {e}，使用纯规则模式")
                self.parser = CommandParser()
        else:
            self.parser = CommandParser()
        
        self.executor = CommandExecutor()
        
        logger.info("[Claw] Claw Runner 初始化完成")
        logger.info("[Claw] 模式: 后台命令执行")
    
    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        default = {
            'provider': 'google',
            'google': {'api_key': os.getenv('GOOGLE_API_KEY', ''), 'model': 'gemini-2.0-flash'}
        }
        
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except:
                pass
        
        return default
    
    def run(self, instruction: str, dry_run: bool = False) -> bool:
        """执行指令"""
        logger.info(f"\n{'='*60}")
        logger.info(f"[Input] {instruction}")
        logger.info(f"{'='*60}")
        
        # 1. 解析指令
        logger.info("\n[Parse] 解析指令...")
        commands = self.parser.parse(instruction)
        
        if not commands:
            logger.error("[Error] 无法解析指令")
            return False
        
        print(f"[Parse] 解析为 {len(commands)} 个命令")
        for i, cmd in enumerate(commands):
            print(f"  {i+1}. [{cmd.type.value}] {cmd.description}")
        
        # 2. 执行命令
        print(f"\n{'='*60}")
        print("[Execute] 开始执行")
        print(f"{'='*60}")
        
        success = self.executor.execute_batch(commands, dry_run)
        
        # 3. 结果
        print(f"\n{'='*60}")
        if success:
            print("[Result] 全部执行成功！")
        else:
            print("[Result] 部分执行失败")
        print(f"{'='*60}")
        
        return success


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Claw Runner - 后台命令执行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python claw_runner.py "打开计算器"
  python claw_runner.py "创建文件夹 Test"
  python claw_runner.py "搜索 Python 教程"
  python claw_runner.py "打开记事本" --dry-run

特点:
  - 后台执行，不操作鼠标键盘
  - 速度快（毫秒级响应）
  - 稳定可靠
  - 支持复杂任务分解
        """
    )
    
    parser.add_argument('instruction', nargs='?', help='自然语言指令')
    parser.add_argument('--dry-run', '-n', action='store_true', help='模拟执行，不实际运行')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件')
    
    args = parser.parse_args()
    
    if not args.instruction:
        parser.print_help()
        return
    
    # 创建并运行
    runner = ClawRunner(config_path=args.config)
    runner.run(args.instruction, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
