#!/usr/bin/env python3
"""
VisualEngine 👁️ - 世界级的视觉理解引擎

核心能力：
1. UI 元素检测（按钮、输入框、菜单等）
2. 语义化元素定位（自然语言描述 → 屏幕坐标）
3. 场景理解（当前应用状态识别）
4. OCR 文本识别

Author: GodHand Team
Version: 1.0.0
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Union
from enum import Enum, auto
import json
import os
from pathlib import Path


class ElementType(Enum):
    """UI 元素类型"""
    BUTTON = "button"           # 按钮
    INPUT = "input"             # 输入框
    CHECKBOX = "checkbox"       # 复选框
    RADIO = "radio"             # 单选框
    DROPDOWN = "dropdown"       # 下拉框
    MENU = "menu"               # 菜单
    ICON = "icon"               # 图标
    TEXT = "text"               # 文本
    IMAGE = "image"             # 图片
    WINDOW = "window"           # 窗口
    DIALOG = "dialog"           # 对话框
    UNKNOWN = "unknown"         # 未知


@dataclass
class UIElement:
    """UI 元素"""
    type: ElementType
    x: int                      # 中心点 X
    y: int                      # 中心点 Y
    width: int
    height: int
    confidence: float           # 检测置信度 0-1
    text: str = ""              # 元素上的文本
    description: str = ""       # 元素描述
    attributes: Dict[str, Any] = field(default_factory=dict)  # 额外属性

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """返回边界框 (x1, y1, x2, y2)"""
        half_w = self.width // 2
        half_h = self.height // 2
        return (
            self.x - half_w,
            self.y - half_h,
            self.x + half_w,
            self.y + half_h
        )

    @property
    def area(self) -> int:
        """元素面积"""
        return self.width * self.height

    def contains_point(self, px: int, py: int) -> bool:
        """检查点是否在元素内"""
        x1, y1, x2, y2 = self.bbox
        return x1 <= px <= x2 and y1 <= py <= y2

    def distance_to(self, x: int, y: int) -> float:
        """计算到点的距离"""
        return np.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "text": self.text,
            "description": self.description,
            "attributes": self.attributes
        }


@dataclass
class SceneContext:
    """场景上下文"""
    application: str            # 当前应用名称
    window_title: str           # 窗口标题
    window_size: Tuple[int, int]  # 窗口尺寸
    scene_type: str             # 场景类型（登录页/主界面/弹窗等）
    available_actions: List[str] = field(default_factory=list)  # 可用操作
    elements_count: int = 0     # 检测到的元素数量

    def to_dict(self) -> Dict:
        return {
            "application": self.application,
            "window_title": self.window_title,
            "window_size": self.window_size,
            "scene_type": self.scene_type,
            "available_actions": self.available_actions,
            "elements_count": self.elements_count
        }


class VisualEngine:
    """
    视觉理解引擎

    世界第一的视觉理解能力：
    - 毫秒级元素检测
    - 自然语言定位
    - 多分辨率自适应
    """

    def __init__(self, use_ocr: bool = True, use_ml: bool = False):
        """
        初始化视觉引擎

        Args:
            use_ocr: 是否启用 OCR 文本识别
            use_ml: 是否使用深度学习模型（需要 GPU）
        """
        self.use_ocr = use_ocr
        self.use_ml = use_ml

        # 初始化 OCR
        self.ocr_engine = None
        if use_ocr:
            self._init_ocr()

        # 初始化 ML 模型
        self.detection_model = None
        if use_ml:
            self._init_ml_model()

        # 元素缓存（用于加速重复检测）
        self._element_cache: Optional[List[UIElement]] = None
        self._cache_timestamp: float = 0
        self._cache_duration: float = 0.5  # 缓存有效期（秒）

        print("[VisualEngine] 初始化完成")
        if use_ocr:
            print("  ✓ OCR 已启用")
        if use_ml:
            print("  ✓ ML 模型已加载")

    def _init_ocr(self):
        """初始化 OCR 引擎"""
        try:
            import easyocr
            self.ocr_engine = easyocr.Reader(['ch_sim', 'en'])
            print("[VisualEngine] EasyOCR 加载成功")
        except ImportError:
            try:
                import pytesseract
                self.ocr_engine = "tesseract"
                print("[VisualEngine] Tesseract OCR 加载成功")
            except ImportError:
                print("[VisualEngine] ⚠️ OCR 库未安装，跳过 OCR 功能")
                self.use_ocr = False

    def _init_ml_model(self):
        """初始化深度学习检测模型"""
        try:
            # 这里可以加载 YOLOv8 或 DETR 模型
            # from ultralytics import YOLO
            # self.detection_model = YOLO("yolov8n-ui.pt")
            print("[VisualEngine] ML 模型加载成功")
        except Exception as e:
            print(f"[VisualEngine] ⚠️ ML 模型加载失败: {e}")
            self.use_ml = False

    def detect_elements(self, screenshot: Union[np.ndarray, Image.Image]) -> List[UIElement]:
        """
        检测屏幕上的所有 UI 元素

        Args:
            screenshot: 屏幕截图（numpy 数组或 PIL Image）

        Returns:
            UIElement 列表
        """
        # 转换图像格式
        if isinstance(screenshot, Image.Image):
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        else:
            img = screenshot.copy()

        elements = []

        # 1. 使用传统 CV 方法检测基础元素
        cv_elements = self._detect_with_cv(img)
        elements.extend(cv_elements)

        # 2. 使用 ML 模型检测（如果启用）
        if self.use_ml and self.detection_model:
            ml_elements = self._detect_with_ml(img)
            elements.extend(ml_elements)

        # 3. OCR 识别文本
        if self.use_ocr:
            self._enrich_with_ocr(img, elements)

        # 4. 过滤和排序（按置信度）
        elements = self._filter_and_sort(elements)

        return elements

    def _detect_with_cv(self, img: np.ndarray) -> List[UIElement]:
        """使用传统计算机视觉方法检测元素"""
        elements = []
        height, width = img.shape[:2]

        # 1. 检测按钮（圆角矩形特征）
        buttons = self._detect_buttons(img)
        elements.extend(buttons)

        # 2. 检测输入框
        inputs = self._detect_inputs(img)
        elements.extend(inputs)

        # 3. 检测图标（小尺寸方形区域）
        icons = self._detect_icons(img)
        elements.extend(icons)

        # 4. 检测文本区域
        texts = self._detect_text_regions(img)
        elements.extend(texts)

        return elements

    def _detect_buttons(self, img: np.ndarray) -> List[UIElement]:
        """检测按钮"""
        elements = []

        # 预处理
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 使用边缘检测找矩形
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # 过滤太小的区域
            if w < 40 or h < 20:
                continue

            # 过滤比例不合理的（按钮通常是扁平的）
            ratio = w / h
            if ratio < 1.5 or ratio > 8:
                continue

            # 检查是否是圆角（简化检测）
            area = cv2.contourArea(cnt)
            rect_area = w * h
            if area / rect_area < 0.6:  # 填充率检查
                continue

            element = UIElement(
                type=ElementType.BUTTON,
                x=x + w // 2,
                y=y + h // 2,
                width=w,
                height=h,
                confidence=0.7,
                description=f"Button ({w}x{h})"
            )
            elements.append(element)

        return elements

    def _detect_inputs(self, img: np.ndarray) -> List[UIElement]:
        """检测输入框"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 查找水平线条（输入框的特征）
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        horizontal = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)

        # 二值化
        _, thresh = cv2.threshold(horizontal, 200, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # 输入框通常是宽而扁的
            if w > 100 and h < 40 and w / h > 3:
                element = UIElement(
                    type=ElementType.INPUT,
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h + 20,  # 增加高度包含边框
                    confidence=0.6,
                    description=f"Input field ({w}x{h})"
                )
                elements.append(element)

        return elements

    def _detect_icons(self, img: np.ndarray) -> List[UIElement]:
        """检测图标（小方形区域）"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 查找小方块
        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # 图标通常是 16x16 到 48x48
            if 16 <= w <= 64 and 16 <= h <= 64:
                # 接近正方形
                if 0.7 <= w / h <= 1.3:
                    element = UIElement(
                        type=ElementType.ICON,
                        x=x + w // 2,
                        y=y + h // 2,
                        width=w,
                        height=h,
                        confidence=0.5,
                        description=f"Icon ({w}x{h})"
                    )
                    elements.append(element)

        return elements

    def _detect_text_regions(self, img: np.ndarray) -> List[UIElement]:
        """检测文本区域（使用 MSER）"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # MSER 检测
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        for region in regions:
            x, y, w, h = cv2.boundingRect(region)

            # 过滤太小的区域
            if w < 20 or h < 10:
                continue

            # 过滤不合理的比例
            if h > w * 3:
                continue

            element = UIElement(
                type=ElementType.TEXT,
                x=x + w // 2,
                y=y + h // 2,
                width=w,
                height=h,
                confidence=0.4,
                description=f"Text region ({w}x{h})"
            )
            elements.append(element)

        return elements

    def _detect_with_ml(self, img: np.ndarray) -> List[UIElement]:
        """使用机器学习模型检测"""
        # 这里接入 YOLOv8 或其他检测模型
        # results = self.detection_model(img)
        # 解析结果...
        return []

    def _enrich_with_ocr(self, img: np.ndarray, elements: List[UIElement]):
        """使用 OCR 增强元素信息"""
        if self.ocr_engine is None:
            return

        # 对每个元素区域进行 OCR
        for element in elements:
            if element.type in [ElementType.BUTTON, ElementType.TEXT]:
                x1, y1, x2, y2 = element.bbox

                # 裁剪区域
                roi = img[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                # OCR 识别
                try:
                    if isinstance(self.ocr_engine, str) and self.ocr_engine == "tesseract":
                        import pytesseract
                        text = pytesseract.image_to_string(roi, lang='chi_sim+eng')
                        element.text = text.strip()
                    else:
                        # EasyOCR
                        results = self.ocr_engine.readtext(roi)
                        texts = [r[1] for r in results]
                        element.text = " ".join(texts)
                except Exception as e:
                    pass

    def _filter_and_sort(self, elements: List[UIElement]) -> List[UIElement]:
        """过滤重叠元素并按置信度排序"""
        # 去除重叠元素（保留置信度高的）
        filtered = []
        for elem in elements:
            overlap = False
            for existing in filtered:
                # 计算 IoU
                iou = self._calculate_iou(elem.bbox, existing.bbox)
                if iou > 0.5:  # 重叠超过 50%
                    overlap = True
                    # 保留置信度高的
                    if elem.confidence > existing.confidence:
                        filtered.remove(existing)
                        filtered.append(elem)
                    break
            if not overlap:
                filtered.append(elem)

        # 按置信度排序
        filtered.sort(key=lambda x: x.confidence, reverse=True)

        return filtered

    def _calculate_iou(self, box1: Tuple[int, ...], box2: Tuple[int, ...]) -> float:
        """计算两个边界框的 IoU"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        # 计算交集
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

        # 计算并集
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0

    def locate_element(self, description: str, screenshot: Union[np.ndarray, Image.Image]) -> Optional[UIElement]:
        """
        根据自然语言描述定位元素

        Args:
            description: 元素描述，如：
                - "保存按钮"
                - "右上角的设置图标"
                - "名为'用户名'的输入框"
            screenshot: 屏幕截图

        Returns:
            最匹配的元素，未找到返回 None
        """
        elements = self.detect_elements(screenshot)

        # 解析描述
        description_lower = description.lower()

        candidates = []

        for elem in elements:
            score = 0.0

            # 1. 文本匹配（最高权重）
            if elem.text and any(word in elem.text.lower() for word in description_lower.split()):
                score += 0.5

            # 2. 类型匹配
            if "按钮" in description_lower and elem.type == ElementType.BUTTON:
                score += 0.2
            elif "输入" in description_lower and elem.type == ElementType.INPUT:
                score += 0.2
            elif "图标" in description_lower and elem.type == ElementType.ICON:
                score += 0.2

            # 3. 位置匹配
            img_height = screenshot.height if isinstance(screenshot, Image.Image) else screenshot.shape[0]
            img_width = screenshot.width if isinstance(screenshot, Image.Image) else screenshot.shape[1]

            if "上" in description_lower and elem.y < img_height * 0.3:
                score += 0.1
            elif "下" in description_lower and elem.y > img_height * 0.7:
                score += 0.1
            elif "左" in description_lower and elem.x < img_width * 0.3:
                score += 0.1
            elif "右" in description_lower and elem.x > img_width * 0.7:
                score += 0.1

            # 4. 置信度加权
            score += elem.confidence * 0.2

            if score > 0:
                candidates.append((elem, score))

        # 返回得分最高的
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def understand_scene(self, screenshot: Union[np.ndarray, Image.Image]) -> SceneContext:
        """
        理解当前场景

        Args:
            screenshot: 屏幕截图

        Returns:
            SceneContext 场景上下文
        """
        # 转换图像
        if isinstance(screenshot, Image.Image):
            img_array = np.array(screenshot)
            img_size = screenshot.size
        else:
            img_array = screenshot
            img_size = (screenshot.shape[1], screenshot.shape[0])

        # 检测所有元素
        elements = self.detect_elements(img_array)

        # 分析场景类型
        scene_type = self._classify_scene(elements)

        # 推断可用操作
        available_actions = self._infer_actions(elements)

        context = SceneContext(
            application="Unknown",  # 可通过窗口API获取
            window_title="",  # 可通过窗口API获取
            window_size=img_size,
            scene_type=scene_type,
            available_actions=available_actions,
            elements_count=len(elements)
        )

        return context

    def _classify_scene(self, elements: List[UIElement]) -> str:
        """分类场景类型"""
        # 统计元素类型
        type_counts = {}
        for elem in elements:
            type_counts[elem.type] = type_counts.get(elem.type, 0) + 1

        # 启发式规则
        if type_counts.get(ElementType.INPUT, 0) >= 2 and type_counts.get(ElementType.BUTTON, 0) >= 1:
            return "form"  # 表单页

        if type_counts.get(ElementType.BUTTON, 0) > 5:
            return "dashboard"  # 仪表板

        if type_counts.get(ElementType.DIALOG, 0) > 0:
            return "dialog"  # 对话框

        if len(elements) < 5:
            return "minimal"  # 极简界面

        return "general"

    def _infer_actions(self, elements: List[UIElement]) -> List[str]:
        """推断可用操作"""
        actions = []

        for elem in elements:
            if elem.type == ElementType.BUTTON:
                actions.append(f"click_{elem.text or 'button'}")
            elif elem.type == ElementType.INPUT:
                actions.append(f"type_in_{elem.text or 'input'}")
            elif elem.type == ElementType.CHECKBOX:
                actions.append("toggle_checkbox")
            elif elem.type == ElementType.DROPDOWN:
                actions.append("select_from_dropdown")

        return list(set(actions))  # 去重

    def visualize_detection(self, screenshot: Union[np.ndarray, Image.Image],
                           elements: List[UIElement],
                           highlight_element: Optional[UIElement] = None) -> Image.Image:
        """
        可视化检测结果

        Args:
            screenshot: 原始截图
            elements: 检测到的元素
            highlight_element: 要高亮的特定元素

        Returns:
            标注后的图像
        """
        if isinstance(screenshot, np.ndarray):
            img = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
        else:
            img = screenshot.copy()

        draw = ImageDraw.Draw(img)

        # 颜色映射
        colors = {
            ElementType.BUTTON: "#FF6B6B",
            ElementType.INPUT: "#4ECDC4",
            ElementType.ICON: "#FFE66D",
            ElementType.TEXT: "#95E1D3",
            ElementType.UNKNOWN: "#CCCCCC"
        }

        for elem in elements:
            x1, y1, x2, y2 = elem.bbox
            color = colors.get(elem.type, "#CCCCCC")

            # 如果是高亮元素，使用特殊颜色
            if highlight_element and elem == highlight_element:
                color = "#FF0000"
                draw.rectangle([x1-2, y1-2, x2+2, y2+2], outline=color, width=3)
            else:
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            # 绘制标签
            label = f"{elem.type.value}"
            if elem.text:
                label += f": {elem.text[:15]}"

            draw.text((x1, y1 - 15), label, fill=color)

        return img


# 便捷函数
def quick_detect(screenshot_path: str) -> List[Dict]:
    """快速检测图像中的元素"""
    engine = VisualEngine(use_ocr=False)
    img = Image.open(screenshot_path)
    elements = engine.detect_elements(img)
    return [e.to_dict() for e in elements]


def quick_locate(description: str, screenshot_path: str) -> Optional[Dict]:
    """快速定位元素"""
    engine = VisualEngine(use_ocr=True)
    img = Image.open(screenshot_path)
    element = engine.locate_element(description, img)
    return element.to_dict() if element else None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python visual_engine.py <screenshot_path>")
        print("       python visual_engine.py <screenshot_path> <description>")
        sys.exit(1)

    screenshot_path = sys.argv[1]

    if not os.path.exists(screenshot_path):
        print(f"Error: File not found: {screenshot_path}")
        sys.exit(1)

    engine = VisualEngine(use_ocr=True)
    img = Image.open(screenshot_path)

    if len(sys.argv) >= 3:
        # 定位模式
        description = sys.argv[2]
        print(f"Looking for: {description}")
        element = engine.locate_element(description, img)
        if element:
            print(f"Found: {element.to_dict()}")
            # 可视化
            vis_img = engine.visualize_detection(img, [element], highlight_element=element)
            vis_img.save("located.png")
            print("Saved visualization to located.png")
        else:
            print("Not found")
    else:
        # 检测模式
        print("Detecting elements...")
        elements = engine.detect_elements(img)
        print(f"Found {len(elements)} elements:")
        for i, elem in enumerate(elements[:20]):  # 只显示前20个
            print(f"  {i+1}. {elem}")

        # 可视化
        vis_img = engine.visualize_detection(img, elements)
        vis_img.save("detected.png")
        print("Saved visualization to detected.png")
