#!/usr/bin/env python3
"""
GodHand CLI - 命令行工具
"""

import sys
import argparse
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.ghost_v2 import GhostHandPro


def main():
    parser = argparse.ArgumentParser(
        description='GodHand - 智能GUI自动化工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python cli.py "打开计算器"
  python cli.py "点击开始菜单"
  python cli.py "在记事本中输入Hello World"
  python cli.py --stats
        '''
    )
    
    parser.add_argument(
        'instruction',
        nargs='?',
        help='要执行的指令'
    )
    parser.add_argument(
        '--config', '-c',
        default='config.json',
        help='配置文件路径 (默认: config.json)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='显示统计信息'
    )
    parser.add_argument(
        '--list-examples',
        action='store_true',
        help='显示示例指令'
    )
    
    args = parser.parse_args()
    
    if args.list_examples:
        print("=" * 60)
        print("GodHand 示例指令")
        print("=" * 60)
        examples = [
            ("打开计算器", "打开Windows计算器"),
            ("点击开始菜单", "点击屏幕左下角的开始按钮"),
            ("在记事本中输入Hello", "打开记事本并输入文字"),
            ("截图", "截取当前屏幕"),
            ("关闭当前窗口", "点击关闭按钮"),
            ("打开浏览器搜索Python", "打开Edge并搜索"),
        ]
        for cmd, desc in examples:
            print(f"  {cmd:<30} # {desc}")
        print("=" * 60)
        return
    
    if args.stats:
        print("统计功能：运行任务后查看日志文件")
        return
    
    if not args.instruction:
        parser.print_help()
        print("\n使用 --list-examples 查看示例指令")
        return
    
    # 执行指令
    try:
        print(f"🖐️ GodHand 启动...")
        print(f"指令: {args.instruction}")
        print("-" * 60)
        
        ghost = GhostHandPro(config_path=args.config)
        success = ghost.execute(args.instruction)
        
        print("-" * 60)
        if success:
            print("✅ 任务完成")
        else:
            print("❌ 任务失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
