# GodHand CLI v3.0

简单、可靠、直接可用的命令行GUI自动化工具。

## 快速开始

### 方式1: 交互式CLI
```bash
python main_cli.py
```

### 方式2: 直接执行命令
```bash
python run.py "打开记事本 然后输入Hello World"
```

## 支持的指令

### 应用程序
- `打开记事本` - 打开记事本
- `打开画图` - 打开画图
- `打开计算器` - 打开计算器
- `打开浏览器` - 打开Edge浏览器

### 复合指令
- `打开画图 然后画个圆` - 打开应用后执行操作
- `打开计算器 然后输入123` - 多步骤自动化

### 鼠标操作
- `点击 500, 500` - 点击指定坐标
- `双击` - 双击鼠标
- `右键` - 右键点击
- `移动 100, 200` - 移动鼠标

### 键盘操作
- `输入 Hello World` - 输入文字
- `按 enter` - 按键
- `快捷键 ctrl+s` - 快捷键组合

### 搜索和网页
- `搜索 Python教程` - 浏览器搜索
- `打开 https://www.bing.com` - 打开网页

### 文件操作
- `创建文件 test.txt` - 创建文件
- `删除文件 test.txt` - 删除文件
- `创建文件夹 myfolder` - 创建目录

### 其他
- `等待 3` - 等待3秒
- `截图` - 屏幕截图

## 使用示例

```bash
# 打开记事本并输入内容
python run.py "打开记事本 然后输入Hello World"

# 打开画图并尝试画圆
python run.py "打开画图 然后画个圆"

# 打开浏览器搜索
python run.py "搜索 Python GUI自动化"

# 创建项目目录
python run.py "创建文件夹 my_project"

# 屏幕截图
python run.py "截图"
```

## 安装依赖

```bash
pip install pyautogui pyperclip
```

## 注意事项

- 运行前请确保屏幕没有被其他窗口遮挡
- 鼠标移到屏幕左上角会触发安全停止
- 复合指令会自动等待2秒让应用启动
