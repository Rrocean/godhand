#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand - Vision-based Universal GUI Agent
基于视觉的通用 GUI 自动化代理 (上帝之手)

Author: Clawd
Version: 1.0.0
"""

# Google GenAI - 新版 SDK (google.generativeai 已弃用)
try:
    from google import genai
    from google.genai import types
    GOOGLE_SDK_NEW = True
except ImportError:
    import google.generativeai as genai
    GOOGLE_SDK_NEW = False
    print("Warning: 使用旧版 google-generativeai，建议升级到 google-genai")
import openai
import pyautogui
import pyperclip
import time
import json
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志 - 兼容 Windows 控制台编码
import io

# 检测 Windows 控制台编码
if sys.platform == 'win32':
    # 设置 stdout 为 UTF-8 模式
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ghosthand.log', encoding='utf-8', errors='replace')
    ]
)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """支持的操作类型"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE = "type"
    PRESS = "press"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    WAIT = "wait"
    DONE = "done"
    FAIL = "fail"


@dataclass
class ActionPlan:
    """动作计划数据结构"""
    action: str
    coordinates: Optional[list] = None
    end_coordinates: Optional[list] = None  # 用于拖拽
    text: Optional[str] = None
    key: Optional[str] = None
    keys: Optional[list] = None  # 用于热键组合
    scroll_amount: Optional[int] = None
    wait_seconds: Optional[float] = None
    reasoning: str = ""


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "provider": "google",  # "google" 或 "openai"
        "google": {
            "api_key": "",
            "model": "gemini-1.5-pro-latest"
        },
        "openai": {
            "api_key": "",
            "model": "gpt-4o",
            "base_url": "https://api.openai.com/v1"
        },
        "safety": {
            "enabled": True,
            "max_steps": 20,
            "step_delay": 1.0,
            "click_delay": 0.5
        },
        "screenshot": {
            "save_dir": "./screenshots",
            "show_grid": False,
            "grid_size": 100
        },
        "logging": {
            "level": "INFO",
            "save_thoughts": True
        }
    }
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> dict:
        """加载配置，优先从文件，其次环境变量"""
        config = self.DEFAULT_CONFIG.copy()
        
        # 从文件加载
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._deep_update(config, file_config)
                logger.info(f"[OK] 已加载配置文件: {self.config_path}")
            except Exception as e:
                logger.warning(f"[WARN] 配置文件加载失败: {e}")
        
        # 从环境变量加载（覆盖配置文件）
        self._load_from_env(config)
        
        return config
    
    def _load_from_env(self, config: dict):
        """从环境变量加载配置"""
        # Google
        if os.getenv("GOOGLE_API_KEY"):
            config["google"]["api_key"] = os.getenv("GOOGLE_API_KEY")
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            config["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("OPENAI_BASE_URL"):
            config["openai"]["base_url"] = os.getenv("OPENAI_BASE_URL")
        
        # 提供商选择
        if os.getenv("GH_PROVIDER"):
            config["provider"] = os.getenv("GH_PROVIDER")
    
    def _deep_update(self, base: dict, update: dict):
        """深度更新字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None):
        """获取配置项，支持点号路径如 'safety.max_steps'"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def save(self, path: Optional[str] = None):
        """保存配置到文件"""
        save_path = path or self.config_path
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        logger.info(f"[SAVE] 配置已保存到: {save_path}")


class GodHand:
    """
    GodHand 核心类
    
    基于多模态大模型的 GUI 自动化代理
    """
    
    def __init__(self, config: Optional[Config] = None, api_key: Optional[str] = None):
        """
        初始化 GodHand
        
        Args:
            config: 配置对象，不传则使用默认配置
            api_key: 直接传入 API Key（优先级最高）
        """
        self.config = config or Config()
        self.history = []
        self.step_count = 0
        
        # 启用 PyAutoGUI 的安全机制（将鼠标移到屏幕角落会触发异常中止）
        pyautogui.FAILSAFE = self.config.get('safety.enabled', True)
        pyautogui.PAUSE = 0.1
        
        # 初始化模型
        self._init_model(api_key)
        
        # 确保截图目录存在（支持嵌套目录）
        self.screenshot_dir = Path(self.config.get('screenshot.save_dir', './screenshots'))
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("[INIT] GodHand 初始化完成")
        logger.info(f"       提供商: {self.config.get('provider')}")
        logger.info(f"       安全模式: {'ON' if pyautogui.FAILSAFE else 'OFF'}")
    
    def _init_model(self, api_key: Optional[str] = None):
        """初始化 AI 模型"""
        provider = self.config.get('provider', 'google')
        
        if provider == 'google':
            key = api_key or self.config.get('google.api_key')
            if not key:
                raise ValueError("Google API Key 未设置。请在 config.json 中配置或设置 GOOGLE_API_KEY 环境变量")
            
            if GOOGLE_SDK_NEW:
                # 新版 SDK
                self.genai_client = genai.Client(api_key=key)
                self.model_name = self.config.get('google.model')
            else:
                # 旧版 SDK
                genai.configure(api_key=key)
                self.model = genai.GenerativeModel(self.config.get('google.model'))
            self.provider = 'google'
            
        elif provider == 'openai':
            key = api_key or self.config.get('openai.api_key')
            if not key:
                raise ValueError("OpenAI API Key 未设置。请在 config.json 中配置或设置 OPENAI_API_KEY 环境变量")
            openai.api_key = key
            openai.base_url = self.config.get('openai.base_url')
            self.model = None  # OpenAI 不需要预初始化模型
            self.provider = 'openai'
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def see(self, save: bool = True, show_grid: Optional[bool] = None) -> Tuple[Image.Image, str]:
        """
        截取屏幕
        
        Args:
            save: 是否保存截图
            show_grid: 是否显示坐标网格（用于调试）
            
        Returns:
            (PIL Image, 文件路径)
        """
        # 截图
        screenshot = pyautogui.screenshot()
        
        # 可选：添加网格覆盖层（帮助模型定位）
        if show_grid or (show_grid is None and self.config.get('screenshot.show_grid')):
            screenshot = self._add_grid(screenshot)
        
        # 保存截图
        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{self.step_count:03d}.png"
            filepath = self.screenshot_dir / filename
            screenshot.save(filepath)
            logger.debug(f"[SCREEN] 截图已保存: {filepath}")
        else:
            filepath = "current_view.png"
            screenshot.save(filepath)
        
        return screenshot, str(filepath)
    
    def _add_grid(self, image: Image.Image) -> Image.Image:
        """在截图上添加坐标网格"""
        draw = ImageDraw.Draw(image)
        width, height = image.size
        grid_size = self.config.get('screenshot.grid_size', 100)
        
        # 画网格线
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill='red', width=1)
            draw.text((x + 2, 2), str(x), fill='red')
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill='red', width=1)
            draw.text((2, y + 2), str(y), fill='red')
        
        return image
    
    def think(self, image_path: str, instruction: str, context: Optional[str] = None) -> ActionPlan:
        """
        分析屏幕并决策下一步动作
        
        Args:
            image_path: 截图路径
            instruction: 用户指令
            context: 额外的上下文信息
            
        Returns:
            ActionPlan 动作计划
        """
        img = Image.open(image_path)
        width, height = img.size
        
        # 构建提示词
        system_prompt = f"""You are GodHand, a GUI Automation Agent. Your task is to analyze the screenshot and determine the next action to fulfill the user's instruction.

## Screen Information
- Screen size: {width}x{height}
- Coordinate system: (0,0) is top-left, ({width},{height}) is bottom-right

## Available Actions
1. "click" - Click at specific coordinates
2. "double_click" - Double click at coordinates
3. "right_click" - Right click at coordinates
4. "drag" - Drag from one point to another
5. "type" - Type text (uses clipboard for Chinese support)
6. "press" - Press a single key (enter, esc, tab, etc.)
7. "hotkey" - Press key combination like ctrl+c, ctrl+v
8. "scroll" - Scroll up (positive) or down (negative)
9. "wait" - Wait for UI to load or stabilize
10. "done" - Task completed successfully
11. "fail" - Unable to complete the task

## Output Format
Return ONLY valid JSON in this exact format:
{{
    "action": "click",
    "coordinates": [x, y],
    "end_coordinates": [x2, y2],
    "text": "text to type",
    "key": "single_key",
    "keys": ["ctrl", "c"],
    "scroll_amount": 3,
    "wait_seconds": 2.0,
    "reasoning": "Detailed explanation of why this action was chosen"
}}

## Rules
- For "click", "double_click", "right_click": provide "coordinates" [x, y]
- For "drag": provide "coordinates" [x1, y1] and "end_coordinates" [x2, y2]
- For "type": provide "text" (supports Chinese)
- For "press": provide "key" (enter, tab, esc, space, etc.)
- For "hotkey": provide "keys" array like ["ctrl", "c"]
- For "scroll": provide "scroll_amount" (positive=up, negative=down)
- For "wait": provide "wait_seconds"
- Coordinates must be precise - aim for the center of clickable elements
- If an element is not found, try "scroll" or "wait"
- Use "done" only when the task is fully complete
- Use "fail" if you've tried multiple approaches and cannot proceed"""

        user_prompt = f"User Instruction: {instruction}"
        if context:
            user_prompt += f"\n\nContext: {context}"
        
        # 调用模型
        if self.provider == 'google':
            if GOOGLE_SDK_NEW:
                # 新版 SDK
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=[system_prompt + "\n\n" + user_prompt, img]
                )
                raw_text = response.text
            else:
                # 旧版 SDK
                response = self.model.generate_content([system_prompt, user_prompt, img])
                raw_text = response.text
        else:  # openai
            with open(image_path, 'rb') as img_file:
                import base64
                base64_image = base64.b64encode(img_file.read()).decode('utf-8')
            
            client = openai.OpenAI(
                api_key=self.config.get('openai.api_key'),
                base_url=self.config.get('openai.base_url')
            )
            response = client.chat.completions.create(
                model=self.config.get('openai.model'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=4096
            )
            raw_text = response.choices[0].message.content
        
        # 解析 JSON
        return self._parse_response(raw_text)
    
    def _parse_response(self, text: str) -> ActionPlan:
        """解析模型返回的 JSON"""
        try:
            # 清理响应文本
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            
            # 保存思考过程
            if self.config.get('logging.save_thoughts'):
                self.history.append({
                    'timestamp': datetime.now().isoformat(),
                    'thought': data
                })
            
            return ActionPlan(**{k: v for k, v in data.items() if k in ActionPlan.__dataclass_fields__})
            
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] JSON 解析失败: {e}")
            logger.debug(f"[RAW] 原始响应: {text}")
            return ActionPlan(action="fail", reasoning=f"Failed to parse LLM response: {text[:200]}")
        except Exception as e:
            logger.error(f"[ERROR] 解析错误: {e}")
            return ActionPlan(action="fail", reasoning=str(e))
    
    def act(self, plan: ActionPlan) -> bool:
        """
        执行动作计划
        
        Args:
            plan: ActionPlan 对象
            
        Returns:
            bool: True 表示任务结束（done/fail），False 表示继续
        """
        action = plan.action
        reasoning = plan.reasoning or "No reasoning provided"
        
        logger.info(f"[THINK] {reasoning}")
        logger.info(f"[ACTION] 执行动作: {action}")
        
        try:
            if action == ActionType.CLICK.value:
                x, y = plan.coordinates
                self._validate_coordinates(x, y)
                pyautogui.moveTo(x, y, duration=self.config.get('safety.click_delay', 0.5))
                pyautogui.click()
                
            elif action == ActionType.DOUBLE_CLICK.value:
                x, y = plan.coordinates
                self._validate_coordinates(x, y)
                pyautogui.moveTo(x, y, duration=self.config.get('safety.click_delay', 0.5))
                pyautogui.doubleClick()
                
            elif action == ActionType.RIGHT_CLICK.value:
                x, y = plan.coordinates
                self._validate_coordinates(x, y)
                pyautogui.moveTo(x, y, duration=self.config.get('safety.click_delay', 0.5))
                pyautogui.rightClick()
                
            elif action == ActionType.DRAG.value:
                x1, y1 = plan.coordinates
                x2, y2 = plan.end_coordinates
                self._validate_coordinates(x1, y1)
                self._validate_coordinates(x2, y2)
                pyautogui.moveTo(x1, y1, duration=0.5)
                pyautogui.dragTo(x2, y2, duration=0.5)
                
            elif action == ActionType.TYPE.value:
                text = plan.text
                if text:
                    # 使用剪贴板支持中文输入
                    pyperclip.copy(text)
                    pyautogui.hotkey('ctrl', 'v')
                    logger.info(f"       输入文本: {text[:50]}{'...' if len(text) > 50 else ''}")
                    
            elif action == ActionType.PRESS.value:
                key = plan.key
                if key:
                    pyautogui.press(key)
                    logger.info(f"       按键: {key}")
                    
            elif action == ActionType.HOTKEY.value:
                keys = plan.keys
                if keys and len(keys) > 0:
                    pyautogui.hotkey(*keys)
                    logger.info(f"       热键: {'+'.join(keys)}")
                    
            elif action == ActionType.SCROLL.value:
                amount = plan.scroll_amount or 3
                pyautogui.scroll(amount * 100)  # PyAutoGUI 的 scroll 单位不同
                logger.info(f"       滚动: {amount}")
                
            elif action == ActionType.WAIT.value:
                seconds = plan.wait_seconds or 1.0
                logger.info(f"       等待 {seconds} 秒...")
                time.sleep(seconds)
                
            elif action == ActionType.DONE.value:
                logger.info("[DONE] 任务完成！")
                return True
                
            elif action == ActionType.FAIL.value:
                logger.error(f"[FAIL] 任务失败: {reasoning}")
                return True
                
            else:
                logger.warning(f"[WARN] 未知动作: {action}")
                
        except Exception as e:
            logger.error(f"[ERROR] 执行动作时出错: {e}")
            
        # 步骤间延迟
        time.sleep(self.config.get('safety.step_delay', 1.0))
        return False
    
    def _validate_coordinates(self, x: int, y: int):
        """验证坐标是否有效"""
        if x < 0 or y < 0:
            raise ValueError(f"坐标不能为负数: ({x}, {y})")
        screen_width, screen_height = pyautogui.size()
        if x > screen_width or y > screen_height:
            logger.warning(f"[WARN] 坐标 ({x}, {y}) 超出屏幕范围 ({screen_width}, {screen_height})")
    
    def run(self, instruction: str, max_steps: Optional[int] = None) -> bool:
        """
        运行主循环
        
        Args:
            instruction: 用户指令
            max_steps: 最大步骤数，默认使用配置
            
        Returns:
            bool: 任务是否成功完成
        """
        logger.info("=" * 60)
        logger.info(f"[TASK] {instruction}")
        logger.info("=" * 60)
        
        max_steps = max_steps or self.config.get('safety.max_steps', 20)
        self.step_count = 0
        success = False
        
        try:
            while self.step_count < max_steps:
                self.step_count += 1
                logger.info(f"\n--- 步骤 {self.step_count}/{max_steps} ---")
                
                # 1. 看
                img, path = self.see(save=True)
                
                # 2. 想
                context = f"Step {self.step_count}/{max_steps}. Previous actions: " + \
                         "; ".join([h['thought'].get('action', 'unknown') for h in self.history[-5:]])
                plan = self.think(path, instruction, context)
                
                # 3. 执行
                finished = self.act(plan)
                
                if finished:
                    success = plan.action == ActionType.DONE.value
                    break
                    
        except pyautogui.FailSafeException:
            logger.warning("[STOP] 安全机制触发：鼠标移到角落，任务中止")
        except KeyboardInterrupt:
            logger.warning("[STOP] 用户中断 (Ctrl+C)")
        except Exception as e:
            logger.error(f"[ERROR] 运行时错误: {e}", exc_info=True)
        
        # 保存历史记录
        if self.config.get('logging.save_thoughts'):
            self._save_history()
        
        logger.info("=" * 60)
        logger.info(f"[END] 任务结束: {'SUCCESS' if success else 'FAILED'}")
        logger.info("=" * 60)
        
        return success
    
    def _save_history(self):
        """保存执行历史"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        history_file = self.screenshot_dir / f"history_{timestamp}.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
        logger.info(f"💾 执行历史已保存: {history_file}")


def create_default_config():
    """创建默认配置文件"""
    config = Config.DEFAULT_CONFIG
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("[OK] 已创建默认配置文件: config.json")
    print("   请编辑 config.json 填入你的 API Key")


def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description='GodHand - Vision-based GUI Automation Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python god.py "打开计算器并计算 123+456"
  python god.py --config my_config.json "打开微信"
  python god.py --provider openai --api-key sk-xxx "截图并保存"
  
安全提示:
  • 将鼠标快速移到屏幕左上角可紧急中止
  • 运行前请确保没有敏感信息暴露在屏幕上
        """
    )
    
    parser.add_argument('instruction', nargs='?', help='要执行的任务指令')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--provider', '-p', choices=['google', 'openai'], help='模型提供商')
    parser.add_argument('--api-key', '-k', help='API Key')
    parser.add_argument('--max-steps', '-m', type=int, help='最大执行步骤数')
    parser.add_argument('--init', action='store_true', help='创建默认配置文件')
    parser.add_argument('--headless', action='store_true', help='无头模式（不显示截图预览）')
    
    args = parser.parse_args()
    
    # 创建默认配置
    if args.init:
        create_default_config()
        return
    
    # 检查指令
    if not args.instruction:
        parser.print_help()
        print("\n[ERROR] 错误: 请提供任务指令，或使用 --init 创建配置文件")
        sys.exit(1)
    
    try:
        # 加载配置
        config = Config(args.config)
        
        # 命令行参数覆盖配置
        if args.provider:
            config.config['provider'] = args.provider
        
        # 初始化 GodHand
        ghost = GodHand(config=config, api_key=args.api_key)
        
        # 运行任务
        success = ghost.run(args.instruction, max_steps=args.max_steps)
        sys.exit(0 if success else 1)
        
    except ValueError as e:
        print(f"\n[ERROR] 配置错误: {e}")
        print("\n提示: 运行以下命令创建配置文件:")
        print("  python god.py --init")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
