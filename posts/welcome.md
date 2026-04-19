---
title: "欢迎使用 Simple Blog"
date: 2026-03-31
category: "指南"
tags: ["开始", "博客", "教程"]
description: "欢迎使用 Simple Blog，这是一篇示例文章，介绍如何使用这个简洁现代的静态博客系统。"
---

## 关于 Simple Blog

Simple Blog 是一个简洁现代的静态博客系统，专为开发者设计。它具有以下特点：

- 🚀 **一键发布** - 支持从 markdown-press 项目快速发布
- 📝 **Markdown 支持** - 完整支持 Markdown 语法，包括代码高亮
- 🏷️ **分类与标签** - 通过 YAML Frontmatter 实现灵活的分类和标签过滤
- 🔍 **全文搜索** - 内置搜索功能，快速找到需要的文章
- 🎨 **现代设计** - 简洁优雅的界面，支持深色模式

## 快速开始

### 1. 安装依赖

```bash
pip install -r build-requirements.txt
```

### 2. 创建文章

在 `posts/` 目录下创建 Markdown 文件：

```markdown
---
title: "我的文章标题"
date: 2026-03-31
category: "技术"
tags: ["Python", "Web"]
description: "文章简介"
---

文章内容...
```

### 3. 构建博客

```bash
bash ./build.sh
```

### 4. 部署

将 `dist/` 目录部署到任意静态托管服务即可。

## Markdown 语法支持

### 代码块

```python
def hello_world():
    print("Hello, Simple Blog!")
```

### 表格

| 特性 | 支持 |
|------|------|
| Markdown | ✅ |
| 代码高亮 | ✅ |
| 数学公式 | 计划中 |

### 引用

> 这是一个引用块，用于突出显示重要内容。

## 结语

感谢使用 Simple Blog！如有问题，欢迎反馈。
