@echo off
REM 双击运行：抓取今日论文/工具/快讯 → 去重 → 生成 Obsidian 领域雷达
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   推送今日领域雷达到 Obsidian
echo ========================================
echo.

python push_today_radar.py
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% NEQ 0 (
    echo [失败] 退出码 %EXIT_CODE%，请查看上方日志。
    pause
    exit /b %EXIT_CODE%
)

echo [完成] 可在 Obsidian 10_Daily 中查看今日领域雷达。
timeout /t 3 >nul
exit /b 0
