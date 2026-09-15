#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${WECHAT_EGRESS_CONFIG:-$SCRIPT_DIR/wechat-egress.local.env}"

die() {
  printf '错误：%s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法：
  ./operations/wechat-egress.sh start
  ./operations/wechat-egress.sh check
  ./operations/wechat-egress.sh token-check
  ./operations/wechat-egress.sh draft-get <account> <media_id>
  ./operations/wechat-egress.sh publish <publish.py 参数...>

说明：
  start       在本机后台启动 SSH SOCKS 通道（密码不会保存）
  check       验证通道和固定出口 IPv4
  token-check 强制刷新一次微信 access_token，不创建草稿
  draft-get   通过固定出口回读草稿摘要字段，不输出正文或凭证
  publish     检查固定出口后调用安装版 publish.py 创建草稿
EOF
}

load_config() {
  [ -f "$CONFIG_FILE" ] || die "缺少私有配置：$CONFIG_FILE。请复制 wechat-egress.example.env 后填写。"

  # 配置文件由当前用户维护；加载后仅导出本进程所需变量。
  # shellcheck disable=SC1090
  . "$CONFIG_FILE"

  required_vars="WECHAT_EGRESS_HOST WECHAT_EGRESS_USER WECHAT_EGRESS_SSH_PORT WECHAT_EGRESS_LOCAL_PORT WECHAT_EXPECTED_EGRESS_IP WECHAT_EGRESS_AUTH_MODE WECHAT_INK_HOME WECHAT_INK_PYTHON"
  for name in $required_vars; do
    eval "value=\${$name:-}"
    [ -n "$value" ] || die "配置项 $name 不能为空。"
  done
}

proxy_url() {
  printf 'socks5h://127.0.0.1:%s' "$WECHAT_EGRESS_LOCAL_PORT"
}

listener_pid() {
  lsof -nP -iTCP:"$WECHAT_EGRESS_LOCAL_PORT" -sTCP:LISTEN -t 2>/dev/null | head -n 1
}

query_proxy_ip() {
  proxy="$(proxy_url)"
  for endpoint in https://api.ipify.org https://icanhazip.com; do
    if actual_ip="$(curl --proxy "$proxy" -4fsS --max-time 8 "$endpoint" 2>/dev/null | tr -d '[:space:]')"; then
      case "$actual_ip" in
        *.*.*.*)
          printf '%s\n' "$actual_ip"
          return 0
          ;;
      esac
    fi
  done
  return 1
}

check_egress() {
  command -v lsof >/dev/null 2>&1 || die "缺少 lsof，无法确认本地监听端口。"
  command -v curl >/dev/null 2>&1 || die "缺少 curl，无法验证固定出口。"

  pid="$(listener_pid || true)"
  [ -n "$pid" ] || die "固定出口通道未运行。请先执行：./operations/wechat-egress.sh start"

  actual_ip="$(query_proxy_ip || true)"
  [ -n "$actual_ip" ] || die "本地端口 $WECHAT_EGRESS_LOCAL_PORT 已被占用，但无法通过它访问固定出口；为安全起见停止发布。"
  [ "$actual_ip" = "$WECHAT_EXPECTED_EGRESS_IP" ] || die "出口 IPv4 为 $actual_ip，不是预期的固定服务器 $WECHAT_EXPECTED_EGRESS_IP；为安全起见停止发布。"

  printf '固定出口正常：%s（本地通道 PID %s）\n' "$actual_ip" "$pid"
}

start_tunnel() {
  # check_egress 的失败路径会调用 die/exit，因此必须放进子 shell；
  # 否则首次 start 会在通道尚未存在时直接结束，无法进入 SSH 启动步骤。
  if (check_egress) >/dev/null 2>&1; then
    check_egress
    return 0
  fi

  existing_pid="$(listener_pid || true)"
  [ -z "$existing_pid" ] || die "本地端口 $WECHAT_EGRESS_LOCAL_PORT 已被进程 $existing_pid 占用，但它不是可用的固定出口。不会自动结束该进程。"

  printf '正在启动固定出口；请输入服务器密码（密码不会保存）...\n'

  if [ -n "${WECHAT_EGRESS_BIND_INTERFACE:-}" ]; then
    set -- -o "BindInterface=$WECHAT_EGRESS_BIND_INTERFACE"
    printf 'SSH 隧道直连网卡：%s\n' "$WECHAT_EGRESS_BIND_INTERFACE"
  else
    set --
  fi

  if [ "$WECHAT_EGRESS_AUTH_MODE" = "password" ]; then
    ssh -fN \
      "$@" \
      -o PreferredAuthentications=password \
      -o PubkeyAuthentication=no \
      -o ExitOnForwardFailure=yes \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -D "127.0.0.1:$WECHAT_EGRESS_LOCAL_PORT" \
      -p "$WECHAT_EGRESS_SSH_PORT" \
      "$WECHAT_EGRESS_USER@$WECHAT_EGRESS_HOST"
  else
    ssh -fN \
      "$@" \
      -o ExitOnForwardFailure=yes \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -D "127.0.0.1:$WECHAT_EGRESS_LOCAL_PORT" \
      -p "$WECHAT_EGRESS_SSH_PORT" \
      "$WECHAT_EGRESS_USER@$WECHAT_EGRESS_HOST"
  fi

  check_egress
}

export_proxy_env() {
  proxy="$(proxy_url)"
  export ALL_PROXY="$proxy"
  export all_proxy="$proxy"
  export HTTP_PROXY="$proxy"
  export http_proxy="$proxy"
  export HTTPS_PROXY="$proxy"
  export https_proxy="$proxy"
  export NO_PROXY="127.0.0.1,localhost"
  export no_proxy="$NO_PROXY"
}

ensure_publisher() {
  [ -d "$WECHAT_INK_HOME/scripts" ] || die "找不到安装版发布工具：$WECHAT_INK_HOME"
  [ -x "$WECHAT_INK_PYTHON" ] || die "找不到发布工具 Python：$WECHAT_INK_PYTHON"
  "$WECHAT_INK_PYTHON" -c 'import requests, socks, yaml' >/dev/null 2>&1 || die "发布环境缺少 requests、PySocks 或 PyYAML。"
}

token_check() {
  check_egress
  ensure_publisher
  export_proxy_env
  cd "$WECHAT_INK_HOME/scripts"
  "$WECHAT_INK_PYTHON" -c 'from wechat_api import get_access_token; token = get_access_token(force_refresh=True); print("微信 token 验证成功（长度 %d，不显示内容）" % len(token))'
}

draft_get() {
  [ "$#" -eq 2 ] || die "draft-get 需要 account 和 media_id 两个参数。"
  account="$1"
  media_id="$2"
  check_egress
  ensure_publisher
  export_proxy_env
  cd "$WECHAT_INK_HOME/scripts"
  WECHAT_DRAFT_ACCOUNT="$account" WECHAT_DRAFT_MEDIA_ID="$media_id" \
    "$WECHAT_INK_PYTHON" - <<'PY'
import json
import os
import re
import sys

import requests

from wechat_api import get_access_token, set_account

set_account(os.environ["WECHAT_DRAFT_ACCOUNT"])
token = get_access_token()
try:
    response = requests.post(
        "https://api.weixin.qq.com/cgi-bin/draft/get",
        params={"access_token": token},
        json={"media_id": os.environ["WECHAT_DRAFT_MEDIA_ID"]},
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    payload = response.json()
except Exception as exc:
    print("草稿回读请求失败（未输出 URL 或 token）：%s" % type(exc).__name__, file=sys.stderr)
    raise SystemExit(1)

if payload.get("errcode"):
    print(
        "草稿回读失败：errcode=%s errmsg=%s"
        % (payload.get("errcode"), payload.get("errmsg", "")),
        file=sys.stderr,
    )
    raise SystemExit(1)

items = payload.get("news_item") or []
if not items:
    print("草稿回读失败：响应中没有 news_item。", file=sys.stderr)
    raise SystemExit(1)

article = items[0]
content = article.get("content") or ""
summary = {
    "title": article.get("title", ""),
    "author": article.get("author", ""),
    "digest": article.get("digest", ""),
    "has_cover": bool(article.get("thumb_media_id")),
    "content_image_count": len(re.findall(r"<img\b", content, flags=re.I)),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
PY
}

publish_draft() {
  [ "$#" -gt 0 ] || die "publish 后需要提供 publish.py 参数。"
  check_egress
  ensure_publisher
  export_proxy_env
  cd "$WECHAT_INK_HOME/scripts"
  # 微信 SDK 的异常文本可能包含带 access_token 的完整请求 URL；
  # 统一在项目出口层脱敏，同时保留 publish.py 的真实退出码。
  set +e
  PYTHONUNBUFFERED=1 "$WECHAT_INK_PYTHON" publish.py "$@" 2>&1 \
    | sed -E 's/(access_token=)[^& )]+/\1[REDACTED]/g'
  status="${PIPESTATUS[0]}"
  set -e
  exit "$status"
}

main() {
  command="${1:-}"
  case "$command" in -h|--help|help|"") usage; return 0 ;; esac
  load_config
  case "$command" in
    start)
      start_tunnel
      ;;
    check|status)
      check_egress
      ;;
    token-check)
      token_check
      ;;
    draft-get)
      shift
      draft_get "$@"
      ;;
    publish)
      shift
      publish_draft "$@"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage >&2
      die "未知命令：$command"
      ;;
  esac
}

main "$@"
