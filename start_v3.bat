@echo off
chcp 65001 >nul
title GodHand v3.0 - 世界级的智能自动化系统

echo ========================================
echo  🖐️ GodHand v3.0
echo  世界级的智能命令与GUI自动化系统
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

echo ✅ Python 已安装

:: 检查依赖
echo.
echo 📦 检查依赖...
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo ⚠️ 依赖未安装，正在安装...
    pip install -r requirements.txt
)

echo ✅ 依赖已就绪

:: 检查配置
if not exist "config.json" (
    echo.
    echo ⚠️ 配置文件不存在，创建默认配置...
    echo {> config.json
    echo   "provider": "google",>> config.json
    echo   "google": {>> config.json
    echo     "api_key": "YOUR_API_KEY_HERE",>> config.json
    echo     "model": "gemini-2.0-flash">> config.json
    echo   }>> config.json
    echo }>> config.json
)

echo.
echo 🚀 启动 GodHand v3.0...
echo 🌐 访问地址: http://127.0.0.1:8000
echo 📚 API 文档: http://127.0.0.1:8000/docs
echo.
echo ✨ 新特性:
echo    • VisualEngine - 视觉理解引擎
echo    • TaskPlanner - 智能任务规划
echo    • Multi-Modal - 多模态AI决策
echo.
echo ========================================

python main_v3.py

pause
