# Vercel 部署指南

## 一键部署

点击下方按钮，1 分钟完成部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Yunz93/simple-blog)

部署完成后：
- 自动分配 HTTPS 域名（如 `simple-blog.vercel.app`）
- 全球 CDN 加速
- 每次 `git push` 自动重新部署

## 命令行部署

### 1. 安装 Vercel CLI

```bash
npm install -g vercel
```

### 2. 登录

```bash
vercel login
```

### 3. 部署

```bash
# 使用脚本一键部署
./deploy-vercel.sh

# 或手动部署
vercel --prod
```

## GitHub 自动部署

### 1. 导入仓库

1. 访问 [vercel.com](https://vercel.com)
2. 点击 "Add New Project"
3. 选择你的 GitHub 仓库
4. Framework Preset: "Other"
5. Build Command: `bash ./build.sh`
6. Output Directory: `dist`
7. 点击 "Deploy"

### 2. 配置自动部署

Vercel 会自动：
- 监听 `git push` 事件
- 为 Pull Request 生成预览链接
- 合并到 main 分支后自动部署生产环境

### 3. 配置 Secrets（可选）

如果需要对接私有 markdown-press 仓库：

1. 在 Vercel Dashboard > Project Settings > Environment Variables 添加：
   - `ENABLE_MARKDOWN_PRESS`: `true`
   - `MARKDOWN_PRESS_REPO`: `yourname/markdown-press`
   - `GH_PAT`: 你的 GitHub Personal Access Token

2. 修改 `vercel.json`：

```json
{
  "buildCommand": "bash ./build.sh",
  "outputDirectory": "dist"
}
```

说明：
- `build.sh` 会自动创建虚拟环境并安装 `build-requirements.txt`
- 直接使用 `python build.py` 会漏掉 Python 依赖安装
- 通过 Vercel 直接导入仓库时，只能访问仓库内文件，无法读取仓库外部的 `../posts`
- 项目根目录不要保留 `requirements.txt`，否则 Vercel 会按 Python 应用去查找入口文件

## 自定义域名

### 添加域名

1. Vercel Dashboard > Project Settings > Domains
2. 输入你的域名（如 `blog.example.com`）
3. 按提示添加 DNS 记录：
   - CNAME 记录指向 `cname.vercel-dns.com`

### 自动 HTTPS

Vercel 自动为所有域名配置 HTTPS 证书，无需额外操作。

## 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `ENABLE_MARKDOWN_PRESS` | 启用 markdown-press 同步 | 否 |
| `MARKDOWN_PRESS_REPO` | markdown-press 仓库名 | 否 |
| `GH_PAT` | GitHub Personal Access Token | 否 |

## 安全建议

### Token 管理

1. **VERCEL_TOKEN**：
   - 在 [Vercel Settings > Tokens](https://vercel.com/account/tokens) 创建
   - 权限：只读项目 + 部署权限
   - 定期轮换（建议 90 天）

2. **GH_PAT**（可选）：
   - 在 [GitHub Settings > Tokens](https://github.com/settings/tokens) 创建
   - 权限：只读代码（`repo:read`）
   - 不要勾选 `repo:write` 权限

### 启用保护

```
GitHub Settings > Branches > Branch protection rules:
- Require pull request reviews
- Require status checks to pass
- Restrict who can push
```

## 故障排查

### 部署失败

查看 Vercel Dashboard > Deployments > 具体部署记录中的 Build Logs。

### 文章未更新

检查 markdown-press 同步配置是否正确：

```bash
# 本地测试
bash ./build.sh
ls -la posts/
```

### 自定义域名不生效

DNS 传播需要时间（通常几分钟到几小时）。检查：

```bash
nslookup blog.example.com
# 应该指向 cname.vercel-dns.com
```

## 性能优化

Vercel 自动提供：
- 🌐 全球 Edge Network（边缘节点缓存）
- 🚀 自动压缩（Gzip/Brotli）
- 📦 HTTP/2 和 HTTP/3
- 🖼️ 图片优化（可选）
- ⚡ 增量静态再生成（ISR）

## 监控

Vercel Dashboard 提供：
- 实时流量分析
- 性能指标（Core Web Vitals）
- 错误追踪
- 构建日志
