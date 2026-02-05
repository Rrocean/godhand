@echo off
chcp 65001 >nul
title GodHand Pro v3.0

echo ============================================
echo 🖐️ GodHand Pro v3.0
echo 统一智能命令与GUI自动化系统
echo ============================================
echo.

:: Check Python
echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已安装

:: Check dependencies
echo.
echo [2/3] 检查依赖...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [警告] 缺少依赖，正在安装...
    pip install -r requirements.txt
)
echo [OK] 依赖检查完成

:: Start server
echo.
echo [3/3] 启动 GodHand Pro...
echo ============================================
echo.
echo 访问地址:
echo   - Web界面: http://127.0.0.1:8000
echo   - API文档: http://127.0.0.1:8000/docs
echo   - 健康检查: http://127.0.0.1:8000/api/health
echo.
echo 按 Ctrl+C 停止服务
echo ============================================
echo.

python main_v2.py

pause
