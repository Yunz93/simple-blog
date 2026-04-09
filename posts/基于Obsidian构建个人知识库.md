---
aliases: 基于Obsidian构建个人知识库
slug: obsidian
category: tools
tags:
  - obsidian
  - 知识库
status: done
link: NA
date created: 2023-01-02 Mon 19:33:43
date modified: "2026-04-09"
is_publish: true
title: 基于Obsidian构建个人知识库
---

关于 Obsidian 软件，在 [基于Obsidian发布静态博客](https://yunz93.dev/posts/obsidian-digital-garden/) 中已有介绍，本文主要说明如何搭建自己的个人知识库。

## 效果

![Pasted image 20230105222339](https://github.com/Yunz93/PicRepo/raw/main/image/Pasted%20image%2020230105222339.png)

主要实现功能如下：

- command + control + B：创建博客，输入文章名称，再输入文章类别，会依据模版创建文章并自动移动到对应目录下；
- command + control + D：依据模板创建当天日记，与前后一天的日记自动建链；
- 通过 dataview 访问文章元数据，博客自动显示在对应的索引文件中；![Pasted image 20230105224044](https://github.com/Yunz93/PicRepo/raw/main/image/Pasted%20image%2020230105224044.png)
- 通过 memos 实现间歇式日记，可以方便地将事项和代办记录到当天的日记中，未完成的代办事件通过 checklist 会显示在右边栏方便跟踪；![Pasted image 20230105224348](https://github.com/Yunz93/PicRepo/raw/main/image/Pasted%20image%2020230105224348.png)
- 通过 Linter 实现文章的自动格式化，元数据自动补齐更新；

## 博客框架

```plantuml
@startmindmap
+ blog
++ Creation 创造与实践
++ Learn 学习总结
++ Share 分享
++ Thought 心得体会
++ Life 生活随笔
@endmindmap
```

## 插件列表

- Dataview 笔记数据可视化
- Home Page 主页插件
- Tasks + Checklist 任务跟踪
- Calendar 日历插件，可以和 Templater、Memos 配合使用
- Memos 随手日记
- Templater + QuickAdd 快捷模版
- Linter md 文档自动格式化
- Admonition md 文档 tips 增强
- Clear unused images 自动清理未使用图片（typora 看哭了）
- Digital garden ob 文档发布