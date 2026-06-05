@echo off
REM 通过本地代理推送 GitHub（HTTPS 443 直连不稳定时使用）
chcp 65001 >nul
cd /d "%~dp0"

set PROXY=http://127.0.0.1:7897

echo 正在推送到 GitHub（代理 %PROXY%）...
git -c http.https://github.com.proxy=%PROXY% -c https.https://github.com.proxy=%PROXY% push origin main
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo.
    echo [失败] 请确认：1^) 代理软件已开启  2^) 端口是否为 7897
    echo 若端口不同，编辑本文件中的 PROXY 变量后重试。
    pause
    exit /b %EXIT_CODE%
)

echo.
echo [完成] 已推送到 https://github.com/XiaoYuanKLQUEEN/paper-research-system
timeout /t 3 >nul
exit /b 0
