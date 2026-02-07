#!/usr/bin/env python3
"""
CloudSync ☁️ - 云端同步与协作系统

实现多设备同步、团队协作、远程执行能力。
支持实时数据同步、冲突解决、离线模式。

Author: GodHand Team
Version: 1.0.0
"""

import json
import time
import asyncio
import hashlib
import threading
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
import sqlite3
import queue


class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"
    OFFLINE = "offline"


class CollaborationRole(Enum):
    """协作角色"""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass
class SyncItem:
    """同步项目"""
    id: str
    type: str  # "config", "workflow", "element", "history"
    data: Dict[str, Any]
    checksum: str
    modified_at: float
    device_id: str
    version: int = 1
    status: SyncStatus = SyncStatus.PENDING
    conflict_data: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "checksum": self.checksum,
            "modified_at": self.modified_at,
            "device_id": self.device_id,
            "version": self.version,
            "status": self.status.value
        }

    @staticmethod
    def calculate_checksum(data: Dict) -> str:
        """计算数据校验和"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class TeamMember:
    """团队成员"""
    user_id: str
    name: str
    email: str
    role: CollaborationRole
    device_ids: List[str] = field(default_factory=list)
    joined_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    is_online: bool = False

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "device_ids": self.device_ids,
            "joined_at": self.joined_at,
            "last_active": self.last_active,
            "is_online": self.is_online
        }


@dataclass
class SharedWorkflow:
    """共享工作流"""
    id: str
    name: str
    description: str
    created_by: str
    steps: List[Dict]
    shared_with: List[str] = field(default_factory=list)
    permissions: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    execution_count: int = 0
    rating: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "steps": self.steps,
            "shared_with": self.shared_with,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "execution_count": self.execution_count,
            "rating": self.rating
        }


class CloudSync:
    """
    云端同步系统

    宇宙第一的多设备同步与协作能力
    """

    def __init__(self, device_id: Optional[str] = None, db_path: str = "cloud_sync.db"):
        self.device_id = device_id or self._generate_device_id()
        self.db_path = db_path
        self.sync_queue: queue.Queue = queue.Queue()
        self.pending_items: Dict[str, SyncItem] = {}
        self.sync_status = SyncStatus.OFFLINE
        self.is_online = False

        # 回调函数
        self.on_sync_complete: Optional[Callable[[str], None]] = None
        self.on_conflict: Optional[Callable[[SyncItem, SyncItem], SyncItem]] = None
        self.on_team_member_join: Optional[Callable[[TeamMember], None]] = None

        # 团队协作
        self.team_members: Dict[str, TeamMember] = {}
        self.shared_workflows: Dict[str, SharedWorkflow] = {}
        self.current_user: Optional[TeamMember] = None

        # 同步线程
        self._sync_thread: Optional[threading.Thread] = None
        self._sync_running = False
        self._sync_interval = 30  # 同步间隔（秒）

        # 初始化数据库
        self._init_database()

        print(f"☁️ [CloudSync] 云端同步系统初始化完成")
        print(f"   设备ID: {self.device_id}")

    def _generate_device_id(self) -> str:
        """生成设备ID"""
        import uuid
        return hashlib.md5(uuid.getnode().to_bytes(6, 'big')).hexdigest()[:12]

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 同步项目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_items (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                checksum TEXT NOT NULL,
                modified_at REAL NOT NULL,
                device_id TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending'
            )
        """)

        # 团队成员表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                device_ids TEXT,
                joined_at REAL,
                last_active REAL,
                is_online INTEGER DEFAULT 0
            )
        """)

        # 共享工作流表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shared_workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT NOT NULL,
                steps TEXT NOT NULL,
                shared_with TEXT,
                permissions TEXT,
                created_at REAL,
                updated_at REAL,
                execution_count INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0
            )
        """)

        # 同步历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                action TEXT,
                timestamp REAL,
                device_id TEXT,
                details TEXT
            )
        """)

        conn.commit()
        conn.close()

    def register_device(self, user_info: Dict[str, str]) -> TeamMember:
        """注册设备到用户"""
        user_id = user_info.get("user_id", self._generate_device_id())

        member = TeamMember(
            user_id=user_id,
            name=user_info.get("name", "Unknown"),
            email=user_info.get("email", ""),
            role=CollaborationRole(user_info.get("role", "editor")),
            device_ids=[self.device_id],
            last_active=time.time(),
            is_online=True
        )

        self.current_user = member
        self.team_members[user_id] = member
        self._save_team_member(member)

        print(f"👤 [CloudSync] 用户注册: {member.name} ({member.email})")
        return member

    def _save_team_member(self, member: TeamMember):
        """保存团队成员到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO team_members
            (user_id, name, email, role, device_ids, joined_at, last_active, is_online)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.user_id,
            member.name,
            member.email,
            member.role.value,
            json.dumps(member.device_ids),
            member.joined_at,
            member.last_active,
            int(member.is_online)
        ))

        conn.commit()
        conn.close()

    def queue_sync(self, item_type: str, item_id: str, data: Dict[str, Any],
                   priority: int = 5):
        """添加项目到同步队列"""
        item = SyncItem(
            id=item_id,
            type=item_type,
            data=data,
            checksum=SyncItem.calculate_checksum(data),
            modified_at=time.time(),
            device_id=self.device_id,
            status=SyncStatus.PENDING
        )

        self.pending_items[item_id] = item
        self.sync_queue.put((priority, item))
        self._log_sync_history(item_id, "queued", f"Type: {item_type}")

        print(f"📤 [CloudSync] 加入同步队列: {item_type}/{item_id}")
        return item

    def _log_sync_history(self, item_id: str, action: str, details: str = ""):
        """记录同步历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sync_history (item_id, action, timestamp, device_id, details)
            VALUES (?, ?, ?, ?, ?)
        """, (item_id, action, time.time(), self.device_id, details))

        conn.commit()
        conn.close()

    def start_sync(self, continuous: bool = True):
        """开始同步服务"""
        if self._sync_running:
            return

        self._sync_running = True
        self.is_online = True
        self.sync_status = SyncStatus.SYNCING

        if continuous:
            self._sync_thread = threading.Thread(
                target=self._sync_loop,
                daemon=True
            )
            self._sync_thread.start()
            print("☁️ [CloudSync] 自动同步服务已启动")
        else:
            self._sync_once()

    def stop_sync(self):
        """停止同步服务"""
        self._sync_running = False
        self.sync_status = SyncStatus.OFFLINE
        self.is_online = False
        print("🛑 [CloudSync] 同步服务已停止")

    def _sync_loop(self):
        """同步循环"""
        while self._sync_running:
            try:
                self._sync_once()
                time.sleep(self._sync_interval)
            except Exception as e:
                print(f"❌ [CloudSync] 同步错误: {e}")
                self.sync_status = SyncStatus.ERROR
                time.sleep(5)  # 错误后等待更短时间重试

    def _sync_once(self):
        """执行一次同步"""
        if not self.is_online:
            return

        self.sync_status = SyncStatus.SYNCING

        # 处理同步队列
        items_to_sync = []
        while not self.sync_queue.empty() and len(items_to_sync) < 10:
            try:
                priority, item = self.sync_queue.get_nowait()
                items_to_sync.append(item)
            except queue.Empty:
                break

        # 同步每个项目
        for item in items_to_sync:
            self._sync_item(item)

        if items_to_sync:
            print(f"☁️ [CloudSync] 同步完成: {len(items_to_sync)} 个项目")

        self.sync_status = SyncStatus.SYNCED

    def _sync_item(self, item: SyncItem) -> bool:
        """同步单个项目"""
        try:
            # 检查本地是否有冲突版本
            local_item = self._get_local_item(item.id)

            if local_item:
                # 版本冲突检测
                if local_item.version > item.version:
                    # 本地版本更新，需要解决冲突
                    resolved = self._resolve_conflict(local_item, item)
                    if resolved:
                        item = resolved
                    else:
                        item.status = SyncStatus.CONFLICT
                        self.pending_items[item.id] = item
                        return False

            # 保存到本地数据库
            item.version += 1
            item.status = SyncStatus.SYNCED
            self._save_sync_item(item)

            # 调用完成回调
            if self.on_sync_complete:
                self.on_sync_complete(item.id)

            self._log_sync_history(item.id, "synced", f"Version: {item.version}")
            return True

        except Exception as e:
            item.status = SyncStatus.ERROR
            self._log_sync_history(item.id, "error", str(e))
            return False

    def _get_local_item(self, item_id: str) -> Optional[SyncItem]:
        """获取本地项目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM sync_items WHERE id = ?",
            (item_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return SyncItem(
                id=row[0],
                type=row[1],
                data=json.loads(row[2]),
                checksum=row[3],
                modified_at=row[4],
                device_id=row[5],
                version=row[6],
                status=SyncStatus(row[7])
            )
        return None

    def _save_sync_item(self, item: SyncItem):
        """保存同步项目到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO sync_items
            (id, type, data, checksum, modified_at, device_id, version, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id,
            item.type,
            json.dumps(item.data, ensure_ascii=False),
            item.checksum,
            item.modified_at,
            item.device_id,
            item.version,
            item.status.value
        ))

        conn.commit()
        conn.close()

    def _resolve_conflict(self, local: SyncItem, remote: SyncItem) -> Optional[SyncItem]:
        """解决同步冲突"""
        if self.on_conflict:
            # 使用自定义冲突解决器
            return self.on_conflict(local, remote)

        # 默认策略：以时间戳最新的为准
        if local.modified_at > remote.modified_at:
            local.version = max(local.version, remote.version) + 1
            return local
        else:
            remote.version = max(local.version, remote.version) + 1
            return remote

    def share_workflow(self, workflow_id: str, name: str,
                       description: str, steps: List[Dict],
                       shared_with: List[str] = None) -> SharedWorkflow:
        """共享工作流"""
        if not self.current_user:
            raise ValueError("必须先注册设备")

        workflow = SharedWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            created_by=self.current_user.user_id,
            steps=steps,
            shared_with=shared_with or [],
            permissions={user_id: "view" for user_id in (shared_with or [])}
        )

        self.shared_workflows[workflow_id] = workflow
        self._save_shared_workflow(workflow)

        # 添加到同步队列
        self.queue_sync("workflow", workflow_id, workflow.to_dict(), priority=3)

        print(f"🔄 [CloudSync] 工作流已共享: {name}")
        return workflow

    def _save_shared_workflow(self, workflow: SharedWorkflow):
        """保存共享工作流到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO shared_workflows
            (id, name, description, created_by, steps, shared_with, permissions,
             created_at, updated_at, execution_count, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow.id,
            workflow.name,
            workflow.description,
            workflow.created_by,
            json.dumps(workflow.steps, ensure_ascii=False),
            json.dumps(workflow.shared_with),
            json.dumps(workflow.permissions),
            workflow.created_at,
            workflow.updated_at,
            workflow.execution_count,
            workflow.rating
        ))

        conn.commit()
        conn.close()

    def get_shared_workflows(self, include_public: bool = True) -> List[SharedWorkflow]:
        """获取共享的工作流"""
        if not self.current_user:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM shared_workflows WHERE created_by = ? OR shared_with LIKE ?",
            (self.current_user.user_id, f'%"{self.current_user.user_id}"%')
        )

        workflows = []
        for row in cursor.fetchall():
            workflows.append(SharedWorkflow(
                id=row[0],
                name=row[1],
                description=row[2],
                created_by=row[3],
                steps=json.loads(row[4]),
                shared_with=json.loads(row[5]),
                permissions=json.loads(row[6]),
                created_at=row[7],
                updated_at=row[8],
                execution_count=row[9],
                rating=row[10]
            ))

        conn.close()
        return workflows

    def invite_team_member(self, email: str, name: str,
                           role: CollaborationRole = CollaborationRole.EDITOR) -> TeamMember:
        """邀请团队成员"""
        if not self.current_user or self.current_user.role not in [CollaborationRole.OWNER, CollaborationRole.ADMIN]:
            raise PermissionError("没有权限邀请成员")

        user_id = hashlib.md5(email.encode()).hexdigest()[:12]

        member = TeamMember(
            user_id=user_id,
            name=name,
            email=email,
            role=role
        )

        self.team_members[user_id] = member
        self._save_team_member(member)

        print(f"📧 [CloudSync] 已邀请团队成员: {name} ({email}) - {role.value}")

        if self.on_team_member_join:
            self.on_team_member_join(member)

        return member

    def sync_config(self, config: Dict[str, Any]):
        """同步配置"""
        config_id = f"config_{self.device_id}"
        self.queue_sync("config", config_id, config, priority=1)

    def sync_workflow_history(self, workflow_id: str, execution_data: Dict):
        """同步工作流执行历史"""
        history_id = f"history_{workflow_id}_{int(time.time())}"
        self.queue_sync("history", history_id, execution_data, priority=2)

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 统计各状态的项目数量
        cursor.execute(
            "SELECT status, COUNT(*) FROM sync_items GROUP BY status"
        )
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # 获取最近的同步历史
        cursor.execute(
            """SELECT action, timestamp, details FROM sync_history
               ORDER BY timestamp DESC LIMIT 10"""
        )
        recent_history = [
            {"action": row[0], "timestamp": row[1], "details": row[2]}
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            "device_id": self.device_id,
            "is_online": self.is_online,
            "sync_status": self.sync_status.value,
            "pending_count": self.sync_queue.qsize(),
            "status_breakdown": status_counts,
            "team_members_count": len(self.team_members),
            "shared_workflows_count": len(self.shared_workflows),
            "recent_history": recent_history
        }

    def export_data(self, export_path: str):
        """导出所有同步数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        export_data = {
            "export_time": time.time(),
            "device_id": self.device_id,
            "sync_items": [],
            "team_members": [],
            "shared_workflows": []
        }

        # 导出同步项目
        cursor.execute("SELECT * FROM sync_items")
        for row in cursor.fetchall():
            export_data["sync_items"].append({
                "id": row[0],
                "type": row[1],
                "data": json.loads(row[2]),
                "checksum": row[3],
                "modified_at": row[4],
                "device_id": row[5],
                "version": row[6],
                "status": row[7]
            })

        # 导出团队成员
        cursor.execute("SELECT * FROM team_members")
        for row in cursor.fetchall():
            export_data["team_members"].append({
                "user_id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "device_ids": json.loads(row[4]),
                "joined_at": row[5],
                "last_active": row[6],
                "is_online": bool(row[7])
            })

        # 导出共享工作流
        cursor.execute("SELECT * FROM shared_workflows")
        for row in cursor.fetchall():
            export_data["shared_workflows"].append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_by": row[3],
                "steps": json.loads(row[4]),
                "shared_with": json.loads(row[5]),
                "permissions": json.loads(row[6]),
                "created_at": row[7],
                "updated_at": row[8],
                "execution_count": row[9],
                "rating": row[10]
            })

        conn.close()

        # 保存到文件
        Path(export_path).parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"💾 [CloudSync] 数据已导出到: {export_path}")
        return export_path

    def import_data(self, import_path: str, merge: bool = True):
        """导入同步数据"""
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not merge:
            # 清空现有数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_items")
            cursor.execute("DELETE FROM team_members")
            cursor.execute("DELETE FROM shared_workflows")
            conn.commit()
            conn.close()

        # 导入同步项目
        for item in data.get("sync_items", []):
            sync_item = SyncItem(
                id=item["id"],
                type=item["type"],
                data=item["data"],
                checksum=item["checksum"],
                modified_at=item["modified_at"],
                device_id=item["device_id"],
                version=item["version"],
                status=SyncStatus(item["status"])
            )
            self._save_sync_item(sync_item)

        # 导入团队成员
        for member in data.get("team_members", []):
            team_member = TeamMember(
                user_id=member["user_id"],
                name=member["name"],
                email=member["email"],
                role=CollaborationRole(member["role"]),
                device_ids=member["device_ids"],
                joined_at=member["joined_at"],
                last_active=member["last_active"],
                is_online=member["is_online"]
            )
            self.team_members[member["user_id"]] = team_member
            self._save_team_member(team_member)

        # 导入共享工作流
        for workflow in data.get("shared_workflows", []):
            shared = SharedWorkflow(
                id=workflow["id"],
                name=workflow["name"],
                description=workflow["description"],
                created_by=workflow["created_by"],
                steps=workflow["steps"],
                shared_with=workflow["shared_with"],
                permissions=workflow["permissions"],
                created_at=workflow["created_at"],
                updated_at=workflow["updated_at"],
                execution_count=workflow["execution_count"],
                rating=workflow["rating"]
            )
            self.shared_workflows[workflow["id"]] = shared
            self._save_shared_workflow(shared)

        print(f"📥 [CloudSync] 数据已导入: {import_path}")
        print(f"   同步项目: {len(data.get('sync_items', []))}")
        print(f"   团队成员: {len(data.get('team_members', []))}")
        print(f"   共享工作流: {len(data.get('shared_workflows', []))}")


# 便捷函数
def create_cloud_sync(device_id: Optional[str] = None) -> CloudSync:
    """创建云端同步实例"""
    return CloudSync(device_id)


if __name__ == "__main__":
    # 测试
    sync = CloudSync()

    # 注册用户
    user = sync.register_device({
        "name": "测试用户",
        "email": "test@example.com",
        "role": "owner"
    })

    # 同步一些配置
    sync.sync_config({
        "theme": "dark",
        "language": "zh-CN",
        "auto_save": True
    })

    # 共享工作流
    workflow = sync.share_workflow(
        workflow_id="wf_001",
        name="自动备份工作流",
        description="每天自动备份重要文件",
        steps=[
            {"action": "open", "target": "文件管理器"},
            {"action": "select", "target": "重要文件夹"},
            {"action": "copy"},
            {"action": "paste", "target": "备份位置"}
        ]
    )

    # 开始同步
    sync.start_sync()

    # 等待一下
    time.sleep(2)

    # 查看状态
    status = sync.get_sync_status()
    print(f"\n同步状态: {json.dumps(status, indent=2, ensure_ascii=False)}")

    # 停止同步
    sync.stop_sync()
