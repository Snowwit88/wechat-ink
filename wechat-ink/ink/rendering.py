"""Token-based Markdown renderer. Raw HTML is escaped, all styles are inline."""
from pathlib import Path
from urllib.parse import urlparse
import base64
import mimetypes
import html
import re
from markdown_it import MarkdownIt
from .document import Document
from .settings import InkError

# Independently specified palettes. Theme names serve as compatibility identifiers.
PALETTES={
 'academic-paper':('#263238','#f5f6f4'), 'business-navy':('#203c58','#f0f3f7'),
 'elegant-ink':('#38434a','#f4f4f1'), 'girly-pink':('#965573','#fff5f8'),
 'ink-wash':('#40554d','#f3f5f1'), 'magazine-grid':('#4a5265','#f3f3f6'),
 'minimal-bw':('#222222','#f6f6f6'), 'minimal-mono':('#333333','#f5f5f5'),
 'mint-fresh':('#347c71','#eff8f5'), 'news-bold':('#8e3634','#fff4f2'),
 'refined-blue':('#376481','#f0f5fa'), 'sage-premium':('#63775b','#f2f5ee'),
 'sunset-coral':('#aa6250','#fff3ec'), 'warm-editorial':('#7a5942','#fbf4eb'),
 'warm-orange':('#a66b36','#fff6e9')}

class Renderer:
    def __init__(self,theme='academic-paper', image_map=None):
        if theme not in PALETTES: raise InkError(f'未知主题：{theme}')
        self.academic=theme=='academic-paper'
        self.accent,self.tint=PALETTES[theme]; self.images=image_map or {}
        self.md=MarkdownIt('commonmark',{'html':False,'breaks':True}).enable('table')

    def inline(self,tokens):
        out=[]
        for t in tokens or []:
            value=html.escape(t.content)
            if t.type=='text': out.append(value)
            elif t.type in ('softbreak','hardbreak'): out.append('<br />')
            elif t.type=='code_inline': out.append('<code style="font-size:0.9em;background:#f0f2f3;padding:2px 4px;">'+value+'</code>')
            elif t.type=='image':
                src=t.attrGet('src') or ''; src=self.images.get(src,src)
                if urlparse(src).scheme not in ('','https','http','file','data'): raise InkError('不支持的图片地址协议')
                # data images must be generated image data, never embedded active content.
                if src.startswith('data:') and not src.startswith(('data:image/png;base64,','data:image/jpeg;base64,')): raise InkError('仅允许 PNG/JPEG 内嵌图片')
                out.append(f'<img src="{html.escape(src,quote=True)}" alt="{value}" style="display:block;max-width:100%;height:auto;margin:18px auto;border-radius:3px;" />')
            elif t.type=='strong_open': out.append(f'<strong style="font-weight:700;color:{self.accent};">')
            elif t.type=='strong_close': out.append('</strong>')
            elif t.type=='em_open': out.append('<em>')
            elif t.type=='em_close': out.append('</em>')
            elif t.type=='link_open': out.append('<span style="text-decoration:underline;">')
            elif t.type=='link_close': out.append('</span>')
            elif t.type=='html_inline': out.append(value)
        output=''.join(out)
        if self.academic:
            output=output.replace('margin:18px auto;border-radius:3px','margin:28px auto;border-radius:0;border:1px solid #d0d0d0;box-sizing:border-box')
            output=re.sub(r'(<img[^>]+alt="([^"]*)"[^>]*>)',r'\1<span style="display:block;text-align:center;font-size:12.5px;color:#5a5a5a;font-style:italic;margin-top:10px;text-indent:0;">\2</span>',output)
        return output

    def render(self,doc:Document):
        tokens=self.md.parse(doc.body); result=[]; ref=False; depth=0; quote=0; i=0
        while i<len(tokens):
            t=tokens[i]; typ=t.type
            if typ=='heading_open':
                inline=tokens[i+1]; name=inline.content.strip()
                if t.tag=='h2': ref=name in ('参考资料','参考文献','References','Sources') or bool(re.match(r'^[一二三四五六七八九十]+、参考',name))
                if self.academic and t.tag=='h1':
                    i+=3; continue
                if self.academic and t.tag=='h2':
                    result.append('<p style="margin:42px 0;text-align:center;font:italic 14px Times New Roman,serif;letter-spacing:14px;opacity:.35;">§  §  §</p>')
                size=({'h1':24,'h2':18,'h3':16} if self.academic else {'h1':24,'h2':20,'h3':17}).get(t.tag,16)
                margin=('40px 0 16px' if self.academic else '28px 0 16px') if t.tag!='h1' else '10px 0 26px'
                result.append(f'<{t.tag} style="font-size:{size}px;line-height:1.6;font-weight:700;color:{self.accent};margin:{margin};text-indent:0;">{self.inline(inline.children)}</{t.tag}>')
                i+=3; continue
            if typ in ('bullet_list_open','ordered_list_open'):
                tag='ol' if ref or typ=='ordered_list_open' else 'ul'
                result.append(f'<{tag} style="padding-left:24px;margin:12px 0;">'); depth+=1
            elif typ in ('bullet_list_close','ordered_list_close'):
                result.append('</ol>' if ref or typ=='ordered_list_close' else '</ul>'); depth-=1
            elif typ=='list_item_open': result.append('<li style="margin:0 0 '+('10' if ref else '8')+'px;text-indent:0;">')
            elif typ=='list_item_close': result.append('</li>')
            elif typ=='blockquote_open':
                quote+=1; result.append(f'<blockquote style="border-left:3px solid {self.accent};padding:10px 16px;margin:18px 0;background:{self.tint};color:#5d6468;">')
            elif typ=='blockquote_close': quote-=1; result.append('</blockquote>')
            elif typ=='paragraph_open':
                inline=tokens[i+1]; children=inline.children or []
                if ref and depth and re.search(r'https?://',inline.content):
                    pieces=re.split(r'(https?://[^\s<>]+)',inline.content)
                    content=[]
                    for part in pieces:
                        if part.startswith(('https://','http://')):
                            content.append('<span style="display:block;font-size:12.5px;line-height:1.6;text-indent:0;margin-top:2px;overflow-wrap:anywhere;word-break:break-all;">'+html.escape(part)+'</span>')
                        elif part.strip():
                            text=part.strip().rstrip(';；')+'；'
                            content.append('<span style="display:block;font-size:14.5px;line-height:1.7;text-indent:0;">'+self.inline(self.md.parseInline(text)[0].children)+'</span>')
                    result.append('<section style="margin:0;text-indent:0;">'+''.join(content)+'</section>')
                else:
                    has_image=any(c.type=='image' for c in children)
                    indent='0' if depth or quote or has_image else '2em'
                    margin='0' if depth else ('16px 0' if self.academic else '0 0 18px')
                    size='15.5' if self.academic else '16'
                    leading='2' if self.academic else '1.85'
                    result.append(f'<p style="margin:{margin};font-size:{size}px;line-height:{leading};text-align:justify;text-indent:{indent};overflow-wrap:anywhere;">{self.inline(children)}</p>')
                i+=3; continue
            elif typ=='fence' or typ=='code_block':
                result.append('<pre style="white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f6;padding:14px;font-size:13px;text-indent:0;"><code>'+html.escape(t.content)+'</code></pre>')
            elif typ=='hr': result.append('<hr style="border:0;border-top:1px solid #dce1e3;margin:24px 0;" />')
            elif typ=='html_block': result.append('<p>'+html.escape(t.content)+'</p>')
            elif typ=='table_open': result.append('<section style="overflow-x:auto;"><table style="border-collapse:collapse;width:100%;font-size:14px;">')
            elif typ=='table_close': result.append('</table></section>')
            elif typ in ('thead_open','tbody_open','tr_open'): result.append('<'+t.tag+'>')
            elif typ in ('thead_close','tbody_close','tr_close'): result.append('</'+t.tag+'>')
            elif typ in ('th_open','td_open'): result.append(f'<{t.tag} style="border:1px solid #d8dfe1;padding:8px;text-indent:0;">')
            elif typ in ('th_close','td_close'): result.append('</'+t.tag+'>')
            elif typ=='inline': result.append(self.inline(t.children))
            i+=1
        output='<section style="max-width:677px;margin:0 auto;padding:20px 18px;font-family:-apple-system,BlinkMacSystemFont,\'PingFang SC\',\'Microsoft YaHei\',sans-serif;color:#333;letter-spacing:0.3px;">'+''.join(result)+'</section>'
        if self.academic:
            output=output.replace('padding:20px 18px','padding:20px 22px').replace("font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif","font-family:'Noto Serif SC','Source Han Serif SC','Times New Roman','Songti SC',serif;font-size:15.5px;word-spacing:1.5px").replace('color:#333','color:#1a1a1a').replace('color:#263238','color:#1a1a1a')
        return output

    def preview(self,doc):
        mapping=dict(self.images)
        for source in doc.image_sources():
            if not urlparse(source).scheme:
                path=(doc.base/source).resolve()
                mime=mimetypes.guess_type(path.name)[0]
                if mime not in ('image/png','image/jpeg'): raise InkError('预览仅支持本地 PNG/JPEG 图片')
                mapping[source]='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
        body=Renderer(next(k for k,v in PALETTES.items() if v==(self.accent,self.tint)),mapping).render(doc)
        return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(doc.title)+'</title></head><body style="margin:0;background:#fff;">'+body+'</body></html>'
