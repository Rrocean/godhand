#!/usr/bin/env python3
"""
ElementLibrary 🗂️ - UI 元素库

缓存和管理常用 UI 元素，加速视觉识别。

核心功能：
1. 元素缓存 - 缓存检测到的 UI 元素
2. 元素匹配 - 快速匹配已知元素
3. 元素学习 - 从用户交互中学习新元素
4. 模板管理 - 管理应用特定的元素模板

Author: GodHand Team
Version: 1.0.0
"""

import json
import os
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from PIL import Image


@dataclass
class ElementTemplate:
    """UI 元素模板"""
    template_id: str
    name: str                         # 元素名称（如"保存按钮"）
    app_name: str                     # 所属应用
    element_type: str                 # 类型（button/input等）

    # 视觉特征
    image_hash: str                   # 图像哈希
    image_path: Optional[str] = None  # 模板图像路径

    # 位置信息（相对于窗口）
    relative_x: float = 0.5           # 相对X位置（0-1）
    relative_y: float = 0.5           # 相对Y位置（0-1）

    # 属性
    text: str = ""                    # 文本内容
    color_profile: Optional[Dict] = None  # 颜色特征

    # 统计
    hit_count: int = 0                # 命中次数
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # 元数据
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "app_name": self.app_name,
            "element_type": self.element_type,
            "image_hash": self.image_hash,
            "image_path": self.image_path,
            "relative_x": self.relative_x,
            "relative_y": self.relative_y,
            "text": self.text,
            "color_profile": self.color_profile,
            "hit_count": self.hit_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ElementTemplate":
        return cls(**data)


@dataclass
class CachedElement:
    """缓存的检测到的元素"""
    element_id: str
    template_id: Optional[str]       # 关联的模板ID

    # 位置（绝对坐标）
    x: int
    y: int
    width: int
    height: int

    # 检测信息
    confidence: float
    detection_method: str            # "template", "ml", "cv"

    # 时间戳
    timestamp: float                 # 检测时间
    ttl: int = 300                   # 缓存有效期（秒）

    def is_valid(self) -> bool:
        """检查缓存是否仍然有效"""
        return time.time() - self.timestamp < self.ttl

    def to_dict(self) -> Dict:
        return {
            "element_id": self.element_id,
            "template_id": self.template_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "timestamp": self.timestamp
        }


class ElementLibrary:
    """
    UI 元素库

    世界级的元素缓存和管理系统
    """

    def __init__(self, data_dir: str = "./data/elements"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 模板存储
        self.templates: Dict[str, ElementTemplate] = {}
        self.app_templates: Dict[str, List[str]] = defaultdict(list)  # app -> template_ids

        # 运行时缓存
        self.cache: Dict[str, CachedElement] = {}
        self.cache_by_position: Dict[str, List[str]] = defaultdict(list)  # 位置区域 -> element_ids

        # 索引
        self.name_index: Dict[str, List[str]] = defaultdict(list)  # name -> template_ids
        self.type_index: Dict[str, List[str]] = defaultdict(list)  # type -> template_ids

        # 统计数据
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "template_matches": 0,
            "new_elements_learned": 0
        }

        # 加载数据
        self._load_templates()

        print(f"[ElementLibrary] 初始化完成，已加载 {len(self.templates)} 个模板")

    def _load_templates(self):
        """加载模板数据"""
        template_file = self.data_dir / "templates.json"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_id, template_data in data.items():
                        template = ElementTemplate.from_dict(template_data)
                        self._add_template_to_index(template)
            except Exception as e:
                print(f"[Warn] 加载模板失败: {e}")

    def _save_templates(self):
        """保存模板数据"""
        template_file = self.data_dir / "templates.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(
                {k: v.to_dict() for k, v in self.templates.items()},
                f,
                ensure_ascii=False,
                indent=2
            )

    def _add_template_to_index(self, template: ElementTemplate):
        """添加模板到索引"""
        self.templates[template.template_id] = template
        self.app_templates[template.app_name].append(template.template_id)
        self.name_index[template.name.lower()].append(template.template_id)
        self.type_index[template.element_type].append(template.template_id)

    # =====================================================================
    # 模板管理
    # =====================================================================

    def add_template(
        self,
        name: str,
        app_name: str,
        element_type: str,
        screenshot: Image.Image,
        bbox: Tuple[int, int, int, int],
        text: str = "",
        tags: List[str] = None
    ) -> ElementTemplate:
        """
        添加新模板

        Args:
            name: 元素名称（如"保存按钮"）
            app_name: 所属应用
            element_type: 元素类型
            screenshot: 屏幕截图
            bbox: 元素区域 (x, y, width, height)
            text: 元素文本
            tags: 标签

        Returns:
            创建的模板
        """
        template_id = f"tpl_{int(time.time() * 1000)}_{hashlib.md5(name.encode()).hexdigest()[:6]}"

        # 裁剪元素图像
        x, y, w, h = bbox
        element_img = screenshot.crop((x, y, x + w, y + h))

        # 计算图像哈希
        image_hash = self._compute_image_hash(element_img)

        # 保存模板图像
        image_path = self.data_dir / "images" / f"{template_id}.png"
        image_path.parent.mkdir(exist_ok=True)
        element_img.save(image_path)

        # 计算相对位置
        screen_w, screen_h = screenshot.size
        rel_x = (x + w / 2) / screen_w
        rel_y = (y + h / 2) / screen_h

        # 提取颜色特征
        color_profile = self._extract_color_profile(element_img)

        # 创建模板
        template = ElementTemplate(
            template_id=template_id,
            name=name,
            app_name=app_name,
            element_type=element_type,
            image_hash=image_hash,
            image_path=str(image_path),
            relative_x=rel_x,
            relative_y=rel_y,
            text=text,
            color_profile=color_profile,
            tags=tags or []
        )

        # 添加到索引
        self._add_template_to_index(template)
        self._save_templates()

        self.stats["new_elements_learned"] += 1
        print(f"[ElementLibrary] 添加模板: {name} ({app_name})")

        return template

    def find_template(self, name: str, app_name: str = None) -> Optional[ElementTemplate]:
        """
        查找模板

        Args:
            name: 元素名称
            app_name: 可选的应用过滤

        Returns:
            匹配的模板
        """
        name_lower = name.lower()

        # 直接匹配
        if name_lower in self.name_index:
            template_ids = self.name_index[name_lower]

            if app_name:
                # 过滤应用
                for tid in template_ids:
                    template = self.templates.get(tid)
                    if template and template.app_name.lower() == app_name.lower():
                        return template
            else:
                # 返回最热门的
                best = max(
                    (self.templates[tid] for tid in template_ids),
                    key=lambda t: t.hit_count,
                    default=None
                )
                return best

        # 模糊匹配
        return self._fuzzy_find_template(name, app_name)

    def _fuzzy_find_template(self, name: str, app_name: str = None) -> Optional[ElementTemplate]:
        """模糊查找模板"""
        import difflib

        candidates = []
        for template in self.templates.values():
            if app_name and template.app_name.lower() != app_name.lower():
                continue

            # 计算名称相似度
            score = difflib.SequenceMatcher(None, name.lower(), template.name.lower()).ratio()
            if score > 0.6:
                candidates.append((template, score))

        if candidates:
            # 返回最相似的
            return max(candidates, key=lambda x: x[1])[0]

        return None

    def match_template(
        self,
        screenshot: Image.Image,
        template: ElementTemplate,
        search_region: Tuple[int, int, int, int] = None
    ) -> Optional[Tuple[int, int, float]]:
        """
        在截图中匹配模板

        Returns:
            (x, y, confidence) 或 None
        """
        try:
            import cv2
            import numpy as np

            # 加载模板图像
            if not template.image_path or not Path(template.image_path).exists():
                return None

            template_img = cv2.imread(template.image_path)
            if template_img is None:
                return None

            # 转换截图
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 如果指定了搜索区域，裁剪
            if search_region:
                sx, sy, sw, sh = search_region
                screenshot_cv = screenshot_cv[sy:sy+sh, sx:sx+sw]
                offset_x, offset_y = sx, sy
            else:
                offset_x, offset_y = 0, 0

            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template_img, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > 0.8:  # 阈值
                x = max_loc[0] + offset_x
                y = max_loc[1] + offset_y

                # 更新统计
                template.hit_count += 1
                template.last_used = datetime.now().isoformat()
                self.stats["template_matches"] += 1

                return (x, y, max_val)

            return None

        except Exception as e:
            print(f"[Error] 模板匹配失败: {e}")
            return None

    # =====================================================================
    # 缓存管理
    # =====================================================================

    def cache_element(
        self,
        element_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
        detection_method: str = "cv",
        template_id: Optional[str] = None,
        ttl: int = 300
    ) -> CachedElement:
        """缓存检测到的元素"""
        cached = CachedElement(
            element_id=element_id,
            template_id=template_id,
            x=x,
            y=y,
            width=width,
            height=height,
            confidence=confidence,
            detection_method=detection_method,
            timestamp=time.time(),
            ttl=ttl
        )

        self.cache[element_id] = cached

        # 添加到位置索引（按100x100网格）
        grid_x = x // 100
        grid_y = y // 100
        grid_key = f"{grid_x},{grid_y}"
        self.cache_by_position[grid_key].append(element_id)

        return cached

    def get_cached_element(self, element_id: str) -> Optional[CachedElement]:
        """获取缓存的元素"""
        cached = self.cache.get(element_id)

        if cached:
            if cached.is_valid():
                self.stats["cache_hits"] += 1
                return cached
            else:
                # 过期，移除
                del self.cache[element_id]

        self.stats["cache_misses"] += 1
        return None

    def find_in_cache(
        self,
        x: int,
        y: int,
        name: str = None,
        element_type: str = None
    ) -> Optional[CachedElement]:
        """
        在缓存中查找附近的元素

        Args:
            x, y: 搜索位置
            name: 可选的名称过滤
            element_type: 可选的类型过滤
        """
        # 获取附近网格的元素
        grid_x = x // 100
        grid_y = y // 100

        nearby_elements = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                grid_key = f"{grid_x + dx},{grid_y + dy}"
                for element_id in self.cache_by_position.get(grid_key, []):
                    cached = self.cache.get(element_id)
                    if cached and cached.is_valid():
                        nearby_elements.append(cached)

        # 找到最接近的
        if nearby_elements:
            # 计算距离
            def distance(elem):
                return (elem.x - x) ** 2 + (elem.y - y) ** 2

            nearby_elements.sort(key=distance)
            return nearby_elements[0]

        return None

    def clear_expired_cache(self):
        """清理过期缓存"""
        expired = [
            element_id
            for element_id, cached in self.cache.items()
            if not cached.is_valid()
        ]

        for element_id in expired:
            del self.cache[element_id]

        # 清理空的位置索引
        empty_grids = [
            grid_key
            for grid_key, element_ids in self.cache_by_position.items()
            if not element_ids or all(eid not in self.cache for eid in element_ids)
        ]

        for grid_key in empty_grids:
            del self.cache_by_position[grid_key]

        return len(expired)

    # =====================================================================
    # 学习功能
    # =====================================================================

    def learn_from_interaction(
        self,
        element_name: str,
        app_name: str,
        screenshot: Image.Image,
        bbox: Tuple[int, int, int, int],
        success: bool = True
    ):
        """从用户交互中学习元素"""
        if not success:
            return

        # 检查是否已存在相似模板
        existing = self.find_template(element_name, app_name)
        if existing:
            # 更新现有模板
            existing.hit_count += 1
            existing.last_used = datetime.now().isoformat()
            return

        # 创建新模板
        self.add_template(
            name=element_name,
            app_name=app_name,
            element_type="unknown",
            screenshot=screenshot,
            bbox=bbox,
            tags=["learned"]
        )

    # =====================================================================
    # 辅助方法
    # =====================================================================

    def _compute_image_hash(self, img: Image.Image) -> str:
        """计算图像哈希"""
        # 缩小图像
        small = img.resize((16, 16), Image.Resampling.LANCZOS)
        # 转换为灰度
        gray = small.convert('L')
        # 计算平均哈希
        pixels = list(gray.getdata())
        avg = sum(pixels) / len(pixels)
        bits = ''.join('1' if p > avg else '0' for p in pixels)
        return hex(int(bits, 2))[2:].zfill(16)

    def _extract_color_profile(self, img: Image.Image) -> Dict:
        """提取颜色特征"""
        # 缩小图像
        small = img.resize((32, 32), Image.Resampling.LANCZOS)

        # 获取主要颜色
        pixels = list(small.getdata())

        # 简化的颜色直方图
        r_vals = [p[0] for p in pixels if len(p) >= 3]
        g_vals = [p[1] for p in pixels if len(p) >= 3]
        b_vals = [p[2] for p in pixels if len(p) >= 3]

        return {
            "r_mean": sum(r_vals) / len(r_vals) if r_vals else 0,
            "g_mean": sum(g_vals) / len(g_vals) if g_vals else 0,
            "b_mean": sum(b_vals) / len(b_vals) if b_vals else 0,
        }

    # =====================================================================
    # 统计和导出
    # =====================================================================

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            "templates_count": len(self.templates),
            "apps_count": len(self.app_templates),
            "cache_size": len(self.cache),
            "cache_hit_rate": self._compute_cache_hit_rate()
        }

    def _compute_cache_hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total == 0:
            return 0.0
        return self.stats["cache_hits"] / total

    def export_templates(self, app_name: str = None) -> List[Dict]:
        """导出模板"""
        templates = self.templates.values()

        if app_name:
            template_ids = self.app_templates.get(app_name, [])
            templates = [self.templates[tid] for tid in template_ids]

        return [t.to_dict() for t in templates]

    def import_templates(self, templates_data: List[Dict]):
        """导入模板"""
        for data in templates_data:
            template = ElementTemplate.from_dict(data)
            self._add_template_to_index(template)

        self._save_templates()


# 便捷函数
def get_element_library(data_dir: str = "./data/elements") -> ElementLibrary:
    """获取元素库单例"""
    if not hasattr(get_element_library, "_instance"):
        get_element_library._instance = ElementLibrary(data_dir)
    return get_element_library._instance


if __name__ == "__main__":
    # 测试
    lib = ElementLibrary()

    # 创建测试截图
    test_img = Image.new('RGB', (1920, 1080), color='white')

    # 添加模板
    template = lib.add_template(
        name="保存按钮",
        app_name="记事本",
        element_type="button",
        screenshot=test_img,
        bbox=(100, 100, 80, 30),
        text="保存"
    )

    print(f"添加模板: {template.template_id}")

    # 查找模板
    found = lib.find_template("保存按钮", "记事本")
    print(f"找到模板: {found.name if found else 'None'}")

    # 缓存元素
    cached = lib.cache_element("elem_001", 150, 150, 80, 30, 0.95, template_id=template.template_id)
    print(f"缓存元素: {cached.element_id}")

    # 统计
    stats = lib.get_stats()
    print(f"统计: {stats}")
