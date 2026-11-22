#!/bin/sh
set -eu
export PYINSTALLER_CONFIG_DIR="$(pwd)/.pyinstaller-cache"
python3 -m pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm --clean HouseCheckAI.spec
echo "Build complete: dist/HouseCheckAI.app"
