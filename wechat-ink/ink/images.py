from pathlib import Path
from urllib.parse import urlparse
import base64
import io
import json
import os
import tempfile
from PIL import Image
import requests
from .network import Transport
from .settings import InkError

STYLE='低饱和学术图解，清晰的信息层级，克制的线条和标注，留白充足，避免装饰性元素。'

def generate(settings,prompt,output,size='1792x1024',transport=None):
    c=settings.image(); base=str(c.get('base_url','')).rstrip('/')
    if not base.startswith('https://') or not base.endswith('/v1'): raise InkError('图片服务 base_url 必须是 HTTPS 地址且以 /v1 结尾')
    if not c.get('api_key'): raise InkError('缺少图片服务凭证，请在本机配置')
    model=c.get('image_model','gpt-image-2')
    if model=='gpt-image-2pro': raise InkError('请使用配置指定的 gpt-image-2，而不是 gpt-image-2pro')
    t=transport or Transport()
    result=t.json('POST',base+'/images/generations',headers={'Authorization':'Bearer '+c['api_key']},
                  json={'model':model,'prompt':prompt,'size':size,'n':1,'response_format':'b64_json'},timeout=360)
    try:
        item=result['data'][0]
        if item.get('b64_json'): raw=base64.b64decode(item['b64_json'],validate=True)
        elif item.get('url'):
            url=item['url']
            if urlparse(url).scheme!='https': raise InkError('图片下载地址不是 HTTPS')
            # A separate request without authorization prevents leaking credentials to storage hosts.
            response=t.session.get(url,timeout=120); response.raise_for_status(); raw=response.content
        else: raise InkError('响应没有图片数据')
        image=Image.open(io.BytesIO(raw)); image.load()
    except (KeyError,IndexError,ValueError,OSError,requests.RequestException):
        raise InkError('无法读取返回的图片数据') from None
    target=Path(output).expanduser().resolve(); target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent,suffix='.png',delete=False) as f: temp=Path(f.name)
    try: image.save(temp,format='PNG'); os.replace(temp,target)
    finally: temp.unlink(missing_ok=True)
    return {'path':str(target),'width':image.width,'height':image.height,'model':model}

def image_plan(doc,count=7):
    import re
    headings=re.findall(r'^##\s+(.+)',doc.body,re.M)
    entries=[]
    for i in range(count):
        subject=doc.title if i==0 else (headings[(i-1)%len(headings)] if headings else doc.title)
        entries.append({'id':i,'role':'cover' if i==0 else 'body','file':f'{i:02d}.png','size':'1792x1024',
                        'prompt':f'{STYLE} 主题：{subject}。'+('封面构图，关键内容置于中央 16:9 安全区域。' if i==0 else '正文解释图，围绕一个核心关系组织画面。')})
    return {'title':doc.title,'cover_crop':'16:9','source_size':'1792x1024','images':entries}

def batch(settings,plan,folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True);done=[]
    for entry in plan['images']:
        name=entry['file']
        if Path(name).name!=name: raise InkError('图片计划中的文件名不能包含路径')
        target=folder/name
        if target.exists():
            try:
                with Image.open(target) as im: im.verify()
                done.append({'path':str(target),'reused':True});continue
            except OSError: raise InkError('已有图片损坏，请移走后再运行') from None
        result=generate(settings,entry['prompt'],target,entry.get('size','1792x1024'));done.append(result)
        (folder/'generation-log.json').write_text(json.dumps(done,ensure_ascii=False,indent=2))
    covers=[e for e in plan['images'] if e.get('role')=='cover']
    if covers: crop_cover(folder/covers[0]['file'],folder/'cover.png')
    return done


def crop_cover(source,output):
    """Make a separate centered 16:9 copy; preserve the source image."""
    from PIL import ImageOps
    with Image.open(source) as image:
        width=(image.width//16)*16
        if width<16: raise InkError('封面图片太小')
        height=width*9//16
        result=ImageOps.fit(image,(width,height),method=Image.Resampling.LANCZOS)
        result.save(output,format='PNG')
    return str(Path(output).resolve())
