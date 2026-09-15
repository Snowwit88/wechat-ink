---
name: wechat-ink
description: 研究、撰写、审校、配图和排版微信公众号文章，并在用户要求时创建微信草稿。适用于公众号选题、参考素材转文章、图文制作和草稿交付。
---

# WeChat Ink · 微墨

首次使用先读 [使用说明](README.md)。脚本路径均相对本技能目录，不依赖分享者电脑。用户文章保存在其工作目录，勿写到技能安装目录。文章与账号定位由用户决定，默认采用严谨克制的学术编辑风格；不冒用分享者身份或虚构亲历。

## 按请求推进

- 用户只问进度、咨询或只要文稿，就执行对应部分；不自动创建草稿。
- 写文章先建立 `brief.md`、`research.md`、`article.md`，用 [任务书](templates/brief.md) 和 [调研模板](templates/research.md)。只缺配置时仍可研究、写稿和本地排版。
- 用公开可访问的原始来源核对数据、日期和口径，区分事实与推断；不捏造数据、引言、文献或作者经历。没有搜索能力时标记待核验，不能声称查证完成。
- 按主题选择结构和开头，参见 [结构库](references/article-structures.md)。避免连续文章结构完全相同。
- 完稿做事实审校与语言审校：删空话，保留具体信息与反方边界；参考 [文字检查](references/anti-ai-checklist.md)，但不执行虚构经历、故意添错或保证规避 AI 检测的做法。脚本分数仅为风格启发式，不能证明作者身份或保证平台判定。

## 默认制作规格

- `academic-paper` 排版；小节标题为 `## 一、主题`，不重复“第一层”等编号。
- 默认每篇 1 张封面＋6 张正文图。源图 1792×1024 PNG，封面另裁为 16:9，保留源图。学术风、低饱和、克制，无装饰性元素；图表数值须有来源。
- 混用不少于 4 种行内强调：`**`、`==`、`++`、`%%`、`&&`、`@@`、`^^`；不过度高亮，不为凑数破坏语义。
- 正文参考资料每条只展示一个与题名匹配且完整可访问的 URL，其余交叉来源保存在 research.md。使用以下格式，不生成外部 Markdown 链接或 `<a>`：

```markdown
1. 机构／作者：《题名》（日期）；
https://example.com/full-source-url
```

来源与 URL 渲染为同一紧凑条目：来源 14.5px、URL 12.5px、间隔 2px；URL 无首行缩进且自然折行。地址仅保证可见可复制。

## 配图

先检查用户已有生图配置，不显示密钥，不继承分享者服务商或账号。使用本技能 `scripts/simple_gen.py`（Python requests，免 Bun）：

```sh
.venv/bin/python scripts/simple_gen.py "完整学术风提示词" "/绝对路径/images/01.png" 1792x1024
```

它从 `image_generation.openai` 读取配置，环境变量可覆盖。兼容地址须含 `/v1`，默认模型名 `gpt-image-2`，不用 `gpt-image-2pro`。此名称及尺寸来自原项目兼容后端，不意味着任何服务商都支持。实际服务不支持时按该服务的文档配置，不盲目重试。超时至少 300 秒。

也保留 `generate_image.py` 多后端入口，需要 Bun；仅使用该路线时读 [配图风格说明](references/image-styles-guide.md)。后端不可用且当前客户端确实提供内置 ImageGen 时，可按配置兜底；没有该工具就交付已完成文稿和提示词，明确缺图，不假称生图完成。每张图目检后再使用。403/1010 可能是 Cloudflare 客户端拦截，不能直接认定密钥失效。

## 排版、验证与交付

```sh
.venv/bin/python scripts/html_converter.py /绝对路径/article.md --theme academic-paper -o /绝对路径/preview.html
.venv/bin/python scripts/ai_score.py /绝对路径/article.md --threshold 45
.venv/bin/python -m pytest tests/ -q
```

评分不达标时修订而非直接跳过。核对图片路径、来源格式、长 URL 换行、原始标记残留；目检手机宽度预览。使用 [发布检查表](templates/publish-checklist.md)，区分建草稿前检查与微信后台终审，未执行项不能勾选。

## 微信草稿

微墨使用固定出口流程，服务器、白名单、账号和私有配置全部由使用者自行提供。没有出口配置时停在本地交付。

所有微信公众号 API 操作只通过本技能 `operations/wechat-egress.sh`，不可直接运行 publish.py、wechat_api.py 或绕过出口。`check` 失败就停止，不回退本机、VPN 或热点。发布参数使用绝对路径。

```sh
bash operations/wechat-egress.sh start
bash operations/wechat-egress.sh check
bash operations/wechat-egress.sh token-check
bash operations/wechat-egress.sh publish --account main --input /绝对路径/article.md --cover /绝对路径/cover.jpg --title "文章标题"
bash operations/wechat-egress.sh draft-get main "返回的media_id"
```

回读核验标题、作者、摘要、封面、正文图数量；记录结果。草稿创建结果不明确时先核实，避免重复创建。上传报 41005 时优先重试失败项或降低并发，不直接认定文件过大。最终交付文稿、预览和草稿状态，微信手机终审由用户完成。自动化到草稿箱为止，不执行群发或默认同步其他平台。

扩展功能的文档保留在 references/（贴图、多平台），仅在用户明确需要时读取；其中示例账号、可选手绘风或命令示例不覆盖微墨的账号配置、学术风与固定出口规则。
