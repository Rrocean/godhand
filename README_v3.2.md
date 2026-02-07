# GodHand CLI v3.2 - 专业版

**GodHand** 是一个功能强大的 Windows GUI 自动化工具，支持自然语言指令、视觉识别、录制回放、任务调度等高级功能。

---

## 安装

```bash
# 克隆仓库
git clone https://github.com/Rrocean/godhand.git
cd godhand

# 安装依赖
pip install pyautogui pyperclip pygetwindow opencv-python
```

---

## 快速开始

### 方式1: 交互式 CLI
```bash
python main_cli.py
```

### 方式2: 直接执行命令
```bash
python run.py "打开记事本 然后输入Hello World"
```

### 方式3: 执行脚本
```bash
python run.py --script demo_calculator.txt
```

---

## 基础功能

### 应用程序控制
```bash
打开 记事本        # 打开记事本
打开 计算器        # 打开计算器
打开 画图          # 打开画图
打开 浏览器        # 打开 Edge
关闭 计算器        # 关闭应用
```

### 复合指令（多步骤）
支持多个"然后"串联：
```bash
打开记事本 然后输入Hello World 然后按回车
打开计算器 然后输入1 然后按加号 然后输入1 然后按等于
打开画图 然后画个圆
```

### 鼠标操作
```bash
点击 500, 500      # 点击指定坐标
双击               # 双击当前位置
右键               # 右键点击
移动 100, 200      # 移动鼠标
随机点击           # 随机位置点击
```

### 键盘操作
```bash
输入 Hello World   # 输入文字
按 enter           # 按单个键
快捷键 ctrl+s      # 快捷键组合
```

#### 支持的中文按键
| 中文 | 实际按键 |
|-----|---------|
| 加号/加 | + |
| 减号/减 | - |
| 乘号/乘 | * |
| 除号/除 | / |
| 等于/等 | = |
| 小数点/点 | . |
| 回车 | enter |
| 空格 | space |
| 退格 | backspace |
| 删除 | delete |
| 上/下/左/右 | 方向键 |

### 剪贴板操作
```bash
复制               # Ctrl+C
粘贴               # Ctrl+V
全选               # Ctrl+A
```

### 文件和目录
```bash
创建文件 test.txt              # 创建空文件
删除文件 test.txt              # 删除文件
创建文件夹 my_folder           # 创建目录
```

---

## 高级功能

### 窗口管理
```bash
列出窗口            # 显示所有窗口标题
激活 记事本        # 激活指定窗口
最小化              # 最小化当前窗口
最大化              # 最大化当前窗口
```

### 视觉识别
```bash
点击图片 button.png          # 找图并点击
等待图片 loading.png         # 等待图片出现（超时30秒）
```

### 系统信息
```bash
获取鼠标位置                 # 显示当前坐标
获取屏幕尺寸                 # 显示分辨率
获取颜色 500, 500           # 获取像素颜色
```

### 提示系统
```bash
蜂鸣                         # 播放提示音
通知 任务完成               # 显示系统通知弹窗
```

### 循环执行
```bash
循环 3次 截图              # 重复执行指令
循环 5次 点击 100, 100
```

---

## 录制与回放

### 交互式录制
```bash
$ python main_cli.py

GodHand> record              # 开始录制
[录制]> 打开记事本           # 输入命令
[录制]> 输入 Hello World
[录制]> stop                 # 停止并保存

GodHand> play                # 回放录制内容
```

### 命令行录制
```bash
# 录制会话
python run.py --record my_session.json

# 回放会话
python run.py --play my_session.json

# 指定间隔回放（每步等待2秒）
python run.py --play my_session.json --delay 2.0
```

---

## 脚本执行

创建脚本文件 `my_script.txt`:
```text
# 这是一个注释
打开记事本
等待 2
输入 这是自动化测试
按 回车
截图
```

执行脚本:
```bash
python run.py --script my_script.txt
```

---

## 配置管理

### 查看配置
```bash
GodHand> config
```

### 设置配置项
```bash
GodHand> config screenshot_dir ./my_screenshots
GodHand> config click_delay 0.2
```

### 配置文件 (godhand_config.json)
```json
{
  "click_delay": 0.1,
  "type_interval": 0.01,
  "move_duration": 0.5,
  "screenshot_dir": "./screenshots",
  "log_enabled": true,
  "log_file": "godhand.log",
  "aliases": {
    "calc": "计算器",
    "notepad": "记事本"
  }
}
```

---

## 定时任务

### 添加定时任务
```bash
GodHand> schedule 14:30 打开记事本
GodHand> schedule 15:00 截图
```

### 启动/停止调度器
```bash
GodHand> scheduler start    # 启动调度器
GodHand> scheduler stop     # 停止调度器
```

---

## 实际示例

### 示例1: 自动计算器
```bash
python run.py "打开计算器 然后输入123 然后按加号 然后输入456 然后按等于"
```

### 示例2: 窗口操作
```bash
python run.py "打开记事本 然后输入Hello 然后列出窗口 然后激活 记事本 然后最大化"
```

### 示例3: 带通知的自动化
```bash
python run.py "打开画图 然后等待 2 然后画个圆 然后截图 然后蜂鸣 然后通知 任务完成"
```

### 示例4: 获取屏幕信息
```bash
python run.py "获取屏幕尺寸 然后获取鼠标位置 然后获取颜色 500, 500"
```

---

## Python API 使用

```python
from main_cli import SimpleParser, ActionExecutor, Config, Logger

# 创建组件
config = Config()
logger = Logger()
parser = SimpleParser()
executor = ActionExecutor()

# 配置组件
executor.parser = parser
executor.config = config

# 解析并执行命令
actions = parser.parse("打开记事本 然后输入Hello")
for action in actions:
    result = executor.execute(action)
    print(result)
```

---

## 安全提示

- 鼠标移到屏幕左上角会触发 pyautogui 的安全停止
- 执行前确保目标窗口可见
- 定时任务会阻塞主线程，建议在后台运行

---

## 故障排除

### 中文显示乱码
```powershell
chcp 65001  # 设置 UTF-8 编码
```

### 图片识别失败
确保安装了 opencv:
```bash
pip install opencv-python
```

### 窗口操作失败
确保安装了 pygetwindow:
```bash
pip install pygetwindow
```

### 权限问题
某些应用需要管理员权限才能自动化。

---

## 项目结构

```
godhand/
├── main_cli.py              # 交互式 CLI 主程序
├── run.py                   # 命令行运行工具
├── test_cli.py              # 测试脚本
├── CLI_README.md            # 快速入门
├── README_GodHand_CLI.md    # 完整文档
├── README_v3.2.md           # 本文件
├── example_script.txt       # 基础示例
├── demo_calculator.txt      # 计算器演示
├── demo_advanced.txt        # 高级功能演示
└── godhand_config.json      # 配置文件（自动生成）
```

---

## 更新日志

### v3.2 (2025-02-07)
- 窗口管理系统（列出/激活/最小化/最大化）
- 视觉识别增强（等待图片）
- 系统信息获取（屏幕尺寸/像素颜色）
- 提示系统（蜂鸣/通知）
- 配置管理系统
- 日志系统
- 任务调度器
- 智能重试机制

### v3.1
- 多链复合指令
- 中文按键映射
- 录制与回放系统
- 脚本批量执行
- 循环执行功能

### v3.0
- 基础 GUI 自动化
- 应用打开/关闭
- 鼠标键盘操作
- 文件操作
- 搜索和网页

---

## 许可证

MIT License

---

**GitHub:** https://github.com/Rrocean/godhand

**作者:** GodHand Team
