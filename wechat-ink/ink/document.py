from dataclasses import dataclass
from pathlib import Path
import re
import yaml
from markdown_it import MarkdownIt
from .settings import InkError

@dataclass
class Document:
    body: str
    metadata: dict
    base: Path

    @classmethod
    def load(cls, path):
        p=Path(path).expanduser().resolve()
        try: text=p.read_text(encoding='utf-8-sig')
        except OSError: raise InkError(f'无法读取文稿：{p}') from None
        return cls.parse(text,p.parent)

    @classmethod
    def parse(cls,text,base=None):
        meta={}; body=text
        found=re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)', text,re.S)
        if found:
            try: meta=yaml.safe_load(found[1]) or {}
            except yaml.YAMLError: raise InkError('文稿元数据不是有效 YAML') from None
            if not isinstance(meta,dict): raise InkError('文稿元数据必须是映射')
            body=text[found.end():]
        return cls(body,meta,Path(base or '.').resolve())

    @property
    def title(self):
        heading=re.search(r'^#\s+(.+)$',self.body,re.M)
        return str(self.metadata.get('title') or (heading[1] if heading else ''))

    def image_sources(self):
        found=[]
        for token in MarkdownIt().parse(self.body):
            for child in token.children or []:
                if child.type=='image' and child.attrGet('src') not in found: found.append(child.attrGet('src'))
        return found

    def audit(self, expected_images=None):
        issues=[]
        if not self.title: issues.append({'level':'error','message':'缺少文章标题'})
        for line in self.body.splitlines():
            if re.match(r'^##\s+[一二三四五六七八九十]+、第[一二三四五六七八九十]+层',line):
                issues.append({'level':'error','message':'小节重复编号：'+line})
        for source in self.image_sources():
            if not source.startswith(('https://','http://')) and not (self.base/source).is_file():
                issues.append({'level':'error','message':'缺少图片：'+source})
        if expected_images is not None and len(self.image_sources())!=expected_images:
            issues.append({'level':'warning','message':f'文中图片为 {len(self.image_sources())} 张，期望 {expected_images} 张'})
        for phrase in ('综上所述','总而言之','值得注意的是'):
            n=self.body.count(phrase)
            if n>1: issues.append({'level':'warning','message':f'重复过渡语「{phrase}」出现 {n} 次，请人工审读'})
        return {'title':self.title,'characters':len(re.sub(r'\s','',self.body)), 'images':len(self.image_sources()),'issues':issues,
                'passed':not any(x['level']=='error' for x in issues), 'note':'文字检查是编辑提示，不预测平台 AI 判定。'}
