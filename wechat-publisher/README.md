# 微信公众号技能 · 朋友可用版

这是一份独立分享包，包含写作规范、学术风主题、配图、排版、审校和微信草稿工具。没有分享者的账号、密钥、服务器配置、文章或历史图片。

## 最简单的开始方式

解压后，把这个文件夹交给你的 AI 客户端，并发送：

> 请阅读此文件夹里的 SKILL.md 和 README.md，帮我安装并检查微信公众号技能。先跑离线演示，不调用生图或微信接口，不覆盖我已有技能或配置。告诉我还缺哪些配置，密钥由我在本机填写。

AI 客户端需要能读取本地文件并运行 Python；写作调研还需要联网搜索能力。网页版聊天仅上传压缩包不等于完成本地安装。

## 安装（Python 3.10 或更高版本）

外层 `install.py` 可复制技能到默认 `~/.codex/skills/wechat-publisher`（如设置 CODEX_HOME 则跟随），并建立独立运行环境：

```sh
python3 install.py
```

Windows 原生命令通常为 `py install.py`。需要联网从 Python 包仓库安装依赖。安装器不会覆盖已有目录；若已安装同名技能，请先自行选择保留方案。可以用 `--target /你的/技能目录/wechat-publisher` 指定目标，用 `--skip-deps` 只复制，稍后自行安装 requirements.txt。若中途依赖下载失败，按终端提示重试，不要重复覆盖安装。

其他客户端可以直接读取 SKILL.md 执行；自动发现技能的安装位置由各客户端决定。本包未逐一验证其他客户端。

## 不填密钥也能先试排版

进入安装后的技能文件夹，运行：

```sh
.venv/bin/python scripts/html_converter.py examples/article.md --theme academic-paper -o examples/preview.html
.venv/bin/python -m pytest tests/ -q
```

用浏览器打开 examples/preview.html。示例是纯文字排版演示，不是可发布成稿。Windows 原生把 `.venv/bin/python` 换为 `.venv/Scripts/python.exe`。

## 自己填配置

安装器已从示例创建空白 `wechat-publisher.yaml`。填写：

- `accounts.main.name`、`author`、`voice`：你的公众号名称、署名和文风。
- `app_id`、`app_secret`：你自己公众号的开发者凭证；只写本机文件，不发聊天或截图。
- `image_generation.openai.api_key`、`base_url`、`image_model`：你自己的图片生成服务。完整基础地址需含 `/v1`。

本项目原兼容后端使用 gpt-image-2、1792×1024；这不是对所有服务商的兼容承诺。需确认你的服务支持该模型、尺寸和 b64_json 返回格式。默认采用 Python simple_gen.py，无需 Bun；选用多后端 generate_image.py 时才需另装 Bun。内置 ImageGen 兜底仅在客户端实际提供该工具时有效，普通 Python 无法调用它。

配置好生图后可让 AI：

> 使用 wechat-publisher 围绕“你选择的主题”研究并写一篇公众号文章。先核对原始来源，使用学术风排版，制作 1 张封面和 6 张正文图，交付文稿与本地预览，暂不创建微信草稿。

生成图片会使用你自己的服务额度。修改主题和文风只需改配置，不要修改源码。

## 自动进微信草稿箱（可选）

需要公众号拥有相关 API 权限、自己的固定出口服务器，以及把该固定 IPv4 加入你公众号的 IP 白名单。固定出口服务器只转发网络流量，文章、图片和凭证仍留在本机。

1. 在技能目录复制 `operations/wechat-egress.example.env` 为 `operations/wechat-egress.local.env`。
2. 填自己的服务器地址、SSH 用户、预期出口 IPv4；默认使用 SSH 密钥认证，需密码认证可改为 password。示例会自动定位安装目录，无需复制别人的本机路径。
3. Mac/Linux 需要 Bash、OpenSSH、curl、lsof。Windows 请在 WSL 中安装整套技能和依赖并运行出口脚本，不复用 Windows 虚拟环境。
4. 让 AI 按 SKILL.md 运行 start、check、token-check，全部成功后再创建草稿和回读。检查失败不绕过。

如果没有服务器或公众号 API 权限，仍可完成文稿、配图和预览，随后手动在微信后台编辑图文；自动草稿功能暂不可用。

## 注意与交付范围

- 没有永久安装后台任务，不自动群发，不默认同步其他平台。
- 写稿的事实核验、手机视觉检查和微信终审仍需认真完成；风格分数不保证 AI 检测结果。
- 不要再次分享你的真实 YAML、local.env、Token 缓存、日志或私有文章。
- 本包验证范围见外层 `验证说明.md`。离线测试不能替代你的账号、白名单和生图服务实测。
