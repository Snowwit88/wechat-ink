# 微墨 2 · WeChat Ink v2

> **新版入口｜2.0.0.dev1｜待真实服务验收**
>
> 新版目录：`wechat-ink-v2` · 技能名称：`wechat-ink-v2` · 安装包：`wechat-ink-v2-candidate.zip`
>
> 第一版已保存在同一仓库的 `legacy-v1` 分支。

把资料整理成文章，把文章变成可预览、可检查的微信公众号草稿。

这是新版实现的本地候选版。核心工具使用 Python，写作与资料核查由承载技能的 AI 助手完成。默认学术排版、七张配图计划、独立的 16:9 封面、固定出口发布和草稿回读集中在一套入口中。

## 安装

需要 Python 3.10 或更新版本。运行：

```sh
python3 install.py
```

安装到 `~/.codex/skills/wechat-ink-v2`，不会覆盖已有技能。修改安装目录的 `wechat-ink.yaml`，填入自己的公众号、图片服务和固定出口配置。配置只保存在本机，不能提交到公开仓库。

如果目录已存在，可通过 `--target` 选择另一个目录。依赖安装失败时，文件会保留，可用安装目录虚拟环境重新安装 `requirements.txt`。

## 给助手的使用提示词

> 使用 wechat-ink-v2 技能，根据我提供的主题和资料制作公众号文章。先核对资料，再写作和审校；使用学术风格，准备一张封面和六张正文配图。先展示本地预览，检查参考资料和手机排版。真实生图使用我已配置的服务。创建草稿前验证固定出口，完成后回读草稿；不要正式群发。

真实生图和微信操作需要可用的账号配置与用户授权；没有配置也可以写作、审校和预览。

## 本地运行

下面命令从技能目录运行，`PYTHON` 指向依赖已安装的 Python：

```sh
$PYTHON scripts/ink.py doctor
$PYTHON scripts/ink.py audit examples/article.md --expected-images 7
$PYTHON scripts/ink.py render examples/article.md -o output/preview.html
$PYTHON scripts/ink.py plan examples/article.md -o output/images.json
$PYTHON scripts/ink.py images output/images.json --output output/images
```

配图计划只是提示词草案，需要先审阅内容。生成得到 `00.png` 至 `06.png`；原图保留，另外输出裁剪后的 `cover.png`。已有有效图片会跳过，生成服务按实际请求计费。修改提示词后需要换输出目录，避免复用旧图。

预览是自包含 HTML，本地图片内嵌其中，可直接发给朋友查看。文稿中的图片路径仍相对于 Markdown 文件，发布前需要更新到实际生成文件。

## 创建微信草稿

先在本机 YAML 设置 `egress`，其中 `expected_ip` 必须是公众号白名单中的固定 IPv4。SSH 只提供 SOCKS 转发，文件与公众号凭证保留在本机。

```sh
export WECHAT_INK_PYTHON=/absolute/path/to/python
export WECHAT_INK_CONFIG=/absolute/path/to/wechat-ink.yaml
bash operations/wechat-egress.sh start
bash operations/wechat-egress.sh check
bash operations/wechat-egress.sh publish \
  --input /absolute/path/to/article.md \
  --cover /absolute/path/to/cover.png
```

只有固定出口校验成功才会继续。失败不回退到本机网络。发布只创建草稿，不提供群发入口。

同一文稿、图片和发布参数会对应一个本地记录。重复执行会回读已有草稿。接口超时且不能确定是否成功时，保留待核对记录并停止；人工查明草稿箱状态前，不删除记录重试。记录保存在文稿旁的 `output`，可通过 `--output` 更换。

## 当前验证范围

- Markdown、标题元数据、图片、列表、引用、表格、代码和裸 URL 参考资料。
- 默认 `academic-paper` 对齐常用字号、字体与图片间距；其他 14 个主题名提供新版配色，**不代表旧版全部视觉细节一致**。
- 配图接口、封面裁剪、草稿上传与回读、重复提交保护有离线测试。
- 新版不依赖旧版脚本、旧版配置加载器或旧版安装目录。
- `newspic` 为实验入口；没有真实微信联调证据。跨平台同步、浏览器 Cookie 生图和旧版自定义样式 JSON 未迁入。
- 本地预览不等于微信客户端最终渲染；真实生图与草稿箱验收仍待执行。

开发者测试：`python -m pytest -q`（项目根目录，另行安装 pytest）。详细结果见 `VALIDATION.md`。

## 开源

本目录新编写的代码和文档采用 MIT，见 LICENSE。运行依赖的许可见 THIRD_PARTY.md。第一版保留为对照，不包含在新版安装包中。
