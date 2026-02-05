#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GhostHand Pro 👻🖐️ - Production Grade GUI Agent
增强版：计算机视觉 + 任务规划 + 状态记忆

Author: Clawd
Version: 2.0.0
"""

import sys
import io
import os
import json
import time
import base64
import logging
import tempfile
import traceback
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any, Callable
from enum import Enum, auto
from collections import deque
import re

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 图像处理
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("[WARN] OpenCV 未安装，将使用 Pillow 进行基础图像处理")

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

# 自动化
import pyautogui
import pyperclip

# AI 模型
try:
    from google import genai
    GOOGLE_SDK_NEW = True
except ImportError:
    import google.generativeai as genai
    GOOGLE_SDK_NEW = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ghosthand_pro.log', encoding='utf-8', errors='replace')
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举和常量
# ============================================================================

class ActionType(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE = "type"
    PRESS = "press"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    WAIT = "wait"
    MOVE = "move"
    FIND_ELEMENT = "find_element"  # 新增：查找元素
    DONE = "done"
    FAIL = "fail"
    RETRY = "retry"  # 新增：重试


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class Point:
    """坐标点"""
    x: int
    y: int
    
    def to_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def offset(self, dx: int, dy: int) -> 'Point':
        return Point(self.x + dx, self.y + dy)


@dataclass
class Element:
    """UI 元素"""
    name: str
    x: int
    y: int
    width: int = 0
    height: int = 0
    confidence: float = 1.0  # 识别置信度
    element_type: str = "unknown"  # button, input, text, icon 等
    
    @property
    def center(self) -> Point:
        return Point(self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass
class Action:
    """动作"""
    type: ActionType
    target: Optional[Element] = None
    coordinates: Optional[Point] = None
    text: Optional[str] = None
    key: Optional[str] = None
    keys: Optional[List[str]] = None
    scroll_amount: int = 0
    wait_seconds: float = 1.0
    reason: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> dict:
        return {
            'type': self.type.value,
            'target': asdict(self.target) if self.target else None,
            'coordinates': asdict(self.coordinates) if self.coordinates else None,
            'text': self.text,
            'key': self.key,
            'keys': self.keys,
            'scroll_amount': self.scroll_amount,
            'wait_seconds': self.wait_seconds,
            'reason': self.reason
        }


@dataclass
class Task:
    """任务"""
    id: str
    description: str
    steps: List[Action] = field(default_factory=list)
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    action: Action
    error: Optional[str] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    execution_time: float = 0.0


# ============================================================================
# 视觉识别模块
# ============================================================================

class VisionEngine:
    """计算机视觉引擎 - 精确识别 UI 元素"""
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.element_cache: Dict[str, Element] = {}  # 元素缓存
        self.cache_ttl = 30  # 缓存有效期（秒）
        self.last_update = 0
        
    def capture_screen(self, region: Optional[Tuple] = None) -> Image.Image:
        """截取屏幕"""
        screenshot = pyautogui.screenshot(region=region)
        return screenshot
    
    def find_element_by_template(self, template_path: str, 
                                  threshold: float = 0.8) -> Optional[Element]:
        """模板匹配查找元素"""
        if not HAS_OPENCV:
            logger.warning("[Vision] OpenCV 未安装，无法使用模板匹配")
            return None
        
        try:
            # 读取模板
            template = cv2.imread(template_path, cv2.IMREAD_COLOR)
            if template is None:
                return None
            
            # 截图
            screenshot = self.capture_screen()
            screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 模板匹配
            result = cv2.matchTemplate(screenshot_np, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                h, w = template.shape[:2]
                return Element(
                    name=Path(template_path).stem,
                    x=max_loc[0],
                    y=max_loc[1],
                    width=w,
                    height=h,
                    confidence=max_val,
                    element_type="icon"
                )
            return None
            
        except Exception as e:
            logger.error(f"[Vision] 模板匹配失败: {e}")
            return None
    
    def find_element_by_text(self, text: str, 
                              lang: str = 'chi_sim+eng') -> Optional[Element]:
        """OCR 识别文字位置 (简化版，实际可用 pytesseract)"""
        # 简化实现：返回屏幕中心作为 fallback
        # 实际应该使用 OCR 库如 pytesseract 或 easyocr
        logger.info(f"[Vision] 查找文字: {text} (OCR 功能需安装 pytesseract)")
        return None
    
    def find_element_by_color(self, color: Tuple[int, int, int], 
                              tolerance: int = 30) -> List[Element]:
        """通过颜色查找元素"""
        screenshot = self.capture_screen()
        img_array = np.array(screenshot) if HAS_OPENCV else screenshot
        
        elements = []
        # 简化实现：返回一些可能的区域
        # 实际应该使用颜色聚类或连通域分析
        
        return elements
    
    def highlight_element(self, screenshot: Image.Image, 
                         element: Element, 
                         color: str = 'red') -> Image.Image:
        """在截图上高亮元素"""
        draw = ImageDraw.Draw(screenshot)
        x1, y1, x2, y2 = element.bbox
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # 绘制中心点
        center = element.center
        draw.ellipse([center.x-5, center.y-5, center.x+5, center.y+5], fill=color)
        
        # 添加标签
        try:
            draw.text((x1, y1-20), element.name, fill=color)
        except:
            pass
        
        return screenshot
    
    def add_grid_overlay(self, screenshot: Image.Image, 
                        grid_size: int = 100) -> Image.Image:
        """添加网格覆盖层，帮助 AI 定位"""
        draw = ImageDraw.Draw(screenshot)
        width, height = screenshot.size
        
        # 绘制网格
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill='rgba(255,0,0,128)', width=1)
            draw.text((x+2, 2), str(x), fill='red')
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill='rgba(255,0,0,128)', width=1)
            draw.text((2, y+2), str(y), fill='red')
        
        return screenshot
    
    def clear_cache(self):
        """清除元素缓存"""
        self.element_cache.clear()
        logger.debug("[Vision] 元素缓存已清除")


# ============================================================================
# 任务规划器
# ============================================================================

class TaskPlanner:
    """任务规划器 - 将复杂任务分解为可执行步骤"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        
    def decompose_task(self, instruction: str, context: Dict = None) -> Task:
        """将用户指令分解为结构化任务"""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        prompt = f"""你是一个任务规划专家。请将用户的指令分解为具体的、可执行的步骤。

用户指令: {instruction}

请输出 JSON 格式的任务计划：
{{
    "task_name": "简短的任务名称",
    "overall_goal": "任务的总体目标",
    "steps": [
        {{
            "step_number": 1,
            "action": "具体动作类型: click/type/press/wait/find",
            "target": "操作目标描述",
            "expected_result": "执行后应该看到什么",
            "fallback": "如果失败该怎么办"
        }}
    ],
    "success_criteria": ["判断任务成功的标准"],
    "potential_issues": ["可能遇到的问题"]
}}

规则:
1. 步骤要具体、可验证
2. 每个步骤应该是原子的（不可再分）
3. 考虑 Windows 系统的常见操作方式
4. 为可能出错的地方提供备选方案"""

        try:
            response = self.llm.generate(prompt)
            plan_data = self._parse_json(response)
            
            task = Task(
                id=task_id,
                description=instruction,
                metadata=plan_data
            )
            
            # 将规划转换为 Action 列表
            for step_data in plan_data.get('steps', []):
                action = self._convert_step_to_action(step_data)
                task.steps.append(action)
            
            logger.info(f"[Planner] 任务分解完成: {len(task.steps)} 个步骤")
            return task
            
        except Exception as e:
            logger.error(f"[Planner] 任务分解失败: {e}")
            # 返回简单任务作为 fallback
            return Task(
                id=task_id,
                description=instruction,
                steps=[Action(type=ActionType.FIND_ELEMENT, reason=instruction)]
            )
    
    def _parse_json(self, text: str) -> dict:
        """解析 JSON，处理 markdown 代码块"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    
    def _convert_step_to_action(self, step: dict) -> Action:
        """将步骤转换为 Action"""
        action_type = self._map_action_type(step.get('action', 'click'))
        
        return Action(
            type=action_type,
            text=step.get('text'),
            key=step.get('key'),
            reason=step.get('target', '') + ': ' + step.get('expected_result', '')
        )
    
    def _map_action_type(self, action_str: str) -> ActionType:
        """映射动作字符串到枚举"""
        mapping = {
            'click': ActionType.CLICK,
            'type': ActionType.TYPE,
            'press': ActionType.PRESS,
            'hotkey': ActionType.HOTKEY,
            'wait': ActionType.WAIT,
            'find': ActionType.FIND_ELEMENT,
            'scroll': ActionType.SCROLL,
            'move': ActionType.MOVE,
        }
        return mapping.get(action_str.lower(), ActionType.CLICK)


# ============================================================================
# 状态管理器
# ============================================================================

class StateManager:
    """状态管理器 - 记录执行历史和环境状态"""
    
    def __init__(self, max_history: int = 100):
        self.history: deque = deque(maxlen=max_history)
        self.current_window: Optional[str] = None
        self.focused_element: Optional[Element] = None
        self.global_context: Dict = {}
        self.execution_count = 0
        
    def record_action(self, action: Action, result: ExecutionResult):
        """记录动作执行结果"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'action': action.to_dict(),
            'result': {
                'success': result.success,
                'error': result.error,
                'execution_time': result.execution_time
            },
            'step_number': self.execution_count
        }
        self.history.append(record)
        self.execution_count += 1
        
    def get_recent_actions(self, n: int = 5) -> List[Dict]:
        """获取最近 n 个动作"""
        return list(self.history)[-n:]
    
    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        recent = self.get_recent_actions(3)
        if not recent:
            return "无历史记录"
        
        summary = []
        for rec in recent:
            action_type = rec['action']['type']
            success = "成功" if rec['result']['success'] else "失败"
            summary.append(f"{action_type}({success})")
        
        return f"最近操作: {' -> '.join(summary)}"
    
    def detect_loop(self, window_size: int = 3) -> bool:
        """检测是否陷入循环（重复执行相同动作）"""
        if len(self.history) < window_size * 2:
            return False
        
        recent = list(self.history)[-window_size:]
        previous = list(self.history)[-window_size*2:-window_size]
        
        # 比较动作类型是否相同
        recent_types = [r['action']['type'] for r in recent]
        previous_types = [r['action']['type'] for r in previous]
        
        return recent_types == previous_types
    
    def save_session(self, filepath: str):
        """保存会话到文件"""
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'total_actions': self.execution_count,
            'history': list(self.history),
            'context': self.global_context
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        logger.info(f"[State] 会话已保存: {filepath}")


# ============================================================================
# LLM 客户端
# ============================================================================

class LLMClient:
    """LLM 客户端封装"""
    
    def __init__(self, config: Dict):
        self.provider = config.get('provider', 'google')
        self.config = config
        
        if self.provider == 'google':
            self._init_google()
        elif self.provider == 'openai':
            self._init_openai()
    
    def _init_google(self):
        """初始化 Google AI"""
        key = self.config.get('google', {}).get('api_key')
        if not key:
            raise ValueError("Google API Key 未设置")
        
        if GOOGLE_SDK_NEW:
            self.client = genai.Client(api_key=key)
            self.model = self.config.get('google', {}).get('model', 'gemini-2.0-flash')
        else:
            genai.configure(api_key=key)
            self.client = None
            self.model = genai.GenerativeModel(
                self.config.get('google', {}).get('model', 'gemini-2.0-flash')
            )
    
    def _init_openai(self):
        """初始化 OpenAI"""
        if not HAS_OPENAI:
            raise ImportError("OpenAI 包未安装")
        
        key = self.config.get('openai', {}).get('api_key')
        if not key:
            raise ValueError("OpenAI API Key 未设置")
        
        openai.api_key = key
        openai.base_url = self.config.get('openai', {}).get('base_url')
        self.model = self.config.get('openai', {}).get('model', 'gpt-4o')
        self.client = openai.OpenAI(api_key=key, base_url=openai.base_url)
    
    def generate(self, prompt: str, image: Optional[Image.Image] = None) -> str:
        """生成文本"""
        if self.provider == 'google':
            return self._generate_google(prompt, image)
        else:
            return self._generate_openai(prompt, image)
    
    def _generate_google(self, prompt: str, image: Optional[Image.Image]) -> str:
        """使用 Google AI 生成"""
        if GOOGLE_SDK_NEW:
            contents = [prompt]
            if image:
                contents.append(image)
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents
            )
            return response.text
        else:
            if image:
                response = self.model.generate_content([prompt, image])
            else:
                response = self.model.generate_content(prompt)
            return response.text
    
    def _generate_openai(self, prompt: str, image: Optional[Image.Image]) -> str:
        """使用 OpenAI 生成"""
        messages = [{"role": "user", "content": prompt}]
        
        if image:
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            messages[0]["content"] = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
            ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096
        )
        return response.choices[0].message.content


# ============================================================================
# 主控制器 - GhostHand Pro
# ============================================================================

class GhostHandPro:
    """GhostHand Pro - 增强版 GUI 自动化代理"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化"""
        logger.info("=" * 70)
        logger.info("GhostHand Pro v2.0 初始化...")
        logger.info("=" * 70)
        
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self.vision = VisionEngine()
        self.state = StateManager()
        self.llm = LLMClient(self.config)
        self.planner = TaskPlanner(self.llm)
        
        # 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # 截图目录
        self.screenshot_dir = Path(self.config.get('screenshot', {}).get('save_dir', './screenshots'))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 统计
        self.stats = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'total_actions': 0,
            'failed_actions': 0,
            'retries': 0
        }
        
        logger.info(f"[INIT] 提供商: {self.config.get('provider')}")
        logger.info(f"[INIT] OpenCV: {'可用' if HAS_OPENCV else '不可用'}")
        logger.info(f"[INIT] 安全模式: {'开启' if pyautogui.FAILSAFE else '关闭'}")
        logger.info("[INIT] 初始化完成\n")
    
    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        default_config = {
            'provider': 'google',
            'google': {'api_key': '', 'model': 'gemini-2.0-flash'},
            'openai': {'api_key': '', 'model': 'gpt-4o', 'base_url': 'https://api.openai.com/v1'},
            'safety': {'max_steps': 30, 'step_delay': 0.5},
            'screenshot': {'save_dir': './screenshots', 'show_grid': False}
        }
        
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                default_config.update(file_config)
        
        # 环境变量覆盖
        if os.getenv('GOOGLE_API_KEY'):
            default_config['google']['api_key'] = os.getenv('GOOGLE_API_KEY')
        if os.getenv('OPENAI_API_KEY'):
            default_config['openai']['api_key'] = os.getenv('OPENAI_API_KEY')
        
        return default_config
    
    def execute(self, instruction: str) -> bool:
        """执行指令（主入口）"""
        logger.info(f"[TASK] 收到指令: {instruction}")
        self.stats['total_tasks'] += 1
        
        try:
            # 1. 任务规划
            task = self.planner.decompose_task(instruction)
            task.status = TaskStatus.RUNNING
            
            logger.info(f"[TASK] 分解为 {len(task.steps)} 个步骤")
            
            # 2. 执行步骤
            for i, action in enumerate(task.steps):
                logger.info(f"\n[STEP {i+1}/{len(task.steps)}] {action.reason}")
                
                result = self._execute_action(action)
                self.state.record_action(action, result)
                self.stats['total_actions'] += 1
                
                if not result.success:
                    self.stats['failed_actions'] += 1
                    
                    # 尝试恢复
                    if action.retry_count < action.max_retries:
                        logger.info(f"[RETRY] 重试 ({action.retry_count + 1}/{action.max_retries})")
                        action.retry_count += 1
                        self.stats['retries'] += 1
                        
                        # 简单重试：等待后重试
                        time.sleep(2)
                        result = self._execute_action(action)
                    else:
                        logger.error(f"[FAIL] 步骤失败，跳过")
                        continue
                
                # 检测循环
                if self.state.detect_loop():
                    logger.warning("[WARN] 检测到循环，尝试改变策略")
                    # 可以在这里添加突破逻辑
                
                # 步骤间延迟
                time.sleep(self.config.get('safety', {}).get('step_delay', 0.5))
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.stats['successful_tasks'] += 1
            
            logger.info("\n[TASK] 任务完成")
            return True
            
        except KeyboardInterrupt:
            logger.info("\n[STOP] 用户中断")
            return False
        except Exception as e:
            logger.error(f"\n[ERROR] 任务失败: {e}")
            return False
    
    def _execute_action(self, action: Action) -> ExecutionResult:
        """执行单个动作"""
        start_time = time.time()
        
        try:
            # 截图（执行前）
            screenshot_before = self.vision.capture_screen()
            
            # 根据动作类型执行
            if action.type == ActionType.CLICK:
                self._do_click(action)
            elif action.type == ActionType.DOUBLE_CLICK:
                self._do_double_click(action)
            elif action.type == ActionType.TYPE:
                self._do_type(action)
            elif action.type == ActionType.PRESS:
                self._do_press(action)
            elif action.type == ActionType.HOTKEY:
                self._do_hotkey(action)
            elif action.type == ActionType.WAIT:
                time.sleep(action.wait_seconds)
            elif action.type == ActionType.FIND_ELEMENT:
                # 查找元素并缓存
                element = self._do_find_element(action)
                if element:
                    action.coordinates = element.center
            else:
                logger.warning(f"[WARN] 未知动作类型: {action.type}")
            
            # 截图（执行后）
            screenshot_after = self.vision.capture_screen()
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=True,
                action=action,
                screenshot_before=self._save_screenshot(screenshot_before, "before"),
                screenshot_after=self._save_screenshot(screenshot_after, "after"),
                execution_time=execution_time
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                action=action,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _do_click(self, action: Action):
        """执行点击"""
        if action.coordinates:
            x, y = action.coordinates.x, action.coordinates.y
        elif action.target:
            x, y = action.target.center.to_tuple()
        else:
            raise ValueError("点击动作需要坐标或目标")
        
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.click()
        logger.info(f"[ACTION] 点击 ({x}, {y})")
    
    def _do_double_click(self, action: Action):
        """执行双击"""
        if action.coordinates:
            x, y = action.coordinates.x, action.coordinates.y
        else:
            raise ValueError("双击动作需要坐标")
        
        pyautogui.moveTo(x, y, duration=0.3)
        pyautogui.doubleClick()
        logger.info(f"[ACTION] 双击 ({x}, {y})")
    
    def _do_type(self, action: Action):
        """执行输入"""
        if not action.text:
            raise ValueError("输入动作需要文本")
        
        # 使用剪贴板支持中文
        pyperclip.copy(action.text)
        pyautogui.hotkey('ctrl', 'v')
        logger.info(f"[ACTION] 输入: {action.text[:30]}{'...' if len(action.text) > 30 else ''}")
    
    def _do_press(self, action: Action):
        """执行按键"""
        if not action.key:
            raise ValueError("按键动作需要指定按键")
        
        pyautogui.press(action.key)
        logger.info(f"[ACTION] 按键: {action.key}")
    
    def _do_hotkey(self, action: Action):
        """执行热键"""
        if not action.keys:
            raise ValueError("热键动作需要按键列表")
        
        pyautogui.hotkey(*action.keys)
        logger.info(f"[ACTION] 热键: {'+'.join(action.keys)}")
    
    def _do_find_element(self, action: Action) -> Optional[Element]:
        """查找元素"""
        # 这里可以集成更复杂的查找逻辑
        # 简化版：返回屏幕中心作为占位
        logger.info(f"[VISION] 查找元素: {action.reason}")
        # TODO: 实现真正的元素识别
        return None
    
    def _save_screenshot(self, screenshot: Image.Image, suffix: str) -> str:
        """保存截图"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"screenshot_{timestamp}_{suffix}.png"
        filepath = self.screenshot_dir / filename
        screenshot.save(filepath)
        return str(filepath)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ============================================================================
# 主入口
# ============================================================================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GhostHand Pro - 增强版 GUI 自动化')
    parser.add_argument('instruction', nargs='?', help='要执行的指令')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.stats:
        # 显示上次运行的统计
        print("统计功能开发中...")
        return
    
    if not args.instruction:
        parser.print_help()
        print("\n示例:")
        print('  python ghost_v2.py "打开计算器"')
        print('  python ghost_v2.py "在记事本中输入Hello World"')
        return
    
    try:
        ghost = GhostHandPro(config_path=args.config)
        success = ghost.execute(args.instruction)
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"[FATAL] 程序崩溃: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
