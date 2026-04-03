# Simple Blog

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Yunz93/simple-blog)

一个简洁现代的静态博客系统，专为开发者设计。

## 特性

- 🚀 **一键部署** - Vercel 一键部署，自动 HTTPS + 全球 CDN
- 📝 **Markdown 支持** - 完整支持 Markdown 语法，包括代码高亮
- 🏷️ **分类与标签** - 通过 YAML Frontmatter 实现灵活的分类和标签过滤
- 🔍 **全文搜索** - 内置搜索功能，Cmd/Ctrl+K 快速唤起
- 🎨 **现代设计** - 简洁优雅的仓耳今楷字体，支持深色模式
- 📱 **响应式** - 完美适配桌面和移动设备
- 🔗 **markdown-press 对接** - 支持从 markdown-press 项目快速发布

## 快速开始

### 一键部署到 Vercel

点击下方按钮，1 分钟完成部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Yunz93/simple-blog)

部署完成后，Vercel 会自动分配域名（如 `simple-blog.vercel.app`）。

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/Yunz93/simple-blog.git
cd simple-blog

# 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r build-requirements.txt

# 创建文章
echo "---
title: Hello World
date: 2026-03-31
category: 随笔
tags: [开始]
---

Hello, Simple Blog!" > posts/hello.md

# 构建
bash ./build.sh

# 本地预览
cd dist && python3 -m http.server 8080
```

访问 http://localhost:8080

## 部署方式

### Vercel（推荐）

**一键部署**

点击上方 "Deploy with Vercel" 按钮，按提示完成部署。

**命令行部署**

```bash
# 安装 Vercel CLI
npm install -g vercel

# 登录
vercel login

# 部署
./deploy-vercel.sh
```

**GitHub 自动部署**

1. 在 Vercel 导入 GitHub 仓库
2. Framework Preset 选择 `Other`
3. Build Command 使用 `bash ./build.sh`
4. Output Directory 使用 `dist`
5. 每次 `git push` 自动部署，Pull Request 自动生成预览链接

详细配置见 [DEPLOY.md](./DEPLOY.md)

## 对接 markdown-press

### 目录结构

```
markdown-press/          # 你的写作项目
├── posts/               # Markdown 文章
└── blog/                # simple-blog（子目录）
    ├── config.yaml      # posts_source: "../posts"
    └── deploy-vercel.sh
```

### 快速对接

```bash
cd /path/to/markdown-press

# 添加 simple-blog
git clone https://github.com/yourname/simple-blog.git blog
cd blog

# 配置文章源
echo 'posts_source: "../posts"' >> config.yaml

# 部署到 Vercel
./deploy-vercel.sh
```

如果你是通过 Vercel 直接导入这个仓库，构建环境只能读取仓库内文件，不能读取仓库外部的 `../posts`。
这时建议：

1. 将文章同步到当前仓库的 `posts/` 目录后再部署
2. 或在 CI 中先拉取 `markdown-press` 内容，再执行 `bash ./build.sh`

更多对接方案见 [MARKDOWN_PRESS_INTEGRATION.md](./MARKDOWN_PRESS_INTEGRATION.md)

## 项目结构

```
simple-blog/
├── build.py              # 构建脚本
├── deploy-vercel.sh      # Vercel 部署脚本
├── config.yaml           # 博客配置
├── vercel.json           # Vercel 配置
├── build-requirements.txt # Python 构建依赖
├── template/             # HTML 模板
├── static/               # 静态资源
├── posts/                # Markdown 文章
├── dist/                 # 输出目录
└── .github/workflows/    # GitHub Actions
```

## 配置文件

`config.yaml`：

```yaml
title: "Simple Blog"
description: "爱吾所爱，一生自在"
author: "BXYZ"
url: "https://your-blog.vercel.app"
posts_per_page: 10

# 对接 markdown-press
posts_source: "../posts"

# 社交链接
social:
  github: "yourname"
  twitter: "yourname"
  email: "your@email.com"

footer: "© 2026 Simple Blog"
```

## 文章格式

```markdown
---
title: "文章标题"
date: 2026-03-31
category: "技术"
tags: ["Python", "Web"]
description: "文章简介"
draft: false
---

正文内容，支持 Markdown 语法...
```

## 自定义主题

编辑 `static/css/style.css` 中的 CSS 变量：

```css
:root {
    --primary: #2563eb;
    --background: #ffffff;
    --text-primary: #0f172a;
    /* ... */
}
```

## 字体

使用 [仓耳今楷 (TsangerJinKai02)](https://tw93.fun/) 作为中文字体，优雅清晰。

## License

MIT License
