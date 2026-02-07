"""
GodHand Core - GUI Automation Engine [emoji]

[emoji] GUI [emoji]
Version: 3.0.0-universe
"""

from .ghost_v3 import GhostHandPro, ActionType, TaskStatus
from .claw_runner import CommandParser, CommandExecutor, CommandType
from .advanced_parser import AdvancedParser
from .smart_parser_v2 import SmartParser, SmartActionExecutor, Action as SmartAction
from .visual_engine import VisualEngine, UIElement, ElementType, SceneContext
from .task_planner import TaskPlanner, PlanExecutor, ExecutionPlan, Step, StepType
from .learning_system import LearningSystem, Demonstration, LearnedPattern
from .element_library import ElementLibrary, ElementTemplate, CachedElement
from .error_recovery import ErrorRecovery, ErrorType, ErrorSeverity, RecoveryResult

# [emoji] - [emoji]
try:
    from .performance_monitor import PerformanceMonitor, ExecutionMetrics
except ImportError:
    PerformanceMonitor = None
    ExecutionMetrics = None

try:
    from .platform_adapters import (
        PlatformAdapter, WindowsAdapter, MacOSAdapter, LinuxAdapter,
        get_platform_adapter, WindowInfo, ScreenInfo
    )
except ImportError:
    PlatformAdapter = WindowsAdapter = MacOSAdapter = LinuxAdapter = None
    get_platform_adapter = WindowInfo = ScreenInfo = None

try:
    from .plugin_system import PluginSystem, Plugin, PluginContext, PluginAPI
except ImportError:
    PluginSystem = Plugin = PluginContext = PluginAPI = None

try:
    from .ai_agent import AIAgent, LongTermMemory, Goal, Memory, AgentState, TaskPriority
except ImportError:
    AIAgent = LongTermMemory = Goal = Memory = AgentState = TaskPriority = None

try:
    from .voice_controller import VoiceController, VoiceCommand, VoiceState
except ImportError:
    VoiceController = VoiceCommand = VoiceState = None

try:
    from .cloud_sync import CloudSync, SyncItem, TeamMember, SharedWorkflow, SyncStatus, CollaborationRole
except ImportError:
    CloudSync = SyncItem = TeamMember = SharedWorkflow = SyncStatus = CollaborationRole = None

__version__ = "3.0.0-universe"
__all__ = [
    # GhostHand Pro
    "GhostHandPro",
    "ActionType",
    "TaskStatus",
    # Claw Runner
    "CommandParser",
    "CommandExecutor",
    "CommandType",
    # Advanced Parser / Smart Parser v2
    "AdvancedParser",
    "SmartParser",
    "SmartActionExecutor",
    # Visual Engine
    "VisualEngine",
    "UIElement",
    "ElementType",
    "SceneContext",
    # Task Planner
    "TaskPlanner",
    "PlanExecutor",
    "ExecutionPlan",
    "Step",
    "StepType",
    # Learning System
    "LearningSystem",
    "Demonstration",
    "LearnedPattern",
    # Element Library
    "ElementLibrary",
    "ElementTemplate",
    "CachedElement",
    # Error Recovery
    "ErrorRecovery",
    "ErrorType",
    "ErrorSeverity",
    "RecoveryResult",
    # Performance Monitor
    "PerformanceMonitor",
    "ExecutionMetrics",
    # Platform Adapters
    "PlatformAdapter",
    "WindowsAdapter",
    "MacOSAdapter",
    "LinuxAdapter",
    "get_platform_adapter",
    "WindowInfo",
    "ScreenInfo",
    # Plugin System
    "PluginSystem",
    "Plugin",
    "PluginContext",
    "PluginAPI",
    # AI Agent
    "AIAgent",
    "LongTermMemory",
    "Goal",
    "Memory",
    "AgentState",
    "TaskPriority",
    # Voice Controller
    "VoiceController",
    "VoiceCommand",
    "VoiceState",
    # Cloud Sync
    "CloudSync",
    "SyncItem",
    "TeamMember",
    "SharedWorkflow",
    "SyncStatus",
    "CollaborationRole",
]
