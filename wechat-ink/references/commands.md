# 命令

在技能根目录，使用依赖已安装的 Python（安装后为 `.venv/bin/python`）。

- `scripts/ink.py doctor`：只检查配置存在状态。
- `scripts/ink.py audit ARTICLE --expected-images 7`：编辑与图片检查。
- `scripts/ink.py render ARTICLE -o PREVIEW --theme academic-paper`：生成可独立查看的 HTML；`--fragment` 输出微信正文片段。
- `scripts/ink.py themes`：列出主题名。
- `scripts/ink.py plan ARTICLE -o PLAN --count 7`：生成可修改的配图计划。
- `scripts/ink.py image PROMPT OUTPUT --size 1792x1024`：单张生图。
- `scripts/ink.py images PLAN --output DIRECTORY`：顺序生图并制作 cover.png。
- `scripts/ink.py --config CONFIG --account NAME publish --input ABSOLUTE_ARTICLE --cover ABSOLUTE_COVER --dry-run`：无网络预检。

真实微信操作统一通过 `operations/wechat-egress.sh`：

- `start` / `check` / `stop`：管理、验证本机 SSH SOCKS 通道。
- `token-check`：校验公众号访问，不打印 token。
- `publish --input ABSOLUTE_ARTICLE --cover ABSOLUTE_COVER [--title TITLE] [--author AUTHOR] [--digest DIGEST] [--theme THEME]`：创建并回读图文草稿。
- `draft-get MEDIA_ID` / `draft-list`：回读指定草稿或查看前 20 条。

通过 `WECHAT_INK_PYTHON` 指定 Python，通过 `WECHAT_INK_CONFIG` 指定 YAML。全局 `--config`、`--account` 参数在直接命令中必须放在子命令前。

图像错误排查：403/1010 可能是中转站客户端指纹拦截，不足以判断密钥或额度失效。微信 41005 不直接代表图片太大；检查文件、请求并顺序重试素材上传。草稿写入请求超时必须先查远端状态。
