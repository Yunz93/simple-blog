---
aliases: 基于Obsidian发布静态博客
slug: obsidian-digital-garden
category: Tools
tags:
  - obsidian
status: done
link: https://yunz93.dev/posts/obsidian-digital-garden/
date created: 2022-12-27 Tue 23:02:54
date modified: "2026-04-10"
is_publish: true
title: 基于Obsidian发布静态博客
---

## [obsidian](https://obsidian.md)

提供了 Zettelkasten 卡片笔记方法与双向链接的能力，即你的笔记不再是一篇篇长篇大论的文章，而是由一个个小的 topic 汇聚而成。每一个小的 topic 只关注一个主题，可能是一个问题和一个答案，也可能是一个小的知识点。所有的 topic 可以按需整合，重复使用。

我从 22 年的 10 月份开始从 Typora 脱离，寻找新的笔记工具。Typora 是一个优秀的 md 编辑器，但不是一个合格的笔记管理器（人家确实也志不在此）。随着笔记数量的增多，采取文件层级式的管理，使用 Typora 确实有点力不从心。比如文件搜索，你需要牢牢记住笔记的存放位置，或者使用 Listary 类似的搜索工具。再比如笔记文件切换，图片附件的所有链接都需要逐个修改，简直要命。

目前支持 md 的笔记软件众多，但我首先 pass 了纯云端的笔记应用，支持本地存储是第一原则，而 ob 就是其中的佼佼者。

得益于 Obsidian 出色的基础设计和活跃的社区环境，提供了大量的开源插件可以实现各种自定义的功能。基于两个月的调教，自我感觉现在 ob 的编辑体验已经超过 typora，当然表格编辑除外。（我个人不太喜欢在 md 文章中插入很多表格，所以其实也无所谓。）

Obsidian 的使用后面我会单独再写一篇文章：[基于Obsidian构建个人知识库](https://yunz93.dev/posts/obsidian/)。（如果点进去没有文章，说明我还没写好😄）

## [obsidian-digital-garden](https://github.com/oleeskild/obsidian-digital-garden)

ODG 是 [oleeskild](https://github.com/oleeskild) 提供的一个 ob 的博客发布插件，比官方的发布服务更优。

有如下几个优点：

- 保留本地知识库的结构，主题也可以同步，支持搜索、目录树、关系图谱等基础功能；
- 通过对文章添加 tag 的方式选择性发布，自定义快捷键一键发布，自动部署更新；
- 支持自定义修改；

目前可以达到的效果：快速编辑，自动格式化，一键发布，自动部署。

总之就非常好用，强力推荐。