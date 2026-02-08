#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand v4.0 - 世界级AI自动化平台
集成GUI自动化、浏览器控制、AI智能决策、Web界面
对标Clawdbot的自托管AI助手

功能:
- 🎮 完整GUI自动化 (pyautogui)
- 🌐 浏览器自动化 (selenium)
- 🧠 AI智能决策引擎
- 💾 持久化记忆系统
- 🖥️ Web控制界面
- 📹 录制回放系统
- ⏰ 定时任务调度
- 🔌 插件扩展系统
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 版本信息
VERSION = "4.0.0"
CODENAME = "World Domination"


def print_banner():
    """打印启动横幅"""
    banner = f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██████╗  ██████╗ ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗██████╗  ║
║  ██╔════╝ ██╔═══██╗██╔══██╗██║  ██║██╔══██╗████╗  ██║██╔══██╗ ║
║  ██║  ███╗██║   ██║██║  ██║███████║███████║██╔██╗ ██║██║  ██║ ║
║  ██║   ██║██║   ██║██║  ██║██╔══██║██╔══██║██║╚██╗██║██║  ██║ ║
║  ╚██████╔╝╚██████╔╝██████╔╝██║  ██║██║  ██║██║ ╚████║██████╔╝ ║
║   ╚═════╝  ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ║
║                                                           ║
║              世界级AI自动化平台 v{VERSION}              ║
║                   "{CODENAME}"                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_cli():
    """运行命令行界面"""
    from main_cli import GodHandCLI
    cli = GodHandCLI()
    cli.run()


def run_web():
    """运行Web界面"""
    try:
        # 尝试使用简化版Web UI
        from web_ui_simple import app
        print_banner()
        print("=" * 60)
        print("GodHand Web UI v4.0")
        print("=" * 60)
        print("访问地址: http://localhost:5000")
        print("=" * 60)
        app.run(host='0.0.0.0', port=5000, debug=False)
    except ImportError as e:
        print(f"[ERROR] 无法启动Web UI: {e}")
        print("安装依赖: pip install flask")


def run_command(command: str):
    """执行单个命令"""
    from main_cli import SimpleParser, ActionExecutor
    from core.agent_engine import create_agent

    print_banner()

    # 使用AI Agent处理
    agent = create_agent()
    result = agent.process(command)

    print(f"\n[🧠 AI分析]")
    print(f"  意图: {result['intent']}")
    print(f"  复杂度: {result['intent']['complexity']}")
    print(f"  估计时间: {result['plan'].estimated_time}秒")

    print(f"\n[📋 执行计划]")
    for step in result['plan'].steps:
        print(f"  {step['step_id']}. {step['action']} - {step['description']}")

    print(f"\n[⚡ 开始执行]")
    executor = ActionExecutor()
    executor.parser = SimpleParser()

    results = []
    for step in result['plan'].steps:
        from main_cli import Action, ActionType
        action_type = getattr(ActionType, step['action'].upper(), ActionType.VISUAL_ACTION)
        action = Action(type=action_type, params=step['params'], description=step['description'])
        result = executor.execute(action)
        results.append(result)

    # 学习
    agent.learn_from_result(agent.current_plan, results)

    # 统计
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\n[✅ 完成] {success_count}/{len(results)} 步骤成功")


def run_script(script_file: str):
    """执行脚本文件"""
    from main_cli import SimpleParser, ActionExecutor

    print_banner()

    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"[📜 执行脚本] {script_file}，共 {len(lines)} 行\n")

        parser = SimpleParser()
        executor = ActionExecutor()
        executor.parser = parser

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            print(f"[{i}] {line}")
            actions = parser.parse(line)

            if actions:
                for action in actions:
                    executor.execute(action)
            else:
                print(f"  [❌] 无法解析")

        print(f"\n[✅] 脚本执行完成")

    except Exception as e:
        print(f"[❌] 脚本执行失败: {e}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='GodHand v4.0 - 世界级AI自动化平台',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式CLI
  python godhand.py cli

  # Web界面
  python godhand.py web

  # 执行命令
  python godhand.py cmd "打开记事本 然后输入Hello"

  # 执行脚本
  python godhand.py script myscript.txt

功能模块:
  - GUI自动化: 控制鼠标、键盘、窗口
  - 浏览器自动化: 控制Chrome/Edge
  - AI决策引擎: 自然语言理解、任务规划
  - 记忆系统: 持久化学习
  - Web界面: 可视化控制面板

了解更多: https://github.com/Rrocean/godhand
        """
    )

    parser.add_argument('mode', choices=['cli', 'web', 'cmd', 'script'],
                       help='运行模式')
    parser.add_argument('argument', nargs='?', help='命令或脚本文件')
    parser.add_argument('--version', '-v', action='version', version=f'GodHand v{VERSION}')

    args = parser.parse_args()

    if args.mode == 'cli':
        print_banner()
        run_cli()
    elif args.mode == 'web':
        run_web()
    elif args.mode == 'cmd':
        if not args.argument:
            print("[❌] 请提供要执行的命令")
            print("示例: python godhand.py cmd '打开记事本'")
            return
        run_command(args.argument)
    elif args.mode == 'script':
        if not args.argument:
            print("[❌] 请提供脚本文件")
            print("示例: python godhand.py script myscript.txt")
            return
        run_script(args.argument)


if __name__ == "__main__":
    main()
