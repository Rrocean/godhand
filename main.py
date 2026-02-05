#!/usr/bin/env python3
"""
GodHand 🖐️ - 智能命令与GUI自动化系统
支持开放式自然语言指令，复合任务自动分解

API:
- POST /api/execute    - 执行系统命令/GUI自动化
- POST /api/chat       - 对话模式
- WebSocket /ws/{session_id} - 实时通信
"""

import os
import sys
import json
import asyncio
import subprocess
import shlex
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 添加核心模块路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入智能解析器
try:
    from core.smart_parser import SmartParser, ActionExecutor, ActionType, Action
    HAS_SMART_PARSER = True
except ImportError as e:
    HAS_SMART_PARSER = False
    print(f"[Warn] SmartParser not available: {e}")

# 导入 GodHand 核心
try:
    from core.ghost_v2 import GhostHandPro, ActionType as GhostActionType
    from core.claw_runner import CommandParser, CommandExecutor
    HAS_GHOSTHAND = True
except ImportError as e:
    HAS_GHOSTHAND = False
    print(f"[Warn] GhostHand core not available: {e}")


# ============================================================================
# 数据模型
# ============================================================================

class CommandRequest(BaseModel):
    """命令请求"""
    command: str
    session_id: Optional[str] = None


class CommandResponse(BaseModel):
    """命令响应"""
    success: bool
    command: str
    description: str
    output: str
    error: Optional[str] = None
    timestamp: str


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str
    content: str
    timestamp: str
    command_result: Optional[Dict] = None


class Session(BaseModel):
    """会话"""
    id: str
    created_at: str
    messages: List[ChatMessage] = []
    history: List[Dict] = []


# ============================================================================
# GodHand 核心管理器 - 新版智能版
# ============================================================================

class GodHandCore:
    """
    GodHand 核心 - 智能版
    支持开放式自然语言，自动分解复合指令
    """
    
    def __init__(self):
        self.parser = None
        self.executor = None
        self.ghost = None
        
        # 初始化智能解析器
        if HAS_SMART_PARSER:
            try:
                config_path = Path(__file__).parent / "config.json"
                self.parser = SmartParser(config_path=str(config_path))
                self.executor = ActionExecutor()
                print("[GodHand] SmartParser initialized")
            except Exception as e:
                print(f"[Warn] SmartParser init failed: {e}")
        
        # 初始化传统解析器（备用）
        try:
            self.cmd_parser = CommandParser()
            self.cmd_executor = CommandExecutor()
        except:
            self.cmd_parser = None
            self.cmd_executor = None
    
    def get_ghost(self) -> Optional[Any]:
        """获取或初始化 GhostHand 实例"""
        if not HAS_GHOSTHAND:
            return None
        
        if self.ghost is None:
            try:
                config_path = Path(__file__).parent / "config.json"
                self.ghost = GhostHandPro(config_path=str(config_path))
            except Exception as e:
                print(f"[Error] GhostHand init failed: {e}")
                return None
        return self.ghost
    
    def process(self, text: str) -> List[Dict]:
        """
        处理自然语言指令
        返回动作列表
        """
        if not text.strip():
            return []
        
        # 优先使用智能解析器
        if self.parser:
            try:
                actions = self.parser.parse(text)
                return [action.to_dict() for action in actions]
            except Exception as e:
                print(f"[Error] SmartParser failed: {e}")
        
        # 备用：传统解析
        if self.cmd_parser:
            try:
                commands = self.cmd_parser.parse(text)
                return [self._cmd_to_dict(cmd) for cmd in commands]
            except Exception as e:
                print(f"[Error] Traditional parser failed: {e}")
        
        # 都无法解析
        return [{
            'type': 'unknown',
            'params': {'raw': text},
            'description': f'无法解析: {text}',
            'reason': 'parser not available'
        }]
    
    def execute(self, action_dict: Dict) -> Dict:
        """执行单个动作"""
        if self.executor:
            try:
                # 重建Action对象
                action = Action(
                    type=ActionType(action_dict.get('type', 'unknown')),
                    params=action_dict.get('params', {}),
                    description=action_dict.get('description', ''),
                    reason=action_dict.get('reason', '')
                )
                return self.executor.execute(action)
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'action': action_dict
                }
        
        return {
            'success': False,
            'error': 'Executor not available',
            'action': action_dict
        }
    
    def execute_batch(self, actions: List[Dict]) -> List[Dict]:
        """批量执行动作"""
        results = []
        for action_dict in actions:
            result = self.execute(action_dict)
            results.append(result)
        return results
    
    def _cmd_to_dict(self, cmd) -> Dict:
        """转换传统命令为字典"""
        return {
            'type': cmd.type.value if hasattr(cmd.type, 'value') else str(cmd.type),
            'params': {
                'command': cmd.command,
                'need_shell': cmd.need_shell
            },
            'description': cmd.description,
            'reason': 'traditional parser'
        }


# ============================================================================
# 会话管理器
# ============================================================================

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
    
    def create_session(self) -> str:
        """创建新会话"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        self.sessions[session_id] = Session(
            id=session_id,
            created_at=datetime.now().isoformat(),
            messages=[]
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, command_result: Optional[Dict] = None):
        """添加消息"""
        if session_id not in self.sessions:
            return
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            command_result=command_result
        )
        self.sessions[session_id].messages.append(message)
    
    def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [msg.dict() for msg in session.messages]


# ============================================================================
# FastAPI 应用
# ============================================================================

app = FastAPI(
    title="GodHand",
    description="智能命令与GUI自动化系统 - 支持开放式自然语言",
    version="2.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
static_dir = Path(__file__).parent / "web" / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 全局实例
godhand = GodHandCore()
session_mgr = SessionManager()


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    return HTMLResponse(content=get_html())


@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """执行命令 API - 智能版"""
    # 解析指令
    actions = godhand.process(request.command)
    
    # 执行
    results = godhand.execute_batch(actions)
    
    # 记录到会话
    if request.session_id:
        for result in results:
            session_mgr.add_message(
                request.session_id,
                "assistant",
                result['action']['description'],
                result
            )
    
    return {
        "success": all(r['success'] for r in results),
        "command": request.command,
        "actions": actions,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/chat")
async def chat(request: CommandRequest):
    """聊天 API - 解析但不执行"""
    actions = godhand.process(request.command)
    
    # 生成回复
    unknown_count = sum(1 for a in actions if a['type'] == 'unknown')
    
    if unknown_count == len(actions):
        reply = f"🤔 我不太理解 '{request.command}'\n\n试试这些:\n"
        reply += "• 打开记事本 输入Hello World\n"
        reply += "• 打开计算器\n"
        reply += "• 搜索Python教程\n"
        reply += "• 截图\n"
        reply += "• 创建文件夹Test"
    else:
        reply = f"✅ 我理解你的指令，包含 {len(actions)} 个动作:\n\n"
        for i, action in enumerate(actions, 1):
            emoji = {
                'open_app': '📱',
                'type_text': '⌨️',
                'press_key': '🔘',
                'hotkey': '⌨️',
                'click': '🖱️',
                'wait': '⏱️',
                'search': '🔍',
                'file': '📁',
                'system': '⚙️',
                'unknown': '❓'
            }.get(action['type'], '▶️')
            reply += f"{i}. {emoji} {action['description']}\n"
        reply += "\n点击发送执行这些动作。"
    
    if request.session_id:
        session_mgr.add_message(request.session_id, "user", request.command)
        session_mgr.add_message(request.session_id, "assistant", reply)
    
    return {
        "reply": reply,
        "actions": actions,
        "session_id": request.session_id
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 实时通信"""
    await websocket.accept()
    
    if not session_mgr.get_session(session_id):
        session_id = session_mgr.create_session()
        await websocket.send_json({
            "type": "system",
            "content": f"✨ 新会话已创建"
        })
    
    try:
        while True:
            data = await websocket.receive_json()
            user_input = data.get('message', '')
            
            if not user_input:
                continue
            
            # 发送思考中
            await websocket.send_json({
                "type": "thinking",
                "content": "🤔 正在理解指令..."
            })
            
            # 解析
            actions = godhand.process(user_input)
            
            # 检查是否全部无法解析
            if all(a['type'] == 'unknown' for a in actions):
                await websocket.send_json({
                    "type": "error",
                    "content": f"❌ 无法理解: {user_input}\n\n试试:\n• 打开记事本 输入123\n• 打开计算器\n• 搜索Python教程"
                })
                await websocket.send_json({"type": "done"})
                continue
            
            # 发送解析结果
            action_list = "\n".join([
                f"{i+1}. {a['description']}"
                for i, a in enumerate(actions)
            ])
            
            await websocket.send_json({
                "type": "parsed",
                "content": f"📋 解析为 {len(actions)} 个动作",
                "actions": actions
            })
            
            # 执行每个动作
            for i, action in enumerate(actions):
                if action['type'] == 'unknown':
                    continue
                
                await websocket.send_json({
                    "type": "executing",
                    "content": f"⚡ 执行: {action['description']}"
                })
                
                # 执行
                result = godhand.execute(action)
                
                # 发送结果
                await websocket.send_json({
                    "type": "result",
                    "success": result['success'],
                    "action": action,
                    "output": result.get('output', ''),
                    "error": result.get('error')
                })
            
            # 完成
            await websocket.send_json({
                "type": "done",
                "content": "✅ 执行完成"
            })
            
    except WebSocketDisconnect:
        print(f"[WebSocket] 会话断开: {session_id}")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"服务器错误: {str(e)}"
            })
        except:
            pass


@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str):
    """获取会话历史"""
    history = session_mgr.get_history(session_id)
    return {"session_id": session_id, "history": history}


@app.post("/api/sessions/new")
async def new_session():
    """创建新会话"""
    session_id = session_mgr.create_session()
    return {"session_id": session_id, "created_at": datetime.now().isoformat()}


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "smart_parser": HAS_SMART_PARSER,
        "ghosthand": HAS_GHOSTHAND,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# 美化版 HTML 页面
# ============================================================================

def get_html() -> str:
    """返回美化的 HTML 页面"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GodHand 🖐️ - 智能自动化助手</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #ec4899;
            --bg-dark: #0f0f23;
            --bg-card: #1a1a2e;
            --bg-input: #16162a;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            --border: rgba(255,255,255,0.1);
            --shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            min-height: 100vh;
            color: var(--text-primary);
            overflow: hidden;
        }
        
        /* 背景动画 */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
        }
        
        .bg-animation::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: 
                radial-gradient(circle at 20% 80%, rgba(99, 102, 241, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(236, 72, 153, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(59, 130, 246, 0.1) 0%, transparent 40%);
            animation: bgPulse 15s ease-in-out infinite;
        }
        
        @keyframes bgPulse {
            0%, 100% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.1) rotate(5deg); }
        }
        
        /* 主容器 */
        .app {
            position: relative;
            z-index: 1;
            height: 100vh;
            display: flex;
            flex-direction: column;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* 头部 */
        .header {
            text-align: center;
            padding: 20px 0;
            animation: slideDown 0.6s ease;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        
        .logo-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            box-shadow: 0 8px 32px rgba(99, 102, 241, 0.4);
            animation: float 3s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .logo-text {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }
        
        /* 聊天容器 */
        .chat-wrapper {
            flex: 1;
            background: var(--bg-card);
            border-radius: 24px;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: slideUp 0.6s ease 0.1s both;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        /* 消息区域 */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            scroll-behavior: smooth;
        }
        
        .chat-container::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-container::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .chat-container::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 3px;
        }
        
        /* 消息样式 */
        .message {
            margin-bottom: 20px;
            animation: messageIn 0.4s ease;
            max-width: 85%;
        }
        
        @keyframes messageIn {
            from { opacity: 0; transform: translateY(20px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        
        .message.user {
            margin-left: auto;
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .message.user .message-header {
            justify-content: flex-end;
        }
        
        .message-avatar {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }
        
        .message.user .message-avatar {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        }
        
        .message.assistant .message-avatar {
            background: linear-gradient(135deg, var(--secondary) 0%, #d946ef 100%);
        }
        
        .message.system .message-avatar {
            background: var(--warning);
        }
        
        .message-content {
            padding: 14px 18px;
            border-radius: 18px;
            font-size: 0.95rem;
            line-height: 1.6;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border-bottom-right-radius: 6px;
        }
        
        .message.assistant .message-content {
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-bottom-left-radius: 6px;
        }
        
        .message.system .message-content {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: var(--warning);
            text-align: center;
            max-width: 100%;
        }
        
        .message.error .message-content {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: var(--error);
        }
        
        /* 动作卡片 */
        .action-card {
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 12px 16px;
            margin: 8px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .action-icon {
            width: 36px;
            height: 36px;
            background: rgba(99, 102, 241, 0.2);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
        }
        
        .action-info {
            flex: 1;
        }
        
        .action-title {
            font-weight: 500;
            color: var(--text-primary);
        }
        
        .action-desc {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        /* 结果卡片 */
        .result-card {
            margin-top: 8px;
            padding: 12px 16px;
            border-radius: 12px;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .result-card.success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .result-card.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        
        /* 快速命令 */
        .quick-commands {
            padding: 16px 24px;
            background: var(--bg-input);
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            overflow-x: auto;
        }
        
        .quick-commands::-webkit-scrollbar {
            height: 4px;
        }
        
        .quick-btn {
            padding: 10px 18px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 20px;
            color: var(--text-primary);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .quick-btn:hover {
            background: rgba(99, 102, 241, 0.3);
            border-color: var(--primary);
            transform: translateY(-2px);
        }
        
        .quick-btn:active {
            transform: translateY(0);
        }
        
        /* 输入区域 */
        .input-area {
            padding: 20px 24px;
            background: var(--bg-card);
            border-top: 1px solid var(--border);
            display: flex;
            gap: 12px;
        }
        
        .input-wrapper {
            flex: 1;
            position: relative;
        }
        
        .input-wrapper input {
            width: 100%;
            padding: 14px 20px;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 16px;
            color: var(--text-primary);
            font-size: 0.95rem;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .input-wrapper input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .input-wrapper input::placeholder {
            color: var(--text-secondary);
        }
        
        .send-btn {
            padding: 14px 28px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border: none;
            border-radius: 16px;
            color: white;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .send-btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        }
        
        .send-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        /* 状态栏 */
        .status-bar {
            padding: 12px 24px;
            background: var(--bg-input);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        
        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }
        
        .status-dot.connected {
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
        }
        
        .status-dot.disconnected {
            background: var(--error);
            animation: none;
        }
        
        .status-dot.connecting {
            background: var(--warning);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* 加载动画 */
        .loading {
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        
        .loading span {
            width: 8px;
            height: 8px;
            background: var(--primary);
            border-radius: 50%;
            animation: bounce 1.4s ease-in-out infinite both;
        }
        
        .loading span:nth-child(1) { animation-delay: -0.32s; }
        .loading span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        /* 思考中动画 */
        .thinking-bubble {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 12px 18px;
            background: rgba(99, 102, 241, 0.1);
            border-radius: 18px;
        }
        
        .thinking-dots {
            display: flex;
            gap: 4px;
        }
        
        .thinking-dots span {
            width: 6px;
            height: 6px;
            background: var(--primary);
            border-radius: 50%;
            animation: thinking 1.4s infinite;
        }
        
        .thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes thinking {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
            30% { transform: translateY(-4px); opacity: 1; }
        }
        
        /* 响应式 */
        @media (max-width: 768px) {
            .app {
                padding: 10px;
            }
            
            .logo-text {
                font-size: 1.5rem;
            }
            
            .message {
                max-width: 95%;
            }
            
            .quick-commands {
                padding: 12px;
            }
            
            .input-area {
                padding: 12px;
            }
        }
    </style>
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="app">
        <header class="header">
            <div class="logo">
                <div class="logo-icon">🖐️</div>
                <h1 class="logo-text">GodHand</h1>
            </div>
            <p class="subtitle">智能命令与自动化助手 - 支持开放式自然语言</p>
        </header>
        
        <div class="chat-wrapper">
            <div class="chat-container" id="chatContainer">
                <div class="message system">
                    <div class="message-header">
                        <div class="message-avatar">🔔</div>
                        <span>系统</span>
                    </div>
                    <div class="message-content">
                        ✨ 欢迎使用 GodHand！我可以帮你执行各种任务：<br><br>
                        <strong>复合指令示例：</strong><br>
                        • "打开记事本 输入Hello World"<br>
                        • "打开计算器 计算1+1"<br>
                        • "截图 保存到桌面"<br><br>
                        <strong>简单指令：</strong><br>
                        • 打开/关闭应用 | 输入文字 | 按键<br>
                        • 搜索内容 | 创建文件夹 | 截图
                    </div>
                </div>
            </div>
            
            <div class="quick-commands" id="quickCommands">
                <button class="quick-btn" onclick="sendQuick(\'打开记事本 输入123\')">
                    📝 记事本输入
                </button>
                <button class="quick-btn" onclick="sendQuick(\'打开计算器\')">
                    🧮 计算器
                </button>
                <button class="quick-btn" onclick="sendQuick(\'截图\')">
                    📸 截图
                </button>
                <button class="quick-btn" onclick="sendQuick(\'搜索Python教程\')">
                    🔍 搜索
                </button>
                <button class="quick-btn" onclick="sendQuick(\'创建文件夹Test\')">
                    📁 新建文件夹
                </button>
                <button class="quick-btn" onclick="sendQuick(\'按键Enter\')">
                    ⌨️ 按回车
                </button>
            </div>
            
            <div class="input-area">
                <div class="input-wrapper">
                    <input 
                        type="text" 
                        id="userInput" 
                        placeholder="输入指令，例如：打开记事本 输入Hello World..."
                        onkeypress="handleKeyPress(event)"
                    >
                </div>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">
                    <span>发送</span>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9"></polygon>
                    </svg>
                </button>
            </div>
            
            <div class="status-bar">
                <div class="status-indicator">
                    <div class="status-dot disconnected" id="statusDot"></div>
                    <span id="statusText">未连接</span>
                </div>
                <span id="sessionInfo">Session: -</span>
            </div>
        </div>
    </div>

    <script>
        // 全局变量
        let ws = null;
        let sessionId = null;
        let reconnectAttempts = 0;
        const MAX_RECONNECT = 5;
        
        // DOM 元素
        const chatContainer = document.getElementById(\'chatContainer\');
        const userInput = document.getElementById(\'userInput\');
        const sendBtn = document.getElementById(\'sendBtn\');
        const statusDot = document.getElementById(\'statusDot\');
        const statusText = document.getElementById(\'statusText\');
        const sessionInfo = document.getElementById(\'sessionInfo\');

        // 生成会话ID
        function generateSessionId() {
            return \'gh_\' + Date.now().toString(36) + \'_\' + Math.random().toString(36).substr(2, 5);
        }

        // 更新状态
        function updateStatus(status, text) {
            statusDot.className = \'status-dot \' + status;
            statusText.textContent = text;
        }

        // 连接 WebSocket
        function connectWebSocket() {
            if (reconnectAttempts >= MAX_RECONNECT) {
                updateStatus(\'disconnected\', \'连接失败，使用HTTP模式\');
                addSystemMessage(\'⚠️ WebSocket连接失败，将使用HTTP模式\');
                return;
            }

            sessionId = generateSessionId();
            sessionInfo.textContent = \`Session: \${sessionId.substr(0, 12)}...\`;
            
            const wsProtocol = window.location.protocol === \'https:\' ? \'wss:\' : \'ws:\';
            const wsHost = window.location.host || \'127.0.0.1:8000\';
            const wsUrl = \`\${wsProtocol}//\${wsHost}/ws/\${sessionId}\`;
            
            console.log(\'Connecting to:\', wsUrl);
            updateStatus(\'connecting\', \'连接中...\');
            
            try {
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    console.log(\'WebSocket connected\');
                    updateStatus(\'connected\', \'已连接\');
                    reconnectAttempts = 0;
                };
                
                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    } catch (e) {
                        console.error(\'Parse error:\', e);
                    }
                };
                
                ws.onclose = () => {
                    console.log(\'WebSocket closed\');
                    updateStatus(\'disconnected\', \'已断开\');
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 3000);
                };
                
                ws.onerror = (error) => {
                    console.error(\'WebSocket error:\', error);
                    updateStatus(\'disconnected\', \'连接错误\');
                };
            } catch (e) {
                console.error(\'Connection error:\', e);
                updateStatus(\'disconnected\', \'连接失败\');
                reconnectAttempts++;
                setTimeout(connectWebSocket, 3000);
            }
        }

        // HTTP 备用发送
        async function sendViaHTTP(text) {
            updateStatus(\'connecting\', \'发送中...\');
            
            try {
                const response = await fetch(\'/api/execute\', {
                    method: \'POST\',
                    headers: { \'Content-Type\': \'application/json\' },
                    body: JSON.stringify({ command: text, session_id: sessionId })
                });
                
                const data = await response.json();
                
                // 显示解析的动作
                if (data.actions && data.actions.length > 0) {
                    const actionText = data.actions.map((a, i) => 
                        \`\${i+1}. \${getActionEmoji(a.type)} \${a.description}\`
                    ).join(\'\\n\');
                    addAssistantMessage(\`📋 解析为 \${data.actions.length} 个动作：\\n\${actionText}\`);
                }
                
                // 显示执行结果
                if (data.results) {
                    data.results.forEach(result => {
                        const icon = result.success ? \'✅\' : \'❌\';
                        const output = result.output || result.error || \'完成\';
                        addResultCard(result.success, output);
                    });
                }
                
                updateStatus(\'disconnected\', \'HTTP模式\');
                enableSendButton();
                
            } catch (e) {
                console.error(\'HTTP error:\', e);
                addErrorMessage(\'发送失败: \' + e.message);
                enableSendButton();
            }
        }

        // 处理 WebSocket 消息
        function handleWebSocketMessage(data) {
            switch(data.type) {
                case \'system\':
                    addSystemMessage(data.content);
                    break;
                    
                case \'thinking\':
                    addThinkingMessage();
                    break;
                    
                case \'parsed\':
                    removeThinkingMessage();
                    // 显示动作列表
                    if (data.actions) {
                        let content = \`📋 \${data.content}\\n\\n\`;
                        data.actions.forEach((a, i) => {
                            content += \`\${i+1}. \${getActionEmoji(a.type)} \${a.description}\\n\`;
                        });
                        addAssistantMessage(content);
                    }
                    break;
                    
                case \'executing\':
                    addAssistantMessage(\`⚡ \${data.content}\`);
                    break;
                    
                case \'result\':
                    const output = data.output || data.error || \'完成\';
                    addResultCard(data.success, output);
                    break;
                    
                case \'done\':
                    enableSendButton();
                    break;
                    
                case \'error\':
                    removeThinkingMessage();
                    addErrorMessage(data.content);
                    enableSendButton();
                    break;
            }
            scrollToBottom();
        }

        // 获取动作表情
        function getActionEmoji(type) {
            const emojis = {
                \'open_app\': \'📱\',
                \'type_text\': \'⌨️\',
                \'press_key\': \'🔘\',
                \'hotkey\': \'⌨️\',
                \'click\': \'🖱️\',
                \'wait\': \'⏱️\',
                \'search\': \'🔍\',
                \'file\': \'📁\',
                \'system\': \'⚙️\',
                \'unknown\': \'❓\'
            };
            return emojis[type] || \'▶️\';
        }

        // 添加消息函数
        function addMessage(role, content, isHTML = false) {
            const msgDiv = document.createElement(\'div\');
            msgDiv.className = \`message \${role}\`;
            
            const avatar = role === \'user\' ? \'👤\' : (role === \'system\' ? \'🔔\' : \'🤖\');
            const name = role === \'user\' ? \'你\' : (role === \'system\' ? \'系统\' : \'GodHand\');
            
            msgDiv.innerHTML = \`
                <div class="message-header">
                    \${role !== \'user\' ? \`<div class="message-avatar">\${avatar}</div><span>\${name}</span>\` : \`<span>\${name}</span><div class="message-avatar">\${avatar}</div>\`}
                </div>
                <div class="message-content">\${isHTML ? content : escapeHtml(content)}</div>
            \`;
            
            chatContainer.appendChild(msgDiv);
            scrollToBottom();
            return msgDiv;
        }

        function addUserMessage(text) {
            return addMessage(\'user\', text);
        }

        function addAssistantMessage(text) {
            return addMessage(\'assistant\', text);
        }

        function addSystemMessage(text) {
            return addMessage(\'system\', text);
        }

        function addErrorMessage(text) {
            const msgDiv = document.createElement(\'div\');
            msgDiv.className = \'message error\';
            msgDiv.innerHTML = \`
                <div class="message-header">
                    <div class="message-avatar">⚠️</div>
                    <span>错误</span>
                </div>
                <div class="message-content">\${escapeHtml(text)}</div>
            \`;
            chatContainer.appendChild(msgDiv);
            scrollToBottom();
        }

        function addResultCard(success, output) {
            const card = document.createElement(\'div\');
            card.className = \`result-card \${success ? \'success\' : \'error\'}\`;
            card.style.marginLeft = \'44px\';
            card.style.marginBottom = \'12px\';
            card.textContent = output;
            chatContainer.appendChild(card);
            scrollToBottom();
        }

        let thinkingMsg = null;
        function addThinkingMessage() {
            thinkingMsg = document.createElement(\'div\');
            thinkingMsg.className = \'message assistant\';
            thinkingMsg.id = \'thinking-msg\';
            thinkingMsg.innerHTML = \`
                <div class="message-header">
                    <div class="message-avatar">🤖</div>
                    <span>GodHand</span>
                </div>
                <div class="message-content">
                    <div class="thinking-bubble">
                        <div class="thinking-dots">
                            <span></span><span></span><span></span>
                        </div>
                        <span>思考中...</span>
                    </div>
                </div>
            \`;
            chatContainer.appendChild(thinkingMsg);
            scrollToBottom();
        }

        function removeThinkingMessage() {
            if (thinkingMsg) {
                thinkingMsg.remove();
                thinkingMsg = null;
            }
            const existing = document.getElementById(\'thinking-msg\');
            if (existing) existing.remove();
        }

        function escapeHtml(text) {
            const div = document.createElement(\'div\');
            div.textContent = text;
            return div.innerHTML.replace(/\\n/g, \'<br>\');
        }

        function scrollToBottom() {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function disableSendButton() {
            sendBtn.disabled = true;
            sendBtn.innerHTML = \`
                <div class="loading"><span></span><span></span><span></span></div>
            \`;
        }

        function enableSendButton() {
            sendBtn.disabled = false;
            sendBtn.innerHTML = \`
                <span>发送</span>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9"></polygon>
                </svg>
            \`;
        }

        // 发送消息
        function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;
            
            addUserMessage(text);
            userInput.value = \'\';
            disableSendButton();
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ message: text }));
            } else {
                sendViaHTTP(text);
            }
        }

        function sendQuick(text) {
            userInput.value = text;
            sendMessage();
        }

        function handleKeyPress(event) {
            if (event.key === \'Enter\' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        // 初始化
        connectWebSocket();
        userInput.focus();
        
        // 页面加载完成
        window.addEventListener(\'load\', () => {
            console.log(\'GodHand initialized\');
        });
    </script>
</body>
</html>'''


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🖐️ GodHand 智能自动化助手")
    print("=" * 60)
    print("访问地址: http://127.0.0.1:8000")
    print("支持复合指令: 打开记事本 输入Hello World")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
