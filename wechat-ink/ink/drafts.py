from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import os
import time
from .settings import InkError
from .document import Document
from .rendering import Renderer

class WeChat:
    def __init__(self,settings,transport):
        self.config=settings; self.transport=transport; self.token=None
        if not all(settings.account.get(k) for k in ('app_id','app_secret')): raise InkError('公众号凭证未配置')

    def access_token(self):
        if self.token: return self.token
        a=self.config.account
        result=self.transport.json('GET','https://api.weixin.qq.com/cgi-bin/token',params={'grant_type':'client_credential','appid':a['app_id'],'secret':a['app_secret']})
        if not result.get('access_token'): raise InkError('接口未返回 access_token')
        self.token=result['access_token'];return self.token

    def request(self,method,path,**kwargs):
        params=dict(kwargs.pop('params',{})); params['access_token']=self.access_token()
        return self.transport.json(method,'https://api.weixin.qq.com/cgi-bin/'+path,params=params,**kwargs)

    def upload(self,file,body=False):
        p=Path(file)
        if not p.is_file(): raise InkError(f'图片不存在：{p}')
        import mimetypes
        with p.open('rb') as f:
            response=self.request('POST','media/uploadimg' if body else 'material/add_material',
                params={} if body else {'type':'image'},files={'media':(p.name,f,mimetypes.guess_type(p.name)[0] or 'image/png')})
        key='url' if body else 'media_id'
        if not response.get(key): raise InkError('上传响应缺少 '+key)
        return response[key]

    def read(self,media_id): return self.request('POST','draft/get',json={'media_id':media_id})

    def list(self,offset=0,count=20):
        return self.request('POST','draft/batchget',json={'offset':offset,'count':count,'no_content':1})


def deliver(settings,client,doc,cover,title=None,author=None,digest=None,theme=None,output=None,kind='news'):
    title=title or doc.title
    if not title: raise InkError('草稿必须有标题')
    report=doc.audit()
    if not report['passed']: raise InkError('文稿检查未通过：'+ '; '.join(x['message'] for x in report['issues'] if x['level']=='error'))
    cover=Path(cover).expanduser().resolve()
    if not cover.is_file(): raise InkError('缺少本地封面文件')
    sources=doc.image_sources()
    # Resolve every input before uploading anything.
    files={}
    for source in sources:
        if urlparse(source).scheme: raise InkError('发布前请把正文图片保存到本地，避免遗漏或第三方链接失效')
        files[source]=(doc.base/source).resolve()
    if kind=='newspic' and not files: raise InkError('图片消息至少需要一张正文图片')
    selected_theme=theme or settings.account.get('theme','academic-paper')
    selected_author=author if author is not None else settings.account.get('author','')
    selected_digest=digest if digest is not None else doc.metadata.get('digest','')
    Renderer(selected_theme)  # Validate before network writes.
    identity=json.dumps([doc.body,title,settings.account.get('app_id'),settings.account_name,selected_theme,selected_author,selected_digest,kind],ensure_ascii=False)
    fingerprint=hashlib.sha256(identity.encode()+cover.read_bytes()+b''.join(p.read_bytes() for p in files.values())).hexdigest()
    folder=Path(output or doc.base/'output').resolve(); folder.mkdir(parents=True,exist_ok=True)
    journal=folder/('draft-'+fingerprint[:20]+'.json')
    if journal.exists():
        saved=json.loads(journal.read_text())
        if saved.get('media_id'):
            remote=client.read(saved['media_id'])
            items=remote.get('news_item',[])
            if not items or items[0].get('title')!=title: raise InkError('已有草稿回读不一致，请先核对草稿箱')
            return {**saved,'reused':True,'readback_title':items[0]['title']}
        raise InkError('存在未确认的草稿请求记录；请先核对草稿箱，避免重复提交')
    uploaded={source:client.upload(path,body=True) for source,path in files.items()}
    thumb=client.upload(cover)
    content=Renderer(selected_theme,uploaded).render(doc)
    entry={'article_type':kind,'title':title,'author':selected_author,
           'digest':selected_digest,'content':content,'thumb_media_id':thumb,
           'need_open_comment':0,'only_fans_can_comment':0}
    if kind=='newspic':
        if not files: raise InkError('图片消息至少需要一张正文图片')
        entry['image_info']={'image_list':[{'image_media_id':client.upload(p)} for p in files.values()]}
    record={'state':'request-pending','fingerprint':fingerprint,'title':title,'account':settings.account_name}
    try:
        with journal.open('x',encoding='utf-8') as handle:
            os.chmod(journal,0o600)
            handle.write(json.dumps(record,ensure_ascii=False,indent=2))
    except FileExistsError: raise InkError('另一进程正在提交同一篇文稿，请先核对草稿记录') from None
    response=client.request('POST','draft/add',json={'articles':[entry]})
    if not response.get('media_id'): raise InkError('未收到草稿标识，请核对草稿箱；不要直接重复提交')
    record.update(state='created',media_id=response['media_id']);journal.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    remote=client.read(record['media_id']); items=remote.get('news_item',[])
    if not items or items[0].get('title')!=title: raise InkError('草稿已创建但回读不一致，请人工核对记录文件')
    remote_content=items[0].get('content','')
    if any(url not in remote_content and url.replace('&','&amp;') not in remote_content for url in uploaded.values()):
        raise InkError('草稿已创建但正文图片回读不一致，请人工核对记录文件')
    record.update(state='verified',readback_title=items[0]['title'],readback_images=len(uploaded))
    journal.write_text(json.dumps(record,ensure_ascii=False,indent=2));return record
