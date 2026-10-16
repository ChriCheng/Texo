#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo "请先按照 README 的 macOS 部署说明创建 .venv。"
    read -r -p "按回车关闭。"
    exit 1
fi
exec .venv/bin/python main.py "$@"
