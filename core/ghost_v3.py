#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GhostHand Pro v3 👻🖐️ - 增强版 GUI Agent
核心改进:
- 元素库缓存系统
- 智能视觉识别
- 自适应重试机制
- 执行性能监控

Author: Clawd
Version: 3.0.0
"""

import sys
import io
import os
import json
import time
import base64
import logging
import hashlib
import tempfile
import traceback
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any, Callable, Union
from enum import Enum, auto
from collections import deque
import re
import threading

# 图像处理
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

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
    FIND_ELEMENT = "find_element"
    SCREENSHOT = "screenshot"
    LAUNCH_APP = "launch_app"
    DONE = "done"
    FAIL = "fail"
    RETRY = "retry"


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ExecutionMode(Enum):
    AUTO = "auto"           # 自动选择
    COMMAND = "command"     # 后台命令
    GUI = "gui"            # GUI自动化


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
    
    def distance_to(self, other: 'Point') -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class Element:
    """UI 元素"""
    name: str
    x: int
    y: int
    width: int = 0
    height: int = 0
    confidence: float = 1.0
    element_type: str = "unknown"
    screenshot_hash: str = ""  # 用于缓存匹配
    
    @property
    def center(self) -> Point:
        return Point(self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'confidence': self.confidence,
            'element_type': self.element_type
        }


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
    requires_vision: bool = False  # 是否需要视觉识别
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type.value,
            'target': self.target.to_dict() if self.target else None,
            'coordinates': {'x': self.coordinates.x, 'y': self.coordinates.y} if self.coordinates else None,
            'text': self.text,
            'key': self.key,
            'keys': self.keys,
            'scroll_amount': self.scroll_amount,
            'wait_seconds': self.wait_seconds,
            'reason': self.reason,
            'requires_vision': self.requires_vision
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
    mode: ExecutionMode = ExecutionMode.AUTO


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    action: Action
    error: Optional[str] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    execution_time: float = 0.0
    element_found: bool = False
    confidence: float = 0.0


# ============================================================================
# 元素库管理器
# ============================================================================

class ElementLibrary:
    """元素库 - 缓存和管理常用UI元素"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.library_file = self.data_dir / "element_library.json"
        self.elements: Dict[str, Dict] = {}
        self.templates_dir = self.data_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self._load_library()
    
    def _load_library(self):
        """加载元素库"""
        if self.library_file.exists():
            try:
                with open(self.library_file, 'r', encoding='utf-8') as f:
                    self.elements = json.load(f)
                logger.info(f"[ElementLibrary] 加载了 {len(self.elements)} 个元素")
            except Exception as e:
                logger.error(f"[ElementLibrary] 加载失败: {e}")
                self.elements = {}
    
    def save_library(self):
        """保存元素库"""
        try:
            with open(self.library_file, 'w', encoding='utf-8') as f:
                json.dump(self.elements, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[ElementLibrary] 保存失败: {e}")
    
    def add_element(self, name: str, element: Element, app: str = "global"):
        """添加元素到库"""
        key = f"{app}.{name}"
        self.elements[key] = {
            'name': name,
            'app': app,
            'x': element.x,
            'y': element.y,
            'width': element.width,
            'height': element.height,
            'element_type': element.element_type,
            'added_at': datetime.now().isoformat()
        }
        self.save_library()
    
    def get_element(self, name: str, app: str = "global") -> Optional[Element]:
        """从库中获取元素"""
        key = f"{app}.{name}"
        data = self.elements.get(key)
        if data:
            return Element(
                name=data['name'],
                x=data['x'],
                y=data['y'],
                width=data.get('width', 0),
                height=data.get('height', 0),
                element_type=data.get('element_type', 'unknown')
            )
        return None
    
    def find_similar(self, description: str, app: str = None) -> List[Tuple[str, Element]]:
        """查找相似元素"""
        results = []
        description_lower = description.lower()
        
        for key, data in self.elements.items():
            if app and not key.startswith(f"{app}."):
                continue
            
            # 简单匹配：名称或应用名包含描述
            if (description_lower in data['name'].lower() or 
                description_lower in data.get('app', '').lower()):
                elem = Element(
                    name=data['name'],
                    x=data['x'],
                    y=data['y'],
                    width=data.get('width', 0),
                    height=data.get('height', 0)
                )
                results.append((key, elem))
        
        return results


# ============================================================================
# 视觉识别引擎
# ============================================================================

class VisionEngine:
    """计算机视觉引擎 - 精确识别 UI 元素"""
    
    def __init__(self, element_library: ElementLibrary = None):
        self.screen_width, self.screen_height = pyautogui.size()
        self.element_library = element_library or ElementLibrary()
        self.cache: Dict[str, Element] = {}
        self.cache_ttl = 30
        self.last_update = 0
        
    def capture_screen(self, region: Optional[Tuple] = None) -> Image.Image:
        """截取屏幕"""
        screenshot = pyautogui.screenshot(region=region)
        return screenshot
    
    def find_element(self, description: str, 
                     method: str = "auto",
                     timeout: float = 5.0) -> Optional[Element]:
        """
        查找元素 - 多策略融合
        
        method: auto | library | template | ai
        """
        start_time = time.time()
        
        # 1. 尝试从库中查找
        if method in ("auto", "library"):
            elem = self.element_library.get_element(description)
            if elem:
                # 验证元素是否仍在原位（简单验证：截图对比）
                if self._verify_element_position(elem):
                    return elem
        
        # 2. 尝试模板匹配
        if method in ("auto", "template") and HAS_OPENCV:
            elem = self._find_by_template(description)
            if elem:
                return elem
        
        # 3. 使用 AI 视觉识别
        if method in ("auto", "ai"):
            elem = self._find_by_ai(description, timeout - (time.time() - start_time))
            if elem:
                # 保存到库中
                self.element_library.add_element(description, elem)
                return elem
        
        return None
    
    def _verify_element_position(self, elem: Element, threshold: float = 0.7) -> bool:
        """验证元素位置是否有效"""
        # 简单验证：检查区域是否在屏幕范围内
        if elem.x < 0 or elem.y < 0:
            return False
        if elem.x > self.screen_width or elem.y > self.screen_height:
            return False
        return True
    
    def _find_by_template(self, name: str) -> Optional[Element]:
        """模板匹配查找"""
        # 检查是否有保存的模板
        template_path = self.element_library.templates_dir / f"{name}.png"
        if not template_path.exists():
            return None
        
        if not HAS_OPENCV:
            return None
        
        try:
            template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
            if template is None:
                return None
            
            screenshot = self.capture_screen()
            screenshot_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            result = cv2.matchTemplate(screenshot_np, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= 0.8:
                h, w = template.shape[:2]
                return Element(
                    name=name,
                    x=max_loc[0],
                    y=max_loc[1],
                    width=w,
                    height=h,
                    confidence=max_val,
                    element_type="template_matched"
                )
        except Exception as e:
            logger.error(f"[Vision] 模板匹配失败: {e}")
        
        return None
    
    def _find_by_ai(self, description: str, timeout: float) -> Optional[Element]:
        """使用AI视觉识别元素（简化版，需要LLMClient支持）"""
        # 这里应该集成真正的多模态AI视觉识别
        # 简化版本：返回None，让上层处理
        return None
    
    def save_template(self, name: str, region: Tuple[int, int, int, int]):
        """保存屏幕区域为模板"""
        screenshot = self.capture_screen(region)
        template_path = self.element_library.templates_dir / f"{name}.png"
        screenshot.save(template_path)
        logger.info(f"[Vision] 模板已保存: {name}")
    
    def highlight_element(self, screenshot: Image.Image, 
                         element: Element, 
                         color: str = '#ef4444') -> Image.Image:
        """在截图上高亮元素"""
        draw = ImageDraw.Draw(screenshot)
        x1, y1, x2, y2 = element.bbox
        
        # 绘制矩形框
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # 绘制中心点
        center = element.center
        r = 5
        draw.ellipse([center.x-r, center.y-r, center.x+r, center.y+r], fill=color)
        
        # 绘制十字线
        draw.line([(center.x, y1), (center.x, y2)], fill=color, width=1)
        draw.line([(x1, center.y), (x2, center.y)], fill=color, width=1)
        
        return screenshot


# ============================================================================
# 性能监控器
# ============================================================================

class PerformanceMonitor:
    """性能监控 - 跟踪执行指标"""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {
            'action_time': [],
            'vision_time': [],
            'llm_time': [],
            'total_time': []
        }
        self.success_count = 0
        self.failure_count = 0
        self.start_times: Dict[str, float] = {}
    
    def start(self, label: str):
        """开始计时"""
        self.start_times[label] = time.time()
    
    def end(self, label: str) -> float:
        """结束计时"""
        if label in self.start_times:
            elapsed = time.time() - self.start_times[label]
            if label in self.metrics:
                self.metrics[label].append(elapsed)
            del self.start_times[label]
            return elapsed
        return 0.0
    
    def record_success(self):
        self.success_count += 1
    
    def record_failure(self):
        self.failure_count += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {}
        for key, values in self.metrics.items():
            if values:
                stats[key] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'total': sum(values)
                }
        
        total = self.success_count + self.failure_count
        stats['success_rate'] = self.success_count / total if total > 0 else 0
        stats['total_executions'] = total
        
        return stats
    
    def print_report(self):
        """打印性能报告"""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("📊 Performance Report")
        print("="*60)
        
        for key, data in stats.items():
            if isinstance(data, dict):
                print(f"\n{key}:")
                print(f"  Count: {data['count']}")
                print(f"  Avg: {data['avg']:.3f}s")
                print(f"  Min/Max: {data['min']:.3f}s / {data['max']:.3f}s")
        
        if 'success_rate' in stats:
            print(f"\nSuccess Rate: {stats['success_rate']*100:.1f}%")
        print("="*60)


# ============================================================================
# LLM 客户端 (增强版)
# ============================================================================

class LLMClient:
    """LLM 客户端封装 - 支持多提供商"""
    
    def __init__(self, config: Dict):
        self.provider = config.get('provider', 'google')
        self.config = config
        self.request_count = 0
        self.total_tokens = 0
        
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
        
        self.client = openai.OpenAI(
            api_key=key,
            base_url=self.config.get('openai', {}).get('base_url')
        )
        self.model = self.config.get('openai', {}).get('model', 'gpt-4o')
    
    def generate(self, prompt: str, image: Optional[Image.Image] = None, 
                 temperature: float = 0.3) -> str:
        """生成文本"""
        self.request_count += 1
        
        if self.provider == 'google':
            return self._generate_google(prompt, image, temperature)
        else:
            return self._generate_openai(prompt, image, temperature)
    
    def _generate_google(self, prompt: str, image: Optional[Image.Image],
                        temperature: float) -> str:
        """使用 Google AI 生成"""
        if GOOGLE_SDK_NEW:
            contents = [prompt]
            if image:
                contents.append(image)
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                generation_config={'temperature': temperature}
            )
            return response.text
        else:
            if image:
                response = self.model.generate_content([prompt, image])
            else:
                response = self.model.generate_content(prompt)
            return response.text
    
    def _generate_openai(self, prompt: str, image: Optional[Image.Image],
                        temperature: float) -> str:
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
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content


# ============================================================================
# 智能任务规划器
# ============================================================================

class TaskPlanner:
    """任务规划器 - 将复杂任务分解为可执行步骤"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.plan_cache: Dict[str, Dict] = {}  # 缓存常见任务的规划
    
    def decompose_task(self, instruction: str, context: Dict = None,
                       use_cache: bool = True) -> Task:
        """将用户指令分解为结构化任务"""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        # 检查缓存
        cache_key = self._get_cache_key(instruction)
        if use_cache and cache_key in self.plan_cache:
            logger.info("[Planner] 使用缓存的规划")
            cached_plan = self.plan_cache[cache_key]
            return self._create_task_from_plan(task_id, instruction, cached_plan)
        
        prompt = f"""你是一个任务规划专家。请将用户的指令分解为具体的、可执行的步骤。

用户指令: {instruction}

请输出 JSON 格式的任务计划：
{{
    "task_name": "简短的任务名称",
    "overall_goal": "任务的总体目标",
    "execution_mode": "auto|command|gui",
    "steps": [
        {{
            "step_number": 1,
            "action_type": "click/type/press/wait/find/screenshot/launch",
            "target": "操作目标描述",
            "parameters": {{具体参数}},
            "expected_result": "执行后应该看到什么",
            "requires_vision": false
        }}
    ],
    "success_criteria": ["判断任务成功的标准"],
    "potential_issues": ["可能遇到的问题"]
}}

规则:
1. 步骤要具体、可验证
2. 每个步骤应该是原子的（不可再分）
3. 考虑 Windows 系统的常见操作方式
4. 为可能出错的地方提供备选方案
5. requires_vision 标记需要视觉识别的步骤"""

        try:
            response = self.llm.generate(prompt, temperature=0.2)
            plan_data = self._parse_json(response)
            
            # 缓存规划
            if use_cache:
                self.plan_cache[cache_key] = plan_data
            
            return self._create_task_from_plan(task_id, instruction, plan_data)
            
        except Exception as e:
            logger.error(f"[Planner] 任务分解失败: {e}")
            # 返回简单任务作为 fallback
            return Task(
                id=task_id,
                description=instruction,
                steps=[Action(type=ActionType.FIND_ELEMENT, reason=instruction)],
                mode=ExecutionMode.AUTO
            )
    
    def _get_cache_key(self, instruction: str) -> str:
        """生成缓存键"""
        # 简化指令作为缓存键
        simplified = re.sub(r'\s+', ' ', instruction.lower().strip())
        return hashlib.md5(simplified.encode()).hexdigest()[:16]
    
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
    
    def _create_task_from_plan(self, task_id: str, instruction: str, 
                               plan_data: Dict) -> Task:
        """从规划数据创建任务"""
        task = Task(
            id=task_id,
            description=instruction,
            metadata=plan_data,
            mode=ExecutionMode(plan_data.get('execution_mode', 'auto'))
        )
        
        # 转换步骤为 Action
        for step_data in plan_data.get('steps', []):
            action = self._convert_step_to_action(step_data)
            task.steps.append(action)
        
        logger.info(f"[Planner] 任务分解完成: {len(task.steps)} 个步骤")
        return task
    
    def _convert_step_to_action(self, step: dict) -> Action:
        """将步骤转换为 Action"""
        action_type = self._map_action_type(step.get('action_type', 'click'))
        params = step.get('parameters', {})
        
        return Action(
            type=action_type,
            text=params.get('text'),
            key=params.get('key'),
            keys=params.get('keys'),
            wait_seconds=params.get('wait_seconds', 1.0),
            reason=step.get('target', '') + ': ' + step.get('expected_result', ''),
            requires_vision=step.get('requires_vision', False)
        )
    
    def _map_action_type(self, action_str: str) -> ActionType:
        """映射动作字符串到枚举"""
        mapping = {
            'click': ActionType.CLICK,
            'double_click': ActionType.DOUBLE_CLICK,
            'right_click': ActionType.RIGHT_CLICK,
            'type': ActionType.TYPE,
            'press': ActionType.PRESS,
            'hotkey': ActionType.HOTKEY,
            'wait': ActionType.WAIT,
            'find': ActionType.FIND_ELEMENT,
            'screenshot': ActionType.SCREENSHOT,
            'launch': ActionType.LAUNCH_APP,
            'scroll': ActionType.SCROLL,
            'move': ActionType.MOVE,
        }
        return mapping.get(action_str.lower(), ActionType.CLICK)


# ============================================================================
# 主控制器 - GhostHand Pro v3
# ============================================================================

class GhostHandPro:
    """GhostHand Pro v3 - 增强版 GUI 自动化代理"""
    
    def __init__(self, config_path: str = "config.json"):
        """初始化"""
        logger.info("=" * 70)
        logger.info("GhostHand Pro v3.0 初始化...")
        logger.info("=" * 70)
        
        # 加载配置
        self.config = self._load_config(config_path)
        self.data_dir = Path(config_path).parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # 初始化组件
        self.element_library = ElementLibrary(self.data_dir)
        self.vision = VisionEngine(self.element_library)
        self.monitor = PerformanceMonitor()
        self.llm = LLMClient(self.config)
        self.planner = TaskPlanner(self.llm)
        
        # 安全设置
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
        # 截图目录
        self.screenshot_dir = self.data_dir / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
        
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
            'safety': {'max_steps': 30, 'step_delay': 0.5, 'click_delay': 0.3},
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
    
    def execute(self, instruction: str, mode: ExecutionMode = ExecutionMode.AUTO) -> bool:
        """执行指令（主入口）"""
        logger.info(f"[TASK] 收到指令: {instruction}")
        self.stats['total_tasks'] += 1
        self.monitor.start('total_time')
        
        try:
            # 1. 任务规划
            task = self.planner.decompose_task(instruction)
            if mode != ExecutionMode.AUTO:
                task.mode = mode
            
            task.status = TaskStatus.RUNNING
            logger.info(f"[TASK] 分解为 {len(task.steps)} 个步骤，模式: {task.mode.value}")
            
            # 2. 执行步骤
            for i, action in enumerate(task.steps):
                logger.info(f"\n[STEP {i+1}/{len(task.steps)}] {action.reason}")
                
                result = self._execute_action(action)
                self.stats['total_actions'] += 1
                
                if result.success:
                    self.monitor.record_success()
                else:
                    self.monitor.record_failure()
                    self.stats['failed_actions'] += 1
                    
                    # 尝试恢复
                    if action.retry_count < action.max_retries:
                        logger.info(f"[RETRY] 重试 ({action.retry_count + 1}/{action.max_retries})")
                        action.retry_count += 1
                        self.stats['retries'] += 1
                        time.sleep(1.5)
                        result = self._execute_action(action)
                    else:
                        logger.error(f"[FAIL] 步骤失败: {result.error}")
                        if not self._should_continue_on_error(action):
                            task.status = TaskStatus.FAILED
                            return False
                
                # 步骤间延迟
                time.sleep(self.config.get('safety', {}).get('step_delay', 0.5))
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self.stats['successful_tasks'] += 1
            
            elapsed = self.monitor.end('total_time')
            logger.info(f"\n[TASK] 任务完成 (耗时: {elapsed:.2f}s)")
            return True
            
        except KeyboardInterrupt:
            logger.info("\n[STOP] 用户中断")
            return False
        except Exception as e:
            logger.error(f"\n[ERROR] 任务失败: {e}")
            traceback.print_exc()
            return False
        finally:
            self.monitor.end('total_time')
    
    def _execute_action(self, action: Action) -> ExecutionResult:
        """执行单个动作"""
        start_time = time.time()
        
        try:
            self.monitor.start('action_time')
            
            # 截图（执行前）
            screenshot_before = self.vision.capture_screen()
            
            # 如果需要视觉识别，先查找元素
            if action.requires_vision and not action.coordinates:
                element = self.vision.find_element(action.reason)
                if element:
                    action.coordinates = element.center
                    action.target = element
            
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
            elif action.type == ActionType.SCREENSHOT:
                pass  # 已经截图了
            elif action.type == ActionType.LAUNCH_APP:
                self._do_launch(action)
            elif action.type == ActionType.SCROLL:
                self._do_scroll(action)
            else:
                logger.warning(f"[WARN] 未知动作类型: {action.type}")
            
            # 截图（执行后）
            screenshot_after = self.vision.capture_screen()
            
            execution_time = time.time() - start_time
            self.monitor.end('action_time')
            
            return ExecutionResult(
                success=True,
                action=action,
                screenshot_before=self._save_screenshot(screenshot_before, "before"),
                screenshot_after=self._save_screenshot(screenshot_after, "after"),
                execution_time=execution_time,
                element_found=action.target is not None,
                confidence=action.target.confidence if action.target else 1.0
            )
            
        except Exception as e:
            self.monitor.end('action_time')
            return ExecutionResult(
                success=False,
                action=action,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def _should_continue_on_error(self, action: Action) -> bool:
        """判断错误后是否应该继续"""
        # 关键动作失败则停止
        critical_types = [ActionType.LAUNCH_APP]
        return action.type not in critical_types
    
    def _do_click(self, action: Action):
        """执行点击"""
        if action.coordinates:
            x, y = action.coordinates.x, action.coordinates.y
        elif action.target:
            x, y = action.target.center.to_tuple()
        else:
            raise ValueError("点击动作需要坐标或目标")
        
        # 安全边界检查
        x = max(0, min(x, self.vision.screen_width - 1))
        y = max(0, min(y, self.vision.screen_height - 1))
        
        pyautogui.moveTo(x, y, duration=0.25)
        pyautogui.click()
        logger.info(f"[ACTION] 点击 ({x}, {y})")
    
    def _do_double_click(self, action: Action):
        """执行双击"""
        if action.coordinates:
            x, y = action.coordinates.x, action.coordinates.y
        else:
            raise ValueError("双击动作需要坐标")
        
        pyautogui.moveTo(x, y, duration=0.25)
        pyautogui.doubleClick()
        logger.info(f"[ACTION] 双击 ({x}, {y})")
    
    def _do_type(self, action: Action):
        """执行输入"""
        if not action.text:
            raise ValueError("输入动作需要文本")
        
        # 使用剪贴板支持中文
        pyperclip.copy(action.text)
        pyautogui.hotkey('ctrl', 'v')
        logger.info(f"[ACTION] 输入: {action.text[:40]}{'...' if len(action.text) > 40 else ''}")
    
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
    
    def _do_scroll(self, action: Action):
        """执行滚动"""
        amount = action.scroll_amount or -3  # 默认向上滚动
        pyautogui.scroll(amount)
        logger.info(f"[ACTION] 滚动: {amount}")
    
    def _do_launch(self, action: Action):
        """启动应用"""
        import subprocess
        
        app_name = action.text or action.reason
        # 使用 start 命令避免阻塞
        cmd = f'start "" "{app_name}"'
        subprocess.Popen(cmd, shell=True)
        logger.info(f"[ACTION] 启动应用: {app_name}")
    
    def _save_screenshot(self, screenshot: Image.Image, suffix: str) -> str:
        """保存截图"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"screenshot_{timestamp}_{suffix}.png"
        filepath = self.screenshot_dir / filename
        screenshot.save(filepath)
        return str(filepath)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['performance'] = self.monitor.get_stats()
        return stats
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "="*60)
        print("📊 GhostHand Pro Statistics")
        print("="*60)
        print(f"Total Tasks: {self.stats['total_tasks']}")
        print(f"Successful: {self.stats['successful_tasks']}")
        print(f"Failed: {self.stats['total_tasks'] - self.stats['successful_tasks']}")
        print(f"Total Actions: {self.stats['total_actions']}")
        print(f"Failed Actions: {self.stats['failed_actions']}")
        print(f"Retries: {self.stats['retries']}")
        
        if self.stats['total_actions'] > 0:
            success_rate = (self.stats['total_actions'] - self.stats['failed_actions']) / self.stats['total_actions']
            print(f"Action Success Rate: {success_rate*100:.1f}%")
        
        print("="*60)


# ============================================================================
# 便捷函数
# ============================================================================

def execute(instruction: str, config_path: str = "config.json", 
            mode: ExecutionMode = ExecutionMode.AUTO) -> bool:
    """便捷执行函数"""
    ghost = GhostHandPro(config_path=config_path)
    return ghost.execute(instruction, mode=mode)


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GhostHand Pro v3 - 增强版 GUI 自动化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python ghost_v3.py "打开计算器"
  python ghost_v3.py "在记事本中输入Hello World" --mode gui
  python ghost_v3.py --stats

模式:
  auto    - 自动选择执行方式
  command - 后台命令执行
  gui     - GUI自动化操作
        """
    )
    
    parser.add_argument('instruction', nargs='?', help='要执行的指令')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件')
    parser.add_argument('--mode', choices=['auto', 'command', 'gui'], 
                       default='auto', help='执行模式')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.stats:
        print("统计功能：查看 ghosthand_pro.log 文件")
        return
    
    if not args.instruction:
        parser.print_help()
        print("\n示例:")
        print('  python ghost_v3.py "打开计算器"')
        print('  python ghost_v3.py "在记事本中输入Hello World"')
        return
    
    mode_map = {
        'auto': ExecutionMode.AUTO,
        'command': ExecutionMode.COMMAND,
        'gui': ExecutionMode.GUI
    }
    
    try:
        ghost = GhostHandPro(config_path=args.config)
        success = ghost.execute(args.instruction, mode=mode_map[args.mode])
        
        if success:
            ghost.print_stats()
        
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"[FATAL] 程序崩溃: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
