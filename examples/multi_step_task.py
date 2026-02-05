#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多步骤任务示例 - 文件操作
"""
import sys
sys.path.insert(0, '..')

from ghost import GhostHand

def main():
    ghost = GhostHand()
    
    # 复杂的跨应用工作流
    task = """
    请完成以下任务：
    1. 打开文件资源管理器
    2. 导航到下载文件夹
    3. 创建一个新的文件夹叫"GhostTest"
    4. 在文件夹内右键新建一个文本文档
    5. 命名为"test.txt"
    """
    
    success = ghost.run(task, max_steps=30)
    
    if success:
        print("✅ 任务成功完成！")
    else:
        print("❌ 任务未完成，请检查屏幕状态")

if __name__ == "__main__":
    main()
