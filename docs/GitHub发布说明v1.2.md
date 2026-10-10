# GitHub 提交说明 v1.2

日期：2026-10-10。用户已授权提交到项目库，当前仓库为[TUANZIDING/storysprout](https://github.com/TUANZIDING/storysprout)，可见性private。内容版本v1.2.0，仍为文档与内容设计仓库，应用尚未实现。

## 当前入口

- 中文：首页README.md与快照READMEv1.2.md一致。
- 完整英文首页：docs/英文说明v1.1.md。
- 第一章方案：docs/第一章内容设计v1.1.md，正文和五页内容保持原设计。
- 当前范围：提交范围v1.1.json，34个文件。
- 当前检查：scripts/仓库检查v1.1.py；GitHub工作流为.github/workflows/仓库检查v1.1.yml。
- 来源、许可和协作说明分别使用docs/素材与许可说明v1.1.md和docs/协作说明v1.1.md。

旧版本保留历史记录；旧工作流已在当前版本替换，Git历史仍保留旧文件。旧版检查脚本与清单只描述初始候选，当前执行入口使用v1.1检查脚本。

## 分支与提交

本地及远端默认分支为codex/storysprout-submission。初次上传提交为7cb6b90；后续首页状态同步沿此分支提交。原codex/storysprout-prompts仅保留在本机，没有推送。

只推送候选分支，不使用--all或--mirror。参考PDF、视频、音频、环境和凭据不在提交范围内。本地第一章v1.0仍保持原样，由.gitignore排除。

## 检查与维护

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r 检查依赖v1.0.txt
.venv/bin/python scripts/仓库检查v1.1.py
```

暂存后增加--check-index核对文件范围和暂存内容。GitHub Actions同样执行此检查，使用只读权限、Python 3.12和固定Action提交。[查看远端检查](https://github.com/TUANZIDING/storysprout/actions)。

首页沿用用户指定的github-homepage-style结构，中英入口、状态和引用同步。封面为原创概念SVG，应用截图、实际插画和音频均未制作。README.md与.gitignore是工具固定入口；自主命名文件均带版本且无下划线。

## 已提交与未执行

已创建私人远端并上传文档；初次远端文件与本地Git对象核对一致，检查流程通过。核验层次见[远端提交记录](远端提交记录v1.0.md)。GitHub服务器生成的README HTML与真实浏览器视觉复核分别记录。

没有公开发布、创建GitHub Release、选择开源许可证或部署应用。原书、课程词表和儿童试读仍待确认；素材范围保持私人仓库。改变仓库可见性、整本书制作、应用开发与在线生成服务按后续明确指令执行。
