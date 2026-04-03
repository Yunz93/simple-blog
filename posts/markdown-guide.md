---
title: "Markdown 完整指南"
date: 2026-03-30
category: "技术"
tags: ["Markdown", "写作", "教程"]
description: "详细介绍 Simple Blog 支持的 Markdown 语法，帮助你写出格式优美的文章。"
---

# Markdown 完整指南

Markdown 是一种轻量级标记语言，让你专注于写作本身。本文介绍 Simple Blog 支持的所有 Markdown 语法。

## 基础语法

### 标题

```markdown
# 一级标题
## 二级标题
### 三级标题
#### 四级标题
```

### 段落和换行

这是一个段落。段落之间用空行分隔。

这是另一个段落。

### 强调

- *斜体*：`*斜体*` 或 `_斜体_`
- **粗体**：`**粗体**` 或 `__粗体__`
- ***粗斜体***：`***粗斜体***`
- ~~删除线~~：`~~删除线~~`

### 列表

无序列表：

- 项目 1
- 项目 2
  - 子项目 2.1
  - 子项目 2.2
- 项目 3

有序列表：

1. 第一步
2. 第二步
3. 第三步

### 链接和图片

[链接文字](https://example.com)

![图片描述](https://example.com/image.png)

## 高级语法

### 代码块

行内代码：使用 `code` 标记。

代码块：

```javascript
function greet(name) {
    return `Hello, ${name}!`;
}

console.log(greet('World'));
```

支持的语言：

```python
# Python 示例
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

```bash
# Bash 示例
echo "Hello, World!"
ls -la
git status
```

### 表格

| 功能 | 语法 | 示例 |
|------|------|------|
| 粗体 | `**text**` | **粗体** |
| 斜体 | `*text*` | *斜体* |
| 代码 | `` `code` `` | `code` |
| 链接 | `[text](url)` | [链接](https://example.com) |

### 引用

> 这是第一级引用
>> 这是嵌套引用
> 
> 回到第一级

### 分割线

---

## YAML Frontmatter

每篇文章开头可以包含 YAML 元数据：

```yaml
---
title: "文章标题"
date: 2026-03-31
category: "分类"
tags: ["标签1", "标签2"]
description: "文章描述"
draft: false
---
```

### 支持的字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | 字符串 | 文章标题（必需） |
| `date` | 日期 | 发布日期 |
| `category` | 字符串 | 文章分类 |
| `tags` | 数组/字符串 | 文章标签 |
| `description` | 字符串 | 文章描述 |
| `draft` | 布尔 | 是否为草稿 |
| `slug` | 字符串 | 自定义 URL |

## 写作建议

1. **标题层级** - 文章主标题使用 H1，段落标题从 H2 开始
2. **代码注释** - 为代码块添加注释说明
3. **图片优化** - 压缩图片以提高加载速度
4. **标签使用** - 使用 3-5 个相关标签便于分类

## 结语

掌握这些 Markdown 语法，你就可以开始创作优美的技术文章了！
