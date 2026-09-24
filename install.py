#!/usr/bin/env python3
"""Install into a new skill directory; never replace an existing installation."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import venv

def main():
    p=argparse.ArgumentParser();p.add_argument('--target',type=Path);p.add_argument('--skip-deps',action='store_true');p.add_argument('--demo',action='store_true',help='只打开离线样稿，不安装依赖');a=p.parse_args()
    if a.demo:
        from demo import main as show_demo
        return show_demo([])
    if sys.version_info<(3,10):p.error('需要 Python 3.10 或更新版本')
    dest=(a.target or Path(os.environ.get('CODEX_HOME',Path.home()/'.codex'))/'skills'/'wechat-ink-v2').expanduser().resolve()
    if dest.exists():p.error('目标已存在；请选新的 --target，不会覆盖已有技能')
    source=Path(__file__).resolve().parent/'wechat-ink'
    shutil.copytree(source,dest,ignore=shutil.ignore_patterns('.venv','__pycache__','*.pyc','wechat-ink.yaml','output','.token_cache*','*.local.env'))
    for name in ('LICENSE','THIRD_PARTY.md'):shutil.copy2(source.parent/name,dest/name)
    config=dest/'wechat-ink.yaml';shutil.copy2(dest/'wechat-ink.yaml.example',config);config.chmod(0o600)
    if not a.skip_deps:
        venv.create(dest/'.venv',with_pip=True)
        python=dest/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        result=subprocess.run([str(python),'-m','pip','install','-r',str(dest/'requirements.txt')])
        if result.returncode:
            print(f'文件已安装至 {dest}；依赖安装失败，可用该目录虚拟环境重试。',file=sys.stderr);return result.returncode
    print(f'已安装：{dest}');return 0
if __name__=='__main__':raise SystemExit(main())
