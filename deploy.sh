#!/bin/bash
set -e

REPO="https://github.com/asdasd070511/gpt-tools.git"
DIR="$HOME/gpt-tools"
WORKERS=30

echo "[1/5] 安装系统依赖..."
apt update -y && apt install -y python3 python3-pip python3-venv git curl > /dev/null 2>&1

echo "[2/5] 安装 Node.js + pm2..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt install -y nodejs > /dev/null 2>&1
fi
npm install -g pm2 > /dev/null 2>&1

echo "[3/5] 拉取代码..."
if [ -d "$DIR" ]; then
    cd "$DIR" && git pull
else
    git clone "$REPO" "$DIR" && cd "$DIR"
fi

echo "[4/5] 建立虚拟环境并安装依赖..."
if [ ! -d "$DIR/venv" ]; then
    python3 -m venv "$DIR/venv"
fi
"$DIR/venv/bin/pip" install -q curl_cffi

echo "[5/5] 用 pm2 启动 gpt.py (workers=$WORKERS)..."
mkdir -p "$DIR/tokens"
cd "$DIR"
pm2 delete gpt 2>/dev/null || true
pm2 start "$DIR/venv/bin/python" --name gpt -- gpt.py --workers "$WORKERS"
pm2 save
pm2 startup 2>/dev/null || true

echo ""
echo "=== 部署完成 ==="
echo "查看日志: pm2 logs gpt"
echo "查看状态: pm2 status"
echo "重启:     pm2 restart gpt"
echo "停止:     pm2 stop gpt"
