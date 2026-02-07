#!/usr/bin/env python3
"""
GodHand Pro v3 🖐️ - 统一智能命令与GUI自动化系统

核心改进:
- 分离模板文件
- 统一执行引擎 (Claw + Ghost 融合)
- WebSocket + HTTP API
- 性能监控
- 任务队列

API:
- POST /api/execute    - 执行指令
- POST /api/parse      - 仅解析
- POST /api/chat       - 对话模式
- WebSocket /ws/{session_id} - 实时通信
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager
import uuid

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# 导入核心模块
sys.path.insert(0, str(Path(__file__).parent / "core"))

try:
    from smart_parser_v2 import SmartParserV2, ActionExecutorV2, Action, ActionType, ParsedIntent, IntentCategory
    HAS_SMART_PARSER = True
except ImportError as e:
    HAS_SMART_PARSER = False
    logger.warning(f"SmartParser v2 not available: {e}")

try:
    from ghost_v3 import GhostHandPro, ExecutionMode, TaskStatus
    HAS_GHOSTHAND = True
except ImportError as e:
    HAS_GHOSTHAND = False
    logger.warning(f"GhostHand not available: {e}")

try:
    from claw_runner import ClawRunner
    HAS_CLAW = True
except ImportError as e:
    HAS_CLAW = False
    logger.warning(f"ClawRunner not available: {e}")


# ============================================================================
# 数据模型
# ============================================================================

class ExecuteRequest(BaseModel):
    """执行请求"""
    command: str = Field(..., description="要执行的指令")
    session_id: Optional[str] = Field(None, description="会话ID")
    mode: str = Field("auto", description="执行模式: auto, command, gui")
    confirm: bool = Field(False, description="是否需要确认")


class ExecuteResponse(BaseModel):
    """执行响应"""
    success: bool
    command: str
    mode: str
    intent: Optional[Dict] = None
    actions: List[Dict] = []
    results: List[Dict] = []
    execution_time: float
    timestamp: str


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


class Session(BaseModel):
    """会话"""
    id: str
    created_at: str
    messages: List[ChatMessage] = []
    context: Dict = {}


# ============================================================================
# 统一执行引擎
# ============================================================================

class UnifiedExecutor:
    """
    统一执行引擎
    根据指令类型自动选择最佳执行方式
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # 初始化组件
        self.parser = None
        self.ghost = None
        self.claw = None
        
        if HAS_SMART_PARSER:
            try:
                # 初始化 LLM 客户端供 SmartParser 使用
                llm_client = None
                if HAS_GHOSTHAND:
                    try:
                        from ghost_v3 import LLMClient
                        llm_client = LLMClient(config=self.config)
                        logger.info("[UnifiedExecutor] LLM client initialized for SmartParser")
                    except Exception as e:
                        logger.warning(f"[UnifiedExecutor] LLM client init failed: {e}")
                
                self.parser = SmartParserV2(llm_client=llm_client, config_path=config_path)
                self.action_executor = ActionExecutorV2()
                logger.info("[UnifiedExecutor] SmartParser v2 initialized")
            except Exception as e:
                logger.error(f"[UnifiedExecutor] SmartParser init failed: {e}")
        
        if HAS_GHOSTHAND:
            try:
                self.ghost = GhostHandPro(config_path=config_path)
                logger.info("[UnifiedExecutor] GhostHand initialized")
            except Exception as e:
                logger.error(f"[UnifiedExecutor] GhostHand init failed: {e}")
        
        if HAS_CLAW:
            try:
                self.claw = ClawRunner(config_path=config_path)
                logger.info("[UnifiedExecutor] ClawRunner initialized")
            except Exception as e:
                logger.error(f"[UnifiedExecutor] ClawRunner init failed: {e}")
        
        # 任务队列
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.is_processing = False
    
    def _load_config(self) -> Dict:
        """加载配置"""
        default = {
            'provider': 'google',
            'google': {'api_key': os.getenv('GOOGLE_API_KEY', ''), 'model': 'gemini-2.0-flash'},
            'openai': {'api_key': os.getenv('OPENAI_API_KEY', ''), 'model': 'gpt-4o'},
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    default.update(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default
    
    async def parse(self, instruction: str) -> tuple:
        """解析指令"""
        if self.parser:
            try:
                actions, intent = self.parser.parse(instruction)
                return actions, intent
            except Exception as e:
                logger.error(f"Parse error: {e}")
        
        # Fallback
        return [], ParsedIntent(
            category=IntentCategory.UNKNOWN,
            confidence=0.0,
            primary_action="unknown",
            parameters={},
            suggested_mode=ExecutionMode.AUTO
        )
    
    async def execute(self, instruction: str, mode: str = "auto") -> Dict:
        """
        执行指令
        
        执行策略:
        1. auto: 根据意图自动选择执行方式
        2. command: 使用 ClawRunner (后台命令)
        3. gui: 使用 GhostHand (GUI自动化)
        """
        start_time = datetime.now()
        
        # 解析
        actions, intent = await self.parse(instruction)
        
        # 确定执行模式
        if mode == "auto":
            if intent.suggested_mode == ExecutionMode.GUI or \
               intent.category == IntentCategory.GUI_AUTOMATION:
                exec_mode = "gui"
            elif intent.suggested_mode == ExecutionMode.COMMAND:
                exec_mode = "command"
            else:
                exec_mode = "hybrid"
        else:
            exec_mode = mode
        
        results = []
        success = True
        
        # 根据模式执行
        if exec_mode == "gui" and self.ghost:
            # GUI自动化模式
            try:
                loop = asyncio.get_event_loop()
                ghost_mode = ExecutionMode.GUI
                result = await loop.run_in_executor(
                    None, self.ghost.execute, instruction, ghost_mode
                )
                success = result
                results.append({
                    'success': result,
                    'output': 'GUI自动化执行完成' if result else 'GUI自动化执行失败',
                    'mode': 'gui'
                })
            except Exception as e:
                success = False
                results.append({'success': False, 'error': str(e), 'mode': 'gui'})
        
        elif exec_mode == "command" and self.claw:
            # 后台命令模式
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, self.claw.run, instruction
                )
                success = result
                results.append({
                    'success': result,
                    'output': '命令执行完成' if result else '命令执行失败',
                    'mode': 'command'
                })
            except Exception as e:
                success = False
                results.append({'success': False, 'error': str(e), 'mode': 'command'})
        
        else:
            # 混合模式 - 使用 SmartParser 的动作执行
            if actions and self.action_executor:
                for action in actions:
                    try:
                        if action.type == ActionType.UNKNOWN:
                            continue
                        
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None, self.action_executor.execute, action
                        )
                        results.append(result)
                        if not result.get('success'):
                            success = False
                    except Exception as e:
                        success = False
                        results.append({
                            'success': False,
                            'error': str(e),
                            'action': action.to_dict()
                        })
            else:
                success = False
                results.append({
                    'success': False,
                    'error': '无法解析指令或执行器不可用'
                })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'success': success,
            'command': instruction,
            'mode': exec_mode,
            'intent': {
                'category': intent.category.value,
                'confidence': intent.confidence,
                'suggested_mode': intent.suggested_mode.value
            },
            'actions': [a.to_dict() for a in actions],
            'results': results,
            'execution_time': execution_time,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# 会话管理器
# ============================================================================

class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.max_sessions = 100
    
    def create_session(self) -> str:
        """创建新会话"""
        session_id = f"gh_{uuid.uuid4().hex[:12]}"
        self.sessions[session_id] = Session(
            id=session_id,
            created_at=datetime.now().isoformat(),
            messages=[]
        )
        
        # 清理旧会话
        if len(self.sessions) > self.max_sessions:
            oldest = min(self.sessions.keys(), 
                        key=lambda k: self.sessions[k].created_at)
            del self.sessions[oldest]
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, role: str, content: str, 
                   metadata: Dict = None):
        """添加消息"""
        session = self.sessions.get(session_id)
        if session:
            message = ChatMessage(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata=metadata
            )
            session.messages.append(message)
    
    def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        return [m.dict() for m in session.messages]


# ============================================================================
# FastAPI 应用
# ============================================================================

# 全局实例
executor = UnifiedExecutor()
session_mgr = SessionManager()

# 模板
base_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(base_dir / "web" / "templates"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 60)
    logger.info("🖐️ GodHand Pro v3.0 启动中...")
    logger.info("=" * 60)
    
    # 检查组件状态
    components = {
        'SmartParser v2': HAS_SMART_PARSER,
        'GhostHand Pro': HAS_GHOSTHAND,
        'ClawRunner': HAS_CLAW
    }
    
    for name, available in components.items():
        status = "✅" if available else "❌"
        logger.info(f"  {status} {name}")
    
    logger.info("=" * 60)
    logger.info(f"📁 数据目录: {base_dir / 'data'}")
    logger.info(f"📸 截图目录: {base_dir / 'data' / 'screenshots'}")
    logger.info("=" * 60)
    
    yield
    
    # 关闭清理
    logger.info("GodHand Pro 关闭中...")


app = FastAPI(
    title="GodHand Pro",
    description="统一智能命令与GUI自动化系统 v3.0",
    version="3.0.0",
    lifespan=lifespan
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
static_dir = base_dir / "web" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/execute", response_model=ExecuteResponse)
async def execute_command(request: ExecuteRequest):
    """执行指令 API"""
    result = await executor.execute(request.command, request.mode)
    
    # 记录到会话
    if request.session_id:
        session_mgr.add_message(
            request.session_id,
            "assistant",
            f"执行: {request.command}",
            {'result': result}
        )
    
    return ExecuteResponse(**result)


@app.post("/api/parse")
async def parse_command(request: ExecuteRequest):
    """仅解析指令，不执行"""
    actions, intent = await executor.parse(request.command)
    
    return {
        "command": request.command,
        "intent": {
            "category": intent.category.value,
            "confidence": intent.confidence,
            "suggested_mode": intent.suggested_mode.value
        },
        "actions": [a.to_dict() for a in actions],
        "suggested_execution": intent.suggested_mode.value,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/chat")
async def chat(request: ExecuteRequest):
    """聊天 API - 返回解析结果和建议"""
    actions, intent = await executor.parse(request.command)
    
    # 生成回复
    if intent.confidence < 0.3:
        reply = f"🤔 我不太理解 '{request.command}'\n\n试试这些:\n"
        reply += "• 打开记事本 输入Hello World\n"
        reply += "• 打开计算器\n"
        reply += "• 搜索Python教程\n"
        reply += "• 截图\n"
        reply += "• 点击开始菜单"
    else:
        reply = f"✅ 我理解你的指令！\n\n"
        reply += f"**意图**: {intent.category.value} (置信度: {intent.confidence:.0%})\n"
        reply += f"**建议模式**: {intent.suggested_mode.value}\n\n"
        reply += f"包含 {len(actions)} 个动作:\n"
        
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
                'gui': '👁️',
                'unknown': '❓'
            }.get(action.type.value, '▶️')
            reply += f"{i}. {emoji} {action.description}\n"
    
    if request.session_id:
        session_mgr.add_message(request.session_id, "user", request.command)
        session_mgr.add_message(request.session_id, "assistant", reply)
    
    return {
        "reply": reply,
        "intent": {
            "category": intent.category.value,
            "confidence": intent.confidence
        },
        "actions": [a.to_dict() for a in actions],
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
            "content": f"✨ 新会话已创建: {session_id[:12]}...",
            "session_id": session_id
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
                "content": "🤔 正在理解指令..."
            })
            
            # 解析
            actions, intent = await executor.parse(user_input)
            
            # 检查是否全部无法解析
            if intent.confidence < 0.3:
                await websocket.send_json({
                    "type": "error",
                    "content": f"❌ 无法理解: {user_input}\n\n试试:\n• 打开记事本 输入123\n• 打开计算器\n• 搜索Python教程"
                })
                await websocket.send_json({"type": "done"})
                continue
            
            # 发送解析结果
            await websocket.send_json({
                "type": "parsed",
                "content": f"📋 解析为 {len(actions)} 个动作 (意图: {intent.category.value})",
                "intent": {
                    "category": intent.category.value,
                    "confidence": intent.confidence
                },
                "actions": [a.to_dict() for a in actions]
            })
            
            # 执行每个动作
            for i, action in enumerate(actions):
                if action.type.value == 'unknown':
                    continue
                
                await websocket.send_json({
                    "type": "executing",
                    "content": f"⚡ 执行: {action.description}"
                })
                
                # 执行
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, executor.action_executor.execute, action
                    )
                except Exception as e:
                    result = {'success': False, 'error': str(e)}
                
                # 发送结果
                await websocket.send_json({
                    "type": "result",
                    "success": result.get('success', False),
                    "action": action.to_dict(),
                    "output": result.get('output', ''),
                    "error": result.get('error')
                })
            
            # 完成
            await websocket.send_json({
                "type": "done",
                "content": "✅ 执行完成"
            })
            
    except WebSocketDisconnect:
        logger.info(f"[WebSocket] 会话断开: {session_id}")
    except Exception as e:
        logger.error(f"[WebSocket] 错误: {e}")
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
    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "3.0.0",
        "components": {
            "smart_parser": HAS_SMART_PARSER,
            "ghosthand": HAS_GHOSTHAND,
            "claw": HAS_CLAW
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/stats")
async def get_stats():
    """获取系统统计"""
    stats = {
        "sessions": len(session_mgr.sessions),
        "components": {
            "smart_parser": HAS_SMART_PARSER,
            "ghosthand": HAS_GHOSTHAND,
            "claw": HAS_CLAW
        }
    }
    
    if HAS_GHOSTHAND and executor.ghost:
        stats['ghost_stats'] = executor.ghost.get_stats()
    
    return stats


# ============================================================================
# 主入口
# ============================================================================

def run_server():
    """运行服务器"""
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("GodHand Pro v3.0 已启动")
    logger.info("访问地址: http://127.0.0.1:8000")
    logger.info("API文档: http://127.0.0.1:8000/docs")
    logger.info("=" * 60)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    run_server()
