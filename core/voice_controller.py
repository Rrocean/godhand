#!/usr/bin/env python3
"""
VoiceController 🎤 - 语音控制系统

实现完全免手的语音控制自动化。
支持语音识别、语音合成、语音命令解析。

Author: GodHand Team
Version: 1.0.0
"""

import asyncio
import threading
import queue
import time
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class VoiceState(Enum):
    """语音状态"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceCommand:
    """语音命令"""
    text: str
    confidence: float
    timestamp: float
    is_wake_word: bool = False


class VoiceController:
    """
    语音控制器

    宇宙第一的语音交互能力
    """

    def __init__(self, wake_words: List[str] = None):
        self.wake_words = wake_words or ["godhand", " god hand", "神之手"]
        self.state = VoiceState.IDLE
        self.command_queue: queue.Queue = queue.Queue()

        # 回调函数
        self.on_command: Optional[Callable[[VoiceCommand], None]] = None
        self.on_wake: Optional[Callable[[], None]] = None

        # 语音识别器
        self._recognizer = None
        self._microphone = None

        # 语音合成器
        self._tts_engine = None

        # 后台监听线程
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None

        self._init_speech_recognition()
        self._init_tts()

        print("🎤 [VoiceController] 语音控制系统初始化完成")
        print(f"   唤醒词: {', '.join(self.wake_words)}")

    def _init_speech_recognition(self):
        """初始化语音识别"""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()

            # 校准环境噪音
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)

            print("✅ 语音识别引擎已加载 (Google Speech Recognition)")
        except ImportError:
            print("⚠️  speech_recognition 未安装，语音功能不可用")
            print("   安装: pip install SpeechRecognition pyaudio")

    def _init_tts(self):
        """初始化语音合成"""
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()

            # 设置语音属性
            self._tts_engine.setProperty('rate', 180)  # 语速
            self._tts_engine.setProperty('volume', 0.9)  # 音量

            # 获取可用语音
            voices = self._tts_engine.getProperty('voices')
            if voices:
                # 优先使用中文语音
                for voice in voices:
                    if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                        self._tts_engine.setProperty('voice', voice.id)
                        break

            print("✅ 语音合成引擎已加载 (pyttsx3)")
        except ImportError:
            print("⚠️  pyttsx3 未安装，语音合成功能不可用")

    def start_listening(self, continuous: bool = True):
        """开始监听语音"""
        if not self._recognizer or not self._microphone:
            print("❌ 语音识别未初始化")
            return

        self._listening = True

        if continuous:
            self._listen_thread = threading.Thread(target=self._continuous_listen, daemon=True)
            self._listen_thread.start()
            print("🎤 开始持续监听...")

    def stop_listening(self):
        """停止监听"""
        self._listening = False
        self.state = VoiceState.IDLE
        print("🛑 停止监听")

    def _continuous_listen(self):
        """持续监听循环"""
        import speech_recognition as sr

        while self._listening:
            try:
                with self._microphone as source:
                    self.state = VoiceState.LISTENING

                    # 监听音频
                    audio = self._recognizer.listen(source, timeout=5, phrase_time_limit=5)

                    self.state = VoiceState.PROCESSING

                    # 识别语音
                    text = self._recognizer.recognize_google(audio, language='zh-CN')
                    confidence = 0.9  # Google API 不提供置信度，使用默认值

                    # 检查唤醒词
                    is_wake = any(wake in text.lower() for wake in self.wake_words)

                    command = VoiceCommand(
                        text=text,
                        confidence=confidence,
                        timestamp=time.time(),
                        is_wake_word=is_wake
                    )

                    if is_wake:
                        print(f"🔔 检测到唤醒词: {text}")
                        if self.on_wake:
                            self.on_wake()
                    else:
                        print(f"🎤 识别到: {text}")

                    # 添加到队列
                    self.command_queue.put(command)

                    # 触发回调
                    if self.on_command:
                        self.on_command(command)

            except sr.WaitTimeoutError:
                pass  # 超时，继续监听
            except sr.UnknownValueError:
                pass  # 无法识别
            except sr.RequestError as e:
                print(f"❌ 语音识别服务错误: {e}")
            except Exception as e:
                print(f"❌ 监听错误: {e}")

    def listen_once(self, timeout: int = 5) -> Optional[VoiceCommand]:
        """单次监听"""
        if not self._recognizer or not self._microphone:
            return None

        import speech_recognition as sr

        try:
            with self._microphone as source:
                self.state = VoiceState.LISTENING
                print("🎤 正在聆听...")

                audio = self._recognizer.listen(source, timeout=timeout)

                self.state = VoiceState.PROCESSING
                print("🧠 正在识别...")

                text = self._recognizer.recognize_google(audio, language='zh-CN')

                command = VoiceCommand(
                    text=text,
                    confidence=0.9,
                    timestamp=time.time()
                )

                print(f"✅ 识别结果: {text}")
                return command

        except sr.WaitTimeoutError:
            print("⏱️  监听超时")
        except sr.UnknownValueError:
            print("❓ 无法识别语音")
        except Exception as e:
            print(f"❌ 错误: {e}")

        return None

    def speak(self, text: str, block: bool = False):
        """语音合成播报"""
        if not self._tts_engine:
            print(f"🔊 [TTS] {text}")
            return

        self.state = VoiceState.SPEAKING

        print(f"🔊 {text}")

        self._tts_engine.say(text)

        if block:
            self._tts_engine.runAndWait()
        else:
            # 非阻塞模式在新线程中运行
            threading.Thread(target=self._tts_engine.runAndWait, daemon=True).start()

    def process_voice_command(self, text: str) -> Dict[str, Any]:
        """处理语音命令"""
        # 移除唤醒词
        clean_text = text.lower()
        for wake in self.wake_words:
            clean_text = clean_text.replace(wake.lower(), "")

        clean_text = clean_text.strip()

        if not clean_text:
            return {"action": "none", "text": ""}

        # 简单的命令映射
        command_map = {
            "打开": "open",
            "点击": "click",
            "输入": "type",
            "截图": "screenshot",
            "搜索": "search",
            "关闭": "close",
            "保存": "save",
        }

        action = "unknown"
        for cn, en in command_map.items():
            if cn in clean_text:
                action = en
                break

        return {
            "action": action,
            "text": clean_text,
            "original": text
        }

    def interactive_mode(self):
        """交互式语音模式"""
        print("\n" + "="*60)
        print("🎤 交互式语音模式")
        print("="*60)
        print("说出命令，或说'退出'结束\n")

        self.speak("语音模式已启动", block=True)

        while True:
            command = self.listen_once(timeout=10)

            if not command:
                self.speak("没有听到声音，请重试")
                continue

            if "退出" in command.text or "结束" in command.text:
                self.speak("再见")
                break

            # 处理命令
            result = self.process_voice_command(command.text)

            if result["action"] != "none":
                self.speak(f"执行: {result['text']}")
                # 这里可以调用实际的执行逻辑
            else:
                self.speak("请再说一遍")

        print("\n退出语音模式")


# 便捷函数
def quick_speak(text: str):
    """快速语音播报"""
    vc = VoiceController()
    vc.speak(text, block=True)


def voice_command_loop(callback: Callable[[str], None]):
    """语音命令循环"""
    vc = VoiceController()
    vc.on_command = lambda cmd: callback(cmd.text)
    vc.start_listening()

    print("按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        vc.stop_listening()


if __name__ == "__main__":
    # 测试
    vc = VoiceController()

    # 测试语音合成
    vc.speak("神之手语音控制系统已启动")

    # 进入交互模式
    vc.interactive_mode()
