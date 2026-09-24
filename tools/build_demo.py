"""Regenerate the portable sample with the current renderer."""
from pathlib import Path
import html
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'wechat-ink'))
from ink.document import Document
from ink.rendering import Renderer
preview=Renderer().preview(Document.load(root/'wechat-ink/examples/article.md'))
shell='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微墨 · 先看一篇成品</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf1ec;color:#223c30;font-family:system-ui,-apple-system,'PingFang SC',sans-serif}main{max-width:1120px;margin:auto;padding:52px 32px;display:grid;grid-template-columns:1fr 410px;gap:70px;align-items:start}.badge{font-size:12px;letter-spacing:2px;font-weight:700}h1{font-size:52px;line-height:1.2;letter-spacing:-2px;margin:32px 0 24px}p{font-size:16px;line-height:1.9;color:#56675e}.steps{display:grid;gap:12px;margin:30px 0}.steps div{background:#fff9;padding:15px 18px;border:1px solid #d5dfd6;border-radius:12px}.steps b{margin-right:16px;color:#658874}a{color:#2b674b}footer{font-size:13px;line-height:1.8;margin-top:30px;color:#63776a}iframe{width:100%;height:740px;border:8px solid #34483c;border-radius:28px;background:white;box-shadow:0 24px 60px #273d3320}.caption{text-align:center;font-size:12px;margin:12px}.note{padding:16px;background:#e1e8df;border-radius:12px;font-size:13px;line-height:1.8}@media(max-width:800px){main{grid-template-columns:1fr;gap:30px;padding:28px 20px}h1{font-size:38px;margin-top:22px}.phone{max-width:410px;width:100%;margin:auto}iframe{height:680px}}
</style></head><body><main><section><div class="badge">微墨 / PREVIEW</div><h1>先看成品。<br>再开始创作。</h1><p>把文稿、图片和资料，整理成一篇清晰的公众号文章。这里是微墨排版器实际生成的完整样稿。</p><div class="steps"><div><b>01</b>你的主题与资料 → 已有 AI 助手创作</div><div><b>02</b>文稿与图片 → 微墨排版与预览</div><div><b>03</b>确认成品 → 可选发送到微信草稿箱</div></div><div class="note">当前展示预置文章和程序绘制的测试图。此页不读取密钥、不调用 AI 或微信接口、不生成新文章、不发送草稿。右侧文稿可滚动查看。</div><footer>想试自己的文章？查看项目内 README.md 的“开始创作”。<br>生图和草稿发布需另行配置，尚待真实服务验收。<br><a href="https://github.com/Snowwit88/wechat-ink">微墨 GitHub 项目</a></footer></section><section class="phone"><iframe title="微墨完整样稿" srcdoc="__ARTICLE__"></iframe><div class="caption">真实排版输出 · 七张测试图 · 完整参考资料</div></section></main></body></html>'''
page=shell.replace('__ARTICLE__',html.escape(preview,quote=True))
(root/'demo.html').write_text(page,encoding='utf-8')
(root/'docs/index.html').write_text(page,encoding='utf-8')
print('demo.html and docs/index.html generated')
