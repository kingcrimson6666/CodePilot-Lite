#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "未找到可用的虚拟环境：$VENV_PY"
  echo "请先执行：python -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

cd "$ROOT_DIR"

if [[ $# -eq 0 ]]; then
  exec "$VENV_PY" -m src.app.cli chat --stream --interactive
fi

exec "$VENV_PY" -m src.app.cli "$@"