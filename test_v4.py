#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GodHand v4.0 功能测试"""

import sys
sys.path.insert(0, 'core')

from super_parser import SuperParser

parser = SuperParser()

# 测试 100+ 种指令
tests = [
    # 应用控制
    '打开记事本', '关闭记事本', '最小化窗口', '最大化窗口', '列出所有窗口',
    # 鼠标
    '点击 500, 500', '双击', '右键', '移动鼠标到 800, 600', 
    '拖拽从 100,100 到 500,500', '滚动向下 5', '鼠标位置',
    # 键盘
    '输入 Hello World', '按回车', '快捷键 Ctrl+C', '按 ESC',
    # 文件
    '创建文件 test.txt', '删除文件 test.txt', '复制文件 a.txt 到 b.txt',
    '移动文件 a.txt 到 D:/Backup', '读取文件 test.txt', '文件是否存在 test.txt',
    '文件大小 test.txt', '搜索文件 *.py',
    # 目录
    '创建文件夹 Test', '删除文件夹 Test', '列出目录 C:/Users', '目录大小 C:',
    # 系统
    '关机', '重启', '睡眠', '锁屏', '设置音量 50', '静音', '系统信息', '电池',
    # 截图
    '截图', '截图区域 0,0,500,500', '开始录屏', '停止录屏', '取色',
    # OCR
    '屏幕识别', '识别图片 screenshot.png',
    # 图像
    '打开图片 photo.jpg', '调整大小 800x600', '裁剪图片 0,0,100,100',
    '旋转图片 90', '水平翻转', '模糊', '锐化', '调整亮度 1.5',
    # 浏览器
    '打开 https://www.bing.com', '搜索 Python教程', '后退', '前进', '刷新',
    # Excel
    '打开Excel data.xlsx', '读取单元格 A1', '写入单元格 A1 Hello',
    # 数据
    '读取JSON data.json', '保存CSV output.csv',
    # HTTP
    'GET请求 https://api.github.com', '下载 https://example.com/file.zip',
    # 压缩
    '压缩 folder 到 backup.zip', '解压 backup.zip 到 extract',
    # 剪贴板
    '获取剪贴板', '设置剪贴板 Hello', '清空剪贴板',
    # 定时
    '定时 10 分钟后 锁屏', '延迟 5',
    # 变量
    '设置变量 name = John', '获取变量 name',
    # 其他
    '执行命令 echo Hello', '通知 任务完成', '提示音', '日志 测试消息',
    # 复合指令
    '打开记事本 然后输入Hello World',
]

print('=' * 70)
print('GodHand Pro v4.0 - 超级功能测试 (100+ 种操作)')
print('=' * 70)

success = 0
failed = 0

for t in tests:
    actions = parser.parse(t)
    if actions and actions[0].type.value != 'unknown':
        status = '[OK]'
        success += 1
    else:
        status = '[FAIL]'
        failed += 1
    
    action_type = actions[0].type.value if actions else 'none'
    desc = actions[0].description[:35] if actions else 'No action'
    print(f'{status} {t[:30]:30} -> [{action_type:20}] {desc[:30]}')

print('=' * 70)
print(f'总计: {len(tests)} | 成功: {success} | 失败: {failed} | 支持率: {success/len(tests)*100:.1f}%')
print('=' * 70)
