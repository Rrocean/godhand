# 🤖 GodHand v4.0 "World Domination" - 世界级AI自动化平台

> **让全世界震惊的AI自动化产品** | 对标Clawdbot的自托管智能助手

---

## 🌍 产品愿景

GodHand 不仅仅是一个GUI自动化工具，它是一个**全能的AI自动化平台**：

- 🧠 **AI大脑** - 自然语言理解、智能任务规划、自主决策
- 🎮 **GUI控制** - 完整的鼠标键盘自动化
- 🌐 **浏览器自动化** - 像人类一样浏览网页
- 💾 **持久记忆** - 学习你的习惯，越用越聪明
- 🖥️ **Web界面** - 现代化的控制面板
- 📱 **多平台** - API接口，随处可用

---

## ✨ 核心特性

### 1. 🧠 AI智能引擎
```bash
# 自然语言指令 - GodHand理解你的意图
"帮我打开计算器算一下123+456，然后截图发到微信"

# AI自动规划:
# 1. 打开计算器
# 2. 输入123
# 3. 按加号
# 4. 输入456
# 5. 按等于
# 6. 截图
# 7. 打开微信
# 8. 发送图片
```

### 2. 🌐 浏览器自动化
```bash
# 启动浏览器
启动浏览器
访问 https://www.bing.com
在搜索框输入 "Python教程"
点击搜索按钮
滚动页面
截图
```

### 3. 💾 持久化记忆
- 记住你的常用操作
- 学习失败模式，自动优化
- 跨会话保持上下文

### 4. 🖥️ Web控制面板
```bash
python godhand.py web
# 然后访问 http://localhost:5000
```

现代化Web界面:
- 📊 实时执行监控
- 📝 可视化日志
- 🎮 一键快捷操作
- 🌐 浏览器远程控制

### 5. 📹 录制回放
```bash
# 录制你的操作
record my_task.json
> 打开记事本
> 输入Hello World
> 截图
> stop

# 随时回放
play my_task.json
```

---

## 🚀 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/Rrocean/godhand.git
cd godhand

# 安装依赖
pip install -r requirements.txt
# requirements.txt:
#   pyautogui
#   pyperclip
#   pygetwindow
#   opencv-python
#   selenium
#   webdriver-manager
#   flask
#   flask-socketio
```

### 使用方式

#### 方式1: 交互式CLI
```bash
python godhand.py cli
```

#### 方式2: Web界面
```bash
python godhand.py web
# 打开浏览器访问 http://localhost:5000
```

#### 方式3: 直接执行命令
```bash
python godhand.py cmd "打开记事本 然后输入Hello World"
```

#### 方式4: 执行脚本
```bash
python godhand.py script my_script.txt
```

---

## 📚 完整功能列表

### GUI自动化
| 功能 | 命令示例 |
|-----|---------|
| 打开应用 | `打开 记事本` |
| 点击 | `点击 500, 500` |
| 输入 | `输入 Hello World` |
| 按键 | `按 回车` / `按 加号` |
| 快捷键 | `快捷键 ctrl+s` |
| 截图 | `截图` |
| 窗口管理 | `列出窗口` / `激活 记事本` / `最大化` |

### 浏览器自动化
| 功能 | 命令示例 |
|-----|---------|
| 启动浏览器 | `启动浏览器` |
| 访问网页 | `访问 https://bing.com` |
| 点击元素 | `点击元素 #search-box` |
| 输入文本 | `在搜索框输入 Python` |
| 滚动 | `滚动 向下` |
| 网页截图 | `网页截图` |

### AI功能
| 功能 | 说明 |
|-----|------|
| 意图分析 | 自动理解用户意图 |
| 任务规划 | 将复杂任务分解为步骤 |
| 错误恢复 | 失败后自动重试 |
| 学习优化 | 从执行中学习 |
| 记忆检索 | 利用历史记忆辅助决策 |

---

## 💡 高级示例

### 示例1: 自动化填写表单
```text
启动浏览器
访问 https://example.com/form
等待 2
在 #name 输入 张三
在 #email 输入 zhangsan@example.com
在 #phone 输入 13800138000
点击 #submit
等待 3
网页截图
关闭浏览器
```

### 示例2: 批量数据处理
```text
循环 10次
    点击 100, 200
    按 复制
    点击 300, 400
    按 粘贴
    按 回车
    等待 1
结束
```

### 示例3: 智能助手对话
```bash
$ python godhand.py cli

GodHand> 帮我准备今天的日报
[🧠 AI分析] 用户需要准备日报，可能需要:
  - 打开文档软件
  - 获取今天的屏幕记录
  - 整理信息

[📋 建议执行计划]
1. 打开记事本
2. 输入日报模板
3. 截图今日工作
4. 保存文件

是否执行? (y/n): y
[⚡ 执行中...]
✓ 已打开记事本
✓ 已输入模板
✓ 已截图
✓ 已保存
```

---

## 🏗️ 架构设计

```
GodHand v4.0
├── 🎮 GUI Layer (pyautogui)
│   ├── Mouse/Keyboard control
│   ├── Window management
│   └── Screen capture
│
├── 🌐 Browser Layer (selenium)
│   ├── Chrome/Edge control
│   ├── Element interaction
│   └── JavaScript execution
│
├── 🧠 AI Engine
│   ├── AgentEngine (决策)
│   ├── TaskPlanner (规划)
│   ├── MemorySystem (记忆)
│   └── IntentAnalyzer (理解)
│
├── 🖥️ Interface Layer
│   ├── CLI (命令行)
│   ├── Web UI (网页)
│   └── API (REST)
│
└── 💾 Storage
    ├── Config (配置)
    ├── Memory (记忆)
    └── Logs (日志)
```

---

## 🎯 路线图

### v4.0 (当前)
- ✅ AI决策引擎
- ✅ 浏览器自动化
- ✅ Web界面
- ✅ 记忆系统

### v4.1 (计划中)
- 🔄 语音控制
- 🔄 图像识别增强
- 🔄 移动端支持

### v4.2 (规划中)
- 📋 插件市场
- 📋 云同步
- 📋 团队协作

### v5.0 (愿景)
- 🚀 完全自主AI代理
- 🚀 跨设备协同
- 🚀 企业级部署

---

## 🤝 对比Clawdbot

| 特性 | GodHand v4.0 | Clawdbot |
|-----|-------------|----------|
| 自托管 | ✅ | ✅ |
| GUI自动化 | ✅ ✅ ✅ | ⚠️ 有限 |
| 浏览器控制 | ✅ ✅ | ✅ |
| AI决策 | ✅ ✅ | ✅ ✅ |
| Web界面 | ✅ ✅ | ✅ |
| 记忆系统 | ✅ ✅ | ✅ ✅ |
| 多平台消息 | 🔄 开发中 | ✅ |
| 开源 | ✅ | ✅ |
| 中文支持 | ✅ ✅ ✅ | ⚠️ 有限 |

**GodHand优势**: 更强的GUI自动化能力、更完善的中文支持、更简单的部署

---

## 📄 许可证

MIT License - 自由使用，欢迎贡献！

---

## 🙏 致谢

- 灵感来自 [Clawdbot](https://github.com/timolins/clawdbot)
- 基于 [PyAutoGUI](https://pyautogui.readthedocs.io/)
- Web界面使用 [Flask](https://flask.palletsprojects.com/)

---

**🌍 让自动化改变世界**

**GitHub**: https://github.com/Rrocean/godhand

**Made with ❤️ by GodHand Team**
