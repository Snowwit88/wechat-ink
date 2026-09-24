#!/usr/bin/env bash
set -euo pipefail
INK_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
INK_PYTHON="${WECHAT_INK_PYTHON:-$INK_ROOT/.venv/bin/python}"
if [[ ! -x "$INK_PYTHON" ]]; then
  printf '%s\n' '请设置 WECHAT_INK_PYTHON 为新版虚拟环境中的 Python 路径。' >&2
  exit 2
fi
export INK_EGRESS_LAUNCH=1
case "${1:-}" in
 start|stop|check) exec "$INK_PYTHON" "$INK_ROOT/scripts/ink.py" egress "$1" ;;
 token-check|publish|draft-get|draft-list) exec "$INK_PYTHON" "$INK_ROOT/scripts/ink.py" "$@" ;;
 *) printf '%s\n' '用法：wechat-egress.sh start|check|stop|token-check|publish|draft-get|draft-list' >&2; exit 2 ;;
esac
