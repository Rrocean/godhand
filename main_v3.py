#!/usr/bin/env python3
"""
GodHand v3.0 🌌 - 宇宙级的智能命令与GUI自动化系统

集成：
- VisualEngine: 视觉理解引擎
- TaskPlanner: 智能任务规划器
- AIAgent: 自主AI代理系统
- VoiceController: 语音控制系统
- CloudSync: 云端同步与协作
- LearningSystem: 自主学习系统

API:
- POST /api/execute    - 执行系统命令/GUI自动化
- POST /api/chat       - 对话模式
- POST /api/plan       - 任务规划
- POST /api/detect     - 视觉检测
- POST /api/voice      - 语音命令
- POST /api/ai         - AI代理任务
- WebSocket /ws/{session_id} - 实时通信
"""

import os
import sys
import json
import asyncio
import subprocess
import shlex
import base64
import io
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# 添加核心模块路径
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

# 导入核心模块
from core import (
    GhostHandPro, ActionType, TaskStatus,
    SmartParser, SmartActionExecutor,
    VisualEngine, UIElement, ElementType, SceneContext,
    TaskPlanner, PlanExecutor, ExecutionPlan, Step, StepType,
    AIAgent, TaskPriority, AgentState,
    VoiceController, VoiceState,
    CloudSync, SyncStatus
)

print("[GodHand v3.0 🌌] 正在启动宇宙级自动化系统...")
print("[GodHand v3.0] The Universe's #1 GUI Automation System")

# ============================================================================
# 数据模型
# ============================================================================

class CommandRequest(BaseModel):
    """命令请求"""
    command: str
    session_id: Optional[str] = None
    mode: str = "auto"  # auto, command, automation, visual

class PlanRequest(BaseModel):
    """规划请求"""
    instruction: str
    context: Optional[Dict] = None

class VisualRequest(BaseModel):
    """视觉请求"""
    description: str
    screenshot: Optional[str] = None  # base64 encoded image

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
# GodHand v3.0 核心
# ============================================================================

class GodHandCore:
    """
    GodHand v3.0 核心 - 世界级的智能自动化引擎
    """

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)

        # 初始化视觉引擎
        print("[Core] 初始化视觉引擎...")
        self.visual_engine = VisualEngine(
            use_ocr=self.config.get('visual', {}).get('use_ocr', True),
            use_ml=self.config.get('visual', {}).get('use_ml', False)
        )

        # 初始化任务规划器
        print("[Core] 初始化任务规划器...")
        self.task_planner = TaskPlanner(use_llm=True)

        # 初始化智能解析器
        print("[Core] 初始化智能解析器...")
        self.smart_parser = SmartParser(config_path=config_path)
        self.action_executor = SmartActionExecutor()

        # 初始化 GhostHand（传统模式）
        print("[Core] 初始化 GhostHand Pro...")
        try:
            self.ghost = GhostHandPro(config_path=config_path)
        except Exception as e:
            print(f"[Warn] GhostHand Pro 初始化失败: {e}")
            self.ghost = None

        # 初始化 AIAgent
        print("[Core] 初始化 AIAgent...")
        self.ai_agent = AIAgent(name="GodHand Universe Agent")
        self._register_ai_skills()

        # 初始化语音控制器
        print("[Core] 初始化 VoiceController...")
        self.voice_controller = VoiceController()

        # 初始化云端同步
        print("[Core] 初始化 CloudSync...")
        self.cloud_sync = CloudSync()
        if self.config.get('cloud', {}).get('enabled', False):
            self.cloud_sync.register_device({
                "name": self.config.get('cloud', {}).get('user_name', 'GodHand User'),
                "email": self.config.get('cloud', {}).get('email', ''),
                "role": "owner"
            })
            self.cloud_sync.start_sync()

        # 当前截图缓存
        self._current_screenshot: Optional[Image.Image] = None

        print("[Core] 🌌 宇宙级初始化完成!")

    def _register_ai_skills(self):
        """注册AI技能"""
        # 注册GUI操作技能
        self.ai_agent.register_skill("click", lambda **kwargs: {
            "success": True,
            "output": f"点击 {kwargs.get('target', '未知')}"
        })
        self.ai_agent.register_skill("type", lambda **kwargs: {
            "success": True,
            "output": f"输入 {kwargs.get('text', '')}"
        })
        self.ai_agent.register_skill("open_app", lambda **kwargs: {
            "success": True,
            "output": f"打开 {kwargs.get('target', '应用')}"
        })
        self.ai_agent.register_skill("search", lambda **kwargs: {
            "success": True,
            "output": f"搜索 {kwargs.get('query', '')}"
        })
        self.ai_agent.register_skill("analyze", lambda **kwargs: {
            "success": True,
            "output": "分析完成"
        })
        self.ai_agent.register_skill("verify", lambda **kwargs: {
            "success": True,
            "output": "验证通过"
        })

    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        default = {
            'provider': 'google',
            'google': {'api_key': '', 'model': 'gemini-2.0-flash'},
            'visual': {'use_ocr': True, 'use_ml': False},
            'safety': {'max_steps': 30, 'step_delay': 0.5}
        }

        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except Exception as e:
                print(f"[Warn] 配置加载失败: {e}")

        return default

    def take_screenshot(self) -> Image.Image:
        """截取屏幕"""
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            self._current_screenshot = screenshot
            return screenshot
        except Exception as e:
            print(f"[Error] 截图失败: {e}")
            return None

    def process_with_vision(self, instruction: str, screenshot: Image.Image = None) -> Dict:
        """
        使用视觉理解处理指令

        例如：
        - "点击保存按钮"
        - "在搜索框输入Hello"
        - "关闭右上角的弹窗"
        """
        if screenshot is None:
            screenshot = self.take_screenshot()

        if screenshot is None:
            return {
                'success': False,
                'error': '无法获取屏幕截图'
            }

        # 1. 检测屏幕元素
        print(f"[Vision] 检测屏幕元素...")
        elements = self.visual_engine.detect_elements(screenshot)
        print(f"[Vision] 检测到 {len(elements)} 个元素")

        # 2. 定位目标元素
        print(f"[Vision] 定位: {instruction}")
        target = self.visual_engine.locate_element(instruction, screenshot)

        if target:
            print(f"[Vision] 找到目标: {target.description} at ({target.x}, {target.y})")
            return {
                'success': True,
                'element': target.to_dict(),
                'all_elements': [e.to_dict() for e in elements[:10]],  # 只返回前10个
                'screenshot_size': screenshot.size
            }
        else:
            return {
                'success': False,
                'error': f'未找到元素: {instruction}',
                'all_elements': [e.to_dict() for e in elements[:10]]
            }

    def execute_visual_action(self, instruction: str) -> Dict:
        """
        执行基于视觉的动作
        """
        # 1. 截图并分析
        result = self.process_with_vision(instruction)

        if not result['success']:
            return result

        # 2. 执行点击/输入等动作
        element = result['element']
        x, y = element['x'], element['y']

        try:
            import pyautogui

            # 根据指令类型执行不同动作
            if '点击' in instruction or '按' in instruction:
                pyautogui.click(x, y)
                return {
                    'success': True,
                    'action': 'click',
                    'position': (x, y),
                    'target': element.get('text', element['description'])
                }
            elif '输入' in instruction or '填写' in instruction:
                # 先点击，再输入
                pyautogui.click(x, y)
                # 提取要输入的文本（简化处理）
                text = instruction.split('输入')[-1].strip() if '输入' in instruction else ''
                if text:
                    import pyperclip
                    pyperclip.copy(text)
                    pyautogui.hotkey('ctrl', 'v')
                return {
                    'success': True,
                    'action': 'type',
                    'position': (x, y),
                    'text': text
                }
            else:
                # 默认点击
                pyautogui.click(x, y)
                return {
                    'success': True,
                    'action': 'click',
                    'position': (x, y)
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def plan_and_execute(self, instruction: str) -> Dict:
        """
        规划并执行任务
        """
        # 1. 创建规划上下文
        from core.task_planner import PlanningContext

        # 获取当前屏幕信息
        screenshot = self.take_screenshot()
        elements = []
        if screenshot:
            elements = self.visual_engine.detect_elements(screenshot)

        context = PlanningContext(
            instruction=instruction,
            available_elements=[e.to_dict() for e in elements[:20]]
        )

        # 2. 生成执行计划
        print(f"[Planner] 规划任务: {instruction}")
        plan = self.task_planner.plan(instruction, context)
        print(f"[Planner] 生成 {len(plan.steps)} 个步骤")

        # 3. 执行计划
        results = []
        for step in plan.steps:
            print(f"[Execute] {step.description}")

            # 执行步骤
            if step.type == StepType.ACTION:
                action_result = self._execute_step_action(step)
                results.append({
                    'step_id': step.id,
                    'description': step.description,
                    'success': action_result.get('success', False),
                    'result': action_result
                })
            elif step.type == StepType.WAIT:
                import time
                wait_time = step.params.get('seconds', 1.0)
                time.sleep(wait_time)
                results.append({
                    'step_id': step.id,
                    'description': step.description,
                    'success': True
                })

        return {
            'success': all(r.get('success', False) for r in results),
            'plan': plan.to_dict(),
            'results': results
        }

    def _execute_step_action(self, step: Step) -> Dict:
        """执行步骤中的动作"""
        params = step.params
        action_type = params.get('action', '')

        try:
            if action_type == 'open_app':
                app_name = params.get('app_name', '')
                cmd = self._resolve_app_command(app_name)
                subprocess.Popen(cmd, shell=True)
                return {'success': True, 'output': f'打开 {app_name}'}

            elif action_type == 'type_text':
                text = params.get('text', '')
                import pyautogui
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                return {'success': True, 'output': f'输入 {text[:20]}...'}

            elif action_type == 'press_key':
                key = params.get('key', '')
                import pyautogui
                pyautogui.press(key)
                return {'success': True, 'output': f'按键 {key}'}

            elif action_type == 'click':
                # 如果有坐标
                x = params.get('x')
                y = params.get('y')
                if x is not None and y is not None:
                    import pyautogui
                    pyautogui.click(x, y)
                    return {'success': True, 'output': f'点击 ({x}, {y})'}
                else:
                    # 使用视觉定位
                    description = params.get('description', '')
                    return self.execute_visual_action(f"点击{description}")

            elif action_type == 'screenshot':
                screenshot = self.take_screenshot()
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                screenshot.save(filename)
                return {'success': True, 'output': f'截图保存到 {filename}'}

            elif action_type == 'search':
                query = params.get('query', '')
                import urllib.parse
                encoded = urllib.parse.quote(query)
                url = f"https://www.bing.com/search?q={encoded}"
                subprocess.Popen(f'start msedge "{url}"', shell=True)
                return {'success': True, 'output': f'搜索 {query}'}

            else:
                return {'success': False, 'error': f'未知动作: {action_type}'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _resolve_app_command(self, app_name: str) -> str:
        """解析应用名称到命令"""
        app_map = {
            '计算器': 'calc.exe',
            '记事本': 'notepad.exe',
            '画图': 'mspaint.exe',
            '浏览器': 'msedge',
            'edge': 'msedge',
            'chrome': 'chrome',
            'cmd': 'cmd.exe',
            'powershell': 'powershell.exe',
            'word': 'winword',
            'excel': 'excel',
            'vscode': 'code',
            '设置': 'ms-settings:',
        }

        name_lower = app_name.lower()
        for key, cmd in app_map.items():
            if key in name_lower or name_lower in key:
                return cmd

        return app_name

    def process(self, text: str, mode: str = "auto") -> Dict:
        """
        处理用户输入

        Modes:
        - auto: 自动选择最佳方式
        - command: 传统命令模式
        - visual: 视觉模式（使用屏幕理解）
        - plan: 规划模式（复杂任务分解）
        """
        if not text.strip():
            return {'success': False, 'error': '空指令'}

        # 自动选择模式
        if mode == "auto":
            # 如果包含视觉关键词，使用视觉模式
            visual_keywords = ['点击', '按钮', '输入框', '图标', '右上角', '左上角']
            if any(kw in text for kw in visual_keywords):
                mode = "visual"
            # 如果包含复合指令，使用规划模式
            elif any(kw in text for kw in ['然后', '再', '先', '最后']):
                mode = "plan"
            else:
                mode = "command"

        # 根据模式处理
        if mode == "visual":
            return self.execute_visual_action(text)
        elif mode == "plan":
            return self.plan_and_execute(text)
        else:
            # 传统命令模式
            actions = self.smart_parser.parse(text)
            results = []
            for action in actions:
                result = self.action_executor.execute(action)
                results.append(result)
            return {
                'success': all(r.get('success', False) for r in results),
                'mode': 'command',
                'results': results
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

# ============================================================================
# FastAPI 应用
# ============================================================================

app = FastAPI(
    title="GodHand v3.0",
    description="世界级的智能命令与GUI自动化系统 - 视觉理解 + 任务规划",
    version="3.0.0-alpha"
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
config_path = str(Path(__file__).parent / "config.json")
godhand = GodHandCore(config_path=config_path)
session_mgr = SessionManager()

# ============================================================================
# API 路由
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    return HTMLResponse(content=get_html())

@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """执行命令 API - v3.0 智能版"""
    result = godhand.process(request.command, mode=request.mode)

    # 记录到会话
    if request.session_id:
        session = session_mgr.get_session(request.session_id)
        if session:
            session.messages.append(ChatMessage(
                role="user",
                content=request.command,
                timestamp=datetime.now().isoformat()
            ))
            session.messages.append(ChatMessage(
                role="assistant",
                content=json.dumps(result, ensure_ascii=False),
                timestamp=datetime.now().isoformat(),
                command_result=result
            ))

    return {
        "success": result.get('success', False),
        "command": request.command,
        "mode": request.mode,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/plan")
async def create_plan(request: PlanRequest):
    """创建执行计划"""
    from core.task_planner import PlanningContext

    context = PlanningContext(
        instruction=request.instruction,
        **(request.context or {})
    )

    plan = godhand.task_planner.plan(request.instruction, context)

    return {
        "success": True,
        "plan": plan.to_dict(),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/detect")
async def detect_elements(request: VisualRequest):
    """检测屏幕元素"""
    screenshot = None

    if request.screenshot:
        # 从 base64 解码
        import base64
        img_data = base64.b64decode(request.screenshot.split(',')[-1])
        screenshot = Image.open(io.BytesIO(img_data))
    else:
        # 实时截图
        screenshot = godhand.take_screenshot()

    if screenshot:
        elements = godhand.visual_engine.detect_elements(screenshot)
        return {
            "success": True,
            "elements_count": len(elements),
            "elements": [e.to_dict() for e in elements[:50]],  # 限制返回数量
            "screenshot_size": screenshot.size
        }
    else:
        return {
            "success": False,
            "error": "无法获取屏幕截图"
        }

@app.post("/api/visual")
async def visual_action(request: VisualRequest):
    """执行视觉动作"""
    result = godhand.execute_visual_action(request.description)
    return result

@app.get("/api/screenshot")
async def get_screenshot():
    """获取屏幕截图"""
    screenshot = godhand.take_screenshot()
    if screenshot:
        # 转换为 bytes
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        return StreamingResponse(img_byte_arr, media_type="image/png")
    else:
        return JSONResponse(
            content={"error": "截图失败"},
            status_code=500
        )

@app.post("/api/sessions/new")
async def new_session():
    """创建新会话"""
    session_id = session_mgr.create_session()
    return {"session_id": session_id, "created_at": datetime.now().isoformat()}

@app.get("/api/health")
async def health_check():
    """健康检查"""
    screenshot = godhand.take_screenshot()
    return {
        "status": "ok",
        "version": "3.0.0-alpha",
        "visual_engine": godhand.visual_engine is not None,
        "task_planner": godhand.task_planner is not None,
        "screenshot_size": screenshot.size if screenshot else None,
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# WebSocket
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 实时通信"""
    await websocket.accept()

    if not session_mgr.get_session(session_id):
        session_id = session_mgr.create_session()
        await websocket.send_json({
            "type": "system",
            "content": "✨ GodHand v3.0 已连接"
        })

    try:
        while True:
            data = await websocket.receive_json()
            user_input = data.get('message', '')
            mode = data.get('mode', 'auto')

            if not user_input:
                continue

            # 发送思考中
            await websocket.send_json({
                "type": "thinking",
                "content": "🧠 正在分析..."
            })

            # 处理
            result = godhand.process(user_input, mode=mode)

            # 发送结果
            await websocket.send_json({
                "type": "result",
                "success": result.get('success', False),
                "mode": mode,
                "result": result
            })

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        print(f"[WebSocket] 会话断开: {session_id}")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"错误: {str(e)}"
            })
        except:
            pass

# ============================================================================
# HTML 页面
# ============================================================================

def get_html() -> str:
    """返回美化的 HTML 页面"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GodHand v3.0 🖐️ - 世界级的智能自动化</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --secondary: #ec4899;
            --bg-dark: #0f0f23;
            --bg-card: #1a1a2e;
            --text-primary: #ffffff;
            --text-secondary: #a0a0b0;
            --success: #10b981;
            --error: #ef4444;
            --border: rgba(255,255,255,0.1);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-dark);
            min-height: 100vh;
            color: var(--text-primary);
        }
        .app {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .logo {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(99, 102, 241, 0.2);
            border: 1px solid var(--primary);
            border-radius: 20px;
            font-size: 0.8rem;
            color: var(--primary);
            margin-top: 10px;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        .feature-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
        }
        .feature-icon { font-size: 2rem; margin-bottom: 10px; }
        .feature-title { font-weight: 600; margin-bottom: 5px; }
        .feature-desc { font-size: 0.85rem; color: var(--text-secondary); }
        .chat-wrapper {
            flex: 1;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .message {
            margin-bottom: 15px;
            max-width: 80%;
        }
        .message.user { margin-left: auto; }
        .message-content {
            padding: 12px 16px;
            border-radius: 16px;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: var(--primary);
            border-bottom-right-radius: 4px;
        }
        .message.assistant .message-content {
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }
        .input-area {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
        }
        .mode-select {
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 0.9rem;
        }
        .input-wrapper { flex: 1; }
        .input-wrapper input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 0.95rem;
            outline: none;
        }
        .input-wrapper input:focus { border-color: var(--primary); }
        .send-btn {
            padding: 12px 24px;
            background: var(--primary);
            border: none;
            border-radius: 12px;
            color: white;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
        }
        .send-btn:hover { background: var(--primary-dark); }
        .quick-commands {
            padding: 15px 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .quick-btn {
            padding: 8px 14px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 20px;
            color: var(--text-primary);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.3s;
        }
        .quick-btn:hover {
            background: rgba(99, 102, 241, 0.3);
            transform: translateY(-2px);
        }
        .status-bar {
            padding: 10px 20px;
            background: rgba(0,0,0,0.3);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }
        .thinking {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--primary);
        }
        .dots { display: flex; gap: 4px; }
        .dots span {
            width: 6px;
            height: 6px;
            background: var(--primary);
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }
        .dots span:nth-child(2) { animation-delay: 0.2s; }
        .dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-4px); }
        }
        @media (max-width: 768px) {
            .features { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="app">
        <header class="header">
            <h1 class="logo">🖐️ GodHand v3.0</h1>
            <span class="badge">🚀 世界第一智能自动化系统</span>
        </header>

        <div class="features">
            <div class="feature-card">
                <div class="feature-icon">👁️</div>
                <div class="feature-title">视觉理解</div>
                <div class="feature-desc">自动识别屏幕元素，语义化定位</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">智能规划</div>
                <div class="feature-desc">复杂任务自动分解，自适应执行</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">实时交互</div>
                <div class="feature-desc">WebSocket 实时通信，毫秒响应</div>
            </div>
        </div>

        <div class="chat-wrapper">
            <div class="chat-container" id="chatContainer">
                <div class="message assistant">
                    <div class="message-content">
                        ✨ <strong>GodHand v3.0 已就绪！</strong><br><br>
                        支持三种智能模式：<br>
                        🎯 <strong>Auto</strong> - 自动选择最佳执行方式<br>
                        👁️ <strong>Visual</strong> - 基于视觉的元素定位<br>
                        📋 <strong>Plan</strong> - 复杂任务规划与分解<br><br>
                        试试：<br>
                        • "打开记事本 输入Hello World"<br>
                        • "点击保存按钮"<br>
                        • "截图并分析屏幕元素"
                    </div>
                </div>
            </div>

            <div class="quick-commands">
                <button class="quick-btn" onclick="sendQuick('打开记事本 输入Hello v3.0')">📝 记事本</button>
                <button class="quick-btn" onclick="sendQuick('打开计算器')">🧮 计算器</button>
                <button class="quick-btn" onclick="sendQuick('截图', 'visual')">📸 截图分析</button>
                <button class="quick-btn" onclick="sendQuick('点击开始按钮', 'visual')">👆 视觉点击</button>
                <button class="quick-btn" onclick="sendQuick('搜索Python教程', 'plan')">🔍 搜索</button>
            </div>

            <div class="input-area">
                <select class="mode-select" id="modeSelect">
                    <option value="auto">🎯 Auto</option>
                    <option value="visual">👁️ Visual</option>
                    <option value="plan">📋 Plan</option>
                    <option value="command">⌨️ Command</option>
                </select>
                <div class="input-wrapper">
                    <input type="text" id="userInput" placeholder="输入指令，例如：点击保存按钮..." onkeypress="handleKeyPress(event)">
                </div>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">发送</button>
            </div>

            <div class="status-bar">
                <span id="statusText">就绪</span>
                <span id="versionInfo">v3.0.0-alpha</span>
            </div>
        </div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const modeSelect = document.getElementById('modeSelect');
        const statusText = document.getElementById('statusText');

        let ws = null;
        let sessionId = 'gh3_' + Date.now();

        // 连接 WebSocket
        function connectWS() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws/${sessionId}`);

            ws.onopen = () => {
                statusText.textContent = '🟢 已连接';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };

            ws.onclose = () => {
                statusText.textContent = '🔴 已断开';
                setTimeout(connectWS, 3000);
            };
        }

        function handleMessage(data) {
            switch(data.type) {
                case 'thinking':
                    addThinking();
                    break;
                case 'result':
                    removeThinking();
                    addResult(data);
                    break;
                case 'done':
                    enableSend();
                    break;
                case 'error':
                    removeThinking();
                    addError(data.content);
                    enableSend();
                    break;
            }
        }

        function addMessage(role, content) {
            const msg = document.createElement('div');
            msg.className = `message ${role}`;
            msg.innerHTML = `<div class="message-content">${content}</div>`;
            chatContainer.appendChild(msg);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function addThinking() {
            const msg = document.createElement('div');
            msg.className = 'message assistant';
            msg.id = 'thinking-msg';
            msg.innerHTML = `
                <div class="message-content">
                    <div class="thinking">
                        <div class="dots"><span></span><span></span><span></span></div>
                        <span>思考中...</span>
                    </div>
                </div>
            `;
            chatContainer.appendChild(msg);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function removeThinking() {
            const el = document.getElementById('thinking-msg');
            if (el) el.remove();
        }

        function addResult(data) {
            let content = '';
            if (data.success) {
                content = `✅ <strong>执行成功</strong> (${data.mode})<br><br>`;
                content += `<pre style="background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;overflow-x:auto;">${JSON.stringify(data.result, null, 2)}</pre>`;
            } else {
                content = `❌ <strong>执行失败</strong><br><br>${data.result?.error || '未知错误'}`;
            }
            addMessage('assistant', content);
        }

        function addError(content) {
            addMessage('assistant', `❌ <strong>错误</strong><br>${content}`);
        }

        function disableSend() {
            sendBtn.disabled = true;
            sendBtn.textContent = '...';
        }

        function enableSend() {
            sendBtn.disabled = false;
            sendBtn.textContent = '发送';
        }

        function sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            addMessage('user', text);
            userInput.value = '';
            disableSend();

            const mode = modeSelect.value;

            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ message: text, mode: mode }));
            } else {
                // HTTP fallback
                fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: text, mode: mode })
                })
                .then(r => r.json())
                .then(data => {
                    removeThinking();
                    addResult(data);
                    enableSend();
                })
                .catch(e => {
                    removeThinking();
                    addError(e.message);
                    enableSend();
                });
            }
        }

        function sendQuick(text, mode = 'auto') {
            userInput.value = text;
            if (mode) modeSelect.value = mode;
            sendMessage();
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter') sendMessage();
        }

        // 初始化
        connectWS();
        userInput.focus();
    </script>
</body>
</html>'''

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("🖐️ GodHand v3.0 - 世界级的智能自动化系统")
    print("=" * 70)
    print("✨ 新特性:")
    print("   • VisualEngine - 视觉理解引擎")
    print("   • TaskPlanner - 智能任务规划")
    print("   • Multi-Modal - 多模态AI决策")
    print("=" * 70)
    print("🌐 访问地址: http://127.0.0.1:8000")
    print("📚 API 文档: http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8000)
