# 安全指南

## 潜在风险与修复方案

### 1. Secrets 泄露风险

**风险**：GitHub Actions 日志可能泄露 Vercel Token 或 GitHub PAT

**修复**：
- ✅ 已在 workflow 中使用 `${{ secrets.XXX }}`，GitHub 会自动打码
- ⚠️ 不要在代码中硬编码任何 Token
- ⚠️ 定期检查 GitHub Actions 日志确认无泄露

### 2. 依赖供应链攻击

**风险**：pip 依赖可能被篡改，植入恶意代码

**修复**：固定依赖版本并校验哈希

```bash
# 生成锁定文件
pip freeze > requirements-lock.txt

# 或使用 pip-tools
pip install pip-tools
pip-compile requirements.in
pip-sync
```

### 3. Markdown 文件代码注入

**风险**：恶意 Markdown 文件可能通过 YAML frontmatter 或内容执行代码

**修复**：已添加以下防护措施

```python
# build.py 中的安全验证
def validate_post(self, post):
    # 限制标题长度
    if len(post['title']) > 200:
        raise ValueError(f"标题过长: {post['filepath']}")
    
    # 验证日期格式
    if post['date'] and not isinstance(post['date'], (str, datetime)):
        raise ValueError(f"日期格式错误: {post['filepath']}")
    
    # 限制标签数量
    if len(post['tags']) > 20:
        raise ValueError(f"标签过多: {post['filepath']}")
```

### 4. 文件系统安全

**风险**：`cp -r` 可能复制恶意脚本或可执行文件

**修复**：

```bash
# 只复制 .md 文件
find markdown-press/posts -name "*.md" -type f -exec cp {} posts/ \;

# 检查文件大小（防止 DoS）
find posts -name "*.md" -size +10M -exec rm {} \;
```

### 5. 构建产物安全检查

**风险**：构建产物中可能意外包含敏感信息

**修复**：添加构建后检查

```bash
# 检查敏感信息
if grep -r "AKIA\|ghp_\|sk-\|private" dist/; then
    echo "❌ 发现敏感信息"
    exit 1
fi
```

## 推荐的安全配置

### GitHub Secrets 设置

1. **VERCEL_TOKEN**：Vercel 部署令牌
   - 权限：只读项目 + 部署权限
   - 定期轮换（建议 90 天）

2. **GH_PAT**（可选）：GitHub Personal Access Token
   - 仅用于私有 markdown-press 仓库
   - 权限：只读代码（`repo:read`）
   - 不要勾选 `repo:write` 权限

3. **MARKDOWN_PRESS_REPO**（可选）：
   - 格式：`username/repo`
   - 公开仓库可留空

### 启用分支保护

```
Settings > Branches > Branch protection rules
- Require pull request reviews
- Require status checks to pass
- Restrict who can push
```

### 依赖自动更新

启用 Dependabot：

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

## 安全最佳实践

1. **定期审计**
   - 检查 GitHub Actions 日志
   - 检查 Secrets 是否泄露（GitHub 会自动扫描）
   - 更新依赖到最新版本

2. **最小权限原则**
   - Token 只给必要权限
   - GitHub Actions 使用最小权限配置

3. **输入验证**
   - 所有外部输入（Markdown 文件）都要验证
   - 限制文件大小和数量

4. **监控告警**
   - 开启 GitHub Security alerts
   - 配置 Vercel 部署通知

## 应急处理

如果怀疑 Token 泄露：

1. **立即撤销 Token**
   - Vercel：Settings > Tokens > Revoke
   - GitHub：Settings > Developer settings > Personal access tokens

2. **轮换 Secrets**
   ```bash
   # 生成新的 Token
   # 更新 GitHub Secrets
   # 重新部署
   ```

3. **检查日志**
   - 查看最近的 GitHub Actions 运行记录
   - 确认是否有异常输出

4. **通知用户**
   - 如果涉及用户数据，按 GDPR/CCPA 要求通知
