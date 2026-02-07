#!/usr/bin/env python3
"""
PluginSystem 🔌 - 插件系统

世界级的插件架构，支持第三方扩展。

Author: GodHand Team
Version: 1.0.0
"""

import os
import sys
import json
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum, auto
import inspect
import pkgutil


class PluginType(Enum):
    """插件类型"""
    ACTION = "action"           # 动作插件
    ADAPTER = "adapter"         # 适配器插件
    PARSER = "parser"           # 解析器插件
    UI = "ui"                   # UI插件
    INTEGRATION = "integration" # 集成插件
    UTILITY = "utility"         # 工具插件


class PluginState(Enum):
    """插件状态"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class PluginManifest:
    """插件清单"""
    id: str
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    config_schema: Dict = field(default_factory=dict)
    min_api_version: str = "3.0.0"

    @classmethod
    def from_dict(cls, data: Dict) -> "PluginManifest":
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            author=data.get("author", "Unknown"),
            plugin_type=PluginType(data.get("type", "utility")),
            entry_point=data["entry_point"],
            dependencies=data.get("dependencies", []),
            permissions=data.get("permissions", []),
            config_schema=data.get("config_schema", {}),
            min_api_version=data.get("min_api_version", "3.0.0")
        )


@dataclass
class PluginContext:
    """插件上下文"""
    plugin_id: str
    config: Dict[str, Any]
    data_dir: Path
    logger: Any
    api: "PluginAPI"


class PluginInterface(ABC):
    """
    插件接口基类

    所有插件必须继承此类
    """

    manifest: PluginManifest
    context: Optional[PluginContext] = None
    state: PluginState = PluginState.UNLOADED

    @abstractmethod
    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        pass

    @abstractmethod
    def shutdown(self):
        """关闭插件"""
        pass

    def get_config(self, key: str, default=None):
        """获取配置"""
        if self.context:
            return self.context.config.get(key, default)
        return default

    def log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.context:
            getattr(self.context.logger, level, print)(f"[{self.manifest.id}] {message}")


class PluginAPI:
    """
    插件API

    提供给插件调用的核心功能
    """

    def __init__(self, core_instance):
        self.core = core_instance
        self._hooks: Dict[str, List[Callable]] = {}
        self._actions: Dict[str, Callable] = {}

    # ========================================================================
    # 核心功能调用
    # ========================================================================

    def execute_command(self, command: str, mode: str = "auto") -> Dict:
        """执行命令"""
        return self.core.process(command, mode)

    def take_screenshot(self):
        """截取屏幕"""
        return self.core.take_screenshot()

    def detect_elements(self, screenshot=None):
        """检测元素"""
        if screenshot is None:
            screenshot = self.take_screenshot()
        return self.core.visual_engine.detect_elements(screenshot)

    def click(self, x: int, y: int):
        """点击"""
        import pyautogui
        pyautogui.click(x, y)

    def type_text(self, text: str):
        """输入文本"""
        import pyautogui
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')

    def press_key(self, key: str):
        """按键"""
        import pyautogui
        pyautogui.press(key)

    # ========================================================================
    # Hook系统
    # ========================================================================

    def register_hook(self, event: str, callback: Callable):
        """注册钩子"""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: Callable):
        """注销钩子"""
        if event in self._hooks and callback in self._hooks[event]:
            self._hooks[event].remove(callback)

    def trigger_hook(self, event: str, *args, **kwargs):
        """触发钩子"""
        results = []
        for callback in self._hooks.get(event, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                print(f"Hook error: {e}")
        return results

    # ========================================================================
    # 动作注册
    # ========================================================================

    def register_action(self, name: str, handler: Callable):
        """注册自定义动作"""
        self._actions[name] = handler

    def get_action(self, name: str) -> Optional[Callable]:
        """获取动作处理器"""
        return self._actions.get(name)


class PluginManager:
    """
    插件管理器

    管理插件的生命周期
    """

    def __init__(self, plugins_dir: str = "./plugins", core=None):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        self.core = core
        self.api = PluginAPI(core) if core else None

        # 插件存储
        self.plugins: Dict[str, PluginInterface] = {}
        self.manifests: Dict[str, PluginManifest] = {}
        self.states: Dict[str, PluginState] = {}
        self.configs: Dict[str, Dict] = {}

        # 内置插件
        self.builtin_plugins: Dict[str, Type[PluginInterface]] = {}

        print(f"[PluginManager] 初始化完成，插件目录: {self.plugins_dir}")

    # ========================================================================
    # 插件发现
    # ========================================================================

    def discover_plugins(self) -> List[PluginManifest]:
        """发现所有可用插件"""
        manifests = []

        # 扫描插件目录
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                manifest_file = item / "manifest.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        manifest = PluginManifest.from_dict(data)
                        manifest._path = item  # 保存路径
                        manifests.append(manifest)
                    except Exception as e:
                        print(f"[Warn] 加载插件清单失败 {item}: {e}")

        return manifests

    # ========================================================================
    # 插件加载
    # ========================================================================

    def load_plugin(self, manifest: PluginManifest) -> bool:
        """加载插件"""
        plugin_id = manifest.id

        if plugin_id in self.plugins:
            print(f"[PluginManager] 插件已加载: {plugin_id}")
            return True

        self.states[plugin_id] = PluginState.LOADING

        try:
            # 检查依赖
            if not self._check_dependencies(manifest):
                self.states[plugin_id] = PluginState.ERROR
                return False

            # 加载插件模块
            plugin_path = getattr(manifest, '_path', None) or self.plugins_dir / plugin_id
            entry_file = plugin_path / manifest.entry_point

            if not entry_file.exists():
                raise FileNotFoundError(f"入口文件不存在: {entry_file}")

            # 动态导入
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}",
                entry_file
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"plugin_{plugin_id}"] = module
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, PluginInterface) and
                    obj is not PluginInterface):
                    plugin_class = obj
                    break

            if not plugin_class:
                raise ValueError("未找到插件类")

            # 实例化
            plugin = plugin_class()
            plugin.manifest = manifest

            self.plugins[plugin_id] = plugin
            self.manifests[plugin_id] = manifest
            self.states[plugin_id] = PluginState.LOADED

            print(f"[PluginManager] 插件加载成功: {plugin_id}")
            return True

        except Exception as e:
            self.states[plugin_id] = PluginState.ERROR
            print(f"[PluginManager] 插件加载失败 {plugin_id}: {e}")
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.plugins:
            return False

        # 先禁用
        self.disable_plugin(plugin_id)

        # 移除
        del self.plugins[plugin_id]
        del self.manifests[plugin_id]
        del self.states[plugin_id]

        print(f"[PluginManager] 插件已卸载: {plugin_id}")
        return True

    # ========================================================================
    # 插件启用/禁用
    # ========================================================================

    def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        # 创建上下文
        data_dir = self.plugins_dir / plugin_id / "data"
        data_dir.mkdir(exist_ok=True)

        context = PluginContext(
            plugin_id=plugin_id,
            config=self.configs.get(plugin_id, {}),
            data_dir=data_dir,
            logger=print,  # 简化处理
            api=self.api
        )

        try:
            if plugin.initialize(context):
                plugin.context = context
                plugin.state = PluginState.ENABLED
                self.states[plugin_id] = PluginState.ENABLED

                # 触发钩子
                if self.api:
                    self.api.trigger_hook("plugin_enabled", plugin_id)

                print(f"[PluginManager] 插件已启用: {plugin_id}")
                return True
            else:
                plugin.state = PluginState.ERROR
                self.states[plugin_id] = PluginState.ERROR
                return False

        except Exception as e:
            plugin.state = PluginState.ERROR
            self.states[plugin_id] = PluginState.ERROR
            print(f"[PluginManager] 启用插件失败 {plugin_id}: {e}")
            return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id not in self.plugins:
            return False

        plugin = self.plugins[plugin_id]

        try:
            plugin.shutdown()
            plugin.state = PluginState.DISABLED
            self.states[plugin_id] = PluginState.DISABLED

            # 触发钩子
            if self.api:
                self.api.trigger_hook("plugin_disabled", plugin_id)

            print(f"[PluginManager] 插件已禁用: {plugin_id}")
            return True

        except Exception as e:
            print(f"[PluginManager] 禁用插件失败 {plugin_id}: {e}")
            return False

    # ========================================================================
    # 批量操作
    # ========================================================================

    def load_all_plugins(self):
        """加载所有插件"""
        manifests = self.discover_plugins()
        for manifest in manifests:
            self.load_plugin(manifest)

    def enable_all_plugins(self):
        """启用所有已加载的插件"""
        for plugin_id in list(self.plugins.keys()):
            if self.states.get(plugin_id) == PluginState.LOADED:
                self.enable_plugin(plugin_id)

    def get_enabled_plugins(self) -> List[str]:
        """获取所有已启用的插件"""
        return [
            pid for pid, state in self.states.items()
            if state == PluginState.ENABLED
        ]

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _check_dependencies(self, manifest: PluginManifest) -> bool:
        """检查依赖是否满足"""
        for dep in manifest.dependencies:
            if dep not in self.plugins:
                print(f"[PluginManager] 缺少依赖: {dep}")
                return False
        return True

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict]:
        """获取插件信息"""
        if plugin_id not in self.manifests:
            return None

        manifest = self.manifests[plugin_id]
        return {
            "id": manifest.id,
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "author": manifest.author,
            "type": manifest.plugin_type.value,
            "state": self.states.get(plugin_id, PluginState.UNLOADED).value
        }

    def list_plugins(self) -> List[Dict]:
        """列出所有插件"""
        return [
            self.get_plugin_info(pid)
            for pid in self.manifests.keys()
        ]


# 便捷函数
def get_plugin_manager(plugins_dir: str = "./plugins", core=None) -> PluginManager:
    """获取插件管理器单例"""
    if not hasattr(get_plugin_manager, "_instance"):
        get_plugin_manager._instance = PluginManager(plugins_dir, core)
    return get_plugin_manager._instance


if __name__ == "__main__":
    # 测试
    pm = PluginManager()

    # 发现插件
    manifests = pm.discover_plugins()
    print(f"发现 {len(manifests)} 个插件")

    for m in manifests:
        print(f"  - {m.name} ({m.id}) v{m.version}")
