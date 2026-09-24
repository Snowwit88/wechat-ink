import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse
from . import __version__
from .settings import ROOT, Settings, InkError
from .document import Document
from .rendering import Renderer, PALETTES
from .images import generate, image_plan, batch
from .network import fixed_transport
from .drafts import WeChat, deliver


def emit(value,output=None):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)
    if output:
        p=Path(output).expanduser().resolve();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
        print(str(p))
    else: print(text)

def parser():
    p=argparse.ArgumentParser(description='微墨 2 · 文稿、配图、排版与草稿交付')
    p.add_argument('--version',action='version',version='WeChat Ink v2 '+__version__)
    p.add_argument('--config');p.add_argument('--account')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor');sub.add_parser('themes')
    r=sub.add_parser('render');r.add_argument('input');r.add_argument('-o','--output');r.add_argument('--theme',default='academic-paper');r.add_argument('--fragment',action='store_true')
    a=sub.add_parser('audit');a.add_argument('input');a.add_argument('--expected-images',type=int);a.add_argument('-o','--output')
    q=sub.add_parser('plan');q.add_argument('input');q.add_argument('-o','--output');q.add_argument('--count',type=int,default=7)
    g=sub.add_parser('image');g.add_argument('prompt');g.add_argument('output');g.add_argument('--size',default='1792x1024')
    b=sub.add_parser('images');b.add_argument('plan');b.add_argument('--output',required=True)
    e=sub.add_parser('egress');e.add_argument('action',choices=['start','check','stop'])
    sub.add_parser('token-check')
    get=sub.add_parser('draft-get');get.add_argument('media_id')
    sub.add_parser('draft-list')
    pub=sub.add_parser('publish');pub.add_argument('--input',required=True);pub.add_argument('--cover',required=True)
    for opt in ['title','author','digest','theme','output']:pub.add_argument('--'+opt)
    pub.add_argument('--type',choices=['news','newspic'],default='news');pub.add_argument('--dry-run',action='store_true')
    return p

def tunnel(settings,action):
    e=settings.data.get('egress',{});proxy=urlparse(e.get('proxy','socks5h://127.0.0.1:1088'))
    if proxy.hostname!='127.0.0.1' or proxy.scheme!='socks5h': raise InkError('只支持本机 SOCKS5h')
    host=e.get('ssh_host','');user=e.get('ssh_user','');port=int(e.get('ssh_port',22))
    if not host or not user or any(x.startswith('-') or any(c.isspace() for c in x) for x in (host,user)):raise InkError('SSH 主机与用户配置无效')
    control=Path.home()/'.cache'/'wechat-ink-v2';control.mkdir(parents=True,exist_ok=True);os.chmod(control,0o700)
    import hashlib
    sock=control/('ssh-'+hashlib.sha256((host+user+str(proxy.port)).encode()).hexdigest()[:16])
    base=['ssh','-p',str(port),'-S',str(sock)]
    target=user+'@'+host
    if action=='stop':args=base+['-O','exit',target]
    else:
        if subprocess.run(base+['-O','check',target],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return {'tunnel':'already-running'}
        args=base+['-M','-f','-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','-D',f'127.0.0.1:{proxy.port or 1088}',target]
    if subprocess.run(args).returncode: raise InkError('SSH 通道操作失败')
    return {'tunnel':action}

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        c=args.command
        if c=='themes': emit(list(PALETTES));return 0
        if c in ('render','audit','plan'):
            doc=Document.load(args.input)
            if c=='render':
                engine=Renderer(args.theme);emit(engine.render(doc) if args.fragment else engine.preview(doc),args.output)
            elif c=='audit':
                report=doc.audit(args.expected_images);emit(report,args.output);return 0 if report['passed'] else 2
            else:
                if not 1<=args.count<=20: raise InkError('图片计划数量需为 1–20')
                emit(image_plan(doc,args.count),args.output)
            return 0
        settings=Settings.read(args.config,args.account,optional=c=='doctor')
        if c=='doctor': emit(settings.check());return 0
        if c=='image': emit(generate(settings,args.prompt,args.output,args.size));return 0
        if c=='images':emit(batch(settings,json.loads(Path(args.plan).read_text()),args.output));return 0
        if c=='publish' and args.dry_run:
            doc=Document.load(args.input);report=doc.audit();report['cover_exists']=Path(args.cover).is_file();report['network_used']=False
            emit(report);return 0 if report['passed'] and report['cover_exists'] else 2
        if c=='egress' and args.action in ('start','stop'):
            emit(tunnel(settings,args.action))
            if args.action=='stop':return 0
        transport=fixed_transport(settings)
        if c=='egress':emit({'egress':'verified'});return 0
        client=WeChat(settings,transport)
        if c=='token-check':client.access_token();emit({'token':'available'})
        elif c=='draft-get':emit(client.read(args.media_id))
        elif c=='draft-list':emit(client.list())
        elif c=='publish':
            for path in (args.input,args.cover):
                if not Path(path).is_absolute():raise InkError('发布的文稿和封面必须使用绝对路径')
            emit(deliver(settings,client,Document.load(args.input),args.cover,args.title,args.author,args.digest,args.theme,args.output,args.type))
        return 0
    except (InkError,OSError,ValueError) as exc:
        # InkError messages are constructed without tokens or raw provider responses.
        print('微墨：'+(str(exc) if isinstance(exc,InkError) else '输入文件或配置无效，请检查本机文件。'),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
