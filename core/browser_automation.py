#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GodHand Browser Automation - 浏览器自动化模块
实现类似Selenium的浏览器控制功能
支持Chrome/Edge浏览器自动化
"""

import os
import sys
import time
from typing import Optional, List, Dict
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 尝试导入selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("[WARN] Selenium未安装，浏览器功能不可用")
    print("  安装: pip install selenium webdriver-manager")


@dataclass
class BrowserSession:
    """浏览器会话"""
    driver: Optional[object] = None
    browser_type: str = "chrome"
    headless: bool = False
    current_url: str = ""
    title: str = ""


class BrowserController:
    """浏览器控制器 - 类似Clawdbot的浏览器控制功能"""

    def __init__(self):
        self.session: Optional[BrowserSession] = None
        self.history: List[str] = []
        self.cookies: Dict = {}

    def launch(self, browser_type: str = "chrome", headless: bool = False) -> bool:
        """启动浏览器"""
        if not HAS_SELENIUM:
            print("[ERROR] Selenium未安装")
            return False

        try:
            if browser_type == "chrome":
                options = ChromeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")

                # 尝试自动下载driver
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options)
                except:
                    driver = webdriver.Chrome(options=options)

            elif browser_type == "edge":
                options = EdgeOptions()
                if headless:
                    options.add_argument("--headless")
                options.add_argument("--no-sandbox")

                try:
                    from webdriver_manager.microsoft import EdgeChromiumDriverManager
                    driver = webdriver.Edge(service=webdriver.edge.service.Service(EdgeChromiumDriverManager().install()), options=options)
                except:
                    driver = webdriver.Edge(options=options)
            else:
                print(f"[ERROR] 不支持的浏览器类型: {browser_type}")
                return False

            self.session = BrowserSession(
                driver=driver,
                browser_type=browser_type,
                headless=headless
            )

            print(f"[Browser] {browser_type} 浏览器已启动")
            return True

        except Exception as e:
            print(f"[ERROR] 浏览器启动失败: {e}")
            return False

    def navigate(self, url: str) -> bool:
        """导航到URL"""
        if not self.session or not self.session.driver:
            print("[ERROR] 浏览器未启动")
            return False

        try:
            self.session.driver.get(url)
            self.session.current_url = self.session.driver.current_url
            self.session.title = self.session.driver.title
            self.history.append(url)

            print(f"[Browser] 导航到: {url}")
            print(f"[Browser] 页面标题: {self.session.title}")
            return True
        except Exception as e:
            print(f"[ERROR] 导航失败: {e}")
            return False

    def click(self, selector: str, by: str = "css") -> bool:
        """点击元素"""
        if not self.session or not self.session.driver:
            return False

        try:
            by_type = self._get_by_type(by)
            element = self.session.driver.find_element(by_type, selector)
            element.click()
            print(f"[Browser] 点击元素: {selector}")
            return True
        except NoSuchElementException:
            print(f"[ERROR] 元素未找到: {selector}")
            return False
        except Exception as e:
            print(f"[ERROR] 点击失败: {e}")
            return False

    def type_text(self, selector: str, text: str, clear_first: bool = True) -> bool:
        """输入文本"""
        if not self.session or not self.session.driver:
            return False

        try:
            element = self.session.driver.find_element(By.CSS_SELECTOR, selector)
            if clear_first:
                element.clear()
            element.send_keys(text)
            print(f"[Browser] 在 {selector} 输入: {text}")
            return True
        except Exception as e:
            print(f"[ERROR] 输入失败: {e}")
            return False

    def submit(self, selector: str) -> bool:
        """提交表单"""
        if not self.session or not self.session.driver:
            return False

        try:
            element = self.session.driver.find_element(By.CSS_SELECTOR, selector)
            element.submit()
            print(f"[Browser] 提交表单: {selector}")
            return True
        except Exception as e:
            print(f"[ERROR] 提交失败: {e}")
            return False

    def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """等待元素出现"""
        if not self.session or not self.session.driver:
            return False

        try:
            WebDriverWait(self.session.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            print(f"[Browser] 元素已出现: {selector}")
            return True
        except TimeoutException:
            print(f"[ERROR] 等待元素超时: {selector}")
            return False

    def screenshot(self, filename: str = None) -> str:
        """浏览器截图"""
        if not self.session or not self.session.driver:
            return ""

        try:
            if not filename:
                from datetime import datetime
                filename = f"browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            self.session.driver.save_screenshot(filename)
            print(f"[Browser] 截图保存: {filename}")
            return filename
        except Exception as e:
            print(f"[ERROR] 截图失败: {e}")
            return ""

    def scroll(self, direction: str = "down", amount: int = 500) -> bool:
        """滚动页面"""
        if not self.session or not self.session.driver:
            return False

        try:
            if direction == "down":
                self.session.driver.execute_script(f"window.scrollBy(0, {amount});")
            elif direction == "up":
                self.session.driver.execute_script(f"window.scrollBy(0, -{amount});")
            elif direction == "bottom":
                self.session.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif direction == "top":
                self.session.driver.execute_script("window.scrollTo(0, 0);")

            print(f"[Browser] 页面滚动: {direction}")
            return True
        except Exception as e:
            print(f"[ERROR] 滚动失败: {e}")
            return False

    def get_text(self, selector: str) -> str:
        """获取元素文本"""
        if not self.session or not self.session.driver:
            return ""

        try:
            element = self.session.driver.find_element(By.CSS_SELECTOR, selector)
            text = element.text
            print(f"[Browser] 获取文本: {text[:50]}...")
            return text
        except Exception as e:
            print(f"[ERROR] 获取文本失败: {e}")
            return ""

    def get_all_links(self) -> List[Dict]:
        """获取所有链接"""
        if not self.session or not self.session.driver:
            return []

        try:
            links = self.session.driver.find_elements(By.TAG_NAME, "a")
            result = []
            for link in links[:20]:  # 限制数量
                href = link.get_attribute("href")
                text = link.text
                if href and text:
                    result.append({"text": text, "url": href})
            return result
        except Exception as e:
            print(f"[ERROR] 获取链接失败: {e}")
            return []

    def execute_script(self, script: str) -> any:
        """执行JavaScript"""
        if not self.session or not self.session.driver:
            return None

        try:
            result = self.session.driver.execute_script(script)
            return result
        except Exception as e:
            print(f"[ERROR] 执行脚本失败: {e}")
            return None

    def close(self):
        """关闭浏览器"""
        if self.session and self.session.driver:
            self.session.driver.quit()
            print("[Browser] 浏览器已关闭")
            self.session = None

    def _get_by_type(self, by: str):
        """获取定位类型"""
        by_map = {
            "css": By.CSS_SELECTOR,
            "id": By.ID,
            "name": By.NAME,
            "xpath": By.XPATH,
            "class": By.CLASS_NAME,
            "tag": By.TAG_NAME,
        }
        return by_map.get(by, By.CSS_SELECTOR)


class BrowserAutomationCLI:
    """浏览器自动化CLI接口"""

    def __init__(self):
        self.controller = BrowserController()

    def execute_command(self, command: str, **kwargs) -> bool:
        """执行浏览器命令"""
        cmd = command.lower()

        if cmd == "launch" or cmd == "启动浏览器":
            browser = kwargs.get("browser", "chrome")
            headless = kwargs.get("headless", False)
            return self.controller.launch(browser, headless)

        elif cmd == "navigate" or cmd == "访问":
            url = kwargs.get("url", "")
            return self.controller.navigate(url)

        elif cmd == "click" or cmd == "点击":
            selector = kwargs.get("selector", "")
            return self.controller.click(selector)

        elif cmd == "type" or cmd == "输入":
            selector = kwargs.get("selector", "")
            text = kwargs.get("text", "")
            return self.controller.type_text(selector, text)

        elif cmd == "screenshot" or cmd == "截图":
            return bool(self.controller.screenshot())

        elif cmd == "scroll" or cmd == "滚动":
            direction = kwargs.get("direction", "down")
            return self.controller.scroll(direction)

        elif cmd == "close" or cmd == "关闭浏览器":
            self.controller.close()
            return True

        else:
            print(f"[ERROR] 未知命令: {command}")
            return False


# 便捷函数
def create_browser() -> BrowserController:
    """创建浏览器控制器"""
    return BrowserController()


if __name__ == "__main__":
    if not HAS_SELENIUM:
        print("请先安装selenium: pip install selenium webdriver-manager")
        sys.exit(1)

    # 测试
    browser = create_browser()

    if browser.launch(headless=False):
        browser.navigate("https://www.bing.com")
        time.sleep(2)
        browser.screenshot("test_browser.png")

        # 搜索
        browser.type_text("#sb_form_q", "Python automation")
        browser.submit("#sb_form_q")
        time.sleep(3)
        browser.screenshot("test_search.png")

        browser.close()
