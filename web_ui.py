#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Web UI - Web界面控制面板
提供类似Clawdbot的Web控制界面
"""

import os
import sys
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入Flask
try:
    from flask import Flask, render_template, jsonify, request, send_from_directory
    from flask_socketio import SocketIO, emit
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("[WARN] Flask未安装，Web UI不可用")
    print("  安装: pip install flask flask-socketio")

from main_cli import SimpleParser, ActionExecutor, Config, Logger, Recorder, TaskScheduler
from core.agent_engine import create_agent
from core.browser_automation import create_browser


class GodHandWebUI:
    """GodHand Web界面"""

    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__) if HAS_FLASK else None
        self.socketio = SocketIO(self.app, cors_allowed_origins="*") if HAS_FLASK else None
        self.config = Config()
        self.logger = Logger()
        self.parser = SimpleParser()
        self.executor = ActionExecutor()
        self.executor.parser = self.parser
        self.agent = create_agent()
        self.browser = create_browser()
        self.recorder = Recorder()
        self.scheduler = TaskScheduler()
        self.is_running = False
        self.execution_log: List[Dict] = []

        if HAS_FLASK:
            self._setup_routes()
            self._setup_socketio()

    def _setup_routes(self):
        """设置路由"""

        @self.app.route('/')
        def index():
            return render_template('dashboard.html')

        @self.app.route('/api/status')
        def status():
            return jsonify({
                'status': 'running',
                'version': '3.3',
                'uptime': self._get_uptime(),
                'executions': len(self.execution_log)
            })

        @self.app.route('/api/execute', methods=['POST'])
        def execute():
            data = request.json
            command = data.get('command', '')

            # 使用AI Agent处理
            result = self.agent.process(command)

            # 执行计划
            actions_result = []
            for step in result['plan'].steps:
                action_result = self._execute_step(step)
                actions_result.append(action_result)

                # 发送实时更新
                if self.socketio:
                    self.socketio.emit('step_complete', {
                        'step': step,
                        'result': action_result
                    }, broadcast=True)

            # 学习
            self.agent.learn_from_result(result['plan'], actions_result)

            # 记录
            self.execution_log.append({
                'timestamp': datetime.now().isoformat(),
                'command': command,
                'results': actions_result
            })

            return jsonify({
                'success': all(r.get('success') for r in actions_result),
                'plan': result['plan'].__dict__,
                'results': actions_result
            })

        @self.app.route('/api/browser/launch', methods=['POST'])
        def browser_launch():
            data = request.json
            browser_type = data.get('browser', 'chrome')
            headless = data.get('headless', False)
            success = self.browser.launch(browser_type, headless)
            return jsonify({'success': success})

        @self.app.route('/api/browser/navigate', methods=['POST'])
        def browser_navigate():
            data = request.json
            url = data.get('url', '')
            success = self.browser.navigate(url)
            return jsonify({'success': success})

        @self.app.route('/api/browser/screenshot', methods=['GET'])
        def browser_screenshot():
            filename = self.browser.screenshot()
            return jsonify({'filename': filename})

        @self.app.route('/api/history')
        def get_history():
            return jsonify(self.execution_log[-50:])  # 最近50条

        @self.app.route('/api/config', methods=['GET', 'POST'])
        def config():
            if request.method == 'GET':
                return jsonify(self.config.data)
            else:
                data = request.json
                for key, value in data.items():
                    self.config.set(key, value)
                return jsonify({'success': True})

        @self.app.route('/api/memory/search')
        def search_memory():
            query = request.args.get('q', '')
            memories = self.agent.memory.search(query)
            return jsonify([m.__dict__ for m in memories])

    def _setup_socketio(self):
        """设置SocketIO事件"""

        @self.socketio.on('connect')
        def handle_connect():
            print('[WebUI] 客户端已连接')
            emit('status', {'message': '已连接到GodHand服务器'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print('[WebUI] 客户端已断开')

        @self.socketio.on('execute_command')
        def handle_command(data):
            command = data.get('command', '')
            emit('execution_start', {'command': command})

            # 执行命令
            result = self.agent.process(command)

            for step in result['plan'].steps:
                action_result = self._execute_step(step)
                emit('step_update', {
                    'step': step['description'],
                    'status': 'success' if action_result.get('success') else 'failed',
                    'output': action_result.get('output', '')
                })

            emit('execution_complete', {
                'command': command,
                'success': True
            })

    def _execute_step(self, step: Dict) -> Dict:
        """执行单个步骤"""
        from main_cli import Action, ActionType

        # 转换步骤为Action
        action_type = getattr(ActionType, step['action'].upper(), ActionType.VISUAL_ACTION)
        action = Action(
            type=action_type,
            params=step['params'],
            description=step['description']
        )

        return self.executor.execute(action)

    def _get_uptime(self) -> str:
        """获取运行时间"""
        # 简化实现
        return "running"

    def run(self):
        """启动Web服务器"""
        if not HAS_FLASK:
            print("[ERROR] Flask未安装，无法启动Web UI")
            return False

        print(f"=" * 60)
        print(f"GodHand Web UI v3.3")
        print(f"=" * 60)
        print(f"访问地址: http://{self.host}:{self.port}")
        print(f"=" * 60)

        self.is_running = True
        self.socketio.run(self.app, host=self.host, port=self.port, debug=False)
        return True

    def stop(self):
        """停止Web服务器"""
        self.is_running = False


def create_dashboard_template():
    """创建Dashboard模板"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)

    template_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GodHand v3.3 - AI自动化控制台</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f23;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            text-align: center;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header .subtitle {
            opacity: 0.8;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        .panel {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2d2d44;
        }
        .panel h2 {
            margin-bottom: 15px;
            color: #667eea;
        }
        .command-input {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #2d2d44;
            border-radius: 8px;
            background: #0f0f23;
            color: #e0e0e0;
            margin-bottom: 10px;
        }
        .command-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-secondary {
            background: #2d2d44;
            color: #e0e0e0;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .log-container {
            height: 400px;
            overflow-y: auto;
            background: #0f0f23;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .log-entry {
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 4px;
            background: rgba(255,255,255,0.05);
        }
        .log-entry.success { border-left: 3px solid #4caf50; }
        .log-entry.error { border-left: 3px solid #f44336; }
        .log-entry.info { border-left: 3px solid #2196f3; }
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #1a1a2e;
            padding: 10px 20px;
            border-top: 1px solid #2d2d44;
            display: flex;
            justify-content: space-between;
        }
        .feature-list {
            list-style: none;
        }
        .feature-list li {
            padding: 8px 0;
            border-bottom: 1px solid #2d2d44;
        }
        .feature-list li:before {
            content: "✓ ";
            color: #4caf50;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 GodHand v3.3</h1>
        <p class="subtitle">世界级AI自动化平台 | 智能 | 高效 | 强大</p>
    </div>

    <div class="container">
        <div class="grid">
            <div class="panel">
                <h2>🎯 命令执行</h2>
                <input type="text" class="command-input" id="commandInput"
                       placeholder="输入命令，例如: 打开记事本 然后输入Hello World">
                <div>
                    <button class="btn btn-primary" onclick="executeCommand()">执行</button>
                    <button class="btn btn-secondary" onclick="startRecord()">录制</button>
                    <button class="btn btn-secondary" onclick="playRecord()">回放</button>
                </div>

                <h3 style="margin-top: 20px;">快速操作</h3>
                <button class="btn btn-secondary" onclick="quickCmd('打开计算器')">计算器</button>
                <button class="btn btn-secondary" onclick="quickCmd('截图')">截图</button>
                <button class="btn btn-secondary" onclick="quickCmd('获取鼠标位置')">鼠标位置</button>
                <button class="btn btn-secondary" onclick="quickCmd('列出窗口')">窗口列表</button>
            </div>

            <div class="panel">
                <h2>📊 执行日志</h2>
                <div class="log-container" id="logContainer">
                    <div class="log-entry info">等待命令执行...</div>
                </div>
            </div>

            <div class="panel">
                <h2>🧠 AI功能</h2>
                <ul class="feature-list">
                    <li>自然语言任务规划</li>
                    <li>持久化记忆系统</li>
                    <li>智能错误重试</li>
                    <li>浏览器自动化</li>
                    <li>视觉识别点击</li>
                    <li>录制回放系统</li>
                    <li>定时任务调度</li>
                </ul>
            </div>

            <div class="panel">
                <h2>🌐 浏览器控制</h2>
                <button class="btn btn-primary" onclick="browserLaunch()">启动浏览器</button>
                <button class="btn btn-secondary" onclick="browserNavigate()">访问网页</button>
                <button class="btn btn-secondary" onclick="browserScreenshot()">网页截图</button>
                <button class="btn btn-secondary" onclick="browserClose()">关闭浏览器</button>
                <div id="browserStatus" style="margin-top: 10px; color: #888;">浏览器: 未启动</div>
            </div>
        </div>
    </div>

    <div class="status-bar">
        <span id="statusText">就绪</span>
        <span>GodHand v3.3 | AI-Powered Automation</span>
    </div>

    <script>
        const socket = io();
        const logContainer = document.getElementById('logContainer');

        socket.on('connect', () => {
            addLog('已连接到服务器', 'info');
        });

        socket.on('step_update', (data) => {
            addLog(`${data.step}: ${data.status}`, data.status === 'success' ? 'success' : 'error');
        });

        function addLog(message, type = 'info') {
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logContainer.appendChild(entry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function executeCommand() {
            const cmd = document.getElementById('commandInput').value;
            if (!cmd) return;

            addLog(`执行: ${cmd}`, 'info');
            document.getElementById('statusText').textContent = '执行中...';

            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => {
                addLog(`执行完成: ${data.success ? '成功' : '失败'}`, data.success ? 'success' : 'error');
                document.getElementById('statusText').textContent = '就绪';
            })
            .catch(err => {
                addLog(`错误: ${err}`, 'error');
                document.getElementById('statusText').textContent = '错误';
            });
        }

        function quickCmd(cmd) {
            document.getElementById('commandInput').value = cmd;
            executeCommand();
        }

        function browserLaunch() {
            fetch('/api/browser/launch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({browser: 'chrome', headless: false})
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('browserStatus').textContent = '浏览器: ' + (data.success ? '已启动' : '启动失败');
            });
        }

        function browserNavigate() {
            const url = prompt('输入网址:', 'https://www.bing.com');
            if (url) {
                fetch('/api/browser/navigate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({url: url})
                });
            }
        }

        function browserScreenshot() {
            fetch('/api/browser/screenshot')
            .then(r => r.json())
            .then(data => {
                addLog(`网页截图: ${data.filename}`, 'success');
            });
        }

        function browserClose() {
            fetch('/api/browser/close', {method: 'POST'})
            .then(() => {
                document.getElementById('browserStatus').textContent = '浏览器: 已关闭';
            });
        }

        function startRecord() {
            addLog('开始录制...', 'info');
        }

        function playRecord() {
            addLog('回放录制...', 'info');
        }
    </script>
</body>
</html>
"""

    with open(os.path.join(template_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(template_content)

    print(f"[WebUI] 模板已创建: {template_dir}/dashboard.html")


def main():
    """主入口"""
    if not HAS_FLASK:
        print("[ERROR] 请先安装Flask: pip install flask flask-socketio")
        return

    # 创建模板
    create_dashboard_template()

    # 启动Web UI
    ui = GodHandWebUI(host='0.0.0.0', port=5000)
    ui.run()


if __name__ == "__main__":
    main()
