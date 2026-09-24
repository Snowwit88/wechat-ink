from pathlib import Path
import base64
import io
import json
import pytest
from PIL import Image
from ink.document import Document
from ink.rendering import Renderer,PALETTES
from ink.settings import Settings,InkError
from ink.images import generate,crop_cover,image_plan
from ink.drafts import deliver
from ink import network

@pytest.fixture
def config(tmp_path):
    return Settings(tmp_path/'config',{'image_generation':{'openai':{'api_key':'test-only','base_url':'https://example.test/v1','image_model':'gpt-image-2'}},'egress':{'expected_ip':'154.12.54.132'}},'main',{'app_id':'test-id','app_secret':'test-secret'})

@pytest.fixture
def article(tmp_path):
    Image.new('RGB',(1792,1024),'white').save(tmp_path/'body.png')
    return Document.parse('# 标题\n\n## 一、主题\n\n解释文字。\n\n![图](body.png)\n\n## 二、参考资料\n\n1. 机构：《资料》；\nhttps://example.com/'+('long-path/'*20),tmp_path)

@pytest.mark.parametrize('theme',list(PALETTES))
def test_theme_renders_escaped_article(theme,article):
    output=Renderer(theme).render(article)
    assert '<h2 ' in output and '一、主题' in output
    assert 'font-size:14.5px' in output and 'font-size:12.5px' in output
    assert 'margin-top:2px' in output and 'word-break:break-all' in output
    assert '<a ' not in output

def test_preview_portable(article):
    output=Renderer().preview(article)
    assert 'data:image/png;base64,' in output and 'file://' not in output

def test_markup_cannot_execute():
    doc=Document.parse('# 标题\n\n<script>alert(1)</script>\n\n[链接](https://example.com)')
    out=Renderer().render(doc)
    assert '<script>' not in out and '<a ' not in out and '&lt;script&gt;' in out

def test_audit_missing_image_and_duplicate_heading(tmp_path):
    doc=Document.parse('# 标题\n\n## 一、第一层：主题\n\n![图](absent.png)',tmp_path)
    assert not doc.audit()['passed']
    assert len(doc.audit()['issues'])==2

def test_frontmatter_and_plan():
    doc=Document.parse('---\ntitle: 自定标题\n---\n## 一、主题\n\n文字')
    assert doc.title=='自定标题'
    plan=image_plan(doc)
    assert len(plan['images'])==7 and plan['images'][0]['role']=='cover'

class ImageTransport:
    def json(self,method,url,**kwargs):
        self.call=(method,url,kwargs)
        raw=io.BytesIO();Image.new('RGB',(32,24),'white').save(raw,format='PNG')
        return {'data':[{'b64_json':base64.b64encode(raw.getvalue()).decode()}]}

def test_image_protocol(config,tmp_path):
    t=ImageTransport();result=generate(config,'test',tmp_path/'image.png',transport=t)
    assert result['width']==32
    assert t.call[1]=='https://example.test/v1/images/generations'
    assert t.call[2]['timeout']>=300
    assert t.call[2]['json']['model']=='gpt-image-2'

def test_image_invalid_base(config,tmp_path):
    config.data['image_generation']['openai']['base_url']='https://example.test'
    with pytest.raises(InkError,match='/v1'): generate(config,'test',tmp_path/'x.png')

def test_cover_crop_preserves_source(article,tmp_path):
    crop_cover(tmp_path/'body.png',tmp_path/'cover.png')
    assert Image.open(tmp_path/'body.png').size==(1792,1024)
    assert Image.open(tmp_path/'cover.png').size==(1792,1008)

def test_egress_requires_wrapper(config,monkeypatch):
    monkeypatch.delenv('INK_EGRESS_LAUNCH',raising=False)
    with pytest.raises(InkError,match='wechat-egress'):network.fixed_transport(config)

def test_egress_mismatch_blocks(config,monkeypatch):
    monkeypatch.setenv('INK_EGRESS_LAUNCH','1');calls=[]
    def fake(self,method,url,**kwargs):calls.append(url);return {'ip':'1.2.3.4'}
    monkeypatch.setattr(network.Transport,'json',fake)
    with pytest.raises(InkError,match='不匹配'): network.fixed_transport(config)
    assert calls==['https://api.ipify.org?format=json']

class Client:
    def __init__(self,fail=False):self.posts=0;self.uploads=0;self.fail=fail;self.entries={}
    def upload(self,path,body=False):self.uploads+=1;return 'https://example.com/image.png' if body else 'cover-id'
    def request(self,method,path,**kwargs):
        self.posts+=1
        if self.fail:raise InkError('模拟超时')
        key='draft-'+str(self.posts);self.entries[key]=kwargs['json']['articles'][0];return {'media_id':key}
    def read(self,key):return {'news_item':[self.entries[key]]}

def test_publish_reuse_and_changed_metadata(config,article,tmp_path):
    c=Client();a=deliver(config,c,article,tmp_path/'body.png')
    b=deliver(config,c,article,tmp_path/'body.png')
    assert a['state']=='verified' and b['reused'] and c.posts==1
    assert c.entries[a['media_id']]['author']==''
    deliver(config,c,article,tmp_path/'body.png',author='Snowwit88')
    assert c.posts==2

def test_unknown_draft_result_is_not_retried(config,article,tmp_path):
    c=Client(fail=True)
    with pytest.raises(InkError,match='超时'):deliver(config,c,article,tmp_path/'body.png')
    with pytest.raises(InkError,match='未确认'):deliver(config,c,article,tmp_path/'body.png')
    assert c.posts==1

def test_invalid_theme_before_upload(config,article,tmp_path):
    c=Client()
    with pytest.raises(InkError,match='未知主题'):deliver(config,c,article,tmp_path/'body.png',theme='invalid')
    assert c.uploads==0 and c.posts==0

def test_missing_body_before_upload(config,article,tmp_path):
    (tmp_path/'body.png').unlink();Image.new('RGB',(16,9)).save(tmp_path/'cover.png');c=Client()
    with pytest.raises(InkError):deliver(config,c,article,tmp_path/'cover.png')
    assert c.uploads==0

def test_settings_checks_do_not_expose_keys(config):
    rendered=json.dumps(config.check())
    assert 'test-secret' not in rendered and 'test-only' not in rendered

def test_transport_errors_redact_credentials():
    import requests
    class Session:
        def request(self,*args,**kwargs):raise requests.ConnectionError('https://host?secret=do-not-print')
    with pytest.raises(InkError) as exc:network.Transport(Session()).json('GET','https://host')
    assert 'do-not-print' not in str(exc.value)

def test_image_url_download_has_no_auth(config,tmp_path):
    class Response:
        def raise_for_status(self):pass
        @property
        def content(self):
            raw=io.BytesIO();Image.new('RGB',(32,24)).save(raw,format='PNG');return raw.getvalue()
    class Storage:
        def get(self,url,**kwargs):
            assert url=='https://storage.test/image.png'
            assert 'headers' not in kwargs
            return Response()
    class Transport:
        session=Storage()
        def json(self,*args,**kwargs):return {'data':[{'url':'https://storage.test/image.png'}]}
    generate(config,'test',tmp_path/'download.png',transport=Transport())

def test_installer_isolated_and_no_overwrite(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1];target=tmp_path/'installed'
    args=[sys.executable,str(root/'install.py'),'--target',str(target),'--skip-deps']
    first=subprocess.run(args,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    assert (target/'SKILL.md').is_file() and (target/'LICENSE').is_file()
    assert (target/'wechat-ink.yaml').stat().st_mode & 0o777==0o600
    second=subprocess.run(args,capture_output=True,text=True)
    assert second.returncode!=0
    rendered=subprocess.run([sys.executable,str(target/'scripts/ink.py'),'render',str(target/'examples/article.md'),'-o',str(tmp_path/'preview.html')],capture_output=True,text=True)
    assert rendered.returncode==0,rendered.stderr
    assert 'data:image/png;base64,' in (tmp_path/'preview.html').read_text()

def test_http_wechat_payload_and_token_cache(config,tmp_path):
    from ink.drafts import WeChat
    class Transport:
        def __init__(self):self.calls=[]
        def json(self,method,url,**kwargs):
            self.calls.append((method,url,kwargs))
            if url.endswith('/token'):return {'access_token':'token-for-test'}
            if url.endswith('/draft/get'):return {'news_item':[{'title':'标题'}]}
            if url.endswith('/media/uploadimg'):
                assert kwargs['files']['media'][1].read()==b'test-image'
                return {'url':'https://example.test/image.png'}
            raise AssertionError(url)
    transport=Transport();client=WeChat(config,transport)
    image=tmp_path/'image.png';image.write_bytes(b'test-image')
    client.upload(image,body=True);client.read('test-media')
    assert len(transport.calls)==3
    assert transport.calls[-1][2]['json']=={'media_id':'test-media'}
    assert transport.calls[-1][2]['params']=={'access_token':'token-for-test'}

def test_demo_runs_without_site_packages(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,'-S',str(root/'demo.py'),'--no-open'],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (root/'demo.html').as_uri() in result.stdout
    from html.parser import HTMLParser
    class Frames(HTMLParser):
        article=None
        def handle_starttag(self,tag,attrs):
            if tag=='iframe':self.article=dict(attrs).get('srcdoc')
    parsed=Frames();parsed.feed((root/'demo.html').read_text())
    assert parsed.article and parsed.article.count('<img ')==7
    assert 'data:image/png;base64,' in parsed.article
    assert '<script' not in parsed.article
