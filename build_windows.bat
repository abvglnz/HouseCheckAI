@echo off
setlocal
set PYINSTALLER_CONFIG_DIR=%CD%\.pyinstaller-cache
py -m pip install -r requirements-build.txt
py -m PyInstaller --noconfirm --clean HouseCheckAI.spec
echo.
echo Build complete: dist\HouseCheckAI\HouseCheckAI.exe
pause
