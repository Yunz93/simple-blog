# 对接 markdown-press 发布指南

## 什么是 markdown-press？

`markdown-press` 是一个基于 Markdown 的写作/出版工作流项目，通常包含：
- Markdown 格式的文章源文件
- 图片等静态资源
- 可能的元数据配置

## 对接方案

### 方案一：目录嵌套（最简单）

将 simple-blog 放入 markdown-press 项目内：

```
markdown-press/
├── posts/              # 你的文章
├── images/             # 你的图片
└── blog/               # simple-blog 目录
    ├── build.py
    ├── build.sh
    ├── deploy-vercel.sh
    └── config.yaml     # 修改 posts_source: "../posts"
```

修改 `blog/config.yaml`：
```yaml
posts_source: "../posts"  # 指向外部文章目录
```

发布：
```bash
cd markdown-press/blog
bash ./build.sh
./deploy-vercel.sh
```

### 方案二：Git 子模块

适合分开管理博客源码和文章：

```bash
# 在 markdown-press 项目中
git submodule add https://github.com/Yunz93/simple-blog.git blog
git submodule update --init

# 修改配置
echo "posts_source: '../posts'" >> blog/config.yaml

# 提交
git add .gitmodules blog
git commit -m "Add simple-blog as submodule"
```

更新博客模板：
```bash
cd blog
git pull origin main
cd ..
git add blog
git commit -m "Update blog template"
```

### 方案三：符号链接（开发环境）

```bash
cd /path/to/simple-blog
ln -s /path/to/markdown-press/posts ./posts

# 现在直接运行
bash ./build.sh
```

### 方案四：独立部署（CI/CD）

在 GitHub Actions 或其他 CI 中自动拉取 markdown-press 并构建。
注意：Vercel 直接导入 `simple-blog` 仓库时，构建环境不能读取仓库外部的 `../posts`，所以需要先把文章同步进当前工作区。

1. 配置 GitHub Secrets：
   - `GH_PAT`: GitHub Personal Access Token（访问 markdown-press 私有仓库）

2. 推送代码后自动部署：
   ```bash
   git push origin main
   ```

3. CI 会自动：
   - 检出 simple-blog
   - 检出 markdown-press
   - 同步文章
   - 执行 `bash ./build.sh`
   - 将 `dist/` 部署到 Vercel

## 文章格式要求

markdown-press 的文章需要符合以下格式：

```markdown
---
title: "文章标题"
aliases: "article-title-en"
slug: "article-title-url"
date: 2026-03-31
category: "技术"
tags: ["Python", "Web"]
description: "文章简介"
draft: false
---

正文内容，支持 Markdown 语法...
```

### 支持的 Frontmatter 字段

| 字段 | 必需 | 说明 |
|------|------|------|
| `title` | ❌ | 文章标题，未填时回退为文件名（文章标题） |
| `aliases` | ❌ | 文章英文名，未填时回退为文章标题 |
| `date` | ❌ | 发布日期（YYYY-MM-DD）|
| `category` | ❌ | 分类名称 |
| `tags` | ❌ | 标签数组或逗号分隔字符串 |
| `description` | ❌ | 文章描述/摘要 |
| `draft` | ❌ | 草稿标记（true 不发布）|
| `slug` | ❌ | 文章发布 URL 后缀，未填时回退为文章标题 |

约定：

- 文章标题默认就是文件名
- `frontmatter.title`、`frontmatter.aliases`、`frontmatter.slug` 建议手动填写
- 若这些字段缺失或留空，系统会统一回退到文章标题

## 图片处理

如果 markdown-press 的图片在单独目录：

### 方法 1：复制到 simple-blog
```bash
bash ./build.sh
```

### 方法 2：配置静态资源路径
修改 `build.py` 中的图片处理逻辑，或手动复制：

```bash
cp -r ../markdown-press/images static/
```

然后在 Markdown 中引用：
```markdown
![描述](/static/images/photo.png)
```

## 多语言支持

如果 markdown-press 有多个语言目录：

```
posts/
├── zh/              # 中文文章
└── en/              # 英文文章
```

修改 `config.yaml`：
```yaml
posts_source: "../posts/zh"  # 指定语言
```

## 常见问题

### Q: 文章更新后没有生效？
A: 检查 publish.sh 是否正确同步了文章，或手动运行：
```bash
rm -rf posts/*
cp -r /path/to/markdown-press/posts/* posts/
bash ./build.sh
```

### Q: 如何排除某些文章？
A: 在文章的 Frontmatter 中设置 `draft: true`

### Q: 如何自定义 URL 结构？
A: 使用 `slug` 字段：
```yaml
---
title: "我的文章"
slug: "my-custom-url"
---
```
生成 URL: `/posts/my-custom-url/`

### Q: markdown-press 使用 Obsidian/Notion 导出？
A: 大多数工具导出的 Markdown 都兼容，注意检查：
- 图片路径是否正确
- YAML Frontmatter 格式是否标准
- 特殊语法（如 WikiLink）是否需要转换

## 最佳实践

1. **版本控制**：将文章和博客模板分开管理
2. **自动化**：使用 GitHub Actions 自动发布
3. **预览**：本地运行 `bash ./build.sh` 预览后再提交
4. **备份**：定期备份 markdown-press 文章源

## 示例工作流

```bash
# 日常写作流程
cd /path/to/markdown-press
vim posts/new-article.md      # 写新文章
git add . && git commit -m "Add new article"
git push

# 发布流程
cd blog
bash ./build.sh                # 构建并预览
git add dist && git commit -m "Update site"
git push origin main          # 触发自动部署
```
