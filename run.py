#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Runner - 直接执行命令行指令
用法:
  python run.py "打开记事本 然后输入Hello World"
  python run.py --script myscript.txt
  python run.py --record mysession.json
  python run.py --play mysession.json
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_cli import SimpleParser, ActionExecutor, Recorder, HAS_PYAUTOGUI


def run_command(command: str):
    """执行单个命令"""
    print(f"=" * 60)
    print(f"[指令] {command}")
    print(f"=" * 60)

    # 解析
    parser = SimpleParser()
    actions = parser.parse(command)

    if not actions:
        print("[ERROR] 无法解析指令")
        return False

    print(f"\n解析到 {len(actions)} 个动作:")
    for i, action in enumerate(actions, 1):
        print(f"  {i}. {action.type.value}: {action.description}")

    # 执行
    print(f"\n{'='*60}")
    print("开始执行...")
    print(f"{'='*60}")

    executor = ActionExecutor()
    results = executor.execute_batch(actions)

    # 结果
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\n{'='*60}")
    print(f"[完成] {success_count}/{len(results)} 个动作成功")
    print(f"{'='*60}")

    return success_count == len(results)


def run_script(script_file: str):
    """执行脚本文件"""
    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print(f"[脚本] 执行 {script_file}，共 {len(lines)} 行")
        print("=" * 60)

        parser = SimpleParser()
        executor = ActionExecutor()
        total_actions = 0
        success_actions = 0

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            print(f"\n[{i}] {line}")
            actions = parser.parse(line)

            if actions:
                for action in actions:
                    result = executor.execute(action)
                    total_actions += 1
                    if result.get('success'):
                        success_actions += 1
            else:
                print(f"  [ERROR] 无法解析: {line}")

        print(f"\n{'='*60}")
        print(f"[脚本] 执行完成: {success_actions}/{total_actions} 个动作成功")
        print(f"{'='*60}")

        return success_actions == total_actions

    except Exception as e:
        print(f"[ERROR] 脚本执行失败: {e}")
        return False


def record_session(filename: str):
    """录制会话"""
    recorder = Recorder()
    recorder.start_recording()
    recorder.record_file = filename

    print("=" * 60)
    print("[录制模式] 输入命令进行录制，输入 'stop' 停止")
    print("=" * 60)

    while True:
        try:
            cmd = input("\n[录制]> ").strip()
            if cmd.lower() == 'stop':
                recorder.stop_recording()
                break
            if cmd:
                recorder.add_action(cmd)
                # 立即执行以便验证
                run_command(cmd)
        except KeyboardInterrupt:
            recorder.stop_recording()
            break


def play_session(filename: str, delay: float = 1.0):
    """回放会话"""
    recorder = Recorder()
    recorder.load_script(filename)

    parser = SimpleParser()
    executor = ActionExecutor()

    recorder.play(executor, parser, delay)


def main():
    parser = argparse.ArgumentParser(
        description='GodHand Runner - GUI自动化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py "打开记事本 然后输入Hello World"
  python run.py --script auto_login.txt
  python run.py --record session.json
  python run.py --play session.json --delay 2.0

脚本文件格式:
  # 这是注释
  打开记事本
  等待 2
  输入 Hello World
  按 enter
  截图
        """
    )

    parser.add_argument('command', nargs='?', help='要执行的命令')
    parser.add_argument('--script', '-s', help='执行脚本文件')
    parser.add_argument('--record', '-r', help='录制会话到文件')
    parser.add_argument('--play', '-p', help='回放录制的会话')
    parser.add_argument('--delay', '-d', type=float, default=1.0, help='回放间隔(秒)')

    args = parser.parse_args()

    # 如果没有参数，显示帮助
    if not any([args.command, args.script, args.record, args.play]):
        parser.print_help()

        if not HAS_PYAUTOGUI:
            print("\n[WARN] pyautogui 未安装")
            print("安装: pip install pyautogui pyperclip opencv-python")
        return

    # 执行命令
    if args.script:
        success = run_script(args.script)
    elif args.record:
        record_session(args.record)
        success = True
    elif args.play:
        play_session(args.play, args.delay)
        success = True
    elif args.command:
        success = run_command(args.command)
    else:
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
