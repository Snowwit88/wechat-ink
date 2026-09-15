#!/usr/bin/env python3
"""
简单的图片生成脚本，直接调用 OpenAI 兼容的图片生成 API。

凭证与地址都从 wechat-ink.yaml 的 image_generation.openai 段读取，
不写在源码里。也可以用环境变量覆盖（环境变量优先）：

    OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_IMAGE_MODEL

注意 OPENAI_BASE_URL 必须带 /v1，本脚本原样拼 ${base_url}/images/generations。
"""
import base64
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

DEFAULT_SIZE = "1792x1024"
# 1792x1024 实测单张 40-80 秒，偶尔更久，留足余量。
REQUEST_TIMEOUT = 300


def _load_backend() -> tuple[str, str, str]:
    """返回 (api_key, api_base, model)。缺配置直接报错，不静默回退。"""
    config.load_env()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    api_base = os.environ.get("OPENAI_BASE_URL", "").strip().rstrip("/")
    model = os.environ.get("OPENAI_IMAGE_MODEL", "").strip() or "gpt-image-2"

    missing = [
        name
        for name, value in (("api_key", api_key), ("base_url", api_base))
        if not value
    ]
    if missing:
        raise SystemExit(
            "缺少生图配置: " + "、".join(missing) + "。\n"
            "请在 wechat-ink.yaml 的 image_generation.openai 段补齐，"
            "或设置 OPENAI_API_KEY / OPENAI_BASE_URL 环境变量。"
        )
    if not api_base.endswith("/v1"):
        print(f"警告: base_url 未以 /v1 结尾（{api_base}），接口可能返回 404。")

    return api_key, api_base, model


def generate_image(prompt: str, output_path: str, size: str = DEFAULT_SIZE) -> bool:
    """生成图片并保存"""
    api_key, api_base, model = _load_backend()

    print(f"生成图片: {prompt[:50]}...")
    print(f"后端: {api_base}  模型: {model}  尺寸: {size}")

    url = f"{api_base}/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json"
    }

    response = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)

    if response.status_code != 200:
        print(f"错误: {response.status_code}")
        print(response.text[:800])
        if response.status_code == 403 and "1010" in response.text:
            # Cloudflare 按 User-Agent 指纹拦截，requests 正常，Python 原生 urllib 会中招。
            print("提示: Cloudflare 1010 是客户端指纹拦截，不是密钥或额度问题。")
        return False

    result = response.json()

    if "data" not in result or len(result["data"]) == 0:
        print("错误: 响应中没有图片数据")
        return False

    # 解码 base64 图片
    image_data = result["data"][0].get("b64_json")
    if not image_data:
        print("错误: 没有找到 b64_json 字段")
        return False

    # 保存图片
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw = base64.b64decode(image_data)
    with open(output_path, "wb") as f:
        f.write(raw)

    print(f"✓ 图片已保存: {output_path}（{len(raw) / 1048576:.2f}MB）")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 simple_gen.py <prompt> <output_path> [size]")
        sys.exit(1)

    prompt = sys.argv[1]
    output_path = sys.argv[2]
    size = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SIZE

    success = generate_image(prompt, output_path, size)
    sys.exit(0 if success else 1)
