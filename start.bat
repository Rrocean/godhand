@echo off
chcp 65001 >nul
echo ==========================================
echo GodHand 智能命令与GUI自动化系统
echo ==========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [提示] 首次运行，安装依赖...
    pip install -r requirements.txt
)

:: 检查配置
echo [2/3] 检查配置...
if not exist config.json (
    echo [警告] 未找到config.json，请配置API密钥
    echo 复制 config.json.example 到 config.json 并填写API密钥
)

:: 启动服务
echo [3/3] 启动服务...
echo.
echo ==========================================
echo 服务启动中，请稍候...
echo 访问地址: http://127.0.0.1:8000
echo 按 Ctrl+C 停止服务
echo ==========================================
echo.

python main.py

pause
