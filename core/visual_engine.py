#!/usr/bin/env python3
"""
VisualEngine [emoji] - [emoji]

[emoji]
1. UI [emoji]
2. [emoji] → [emoji]
3. [emoji]
4. OCR [emoji]

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
    """UI [emoji]"""
    BUTTON = "button"           # [emoji]
    INPUT = "input"             # [emoji]
    CHECKBOX = "checkbox"       # [emoji]
    RADIO = "radio"             # [emoji]
    DROPDOWN = "dropdown"       # [emoji]
    MENU = "menu"               # [emoji]
    ICON = "icon"               # [emoji]
    TEXT = "text"               # [emoji]
    IMAGE = "image"             # [emoji]
    WINDOW = "window"           # [emoji]
    DIALOG = "dialog"           # [emoji]
    UNKNOWN = "unknown"         # [emoji]


@dataclass
class UIElement:
    """UI [emoji]"""
    type: ElementType
    x: int                      # [emoji] X
    y: int                      # [emoji] Y
    width: int
    height: int
    confidence: float           # [emoji] 0-1
    text: str = ""              # [emoji]
    description: str = ""       # [emoji]
    attributes: Dict[str, Any] = field(default_factory=dict)  # [emoji]

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """[emoji] (x1, y1, x2, y2)"""
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
        """[emoji]"""
        return self.width * self.height

    def contains_point(self, px: int, py: int) -> bool:
        """[emoji]"""
        x1, y1, x2, y2 = self.bbox
        return x1 <= px <= x2 and y1 <= py <= y2

    def distance_to(self, x: int, y: int) -> float:
        """[emoji]"""
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
    """[emoji]"""
    application: str            # [emoji]
    window_title: str           # [emoji]
    window_size: Tuple[int, int]  # [emoji]
    scene_type: str             # [emoji]/[emoji]/[emoji]
    available_actions: List[str] = field(default_factory=list)  # [emoji]
    elements_count: int = 0     # [emoji]

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
    [emoji]

    [emoji]
    - [emoji]
    - [emoji]
    - [emoji]
    """

    def __init__(self, use_ocr: bool = True, use_ml: bool = False):
        """
        [emoji]

        Args:
            use_ocr: [emoji] OCR [emoji]
            use_ml: [emoji] GPU[emoji]
        """
        self.use_ocr = use_ocr
        self.use_ml = use_ml

        # [emoji] OCR
        self.ocr_engine = None
        if use_ocr:
            self._init_ocr()

        # [emoji] ML [emoji]
        self.detection_model = None
        if use_ml:
            self._init_ml_model()

        # [emoji]
        self._element_cache: Optional[List[UIElement]] = None
        self._cache_timestamp: float = 0
        self._cache_duration: float = 0.5  # [emoji]

        print("[VisualEngine] initialized")
        if use_ocr:
            print("  [OK] OCR ready")
        if use_ml:
            print("  [OK] ML ready")

    def _init_ocr(self):
        """[emoji] OCR [emoji]"""
        try:
            import easyocr
            self.ocr_engine = easyocr.Reader(['ch_sim', 'en'])
            print("[VisualEngine] EasyOCR [emoji]")
        except ImportError:
            try:
                import pytesseract
                self.ocr_engine = "tesseract"
                print("[VisualEngine] Tesseract OCR [emoji]")
            except ImportError:
                print("[VisualEngine] [WARN] OCR not installed")
                self.use_ocr = False

    def _init_ml_model(self):
        """[emoji]"""
        try:
            # [emoji] YOLOv8 [emoji] DETR [emoji]
            # from ultralytics import YOLO
            # self.detection_model = YOLO("yolov8n-ui.pt")
            print("[VisualEngine] ML [emoji]")
        except Exception as e:
            print(f"[VisualEngine] [WARN] ML [emoji]: {e}")
            self.use_ml = False

    def detect_elements(self, screenshot: Union[np.ndarray, Image.Image]) -> List[UIElement]:
        """
        [emoji] UI [emoji]

        Args:
            screenshot: [emoji]numpy [emoji] PIL Image[emoji]

        Returns:
            UIElement [emoji]
        """
        # [emoji]
        if isinstance(screenshot, Image.Image):
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        else:
            img = screenshot.copy()

        elements = []

        # 1. [emoji] CV [emoji]
        cv_elements = self._detect_with_cv(img)
        elements.extend(cv_elements)

        # 2. [emoji] ML [emoji]
        if self.use_ml and self.detection_model:
            ml_elements = self._detect_with_ml(img)
            elements.extend(ml_elements)

        # 3. OCR [emoji]
        if self.use_ocr:
            self._enrich_with_ocr(img, elements)

        # 4. [emoji]
        elements = self._filter_and_sort(elements)

        return elements

    def _detect_with_cv(self, img: np.ndarray) -> List[UIElement]:
        """[emoji]"""
        elements = []
        height, width = img.shape[:2]

        # 1. [emoji]
        buttons = self._detect_buttons(img)
        elements.extend(buttons)

        # 2. [emoji]
        inputs = self._detect_inputs(img)
        elements.extend(inputs)

        # 3. [emoji]
        icons = self._detect_icons(img)
        elements.extend(icons)

        # 4. [emoji]
        texts = self._detect_text_regions(img)
        elements.extend(texts)

        return elements

    def _detect_buttons(self, img: np.ndarray) -> List[UIElement]:
        """[emoji]"""
        elements = []

        # [emoji]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # [emoji]
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # [emoji]
            if w < 40 or h < 20:
                continue

            # [emoji]
            ratio = w / h
            if ratio < 1.5 or ratio > 8:
                continue

            # [emoji]
            area = cv2.contourArea(cnt)
            rect_area = w * h
            if area / rect_area < 0.6:  # [emoji]
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
        """[emoji]"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # [emoji]
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        horizontal = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel)

        # [emoji]
        _, thresh = cv2.threshold(horizontal, 200, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # [emoji]
            if w > 100 and h < 40 and w / h > 3:
                element = UIElement(
                    type=ElementType.INPUT,
                    x=x + w // 2,
                    y=y + h // 2,
                    width=w,
                    height=h + 20,  # [emoji]
                    confidence=0.6,
                    description=f"Input field ({w}x{h})"
                )
                elements.append(element)

        return elements

    def _detect_icons(self, img: np.ndarray) -> List[UIElement]:
        """[emoji]"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # [emoji]
        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # [emoji] 16x16 [emoji] 48x48
            if 16 <= w <= 64 and 16 <= h <= 64:
                # [emoji]
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
        """[emoji] MSER[emoji]"""
        elements = []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # MSER [emoji]
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        for region in regions:
            x, y, w, h = cv2.boundingRect(region)

            # [emoji]
            if w < 20 or h < 10:
                continue

            # [emoji]
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
        """[emoji]"""
        # [emoji] YOLOv8 [emoji]
        # results = self.detection_model(img)
        # [emoji]...
        return []

    def _enrich_with_ocr(self, img: np.ndarray, elements: List[UIElement]):
        """[emoji] OCR [emoji]"""
        if self.ocr_engine is None:
            return

        # [emoji] OCR
        for element in elements:
            if element.type in [ElementType.BUTTON, ElementType.TEXT]:
                x1, y1, x2, y2 = element.bbox

                # [emoji]
                roi = img[y1:y2, x1:x2]
                if roi.size == 0:
                    continue

                # OCR [emoji]
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
        """[emoji]"""
        # [emoji]
        filtered = []
        for elem in elements:
            overlap = False
            for existing in filtered:
                # [emoji] IoU
                iou = self._calculate_iou(elem.bbox, existing.bbox)
                if iou > 0.5:  # [emoji] 50%
                    overlap = True
                    # [emoji]
                    if elem.confidence > existing.confidence:
                        filtered.remove(existing)
                        filtered.append(elem)
                    break
            if not overlap:
                filtered.append(elem)

        # [emoji]
        filtered.sort(key=lambda x: x.confidence, reverse=True)

        return filtered

    def _calculate_iou(self, box1: Tuple[int, ...], box2: Tuple[int, ...]) -> float:
        """[emoji] IoU"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2

        # [emoji]
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)

        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

        # [emoji]
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        union_area = box1_area + box2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0

    def locate_element(self, description: str, screenshot: Union[np.ndarray, Image.Image]) -> Optional[UIElement]:
        """
        [emoji]

        Args:
            description: [emoji]
                - "[emoji]"
                - "[emoji]"
                - "[emoji]'[emoji]'[emoji]"
            screenshot: [emoji]

        Returns:
            [emoji] None
        """
        elements = self.detect_elements(screenshot)

        # [emoji]
        description_lower = description.lower()

        candidates = []

        for elem in elements:
            score = 0.0

            # 1. [emoji]
            if elem.text and any(word in elem.text.lower() for word in description_lower.split()):
                score += 0.5

            # 2. [emoji]
            if "按钮" in description_lower and elem.type == ElementType.BUTTON:
                score += 0.2
            elif "输入框" in description_lower and elem.type == ElementType.INPUT:
                score += 0.2
            elif "图标" in description_lower and elem.type == ElementType.ICON:
                score += 0.2

            # 3. [emoji]
            img_height = screenshot.height if isinstance(screenshot, Image.Image) else screenshot.shape[0]
            img_width = screenshot.width if isinstance(screenshot, Image.Image) else screenshot.shape[1]

            if "顶部" in description_lower and elem.y < img_height * 0.3:
                score += 0.1
            elif "底部" in description_lower and elem.y > img_height * 0.7:
                score += 0.1
            elif "左侧" in description_lower and elem.x < img_width * 0.3:
                score += 0.1
            elif "右侧" in description_lower and elem.x > img_width * 0.7:
                score += 0.1

            # 4. [emoji]
            score += elem.confidence * 0.2

            if score > 0:
                candidates.append((elem, score))

        # [emoji]
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        return None

    def understand_scene(self, screenshot: Union[np.ndarray, Image.Image]) -> SceneContext:
        """
        [emoji]

        Args:
            screenshot: [emoji]

        Returns:
            SceneContext [emoji]
        """
        # [emoji]
        if isinstance(screenshot, Image.Image):
            img_array = np.array(screenshot)
            img_size = screenshot.size
        else:
            img_array = screenshot
            img_size = (screenshot.shape[1], screenshot.shape[0])

        # [emoji]
        elements = self.detect_elements(img_array)

        # [emoji]
        scene_type = self._classify_scene(elements)

        # [emoji]
        available_actions = self._infer_actions(elements)

        context = SceneContext(
            application="Unknown",  # [emoji]API[emoji]
            window_title="",  # [emoji]API[emoji]
            window_size=img_size,
            scene_type=scene_type,
            available_actions=available_actions,
            elements_count=len(elements)
        )

        return context

    def _classify_scene(self, elements: List[UIElement]) -> str:
        """[emoji]"""
        # [emoji]
        type_counts = {}
        for elem in elements:
            type_counts[elem.type] = type_counts.get(elem.type, 0) + 1

        # [emoji]
        if type_counts.get(ElementType.INPUT, 0) >= 2 and type_counts.get(ElementType.BUTTON, 0) >= 1:
            return "form"  # [emoji]

        if type_counts.get(ElementType.BUTTON, 0) > 5:
            return "dashboard"  # [emoji]

        if type_counts.get(ElementType.DIALOG, 0) > 0:
            return "dialog"  # [emoji]

        if len(elements) < 5:
            return "minimal"  # [emoji]

        return "general"

    def _infer_actions(self, elements: List[UIElement]) -> List[str]:
        """[emoji]"""
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

        return list(set(actions))  # [emoji]

    def visualize_detection(self, screenshot: Union[np.ndarray, Image.Image],
                           elements: List[UIElement],
                           highlight_element: Optional[UIElement] = None) -> Image.Image:
        """
        [emoji]

        Args:
            screenshot: [emoji]
            elements: [emoji]
            highlight_element: [emoji]

        Returns:
            [emoji]
        """
        if isinstance(screenshot, np.ndarray):
            img = Image.fromarray(cv2.cvtColor(screenshot, cv2.COLOR_BGR2RGB))
        else:
            img = screenshot.copy()

        draw = ImageDraw.Draw(img)

        # [emoji]
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

            # [emoji]
            if highlight_element and elem == highlight_element:
                color = "#FF0000"
                draw.rectangle([x1-2, y1-2, x2+2, y2+2], outline=color, width=3)
            else:
                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

            # [emoji]
            label = f"{elem.type.value}"
            if elem.text:
                label += f": {elem.text[:15]}"

            draw.text((x1, y1 - 15), label, fill=color)

        return img


# [emoji]
def quick_detect(screenshot_path: str) -> List[Dict]:
    """[emoji]"""
    engine = VisualEngine(use_ocr=False)
    img = Image.open(screenshot_path)
    elements = engine.detect_elements(img)
    return [e.to_dict() for e in elements]


def quick_locate(description: str, screenshot_path: str) -> Optional[Dict]:
    """[emoji]"""
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
        # [emoji]
        description = sys.argv[2]
        print(f"Looking for: {description}")
        element = engine.locate_element(description, img)
        if element:
            print(f"Found: {element.to_dict()}")
            # [emoji]
            vis_img = engine.visualize_detection(img, [element], highlight_element=element)
            vis_img.save("located.png")
            print("Saved visualization to located.png")
        else:
            print("Not found")
    else:
        # [emoji]
        print("Detecting elements...")
        elements = engine.detect_elements(img)
        print(f"Found {len(elements)} elements:")
        for i, elem in enumerate(elements[:20]):  # [emoji]20[emoji]
            print(f"  {i+1}. {elem}")

        # [emoji]
        vis_img = engine.visualize_detection(img, elements)
        vis_img.save("detected.png")
        print("Saved visualization to detected.png")
