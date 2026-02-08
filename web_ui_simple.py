#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Web UI - 简化版
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template_string, jsonify, request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("[ERROR] Flask未安装: pip install flask")
    sys.exit(1)

from main_cli import SimpleParser, ActionExecutor, HAS_PYAUTOGUI

app = Flask(__name__)
parser = SimpleParser()
executor = ActionExecutor()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>GodHand v4.0 - AI自动化平台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
        }
        .panel {
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        .command-input {
            width: 100%;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .command-input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 12px 30px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .log-container {
            background: #1a1a2e;
            color: #00ff00;
            padding: 20px;
            border-radius: 8px;
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .feature-btn {
            padding: 15px;
            background: #f5f5f5;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .feature-btn:hover {
            background: #667eea;
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 GodHand v4.0</h1>
            <p>世界级AI自动化平台</p>
        </div>

        <div class="panel">
            <h2>🎯 命令执行</h2>
            <input type="text" class="command-input" id="cmdInput"
                   placeholder="输入命令，如: 打开记事本 然后输入Hello World">
            <button class="btn btn-primary" onclick="execute()">执行</button>
            <button class="btn" onclick="clearLog()">清空日志</button>

            <div class="feature-grid">
                <button class="feature-btn" onclick="quickCmd('打开记事本')">📝 记事本</button>
                <button class="feature-btn" onclick="quickCmd('打开计算器')">🧮 计算器</button>
                <button class="feature-btn" onclick="quickCmd('截图')">📸 截图</button>
                <button class="feature-btn" onclick="quickCmd('获取鼠标位置')">🖱️ 鼠标位置</button>
                <button class="feature-btn" onclick="quickCmd('列出窗口')">🪟 窗口列表</button>
                <button class="feature-btn" onclick="quickCmd('获取屏幕尺寸')">📺 屏幕尺寸</button>
            </div>
        </div>

        <div class="panel">
            <h2>📊 执行日志</h2>
            <div class="log-container" id="log"></div>
        </div>
    </div>

    <script>
        function log(msg, type='info') {
            const logDiv = document.getElementById('log');
            const time = new Date().toLocaleTimeString();
            logDiv.innerHTML += `[${time}] ${msg}\n`;
            logDiv.scrollTop = logDiv.scrollHeight;
        }

        function execute() {
            const cmd = document.getElementById('cmdInput').value;
            if (!cmd) return;

            log('> ' + cmd);

            fetch('/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    log('✓ 执行成功');
                } else {
                    log('✗ 执行失败: ' + data.error);
                }
            })
            .catch(e => log('✗ 错误: ' + e));
        }

        function quickCmd(cmd) {
            document.getElementById('cmdInput').value = cmd;
            execute();
        }

        function clearLog() {
            document.getElementById('log').innerHTML = '';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/execute', methods=['POST'])
def execute():
    data = request.json
    command = data.get('command', '')

    actions = parser.parse(command)
    if not actions:
        return jsonify({'success': False, 'error': '无法解析命令'})

    results = []
    for action in actions:
        result = executor.execute(action)
        results.append(result)

    success = all(r.get('success') for r in results)
    return jsonify({'success': success, 'results': results})

@app.route('/status')
def status():
    return jsonify({
        'status': 'running',
        'version': '4.0',
        'pyautogui': HAS_PYAUTOGUI
    })

if __name__ == '__main__':
    print("=" * 60)
    print("GodHand Web UI v4.0")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
