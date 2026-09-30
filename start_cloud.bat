@echo off
chcp 65001 >nul
:: ── FairyReport 云端服务启动脚本 (Windows Server) ──

if "%PORT%"=="" set PORT=8001
if "%HOST%"=="" set HOST=0.0.0.0
if "%ENGINE_DATA_DIR%"=="" set ENGINE_DATA_DIR=%~dp0data

echo ==================================================
echo   FairyReport 云端服务启动中...
echo   主机: %HOST%
echo   端口: %PORT%
echo   数据目录: %ENGINE_DATA_DIR%
echo ==================================================

python -m engine.app.main --host %HOST% --port %PORT%
pause
