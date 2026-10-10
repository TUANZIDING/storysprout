# GitHub 提交说明 v1.1

当前目标：可提交的文档与内容设计仓库，版本v1.1.0。远端仓库、公开Release和应用部署均未执行。

## 仓库信息

建议名称：storysprout。可用性在实际创建远端时确认。

中文简介：儿童漫画伴读的内容设计、创作提示词与数据契约；规划图文同源编辑和逐句跟读，应用尚未实现。

English description: Content design, prompts and data contracts for children's comic companions and sentence-by-sentence read-along. Application not implemented yet.

当前建议可见性：private。候选含既有作品相关第一章设计，尚未确认公开分发范围。不要将当前候选自动当作公开开源发布。

## 当前入口与提交范围

- 中文首页：README.md；版本快照：READMEv1.1.md。
- 完整英文首页：docs/英文说明v1.0.md。
- 最新第一章方案：docs/第一章内容设计v1.1.md，去掉本机路径，正文与上一轮保持一致。
- 明确文件列表：提交范围v1.0.json。检查脚本用此列表检查文件、引用及Git索引；ZIP也仅使用此列表。
- 本地原方案 docs/第一章内容设计v1.0.md 保持原样，列为 localOnly 并排除，不进入新提交或提交包。
- 所有参考PDF、视频、音频、环境配置与凭据不进入候选。

## 本地检查

需要Python 3.12；依赖安装在独立环境，不修改应用或接入生成服务。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r 检查依赖v1.0.txt
.venv/bin/python scripts/仓库检查v1.0.py
```

`.venv`是工具环境目录，会被Git排除。Windows可用环境内的Python执行同一脚本。暂存后增加 `--check-index` 检查实际提交范围。

GitHub Actions文件已经准备，使用只读权限及固定的Action提交；尚未在远端运行。不放“CI通过”或“最新Release”徽章。

## 提交与历史

收尾使用独立的 codex/storysprout-submission 分支，只有当前候选的一个根提交，避免把旧自动配置的本机提交身份带入候选。原 codex/storysprout-prompts 分支保持原样。新提交使用当前已验证GitHub账号的noreply身份，只影响此仓库配置。

后续仅推送候选分支；不使用 `--all` 或 `--mirror` 推送本地其他分支。创建远端与推送须按用户随后明确授权执行，本说明不含已经执行的远端命令。

## 首页与命名

按 github-homepage-style 的固定入口规则使用README.md，并保留带版本首页快照；自主命名的文档、图片、脚本与清单均带版本且无下划线。没有应用界面截图，所以首页展示真实文档成果及注明性质的概念封面。

## 本轮检查边界

本地内容、文件、图像引用、锚点、正文、契约和提交包按检查记录验收。GitHub远程文件、真实GitHub页面渲染及浏览器显示尚未验证；不能用本地预览代替远端视觉复核。参见 交付检查v1.1.md。
