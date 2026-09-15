#!/usr/bin/env python3
"""复制分享包并安装独立依赖，不读取已有账号配置，不覆盖已有安装。"""
import argparse, os, shutil, subprocess, sys, venv
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path)
    parser.add_argument('--skip-deps', action='store_true')
    args=parser.parse_args()
    if sys.version_info < (3,10):
        parser.error('需要 Python 3.10 或更高版本')
    source=Path(__file__).resolve().parent/'wechat-ink'
    home=Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))).expanduser()
    target=(args.target or home/'skills/wechat-ink').expanduser().resolve()
    if target.exists():
        parser.error('目标已存在，为保护原有技能和配置，未做任何修改：'+str(target))
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('.venv', '__pycache__', '.pytest_cache', '*.pyc', '.token_cache*', 'wechat-ink.yaml', 'wechat-egress.local.env', '*.log'))
    config=target/'wechat-ink.yaml'
    shutil.copyfile(target/'wechat-ink.yaml.example',config)
    config.chmod(0o600)
    print('技能已复制到：',target)
    if not args.skip_deps:
        try:
            venv.EnvBuilder(with_pip=True).create(target/'.venv')
            python=target/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            subprocess.run([str(python),'-m','pip','install','-r',str(target/'requirements.txt')],check=True)
        except Exception as exc:
            print('依赖安装未完成：'+type(exc).__name__,file=sys.stderr)
            print('已复制文件保留。可在目标目录运行 python -m venv .venv，再用虚拟环境 Python -m pip install -r requirements.txt。',file=sys.stderr)
            return 1
    print('下一步：阅读安装目录 README.md，先试离线排版，再填写自己的配置。')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
