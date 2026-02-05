#!/usr/bin/env python3
"""
GhostHand Agent - 自主智能体
实时观察 -> 思考 -> 行动 -> 验证 的完整循环
"""

import sys
sys.path.insert(0, '.')

import os
import json
import time
import base64
from io import BytesIO
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import pyautogui
import pyperclip

# 尝试导入组件
from ghost_v2 import LLMClient, VisionEngine, Action, ActionType, Element


class GhostAgent:
    """
    GhostHand Agent - 真正的自主智能体
    
    特点:
    1. 实时观察屏幕
    2. 自主决策下一步
    3. 基于结果调整策略
    4. 支持复杂多步骤任务
    """
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.llm = LLMClient(self.config)
        self.vision = VisionEngine()
        
        # 状态
        self.step_count = 0
        self.max_steps = self.config.get('safety', {}).get('max_steps', 30)
        self.history: List[Dict] = []
        
        # 安全
        pyautogui.FAILSAFE = True
        
        # 截图保存
        self.save_dir = os.path.join(os.getcwd(), "agent_screenshots")
        os.makedirs(self.save_dir, exist_ok=True)
        
        print("[Agent] GhostHand Agent 初始化完成")
        print(f"[Agent] 最大步数: {self.max_steps}")
        print(f"[Agent] 安全模式: {'开启' if pyautogui.FAILSAFE else '关闭'}")
    
    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        default = {
            'provider': 'google',
            'google': {'api_key': os.getenv('GOOGLE_API_KEY', ''), 'model': 'gemini-2.0-flash'},
            'safety': {'max_steps': 30, 'step_delay': 0.5}
        }
        
        if os.path.exists(path):
            with open(path, 'r') as f:
                default.update(json.load(f))
        return default
    
    def run(self, goal: str) -> bool:
        """
        执行目标
        
        Args:
            goal: 用户的任务目标
        """
        print(f"\n[Goal] {goal}")
        print("=" * 60)
        
        self.step_count = 0
        
        try:
            while self.step_count < self.max_steps:
                self.step_count += 1
                print(f"\n[Step {self.step_count}/{self.max_steps}]")
                
                # 1. 观察
                screenshot = self._observe()
                
                # 2. 思考
                action = self._think(screenshot, goal)
                
                if action is None:
                    print("[Agent] 无法确定下一步，任务中止")
                    return False
                
                # 检查是否完成
                if action.get('action') == 'done':
                    print(f"[Agent] 任务完成: {action.get('reasoning', '')}")
                    return True
                
                if action.get('action') == 'fail':
                    print(f"[Agent] 无法完成任务: {action.get('reasoning', '')}")
                    return False
                
                # 3. 执行
                success = self._act(action)
                
                # 4. 记录
                self._record(action, success)
                
                # 5. 等待 UI 稳定
                time.sleep(self.config.get('safety', {}).get('step_delay', 0.5))
                
            print("[Agent] 达到最大步数限制")
            return False
            
        except pyautogui.FailSafeException:
            print("[Agent] 安全触发：任务中止")
            return False
        except Exception as e:
            print(f"[Agent] 错误: {e}")
            return False
    
    def _observe(self) -> Image.Image:
        """观察屏幕"""
        screenshot = pyautogui.screenshot()
        
        # 添加辅助信息（网格、坐标等）
        screenshot = self._add_overlay(screenshot)
        
        # 保存截图用于调试
        timestamp = datetime.now().strftime("%H%M%S")
        screenshot.save(os.path.join(self.save_dir, f"step_{self.step_count:02d}_{timestamp}.png"))
        
        return screenshot
    
    def _add_overlay(self, screenshot: Image.Image) -> Image.Image:
        """添加辅助覆盖层"""
        draw = ImageDraw.Draw(screenshot)
        width, height = screenshot.size
        
        # 绘制网格线（每100像素）
        grid_size = 100
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill='red', width=1)
            draw.text((x+2, 2), str(x), fill='red')
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill='red', width=1)
            draw.text((2, y+2), str(y), fill='red')
        
        # 标记屏幕中心
        cx, cy = width // 2, height // 2
        draw.line([(cx-20, cy), (cx+20, cy)], fill='blue', width=2)
        draw.line([(cx, cy-20), (cx, cy+20)], fill='blue', width=2)
        
        return screenshot
    
    def _think(self, screenshot: Image.Image, goal: str) -> Optional[Dict]:
        """
        思考下一步行动
        
        使用多模态 LLM 分析截图并决策
        """
        # 构建上下文
        context = self._build_context()
        
        # 构建提示词
        prompt = f"""你是一个 GUI 自动化智能体。观察当前屏幕截图，决定下一步行动以完成用户目标。

用户目标: {goal}

当前状态: 
- 步数: {self.step_count}/{self.max_steps}
{context}

可用行动:
1. click - 点击指定坐标 [x, y]
2. type - 输入文本
3. press - 按单个按键 (enter, tab, esc 等)
4. hotkey - 按组合键 (ctrl+c, ctrl+v 等)
5. scroll - 滚动 (正值向上，负值向下)
6. wait - 等待几秒
7. done - 任务已完成
8. fail - 无法完成任务

决策规则:
- 优先使用搜索/开始菜单打开应用
- 点击前确保坐标合理 (在屏幕范围内)
- 输入文本前确保输入框有焦点
- 如果找不到元素，尝试滚动或等待
- 如果多次尝试失败，报告 fail

输出严格的 JSON 格式:
{{
    "action": "click|type|press|hotkey|scroll|wait|done|fail",
    "coordinates": [x, y],
    "text": "要输入的文本",
    "key": "单个按键",
    "keys": ["ctrl", "c"],
    "scroll_amount": 3,
    "wait_seconds": 1.0,
    "reasoning": "为什么选择这个行动"
}}

只输出 JSON，不要其他内容。"""

        try:
            # 调用 LLM
            response = self.llm.generate(prompt, screenshot)
            
            # 解析响应
            action = self._parse_response(response)
            
            print(f"[Think] {action.get('reasoning', 'No reasoning')}")
            print(f"[Plan] 行动: {action.get('action')}")
            
            return action
            
        except Exception as e:
            print(f"[Error] 思考失败: {e}")
            return None
    
    def _build_context(self) -> str:
        """构建上下文"""
        if not self.history:
            return "- 无历史操作"
        
        # 最近 3 步
        recent = self.history[-3:]
        lines = ["- 最近操作:"]
        for h in recent:
            status = "成功" if h['success'] else "失败"
            lines.append(f"  {h['action']} ({status})")
        
        return "\n".join(lines)
    
    def _parse_response(self, text: str) -> Dict:
        """解析 LLM 响应"""
        # 清理 markdown
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
    
    def _act(self, action: Dict) -> bool:
        """执行动作"""
        action_type = action.get('action', '')
        
        try:
            if action_type == 'click':
                coords = action.get('coordinates', [0, 0])
                x, y = int(coords[0]), int(coords[1])
                
                # 边界检查
                screen_w, screen_h = pyautogui.size()
                x = max(0, min(x, screen_w))
                y = max(0, min(y, screen_h))
                
                pyautogui.moveTo(x, y, duration=0.3)
                pyautogui.click()
                print(f"[Act] 点击 ({x}, {y})")
                
            elif action_type == 'type':
                text = action.get('text', '')
                if text:
                    pyperclip.copy(text)
                    pyautogui.hotkey('ctrl', 'v')
                    print(f"[Act] 输入: {text[:30]}{'...' if len(text) > 30 else ''}")
                    
            elif action_type == 'press':
                key = action.get('key', '')
                if key:
                    pyautogui.press(key)
                    print(f"[Act] 按键: {key}")
                    
            elif action_type == 'hotkey':
                keys = action.get('keys', [])
                if keys:
                    pyautogui.hotkey(*keys)
                    print(f"[Act] 热键: {'+'.join(keys)}")
                    
            elif action_type == 'scroll':
                amount = action.get('scroll_amount', 3)
                pyautogui.scroll(int(amount) * 100)
                print(f"[Act] 滚动: {amount}")
                
            elif action_type == 'wait':
                seconds = action.get('wait_seconds', 1.0)
                print(f"[Act] 等待 {seconds} 秒...")
                time.sleep(float(seconds))
                
            elif action_type in ['done', 'fail']:
                # 这两个是终止信号，不需要执行
                pass
                
            else:
                print(f"[Act] 未知动作: {action_type}")
                return False
                
            return True
            
        except Exception as e:
            print(f"[Error] 执行失败: {e}")
            return False
    
    def _record(self, action: Dict, success: bool):
        """记录历史"""
        self.history.append({
            'step': self.step_count,
            'action': action.get('action'),
            'reasoning': action.get('reasoning'),
            'success': success,
            'timestamp': datetime.now().isoformat()
        })


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GhostHand Agent - 自主智能体')
    parser.add_argument('goal', nargs='?', help='任务目标')
    parser.add_argument('--max-steps', '-m', type=int, default=30, help='最大步数')
    
    args = parser.parse_args()
    
    if not args.goal:
        print("GhostHand Agent - 自主 GUI 智能体")
        print("\n用法示例:")
        print('  python ghost_agent.py "打开计算器并计算 123+456"')
        print('  python ghost_agent.py "打开 Chrome 搜索 Python 教程"')
        print('  python ghost_agent.py "在桌面创建名为 Test 的文件夹"')
        print('\n提示:')
        print('- 把鼠标移到屏幕左上角可紧急中止')
        print('- 每步 AI 思考需要 5-10 秒，请耐心等待')
        exit(1)
    
    # 创建并运行 Agent
    agent = GhostAgent()
    agent.max_steps = args.max_steps
    
    print("\n" + "=" * 60)
    print("开始执行任务...")
    print("=" * 60)
    
    success = agent.run(args.goal)
    
    print("\n" + "=" * 60)
    if success:
        print("[RESULT] 任务成功完成！")
    else:
        print("[RESULT] 任务失败或中止")
    print("=" * 60)


if __name__ == "__main__":
    main()
