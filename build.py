#!/usr/bin/env python3
"""
Simple Blog - 静态博客构建工具
支持从 markdown-press 项目一键发布
"""

import os
import re
import shutil
import json
import html
from pathlib import Path
from datetime import date as date_cls, datetime
from html.parser import HTMLParser

import yaml
import markdown
from markdown.extensions import fenced_code, tables, toc
from jinja2 import Environment, FileSystemLoader

# 配置
CONFIG_FILE = "config.yaml"
POSTS_DIR = "posts"
TEMPLATE_DIR = "template"
STATIC_DIR = "static"
DIST_DIR = "dist"

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class SearchContentParser(HTMLParser):
    """提取段落及其所属章节，供搜索结果预览和跳转使用"""

    HEADING_TAGS = {f'h{index}' for index in range(1, 7)}
    TEXT_BLOCK_TAGS = {'p', 'li', 'pre', 'td', 'th'}
    IGNORED_TAGS = {'script', 'style'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.current_section_title = ''
        self.current_section_anchor = ''
        self.current_heading = None
        self.block_stack = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
            return

        if self.ignored_depth:
            return

        attrs_dict = dict(attrs)
        if tag in self.HEADING_TAGS:
            self.current_heading = {
                'anchor': attrs_dict.get('id', ''),
                'chunks': []
            }
        elif tag in self.TEXT_BLOCK_TAGS:
            self.block_stack.append({
                'tag': tag,
                'chunks': []
            })

    def handle_endtag(self, tag):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth = max(0, self.ignored_depth - 1)
            return

        if self.ignored_depth:
            return

        if tag in self.HEADING_TAGS and self.current_heading is not None:
            heading_text = self.clean_text(''.join(self.current_heading['chunks']))
            if heading_text:
                self.current_section_title = heading_text
                self.current_section_anchor = self.current_heading['anchor']
            self.current_heading = None
            return

        if self.block_stack and self.block_stack[-1]['tag'] == tag:
            block = self.block_stack.pop()
            text = self.clean_text(''.join(block['chunks']))
            if text:
                self.entries.append({
                    'text': text,
                    'section_title': self.current_section_title,
                    'section_anchor': self.current_section_anchor
                })

    def handle_data(self, data):
        if self.ignored_depth or not data:
            return

        if self.current_heading is not None:
            self.current_heading['chunks'].append(data)
        elif self.block_stack:
            self.block_stack[-1]['chunks'].append(data)

    @staticmethod
    def clean_text(text):
        return re.sub(r'\s+', ' ', text).strip()

class BlogBuilder:
    def __init__(self):
        self.config = self.load_config()
        self.md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'toc',
            'meta',
        ])
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        self.posts = []
        self.categories = {}
        self.tags = {}
    
    def load_config(self):
        """加载博客配置"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        return {
            'title': 'Simple Blog',
            'description': '简洁现代的静态博客',
            'author': 'Author',
            'url': 'https://example.com',
            'posts_per_page': 10
        }
    
    def validate_post(self, post, filepath):
        """验证文章安全性"""
        # 限制标题长度（防止 DoS）
        if len(post.get('title', '')) > 200:
            raise ValueError(f"标题过长 (>200字符): {filepath}")
        
        # 限制标签数量
        tags = post.get('tags', [])
        if len(tags) > 20:
            raise ValueError(f"标签过多 (>20个): {filepath}")
        
        # 验证标签内容（防止注入）
        for tag in tags:
            if len(str(tag)) > 50:
                raise ValueError(f"标签过长: {filepath}")
        
        # 限制描述长度
        if len(post.get('description', '')) > 500:
            raise ValueError(f"描述过长 (>500字符): {filepath}")
        
        return True

    def extract_search_paragraphs(self, html_content):
        """从 HTML 内容中提取带章节信息的纯文本段落"""
        parser = SearchContentParser()
        parser.feed(html_content)
        parser.close()

        if parser.entries:
            return parser.entries

        text = re.sub(r'<br\s*/?>', '\n', html_content, flags=re.IGNORECASE)
        text = re.sub(r'</(p|div|h[1-6]|li|blockquote|pre|tr|ul|ol)>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        paragraphs = []
        for block in re.split(r'\n\s*\n+', text):
            cleaned = re.sub(r'\s+', ' ', block).strip()
            if cleaned:
                paragraphs.append({
                    'text': cleaned,
                    'section_title': '',
                    'section_anchor': ''
                })

        return paragraphs

    def parse_markdown(self, filepath):
        """解析 markdown 文件，提取 frontmatter 和内容"""
        # 文件大小检查（防止大文件攻击）
        max_size = 10 * 1024 * 1024  # 10MB
        if os.path.getsize(filepath) > max_size:
            raise ValueError(f"文件过大 (>10MB): {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析 YAML frontmatter
        frontmatter = {}
        body = content
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except yaml.YAMLError:
                    pass
        
        # 渲染 markdown
        html_content = self.md.convert(body)
        self.md.reset()
        
        # 提取元数据
        filename = os.path.basename(filepath)
        slug = frontmatter.get('slug', os.path.splitext(filename)[0])
        title = frontmatter.get('title', slug)
        post_date = frontmatter.get('date')
        if post_date and isinstance(post_date, (datetime, date_cls)):
            post_date = post_date.strftime('%Y-%m-%d')
        category = frontmatter.get('category', '未分类')
        tags = frontmatter.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        description = frontmatter.get('description', '')
        draft = frontmatter.get('draft', False)
        
        post = {
            'title': title,
            'slug': slug,
            'date': post_date,
            'category': category,
            'tags': tags,
            'description': description,
            'content': html_content,
            'search_paragraphs': self.extract_search_paragraphs(html_content),
            'draft': draft,
            'filepath': filepath,
            'filename': filename
        }
        
        # 安全验证
        self.validate_post(post, filepath)
        
        return post
    
    def load_posts(self):
        """加载所有文章"""
        # 支持从配置指定文章源目录（用于对接 markdown-press）
        posts_source = self.config.get('posts_source', POSTS_DIR)
        posts_path = Path(posts_source)
        
        if not posts_path.exists():
            # 回退到默认 posts 目录
            posts_path = Path(POSTS_DIR)
            if not posts_path.exists():
                print(f"文章目录不存在: {posts_source} 或 {POSTS_DIR}")
                return
            else:
                print(f"使用默认文章目录: {POSTS_DIR}")
        else:
            print(f"使用文章源目录: {posts_source}")
        
        for md_file in posts_path.rglob('*.md'):
            post = self.parse_markdown(str(md_file))
            if not post['draft']:  # 跳过草稿
                self.posts.append(post)
        
        # 按日期排序
        self.posts.sort(key=lambda x: x['date'] or '', reverse=True)
        
        # 构建分类和标签索引
        for post in self.posts:
            cat = post['category']
            if cat not in self.categories:
                self.categories[cat] = []
            self.categories[cat].append(post)
            
            for tag in post['tags']:
                if tag not in self.tags:
                    self.tags[tag] = []
                self.tags[tag].append(post)
        
        print(f"加载了 {len(self.posts)} 篇文章")
        print(f"分类: {list(self.categories.keys())}")
        print(f"标签: {list(self.tags.keys())}")
    
    def clean_dist(self):
        """清理输出目录"""
        if os.path.exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)
        os.makedirs(DIST_DIR)
    
    def copy_static(self):
        """复制静态资源"""
        if os.path.exists(STATIC_DIR):
            dist_static = os.path.join(DIST_DIR, 'static')
            shutil.copytree(STATIC_DIR, dist_static)
            print("静态资源已复制")
    
    def render_template(self, template_name, context, output_path):
        """渲染模板并保存"""
        template = self.env.get_template(template_name)
        html = template.render(**context)
        
        full_path = os.path.join(DIST_DIR, output_path)
        os.makedirs(os.path.dirname(full_path) if '/' in output_path else DIST_DIR, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(html)
    
    def generate_index(self):
        """生成首页"""
        self.render_template('index.html', {
            'config': self.config,
            'posts': self.posts[:self.config.get('posts_per_page', 10)],
            'categories': self.categories,
            'tags': self.tags
        }, 'index.html')
        print("首页已生成")
    
    def generate_posts(self):
        """生成文章页面"""
        for post in self.posts:
            output_path = f"posts/{post['slug']}/index.html"
            self.render_template('post.html', {
                'config': self.config,
                'post': post,
                'categories': self.categories,
                'tags': self.tags
            }, output_path)
        print(f"生成了 {len(self.posts)} 篇文章页面")
    
    def generate_categories(self):
        """生成分类页面"""
        # 分类列表页
        self.render_template('categories.html', {
            'config': self.config,
            'categories': self.categories,
            'tags': self.tags
        }, 'categories/index.html')
        
        # 单个分类页
        for category, posts in self.categories.items():
            slug = self.slugify(category)
            self.render_template('category.html', {
                'config': self.config,
                'category': category,
                'posts': posts,
                'categories': self.categories,
                'tags': self.tags
            }, f'category/{slug}/index.html')
        print(f"生成了 {len(self.categories)} 个分类页面")
    
    def generate_tags(self):
        """生成标签页面"""
        # 标签列表页
        self.render_template('tags.html', {
            'config': self.config,
            'tags': self.tags,
            'categories': self.categories
        }, 'tags/index.html')
        
        # 单个标签页
        for tag, posts in self.tags.items():
            slug = self.slugify(tag)
            self.render_template('tag.html', {
                'config': self.config,
                'tag': tag,
                'posts': posts,
                'categories': self.categories,
                'tags': self.tags
            }, f'tag/{slug}/index.html')
        print(f"生成了 {len(self.tags)} 个标签页面")
    
    def generate_search_data(self):
        """生成搜索数据"""
        search_data = []
        for post in self.posts:
            date_str = post['date']
            if hasattr(date_str, 'strftime'):
                date_str = date_str.strftime('%Y-%m-%d')
            search_data.append({
                'title': post['title'],
                'slug': post['slug'],
                'description': post['description'],
                'search_paragraphs': post.get('search_paragraphs', []),
                'category': post['category'],
                'tags': post['tags'],
                'date': date_str
            })
        
        output_path = os.path.join(DIST_DIR, 'search.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
        print("搜索数据已生成")
    
    def slugify(self, text):
        """将文本转换为 URL slug"""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
    
    def build(self):
        """执行完整构建"""
        print("=" * 50)
        print("Simple Blog 构建开始")
        print("=" * 50)
        
        self.clean_dist()
        self.load_posts()
        self.copy_static()
        self.generate_index()
        self.generate_posts()
        self.generate_categories()
        self.generate_tags()
        self.generate_search_data()
        
        print("=" * 50)
        print(f"构建完成！输出目录: {DIST_DIR}")
        print("=" * 50)


def main():
    builder = BlogBuilder()
    builder.build()


if __name__ == '__main__':
    main()
