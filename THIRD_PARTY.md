# 运行依赖

本项目通过包管理器安装以下组件，不把其源码作为本项目自有代码重新分发：

| 组件 | 用途 | 上游与许可 |
| --- | --- | --- |
| markdown-it-py | Markdown 词法与结构解析 | https://github.com/executablebooks/markdown-it-py · MIT |
| requests | HTTP 客户端 | https://github.com/psf/requests · Apache-2.0 |
| PySocks | SOCKS 代理支持 | https://github.com/Anorov/PySocks · BSD-3-Clause |
| PyYAML | 本机配置与文稿元数据 | https://github.com/yaml/pyyaml · MIT |
| Pillow | 图片读取与封面裁剪 | https://github.com/python-pillow/Pillow · MIT-CMU |

传递依赖以及测试工具遵循各自发行包所附许可。将依赖打包分发时，需要一并保留对应许可。微信与图片服务的名称用于说明接口兼容性，不表示官方隶属关系。
