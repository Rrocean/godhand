#!/usr/bin/env python3
"""
Super Parser - 超级解析器 v4.0
支持 100+ 种自然语言指令
"""

import re
from typing import List, Optional
from actions_v4 import Action, ActionType


class SuperParser:
    """超级解析器"""
    
    def __init__(self):
        # 应用别名
        self.apps = {
            '计算器': 'calc', '记事本': 'notepad', '画图': 'mspaint',
            'cmd': 'cmd', '命令提示符': 'cmd', 'powershell': 'powershell',
            '任务管理器': 'taskmgr', '设置': 'ms-settings:',
            '浏览器': 'msedge', 'edge': 'msedge', 'chrome': 'chrome',
            'word': 'winword', 'excel': 'excel', 'ppt': 'powerpnt',
            'vscode': 'code', '微信': 'wechat', 'qq': 'qq',
        }
        
        # 按键别名
        self.keys = {
            '回车': 'enter', '空格': 'space', '退格': 'backspace',
            '删除': 'delete', 'esc': 'escape',
            '上': 'up', '下': 'down', '左': 'left', '右': 'right',
            'tab': 'tab', 'ctrl': 'ctrl', 'alt': 'alt', 'shift': 'shift',
            'win': 'win', 'f1': 'f1', 'f2': 'f2', 'f12': 'f12',
        }
        
        # 图像滤镜
        self.img_filters = ['模糊', '锐化', '边缘', '轮廓', '浮雕', '平滑']
        
        # HTTP方法
        self.http_methods = ['get', 'post', 'put', 'delete', 'patch', 'head']
    
    def parse(self, instruction: str) -> List[Action]:
        """解析指令 - 主入口"""
        instruction = instruction.strip()
        if not instruction:
            return []
        
        # 尝试复合指令
        composite = self._parse_composite(instruction)
        if composite:
            return composite
        
        # 单条指令
        action = self._parse_single(instruction)
        return [action] if action else []
    
    def _parse_composite(self, instruction: str) -> Optional[List[Action]]:
        """解析复合指令"""
        actions = []
        
        # 模式1: A然后B然后C
        pattern1 = r'(.+?)(?:然后|再|接着|之后|>|→)(.+)'  
        match = re.search(pattern1, instruction)
        if match:
            left = match.group(1).strip()
            right = match.group(2).strip()
            
            left_actions = self.parse(left)
            right_actions = self.parse(right)
            
            actions.extend(left_actions)
            # 如果是打开应用后执行操作，添加等待
            if left_actions and left_actions[0].type == ActionType.APP_OPEN:
                actions.append(Action(
                    ActionType.WAIT,
                    {'seconds': 1.5},
                    '等待应用启动',
                    1.0
                ))
            actions.extend(right_actions)
            return actions
        
        return None
    
    def _parse_single(self, instruction: str) -> Optional[Action]:
        """解析单条指令"""
        inst = instruction.lower().strip()
        
        # ==================== 应用控制 ====================
        if self._match(inst, [r'打开\s*(.+)', r'启动\s*(.+)', r'运行\s*(.+)']):
            app = self._extract(inst, [r'打开\s*(.+)', r'启动\s*(.+)', r'运行\s*(.+)'])
            return Action(ActionType.APP_OPEN, {'app': self._resolve_app(app)}, f'打开应用: {app}')
        
        if self._match(inst, [r'关闭\s*(.+)', r'退出\s*(.+)', r'杀掉\s*(.+)']):
            app = self._extract(inst, [r'关闭\s*(.+)', r'退出\s*(.+)', r'杀掉\s*(.+)'])
            return Action(ActionType.APP_CLOSE, {'app': app}, f'关闭应用: {app}')
        
        if self._match(inst, ['最小化', '缩小']):
            return Action(ActionType.WINDOW_MINIMIZE, {}, '最小化窗口')
        
        if self._match(inst, ['最大化', '放大']):
            return Action(ActionType.WINDOW_MAXIMIZE, {}, '最大化窗口')
        
        if self._match(inst, ['列出窗口', '所有窗口', '窗口列表']):
            return Action(ActionType.WINDOW_LIST, {}, '列出所有窗口')
        
        # ==================== 鼠标操作 ====================
        if self._match(inst, [r'点击\s*(\d+)\s*,\s*(\d+)']):
            x, y = self._extract_coords(inst, r'点击\s*(\d+)\s*,\s*(\d+)')
            return Action(ActionType.MOUSE_CLICK, {'x': x, 'y': y}, f'点击 ({x}, {y})')
        
        if self._match(inst, ['点击', '单击', '左键']):
            return Action(ActionType.MOUSE_CLICK, {}, '点击鼠标左键')
        
        if self._match(inst, ['双击', 'double click']):
            return Action(ActionType.MOUSE_DOUBLE_CLICK, {}, '双击鼠标')
        
        if self._match(inst, ['右键', '右击', 'right click']):
            return Action(ActionType.MOUSE_RIGHT_CLICK, {}, '点击鼠标右键')
        
        if self._match(inst, ['中键', 'middle click']):
            return Action(ActionType.MOUSE_MIDDLE_CLICK, {}, '点击鼠标中键')
        
        if self._match(inst, [r'移动\s*(?:鼠标)?\s*(?:到)?\s*(\d+)\s*,\s*(\d+)']):
            x, y = self._extract_coords(inst, r'移动\s*(?:鼠标)?\s*(?:到)?\s*(\d+)\s*,\s*(\d+)')
            return Action(ActionType.MOUSE_MOVE, {'x': x, 'y': y}, f'移动鼠标到 ({x}, {y})')
        
        if self._match(inst, [r'拖拽\s*(?:从)?\s*(\d+)\s*,\s*(\d+)\s*(?:到)?\s*(\d+)\s*,\s*(\d+)']):
            coords = re.findall(r'(\d+)', inst)
            if len(coords) >= 4:
                return Action(ActionType.MOUSE_DRAG, 
                    {'x1': int(coords[0]), 'y1': int(coords[1]), 'x2': int(coords[2]), 'y2': int(coords[3])},
                    f'拖拽从 ({coords[0]}, {coords[1]}) 到 ({coords[2]}, {coords[3]})')
        
        if self._match(inst, [r'滚动\s*(向上|向下|up|down)?\s*(\d+)?']):
            direction = 1 if '下' in inst or 'down' in inst else -1
            amount = self._extract_number(inst) or 3
            return Action(ActionType.MOUSE_SCROLL, {'amount': amount * direction}, f'滚动 {amount}')
        
        if self._match(inst, ['鼠标位置', '获取鼠标位置']):
            return Action(ActionType.MOUSE_POSITION, {}, '获取鼠标位置')
        
        # ==================== 键盘操作 ====================
        if self._match(inst, [r'输入\s*(.+)', r'打字\s*(.+)', r'键入\s*(.+)']):
            text = self._extract(inst, [r'输入\s*(.+)', r'打字\s*(.+)', r'键入\s*(.+)'])
            return Action(ActionType.KEYBOARD_TYPE, {'text': text}, f'输入: {text[:20]}...')
        
        if self._match(inst, [r'按\s*(.+?)(?:键)?$', r'按下\s*(.+)']):
            key = self._extract(inst, [r'按\s*(.+?)(?:键)?$', r'按下\s*(.+)'])
            return Action(ActionType.KEYBOARD_PRESS, {'key': self._resolve_key(key)}, f'按键: {key}')
        
        if self._match(inst, [r'快捷键\s*(.+)', r'组合键\s*(.+)']):
            keys = self._extract(inst, [r'快捷键\s*(.+)', r'组合键\s*(.)'])
            return Action(ActionType.KEYBOARD_HOTKEY, {'keys': keys.split('+')}, f'快捷键: {keys}')
        
        # ==================== 文件操作 ====================
        if self._match(inst, [r'创建文件\s*(.+)', r'新建文件\s*(.+)']):
            path = self._extract(inst, [r'创建文件\s*(.+)', r'新建文件\s*(.+)'])
            return Action(ActionType.FILE_CREATE, {'path': path}, f'创建文件: {path}')
        
        if self._match(inst, [r'删除文件\s*(.+)', r'移除文件\s*(.+)']):
            path = self._extract(inst, [r'删除文件\s*(.+)', r'移除文件\s*(.+)'])
            return Action(ActionType.FILE_DELETE, {'path': path}, f'删除文件: {path}')
        
        if self._match(inst, [r'复制文件\s*(.+?)\s*到\s*(.+)']):
            src, dst = self._extract_two(inst, r'复制文件\s*(.+?)\s*到\s*(.+)')
            return Action(ActionType.FILE_COPY, {'src': src, 'dst': dst}, f'复制文件: {src} -> {dst}')
        
        if self._match(inst, [r'移动文件\s*(.+?)\s*到\s*(.+)']):
            src, dst = self._extract_two(inst, r'移动文件\s*(.+?)\s*到\s*(.+)')
            return Action(ActionType.FILE_MOVE, {'src': src, 'dst': dst}, f'移动文件: {src} -> {dst}')
        
        if self._match(inst, [r'读取文件\s*(.+)', r'查看文件\s*(.+)']):
            path = self._extract(inst, [r'读取文件\s*(.+)', r'查看文件\s*(.+)'])
            return Action(ActionType.FILE_READ, {'path': path}, f'读取文件: {path}')
        
        if self._match(inst, [r'写入文件\s*(.+?)\s*(.+)']):
            path, content = self._extract_two(inst, r'写入文件\s*(.+?)\s*(.+)')
            return Action(ActionType.FILE_WRITE, {'path': path, 'content': content}, f'写入文件: {path}')
        
        if self._match(inst, [r'文件是否存在\s*(.+)']):
            path = self._extract(inst, [r'文件是否存在\s*(.+)'])
            return Action(ActionType.FILE_EXISTS, {'path': path}, f'检查文件是否存在: {path}')
        
        if self._match(inst, [r'文件大小\s*(.+)']):
            path = self._extract(inst, [r'文件大小\s*(.+)'])
            return Action(ActionType.FILE_SIZE, {'path': path}, f'获取文件大小: {path}')
        
        if self._match(inst, [r'搜索文件\s*(.+)', r'查找文件\s*(.+)']):
            pattern = self._extract(inst, [r'搜索文件\s*(.+)', r'查找文件\s*(.+)'])
            return Action(ActionType.FILE_SEARCH, {'pattern': pattern}, f'搜索文件: {pattern}')
        
        # ==================== 目录操作 ====================
        if self._match(inst, [r'创建文件夹\s*(.+)', r'创建目录\s*(.+)', r'新建文件夹\s*(.+)']):
            path = self._extract(inst, [r'创建文件夹\s*(.+)', r'创建目录\s*(.+)', r'新建文件夹\s*(.+)'])
            return Action(ActionType.DIR_CREATE, {'path': path}, f'创建目录: {path}')
        
        if self._match(inst, [r'删除文件夹\s*(.+)', r'删除目录\s*(.+)']):
            path = self._extract(inst, [r'删除文件夹\s*(.+)', r'删除目录\s*(.+)'])
            return Action(ActionType.DIR_DELETE, {'path': path, 'recursive': True}, f'删除目录: {path}')
        
        if self._match(inst, [r'列出目录\s*(.+)', r'ls\s*(.+)', r'dir\s*(.+)']):
            path = self._extract(inst, [r'列出目录\s*(.+)', r'ls\s*(.+)', r'dir\s*(.+)']) or '.'
            return Action(ActionType.DIR_LIST, {'path': path}, f'列出目录: {path}')
        
        if self._match(inst, [r'目录大小\s*(.+)']):
            path = self._extract(inst, [r'目录大小\s*(.+)'])
            return Action(ActionType.DIR_SIZE, {'path': path}, f'获取目录大小: {path}')
        
        if self._match(inst, [r'搜索目录\s*(.+)']):
            path = self._extract(inst, [r'搜索目录\s*(.+)'])
            return Action(ActionType.DIR_SEARCH, {'path': path}, f'搜索目录: {path}')
        
        # ==================== 系统控制 ====================
        if self._match(inst, ['关机', '关闭电脑', 'shutdown']):
            delay = self._extract_number(inst) or 60
            return Action(ActionType.SYS_SHUTDOWN, {'delay': delay}, f'关机 (延迟 {delay} 秒)')
        
        if self._match(inst, ['重启', '重新启动', 'restart']):
            delay = self._extract_number(inst) or 60
            return Action(ActionType.SYS_RESTART, {'delay': delay}, f'重启 (延迟 {delay} 秒)')
        
        if self._match(inst, ['睡眠', '休眠', 'sleep']):
            return Action(ActionType.SYS_SLEEP, {}, '进入睡眠模式')
        
        if self._match(inst, ['锁屏', '锁定', 'lock']):
            return Action(ActionType.SYS_LOCK, {}, '锁定屏幕')
        
        if self._match(inst, ['注销', 'logoff']):
            return Action(ActionType.SYS_LOGOFF, {}, '注销用户')
        
        if self._match(inst, [r'设置音量\s*(\d+)', r'音量\s*(\d+)']):
            level = self._extract_number(inst) or 50
            return Action(ActionType.SYS_VOLUME_SET, {'level': level}, f'设置音量: {level}%')
        
        if self._match(inst, ['静音', 'mute']):
            return Action(ActionType.SYS_VOLUME_MUTE, {}, '静音')
        
        if self._match(inst, ['获取音量', '当前音量']):
            return Action(ActionType.SYS_VOLUME_GET, {}, '获取当前音量')
        
        if self._match(inst, ['系统信息', '电脑信息', 'sysinfo']):
            return Action(ActionType.SYS_INFO, {}, '获取系统信息')
        
        if self._match(inst, ['电池', '电量', 'battery']):
            return Action(ActionType.SYS_BATTERY, {}, '获取电池信息')
        
        # ==================== 截图录屏 ====================
        if self._match(inst, ['截图', '截屏', 'screenshot', 'snapshot']):
            return Action(ActionType.SCREENSHOT, {}, '截取屏幕')
        
        if self._match(inst, [r'截图区域\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)']):
            coords = re.findall(r'(\d+)', inst)
            return Action(ActionType.SCREENSHOT_REGION, 
                {'x': int(coords[0]), 'y': int(coords[1]), 'w': int(coords[2]), 'h': int(coords[3])},
                f'截图区域 ({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]})')
        
        if self._match(inst, ['开始录屏', '录制屏幕', 'screen record start']):
            return Action(ActionType.SCREEN_RECORD_START, {}, '开始屏幕录制')
        
        if self._match(inst, ['停止录屏', '结束录制', 'screen record stop']):
            return Action(ActionType.SCREEN_RECORD_STOP, {}, '停止屏幕录制')
        
        if self._match(inst, ['取色', '获取颜色', 'color pick']):
            return Action(ActionType.SCREEN_COLOR_PICK, {}, '获取屏幕颜色')
        
        # ==================== OCR ====================
        if self._match(inst, ['屏幕识别', '屏幕文字', 'ocr screen']):
            return Action(ActionType.OCR_SCREEN, {}, '识别屏幕文字')
        
        if self._match(inst, [r'识别图片\s*(.+)']):
            path = self._extract(inst, [r'识别图片\s*(.+)'])
            return Action(ActionType.OCR_IMAGE, {'path': path}, f'识别图片文字: {path}')
        
        # ==================== 图像处理 ====================
        if self._match(inst, [r'打开图片\s*(.+)']):
            path = self._extract(inst, [r'打开图片\s*(.+)'])
            return Action(ActionType.IMG_OPEN, {'path': path}, f'打开图片: {path}')
        
        if self._match(inst, [r'保存图片\s*(.+)']):
            path = self._extract(inst, [r'保存图片\s*(.+)'])
            return Action(ActionType.IMG_SAVE, {'path': path}, f'保存图片: {path}')
        
        if self._match(inst, [r'调整大小\s*(\d+)\s*x\s*(\d+)']):
            w, h = self._extract_coords(inst, r'(\d+)\s*x\s*(\d+)')
            return Action(ActionType.IMG_RESIZE, {'width': w, 'height': h}, f'调整图片大小为 {w}x{h}')
        
        if self._match(inst, [r'裁剪图片\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)']):
            coords = re.findall(r'(\d+)', inst)
            return Action(ActionType.IMG_CROP,
                {'x': int(coords[0]), 'y': int(coords[1]), 'w': int(coords[2]), 'h': int(coords[3])},
                f'裁剪图片 ({coords[0]}, {coords[1]}, {coords[2]}, {coords[3]})')
        
        if self._match(inst, [r'旋转图片\s*(\d+)']):
            angle = self._extract_number(inst) or 90
            return Action(ActionType.IMG_ROTATE, {'angle': angle}, f'旋转图片 {angle} 度')
        
        if self._match(inst, ['水平翻转', '左右翻转']):
            return Action(ActionType.IMG_FLIP, {'direction': 'horizontal'}, '水平翻转图片')
        
        if self._match(inst, ['垂直翻转', '上下翻转']):
            return Action(ActionType.IMG_FLIP, {'direction': 'vertical'}, '垂直翻转图片')
        
        if self._match(inst, ['模糊', '高斯模糊']):
            return Action(ActionType.IMG_FILTER, {'filter': 'blur'}, '应用模糊滤镜')
        
        if self._match(inst, ['锐化', 'sharpen']):
            return Action(ActionType.IMG_FILTER, {'filter': 'sharpen'}, '应用锐化滤镜')
        
        if self._match(inst, ['调整亮度\s*(\d+)']):
            value = self._extract_number(inst) or 1.0
            return Action(ActionType.IMG_ADJUST, {'type': 'brightness', 'value': value}, f'调整亮度: {value}')
        
        if self._match(inst, ['调整对比度\s*(\d+)']):
            value = self._extract_number(inst) or 1.0
            return Action(ActionType.IMG_ADJUST, {'type': 'contrast', 'value': value}, f'调整对比度: {value}')
        
        if self._match(inst, ['压缩图片', '图片压缩']):
            return Action(ActionType.IMG_COMPRESS, {}, '压缩图片')
        
        if self._match(inst, [r'转换格式\s*(.+)']):
            fmt = self._extract(inst, [r'转换格式\s*(.+)'])
            return Action(ActionType.IMG_CONVERT, {'format': fmt}, f'转换图片格式为 {fmt}')
        
        # ==================== 浏览器 ====================
        if self._match(inst, [r'打开网址\s*(.+)', r'访问\s*(.+)', r'打开\s*(https?://\S+)']):
            url = self._extract(inst, [r'打开网址\s*(.+)', r'访问\s*(.+)', r'打开\s*(https?://\S+)'])
            return Action(ActionType.BROWSER_OPEN, {'url': url}, f'打开网址: {url}')
        
        if self._match(inst, [r'搜索\s*(.+)', r'百度\s*(.+)', r'google\s*(.+)']):
            query = self._extract(inst, [r'搜索\s*(.+)', r'百度\s*(.+)', r'google\s*(.+)'])
            return Action(ActionType.BROWSER_SEARCH, {'query': query}, f'搜索: {query}')
        
        if self._match(inst, ['后退', '返回', 'back']):
            return Action(ActionType.BROWSER_BACK, {}, '浏览器后退')
        
        if self._match(inst, ['前进', 'forward']):
            return Action(ActionType.BROWSER_FORWARD, {}, '浏览器前进')
        
        if self._match(inst, ['刷新', 'reload', 'refresh']):
            return Action(ActionType.BROWSER_REFRESH, {}, '刷新页面')
        
        if self._match(inst, ['关闭浏览器', '关闭标签']):
            return Action(ActionType.BROWSER_CLOSE, {}, '关闭浏览器标签')
        
        if self._match(inst, ['获取网址', '当前网址', 'get url']):
            return Action(ActionType.BROWSER_GET_URL, {}, '获取当前网址')
        
        # ==================== Excel ====================
        if self._match(inst, [r'打开Excel\s*(.+)', r'打开excel\s*(.+)']):
            path = self._extract(inst, [r'打开Excel\s*(.+)', r'打开excel\s*(.+)'])
            return Action(ActionType.EXCEL_OPEN, {'path': path}, f'打开Excel: {path}')
        
        if self._match(inst, [r'新建Excel\s*(.+)?']):
            path = self._extract(inst, [r'新建Excel\s*(.+)?']) or '新建.xlsx'
            return Action(ActionType.EXCEL_CREATE, {'path': path}, f'新建Excel: {path}')
        
        if self._match(inst, [r'读取单元格\s*(\w+\d+)']):
            cell = self._extract(inst, [r'读取单元格\s*(\w+\d+)'])
            return Action(ActionType.EXCEL_READ_CELL, {'cell': cell}, f'读取单元格: {cell}')
        
        if self._match(inst, [r'写入单元格\s*(\w+\d+)\s*(.+)']):
            cell, value = self._extract_two(inst, r'写入单元格\s*(\w+\d+)\s*(.+)')
            return Action(ActionType.EXCEL_WRITE_CELL, {'cell': cell, 'value': value}, f'写入单元格 {cell}: {value}')
        
        if self._match(inst, [r'保存Excel']):
            return Action(ActionType.EXCEL_SAVE, {}, '保存Excel')
        
        # ==================== 数据处理 ====================
        if self._match(inst, [r'读取JSON\s*(.+)']):
            path = self._extract(inst, [r'读取JSON\s*(.+)'])
            return Action(ActionType.DATA_JSON_READ, {'path': path}, f'读取JSON: {path}')
        
        if self._match(inst, [r'保存JSON\s*(.+)']):
            path = self._extract(inst, [r'保存JSON\s*(.+)'])
            return Action(ActionType.DATA_JSON_WRITE, {'path': path}, f'保存JSON: {path}')
        
        if self._match(inst, [r'读取CSV\s*(.+)']):
            path = self._extract(inst, [r'读取CSV\s*(.+)'])
            return Action(ActionType.DATA_CSV_READ, {'path': path}, f'读取CSV: {path}')
        
        if self._match(inst, [r'保存CSV\s*(.+)']):
            path = self._extract(inst, [r'保存CSV\s*(.+)'])
            return Action(ActionType.DATA_CSV_WRITE, {'path': path}, f'保存CSV: {path}')
        
        # ==================== HTTP请求 ====================
        if self._match(inst, [r'GET请求\s*(.+)', r'get\s*(.+)']):
            url = self._extract(inst, [r'GET请求\s*(.+)', r'get\s*(.+)'])
            return Action(ActionType.HTTP_GET, {'url': url}, f'GET请求: {url}')
        
        if self._match(inst, [r'POST请求\s*(.+)']):
            url = self._extract(inst, [r'POST请求\s*(.+)'])
            return Action(ActionType.HTTP_POST, {'url': url}, f'POST请求: {url}')
        
        if self._match(inst, [r'下载\s*(.+?)\s*(?:到|to)?\s*(.+)?']):
            url, path = self._extract_two_optional(inst, r'下载\s*(.+?)\s*(?:到|to)?\s*(.+)?')
            return Action(ActionType.HTTP_DOWNLOAD, {'url': url, 'path': path}, f'下载: {url}')
        
        # ==================== 压缩解压 ====================
        if self._match(inst, [r'压缩\s*(.+?)\s*(?:到|to)?\s*(.+)']):
            src, dst = self._extract_two(inst, r'压缩\s*(.+?)\s*(?:到|to)?\s*(.+)')
            return Action(ActionType.ZIP_CREATE, {'src': src, 'dst': dst}, f'压缩: {src} -> {dst}')
        
        if self._match(inst, [r'解压\s*(.+?)\s*(?:到|to)?\s*(.+)']):
            src, dst = self._extract_two(inst, r'解压\s*(.+?)\s*(?:到|to)?\s*(.+)')
            return Action(ActionType.ZIP_EXTRACT, {'src': src, 'dst': dst}, f'解压: {src} -> {dst}')
        
        # ==================== 剪贴板 ====================
        if self._match(inst, ['获取剪贴板', '查看剪贴板', 'clipboard get']):
            return Action(ActionType.CLIPBOARD_GET, {}, '获取剪贴板内容')
        
        if self._match(inst, [r'设置剪贴板\s*(.+)', r'复制到剪贴板\s*(.+)']):
            content = self._extract(inst, [r'设置剪贴板\s*(.+)', r'复制到剪贴板\s*(.+)'])
            return Action(ActionType.CLIPBOARD_SET, {'content': content}, f'设置剪贴板: {content[:20]}...')
        
        if self._match(inst, ['清空剪贴板', '清除剪贴板', 'clipboard clear']):
            return Action(ActionType.CLIPBOARD_CLEAR, {}, '清空剪贴板')
        
        # ==================== 定时任务 ====================
        if self._match(inst, [r'定时\s*(\d+)\s*(秒|分钟|小时)?\s*(?:后)?\s*(.+)']):
            match = re.search(r'定时\s*(\d+)\s*(秒|分钟|小时)?\s*(?:后)?\s*(.+)', inst)
            if match:
                amount, unit, cmd = match.groups()
                return Action(ActionType.SCHEDULE_CREATE, 
                    {'amount': int(amount), 'unit': unit or '秒', 'command': cmd},
                    f'定时 {amount}{unit or "秒"}后执行: {cmd}')
        
        if self._match(inst, ['延迟\s*(\d+)']):
            seconds = self._extract_number(inst) or 1
            return Action(ActionType.WAIT, {'seconds': seconds}, f'等待 {seconds} 秒')
        
        # ==================== 流程控制 ====================
        if self._match(inst, ['等待', 'wait']):
            seconds = self._extract_number(inst) or 1
            return Action(ActionType.WAIT, {'seconds': seconds}, f'等待 {seconds} 秒')
        
        if self._match(inst, [r'等待直到\s*(.+)']):
            condition = self._extract(inst, [r'等待直到\s*(.+)'])
            return Action(ActionType.WAIT_UNTIL, {'condition': condition}, f'等待直到: {condition}')
        
        # ==================== 变量操作 ====================
        if self._match(inst, [r'设置变量\s*(\w+)\s*=\s*(.+)']):
            name, value = self._extract_two(inst, r'设置变量\s*(\w+)\s*=\s*(.+)')
            return Action(ActionType.VAR_SET, {'name': name, 'value': value}, f'设置变量 {name} = {value}')
        
        if self._match(inst, [r'获取变量\s*(\w+)']):
            name = self._extract(inst, [r'获取变量\s*(\w+)'])
            return Action(ActionType.VAR_GET, {'name': name}, f'获取变量: {name}')
        
        # ==================== 其他 ====================
        if self._match(inst, [r'执行命令\s*(.+)', r'cmd\s*(.+)']):
            cmd = self._extract(inst, [r'执行命令\s*(.+)', r'cmd\s*(.+)'])
            return Action(ActionType.COMMAND, {'command': cmd}, f'执行命令: {cmd}')
        
        if self._match(inst, [r'通知\s*(.+)', r'提醒\s*(.+)']):
            msg = self._extract(inst, [r'通知\s*(.+)', r'提醒\s*(.+)'])
            return Action(ActionType.NOTIFY, {'message': msg}, f'通知: {msg}')
        
        if self._match(inst, ['提示音', 'beep', '响铃']):
            return Action(ActionType.BEEP, {}, '播放提示音')
        
        if self._match(inst, [r'日志\s*(.+)']):
            msg = self._extract(inst, [r'日志\s*(.+)'])
            return Action(ActionType.LOG, {'message': msg}, f'记录日志: {msg}')
        
        # 未知指令
        return Action(ActionType.UNKNOWN, {'raw': instruction}, f'未知指令: {instruction}', 0.0)
    
    # ==================== 辅助方法 ====================
    
    def _match(self, text: str, patterns: list) -> bool:
        """匹配任意模式"""
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return True
        return False
    
    def _extract(self, text: str, patterns: list) -> str:
        """提取第一个匹配"""
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    def _extract_two(self, text: str, pattern: str) -> tuple:
        """提取两个值"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match and len(match.groups()) >= 2:
            return match.group(1).strip(), match.group(2).strip()
        return '', ''
    
    def _extract_two_optional(self, text: str, pattern: str) -> tuple:
        """提取两个值（第二个可选）"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            g1 = match.group(1).strip() if match.group(1) else ''
            g2 = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
            return g1, g2
        return '', None
    
    def _extract_coords(self, text: str, pattern: str) -> tuple:
        """提取坐标"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 0, 0
    
    def _extract_number(self, text: str) -> Optional[int]:
        """提取数字"""
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None
    
    def _resolve_app(self, name: str) -> str:
        """解析应用名称"""
        return self.apps.get(name.lower(), name)
    
    def _resolve_key(self, key: str) -> str:
        """解析按键名称"""
        return self.keys.get(key.lower(), key)


# 便捷函数
def parse(instruction: str) -> List[Action]:
    """便捷解析函数"""
    parser = SuperParser()
    return parser.parse(instruction)


if __name__ == "__main__":
    # 测试
    tests = [
        "打开记事本然后输入Hello",
        "点击 500, 500",
        "截图",
        "搜索 Python教程",
        "创建文件夹 Test",
        "音量设置到 50",
        "下载 https://example.com/file.zip 到 D:\\Downloads",
        "定时 5 分钟后 锁屏",
        "获取剪贴板",
        "设置变量 name = John",
    ]
    
    parser = SuperParser()
    for t in tests:
        print(f"\n指令: {t}")
        actions = parser.parse(t)
        for a in actions:
            print(f"  -> [{a.type.value}] {a.description}")
