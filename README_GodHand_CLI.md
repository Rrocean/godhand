# GodHand CLI v3.1 - 完整使用指南

简单、强大、可靠的 Windows GUI 自动化工具。

## 快速开始

```bash
# 方式1: 交互式 CLI
python main_cli.py

# 方式2: 直接执行命令
python run.py "打开记事本 然后输入Hello World"

# 方式3: 执行脚本
python run.py --script demo_calculator.txt
```

## 安装依赖

```bash
pip install pyautogui pyperclip opencv-python
```

## 基础指令

### 应用程序控制
```bash
打开 记事本        # 打开记事本
打开 计算器        # 打开计算器
打开 画图          # 打开画图
打开 浏览器        # 打开 Edge
关闭 计算器        # 关闭应用
```

### 复合指令（多步骤）
```bash
# 支持多个\"然后\"串联
打开记事本 然后输入Hello World 然后按回车
打开计算器 然后输入1 然后按加号 然后输入1 然后按等于
打开画图 然后画个圆
```

### 鼠标操作
```bash
点击 500, 500      # 点击坐标 (x, y)
双击               # 双击当前位置
右键               # 右键点击
移动 100, 200      # 移动鼠标到 (x, y)
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

### 搜索和网页
```bash
搜索 Python教程               # 浏览器搜索
打开 https://www.bing.com     # 打开网址
```

### 高级功能
```bash
截图                           # 屏幕截图
获取鼠标位置                   # 显示当前坐标
点击图片 button.png           # 图片识别点击（需要 opencv）
循环 3次 截图                 # 重复执行
等待 5                         # 等待5秒
```

## 录制与回放

### 交互式录制
```bash
$ python main_cli.py

GodHand> record           # 开始录制
[录制]> 打开记事本         # 输入命令
[录制]> 输入 Hello World
[录制]> stop              # 停止并保存

GodHand> play             # 回放录制内容
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

## 实际示例

### 示例1: 自动记事本编辑
```bash
python run.py "打开记事本 然后输入Hello World 然后按回车 然后输入这是自动化测试"
```

### 示例2: 计算器计算
```bash
python run.py "打开计算器 然后输入123 然后按加号 然后输入456 然后按等于"
```

### 示例3: 浏览器搜索
```bash
python run.py "搜索 Python GUI自动化教程"
```

### 示例4: 批量截图
```bash
python run.py "循环 5次 截图"
```

## 安全提示

- 鼠标移到屏幕左上角会触发 pyautogui 的安全停止
- 执行前确保目标窗口可见
- 等待时间可以调整以适应不同电脑速度

## 故障排除

### 中文显示乱码
在 Windows PowerShell 中执行:
```powershell
chcp 65001  # 设置 UTF-8 编码
```

### 图片识别失败
确保安装了 opencv:
```bash
pip install opencv-python
```

### 权限问题
某些应用需要管理员权限才能自动化。

## 进阶用法

### 创建复杂的自动化脚本

```text
# login_script.txt - 自动登录示例
打开 浏览器
等待 3
打开 https://example.com/login
等待 2
点击 500, 300        # 用户名输入框
输入 myusername
按 Tab               # 切换到密码框
输入 mypassword
点击 500, 450        # 登录按钮
等待 3
截图                 # 保存登录结果
```

### 在 Python 代码中使用

```python
from main_cli import SimpleParser, ActionExecutor

# 创建解析器和执行器
parser = SimpleParser()
executor = ActionExecutor()

# 解析命令
actions = parser.parse("打开记事本 然后输入Hello")

# 执行
for action in actions:
    result = executor.execute(action)
    print(result)
```

## 项目结构

```
godhand/
├── main_cli.py          # 交互式 CLI 主程序
├── run.py               # 命令行运行工具
├── test_cli.py          # 测试脚本
├── CLI_README.md        # 快速入门
├── README_GodHand_CLI.md # 完整文档
├── example_script.txt   # 基础示例
└── demo_calculator.txt  # 计算器演示
```

## 更新日志

### v3.1
- 支持多链复合指令
- 中文按键映射
- 录制与回放系统
- 脚本批量执行
- 循环执行功能
- 图片识别点击

### v3.0
- 基础 GUI 自动化
- 应用打开/关闭
- 鼠标键盘操作
- 文件操作
- 搜索和网页

## 许可证

MIT License

---

**GitHub:** https://github.com/Rrocean/godhand
