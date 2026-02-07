#!/usr/bin/env python3
"""
CloudSync 测试套件
"""

import os
import sys
import json
import time
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cloud_sync import (
    CloudSync, SyncItem, TeamMember, SharedWorkflow,
    SyncStatus, CollaborationRole
)


class TestCloudSync:
    """CloudSync 测试类"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sync.db")
        self.sync = CloudSync(device_id="test_device_001", db_path=self.db_path)

    def teardown_method(self):
        """测试后清理"""
        self.sync.stop_sync()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """测试初始化"""
        assert self.sync.device_id == "test_device_001"
        assert self.sync.sync_status == SyncStatus.OFFLINE
        assert not self.sync.is_online
        assert os.path.exists(self.db_path)
        print("✅ 初始化测试通过")

    def test_device_registration(self):
        """测试设备注册"""
        user = self.sync.register_device({
            "name": "测试用户",
            "email": "test@example.com",
            "role": "owner"
        })

        assert user is not None
        assert user.name == "测试用户"
        assert user.email == "test@example.com"
        assert user.role == CollaborationRole.OWNER
        assert "test_device_001" in user.device_ids
        assert self.sync.current_user == user
        print("✅ 设备注册测试通过")

    def test_sync_queue(self):
        """测试同步队列"""
        # 添加同步项目
        item = self.sync.queue_sync(
            item_type="config",
            item_id="test_config",
            data={"theme": "dark", "lang": "zh"},
            priority=1
        )

        assert item.id == "test_config"
        assert item.type == "config"
        assert item.status == SyncStatus.PENDING
        assert "test_config" in self.sync.pending_items
        print("✅ 同步队列测试通过")

    def test_checksum_calculation(self):
        """测试校验和计算"""
        data1 = {"key": "value", "num": 123}
        data2 = {"num": 123, "key": "value"}
        data3 = {"key": "different", "num": 123}

        checksum1 = SyncItem.calculate_checksum(data1)
        checksum2 = SyncItem.calculate_checksum(data2)
        checksum3 = SyncItem.calculate_checksum(data3)

        # 相同数据（顺序不同）应产生相同校验和
        assert checksum1 == checksum2
        # 不同数据应产生不同校验和
        assert checksum1 != checksum3
        print("✅ 校验和计算测试通过")

    def test_workflow_sharing(self):
        """测试工作流共享"""
        # 先注册用户
        self.sync.register_device({
            "name": "测试用户",
            "email": "test@example.com",
            "role": "owner"
        })

        workflow = self.sync.share_workflow(
            workflow_id="wf_test_001",
            name="测试工作流",
            description="这是一个测试工作流",
            steps=[
                {"action": "open", "target": "计算器"},
                {"action": "click", "target": "按钮1"}
            ]
        )

        assert workflow.id == "wf_test_001"
        assert workflow.name == "测试工作流"
        assert len(workflow.steps) == 2
        assert workflow.created_by == self.sync.current_user.user_id
        print("✅ 工作流共享测试通过")

    def test_team_invitation(self):
        """测试团队成员邀请"""
        # 先注册管理员
        self.sync.register_device({
            "name": "管理员",
            "email": "admin@example.com",
            "role": "owner"
        })

        member = self.sync.invite_team_member(
            email="member@example.com",
            name="新成员",
            role=CollaborationRole.EDITOR
        )

        assert member.email == "member@example.com"
        assert member.name == "新成员"
        assert member.role == CollaborationRole.EDITOR
        assert member.user_id in self.sync.team_members
        print("✅ 团队邀请测试通过")

    def test_permission_check(self):
        """测试权限检查"""
        # 注册普通成员（非管理员）
        self.sync.register_device({
            "name": "普通成员",
            "email": "user@example.com",
            "role": "editor"
        })

        # 普通成员不应能邀请其他人
        try:
            self.sync.invite_team_member(
                email="new@example.com",
                name="新用户",
                role=CollaborationRole.EDITOR
            )
            assert False, "应该抛出权限错误"
        except PermissionError:
            pass

        print("✅ 权限检查测试通过")

    def test_data_export_import(self):
        """测试数据导出导入"""
        # 注册并创建数据
        self.sync.register_device({
            "name": "测试用户",
            "email": "test@example.com",
            "role": "owner"
        })

        self.sync.sync_config({"theme": "dark"})

        self.sync.share_workflow(
            workflow_id="wf_001",
            name="工作流1",
            description="描述",
            steps=[{"action": "test"}]
        )

        # 导出
        export_path = os.path.join(self.temp_dir, "export.json")
        self.sync.export_data(export_path)
        assert os.path.exists(export_path)

        # 验证导出内容
        with open(export_path, 'r') as f:
            data = json.load(f)
        assert "sync_items" in data
        assert "shared_workflows" in data

        # 创建新的同步实例并导入
        new_sync = CloudSync(device_id="test_device_002",
                             db_path=os.path.join(self.temp_dir, "new_sync.db"))
        new_sync.import_data(export_path)

        # 验证导入
        workflows = new_sync.get_shared_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "工作流1"

        print("✅ 数据导出导入测试通过")

    def test_sync_status(self):
        """测试同步状态获取"""
        status = self.sync.get_sync_status()

        assert "device_id" in status
        assert "is_online" in status
        assert "sync_status" in status
        assert "pending_count" in status
        assert status["device_id"] == "test_device_001"
        print("✅ 同步状态测试通过")

    def test_conflict_resolution(self):
        """测试冲突解决"""
        # 创建两个版本的相同项目
        local_item = SyncItem(
            id="conflict_test",
            type="config",
            data={"value": "local"},
            checksum="abc123",
            modified_at=time.time(),
            device_id="device_local",
            version=1
        )

        remote_item = SyncItem(
            id="conflict_test",
            type="config",
            data={"value": "remote"},
            checksum="def456",
            modified_at=time.time() - 100,  # 更早的修改时间
            device_id="device_remote",
            version=1
        )

        # 测试默认冲突解决（时间戳最新的胜出）
        resolved = self.sync._resolve_conflict(local_item, remote_item)
        assert resolved.data["value"] == "local"  # 本地更新

        # 反转时间戳
        remote_item.modified_at = time.time() + 100
        resolved = self.sync._resolve_conflict(local_item, remote_item)
        assert resolved.data["value"] == "remote"  # 远程更新

        print("✅ 冲突解决测试通过")

    def test_config_sync(self):
        """测试配置同步"""
        config = {
            "theme": "dark",
            "language": "zh-CN",
            "auto_save": True,
            "shortcuts": {
                "execute": "Ctrl+Enter",
                "stop": "Ctrl+C"
            }
        }

        self.sync.sync_config(config)

        # 验证队列中有项目
        assert not self.sync.sync_queue.empty()
        print("✅ 配置同步测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 CloudSync 测试套件")
    print("="*60 + "\n")

    test = TestCloudSync()

    try:
        test.setup_method()
        test.test_initialization()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 初始化测试失败: {e}")

    try:
        test.setup_method()
        test.test_device_registration()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 设备注册测试失败: {e}")

    try:
        test.setup_method()
        test.test_sync_queue()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 同步队列测试失败: {e}")

    try:
        test.setup_method()
        test.test_checksum_calculation()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 校验和计算测试失败: {e}")

    try:
        test.setup_method()
        test.test_workflow_sharing()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 工作流共享测试失败: {e}")

    try:
        test.setup_method()
        test.test_team_invitation()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 团队邀请测试失败: {e}")

    try:
        test.setup_method()
        test.test_permission_check()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 权限检查测试失败: {e}")

    try:
        test.setup_method()
        test.test_data_export_import()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 数据导出导入测试失败: {e}")

    try:
        test.setup_method()
        test.test_sync_status()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 同步状态测试失败: {e}")

    try:
        test.setup_method()
        test.test_conflict_resolution()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 冲突解决测试失败: {e}")

    try:
        test.setup_method()
        test.test_config_sync()
        test.teardown_method()
    except Exception as e:
        print(f"❌ 配置同步测试失败: {e}")

    print("\n" + "="*60)
    print("✅ 所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
