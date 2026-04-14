---
category: creation
tags:
  - vibe-coding
status: done
slug: markdown-press
aliases: M记
is_publish: true
create_time: "2026-04-09"
update_time: "2026-04-14 23:13:31"
title: M 記
---

# M 記

![M 記-1776170252301.png](https://raw.githubusercontent.com/Yunz93/bxyz-blog/main/resource/M-4dd9e/01-M-1776170252301.png)

项目地址：[M 記](https://github.com/Yunz93/markdown-press)

## 楔子

> 这是我理想中 Markdown 编辑器应该有的样子，希望你也会喜欢。

最早的时候我使用的是 typora，因为他的实时预览模式很优秀，所以当软件转向收费的时候也购买了 license，后面放弃是因为在文件管理部分不尽如人意。文件一更换路径，附件就全挂了，需要手动一个个修改，很麻烦。

最近几年一直在使用 Obsidian，因为 Obsidian 优秀的插件机制，使得他的自定义程度极高。我安装了 30+的插件，自动化工作流的体验确实非常好。具体见[基于Obsidian构建个人知识库](https://yunz93.dev/posts/obsidian/)

动手的契机是公司开始清理第三方未授权的商业软件，所以被迫放弃 Obsidian，想着自己写一个介入 Obsidian 和 Typora 中间形态的编辑器，比 Typora 的知识库管理能力更强，比 Obsidian 更易上手。

这里很感谢[妙言](https://miaoyan.app/)，中间使用过一段时间，简洁优雅，非常推荐。M 記的 UI 和交互逻辑深受其影响，但因为关于知识库管理的想法还是不太一样，我认为`Mind is deep`，两级目录不太适合我的知识库，而且很多想法构建在别人的基座上不太好发挥，所以我还是决定自己做一个属于自己的知识库软件。

> 最早我是用 AI studio 搓了一个简单的在线版本，后面因为本地文件交互一直有问题，就又拿 codex 和 claude code 重写了一遍，前后打磨了 2 个多月，目前达到了一个基本可用的状态。

## 关键能力

- 基于 Tauri 2 构建，极度轻量，多端支持；
- 极简 UI 的同时高度自定义，美观易用；
- AI 加持，自动知识库生成；
- 一站式，从知识管理到博文发布，端到端搞定。

> 目前在 MacOS 上日常使用，进行了比较详尽的测试，windows 未细致测试，有问题可以提 issue。

## 功能介绍

- 标准 Markdown 语法支持
- Obsidian 内链语法支持
- 文章内容保存自动 format
- 全局快捷键操作
- 全库文章内容检索
- AI 辅助，自动生成目标内容的解释性 wiki
- 一键博客发布（依赖部署关联的 simple-blog 项目）
- 支持自定义图床
- 明亮/暗黑模式切换
- 编辑/分屏/预览模式切换
- 预置字体，支持字体切换
- 多 tab 文件切换
- 附件一键清理，附件移动自动更新关联文章的链接

> 实时编辑预览的功能未实现，尝试了几次，稳定性太差，先不考虑了。

## 快捷键说明

- 打开设置页：`cmd + shift + 0`
- 侧边栏开合：`cmd + shift + B`
- 目录栏开合：`cmd + shift + O`
- 编辑模式切换：`cmd + shift + V`
- 明亮/暗黑模式切换：`cmd + shift + T`
- 全局搜索：`cmd + shift + S`
- 文章内搜索：`cmd + shift + F`
- 切换知识库：`cmd + shift + K`
- 定位到当前文章位置：`cmd + shift + L`

## 后记

还有很多 idea 需要慢慢实现，希望 M 記能成长为一个 AI 时代的知识库笔记软件，有使用上的问题欢迎提 issue，感谢。