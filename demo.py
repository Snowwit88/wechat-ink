#!/usr/bin/env python3
"""Open the bundled sample: standard library only, no service calls."""
from pathlib import Path
import argparse
import webbrowser

def main(argv=None):
    parser=argparse.ArgumentParser(description='微墨 v2 离线样稿预览：不联网、不生图、不发稿')
    parser.add_argument('--no-open',action='store_true')
    args=parser.parse_args(argv)
    page=Path(__file__).resolve().parent/'demo.html'
    if not page.is_file():parser.error('缺少 demo.html，请下载完整项目')
    print('微墨 v2 · 预置样稿演示（不是现场 AI 生成）')
    print(page.as_uri())
    if not args.no_open:webbrowser.open(page.as_uri())
    return 0
if __name__=='__main__':raise SystemExit(main())
