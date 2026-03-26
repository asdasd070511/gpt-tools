#!/bin/bash
set -e

REPO="https://github.com/asdasd070511/gpt-tools.git"
DIR="$HOME/gpt-tools"
WORKERS=30

echo "[1/4] 安装系统依赖..."
apt update -y && apt install -y python3 python3-pip python3-venv git curl screen > /dev/null 2>&1

echo "[2/4] 拉取代码..."
if [ -d "$DIR" ]; then
    cd "$DIR" && git pull
else
    git clone "$REPO" "$DIR" && cd "$DIR"
fi

echo "[3/4] 建立虚拟环境并安装依赖..."
if [ ! -d "$DIR/venv" ]; then
    python3 -m venv "$DIR/venv"
fi
"$DIR/venv/bin/pip" install -q curl_cffi

echo "[4/4] 用 screen 启动 gpt.py (workers=$WORKERS)..."
mkdir -p "$DIR/tokens"
cd "$DIR"
screen -dmS gpt "$DIR/venv/bin/python" gpt.py --workers "$WORKERS"

echo ""
echo "=== 部署完成 ==="
echo "查看日志: screen -r gpt"
echo "脱离终端: Ctrl+A 再按 D"
echo "重启:     screen -XS gpt quit && screen -dmS gpt $DIR/venv/bin/python gpt.py --workers $WORKERS"
