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
import math
from pathlib import Path
from datetime import UTC, date as date_cls, datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse, urlunparse

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

os.chdir(os.path.dirname(os.path.abspath(__file__)))


def _xml_10_safe_text(s: str) -> str:
    """Remove code points illegal in XML 1.0 text (html.escape does not handle these).

    Browsers report errors like "PCDATA invalid Char value 8" when markdown or
    front matter contains control characters such as backspace (U+0008).
    """
    if not s:
        return s or ''
    out = []
    for ch in s:
        o = ord(ch)
        if o < 0x20 and o not in (0x9, 0xA, 0xD):
            continue
        if 0xD800 <= o <= 0xDFFF:
            continue
        if o in (0xFFFE, 0xFFFF):
            continue
        out.append(ch)
    return ''.join(out)


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
    VIDEO_FILE_EXTENSIONS = ('.mp4', '.webm', '.ogg', '.ogv', '.mov', '.m4v')

    def __init__(self):
        self.config = self.load_config()
        self.build_version = self.resolve_build_version()
        self.md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'toc',
            'meta',
        ])
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        self.env.globals['build_version'] = self.build_version
        self.env.filters['slugify'] = self.slugify
        self.posts = []
        self.categories = {}
        self.tags = {}

    def resolve_build_version(self):
        """生成部署版本号，用于静态资源缓存失效"""
        vercel_sha = os.environ.get('VERCEL_GIT_COMMIT_SHA', '').strip()
        if vercel_sha:
            return vercel_sha[:12]

        git_sha = os.environ.get('GIT_COMMIT_SHA', '').strip()
        if git_sha:
            return git_sha[:12]

        return datetime.now(UTC).strftime('%Y%m%d%H%M%S')
    
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

    @staticmethod
    def resolve_frontmatter_value(frontmatter, key, fallback):
        """获取 frontmatter 字段，缺失或留空时回退到默认值"""
        value = frontmatter.get(key)
        if value is None:
            return fallback
        if isinstance(value, str) and not value.strip():
            return fallback
        if isinstance(value, list) and not value:
            return fallback
        return value

    @staticmethod
    def normalize_datetime(value):
        """统一为无时区 datetime，避免排序时混用 aware/naive 类型"""
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value

    def parse_timestamp_value(self, value):
        """解析 frontmatter 中常见的日期/时间格式"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return self.normalize_datetime(value)

        if isinstance(value, date_cls):
            return datetime.combine(value, datetime.min.time())

        text = str(value).strip()
        if not text:
            return None

        try:
            return self.normalize_datetime(datetime.fromisoformat(text.replace('Z', '+00:00')))
        except ValueError:
            pass

        for fmt in (
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%Y-%m-%d %a %H:%M:%S',
            '%Y-%m-%d %A %H:%M:%S',
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        match = re.match(r'^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}:\d{2}))?', text)
        if match:
            if match.group(2):
                return datetime.strptime(f"{match.group(1)} {match.group(2)}", '%Y-%m-%d %H:%M:%S')
            return datetime.strptime(match.group(1), '%Y-%m-%d')

        # Obsidian / markdown-press: "2024-03-17 Sun 15:44:48"（中间星期几因 locale 可能无法用 %a 解析）
        obs = re.search(
            r'(\d{4}-\d{2}-\d{2})\s+\S+\s+(\d{1,2}:\d{2}:\d{2})',
            text,
        )
        if obs:
            try:
                return datetime.strptime(f"{obs.group(1)} {obs.group(2)}", '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        return None

    CREATED_AT_KEYS = ('create_time', 'date created', 'created_at', 'date')
    UPDATED_AT_KEYS = ('update_time', 'date modified', 'updated_at', 'modified')

    def resolve_post_created_at(self, frontmatter):
        """提取文章创建时间，兼容 create_time / date created / date 等字段"""
        for key in self.CREATED_AT_KEYS:
            parsed = self.parse_timestamp_value(frontmatter.get(key))
            if parsed is not None:
                return parsed
        return None

    def resolve_post_updated_at(self, frontmatter):
        """提取文章更新时间"""
        for key in self.UPDATED_AT_KEYS:
            parsed = self.parse_timestamp_value(frontmatter.get(key))
            if parsed is not None:
                return parsed
        return None

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

    def normalize_media_src(self, src):
        """将 GitHub raw 页面链接转换为更直接的原始资源地址"""
        parsed = urlparse(src)
        path_parts = parsed.path.lstrip('/').split('/')

        if parsed.scheme != 'https' or parsed.netloc != 'github.com':
            return src

        if len(path_parts) < 5 or path_parts[2] != 'raw':
            return src

        owner, repo, _, branch, *asset_path = path_parts
        normalized_path = '/'.join([owner, repo, branch, *asset_path])

        return urlunparse((
            'https',
            'raw.githubusercontent.com',
            f'/{normalized_path}',
            '',
            parsed.query,
            ''
        ))

    def is_video_file_url(self, src):
        """判断链接是否指向可直接播放的视频文件"""
        parsed = urlparse(src)
        path = parsed.path.lower()
        return path.endswith(self.VIDEO_FILE_EXTENSIONS)

    def get_video_mime_type(self, src):
        """根据扩展名推断视频 MIME 类型"""
        ext = Path(urlparse(src).path).suffix.lower()
        return {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.ogg': 'video/ogg',
            '.ogv': 'video/ogg',
            '.mov': 'video/quicktime',
            '.m4v': 'video/mp4',
        }.get(ext, 'video/mp4')

    def ensure_tag_attribute(self, tag, name, value):
        """仅在属性缺失时追加 HTML 属性"""
        if re.search(rf'\b{name}\s*=', tag, flags=re.IGNORECASE):
            return tag

        return re.sub(r'\s*/?>$', f' {name}="{value}"\\g<0>', tag)

    def ensure_boolean_attribute(self, tag, name):
        """仅在属性缺失时追加布尔属性"""
        if re.search(rf'\b{name}\b', tag, flags=re.IGNORECASE):
            return tag

        return re.sub(r'\s*/?>$', f' {name}\\g<0>', tag)

    def optimize_image_tag(self, match):
        """为文章图片补充懒加载属性并规范图源"""
        tag = match.group(0)
        src_match = re.search(r'\bsrc=(["\'])(.*?)\1', tag, flags=re.IGNORECASE)

        if src_match:
            src = html.unescape(src_match.group(2))
            normalized_src = self.normalize_media_src(src)
            if normalized_src != src:
                escaped_src = html.escape(normalized_src, quote=True)
                tag = (
                    f"{tag[:src_match.start(2)]}"
                    f"{escaped_src}"
                    f"{tag[src_match.end(2):]}"
                )

        tag = self.ensure_tag_attribute(tag, 'loading', 'lazy')
        tag = self.ensure_tag_attribute(tag, 'decoding', 'async')
        return tag

    def optimize_source_tag(self, match):
        """规范 video/source 等标签中的资源地址"""
        tag = match.group(0)
        src_match = re.search(r'\bsrc=(["\'])(.*?)\1', tag, flags=re.IGNORECASE)

        if not src_match:
            return tag

        src = html.unescape(src_match.group(2))
        normalized_src = self.normalize_media_src(src)
        if normalized_src == src:
            return tag

        escaped_src = html.escape(normalized_src, quote=True)
        return (
            f"{tag[:src_match.start(2)]}"
            f"{escaped_src}"
            f"{tag[src_match.end(2):]}"
        )

    def optimize_video_tag(self, match):
        """为原生 video 标签补充常用播放属性"""
        tag = self.optimize_source_tag(match)
        tag = self.ensure_boolean_attribute(tag, 'controls')
        tag = self.ensure_boolean_attribute(tag, 'playsinline')
        tag = self.ensure_tag_attribute(tag, 'preload', 'metadata')
        return tag

    def optimize_iframe_tag(self, match):
        """为原生 iframe 标签补充懒加载和播放体验属性"""
        tag = match.group(0)
        tag = self.ensure_tag_attribute(tag, 'loading', 'lazy')
        tag = self.ensure_tag_attribute(tag, 'referrerpolicy', 'strict-origin-when-cross-origin')
        tag = self.ensure_tag_attribute(
            tag,
            'allow',
            'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share'
        )
        tag = self.ensure_boolean_attribute(tag, 'allowfullscreen')
        return tag

    def get_video_embed_url(self, src):
        """将常见视频平台链接转换为 iframe 可用的嵌入地址"""
        parsed = urlparse(src)
        host = parsed.netloc.lower().removeprefix('www.')
        path = parsed.path.rstrip('/')
        query = parse_qs(parsed.query)

        if host in {'youtube.com', 'm.youtube.com'}:
            if path == '/watch':
                video_id = query.get('v', [''])[0]
            elif path.startswith('/shorts/'):
                video_id = path.split('/shorts/', 1)[1]
            elif path.startswith('/embed/'):
                video_id = path.split('/embed/', 1)[1]
            else:
                video_id = ''

            if video_id:
                return f'https://www.youtube.com/embed/{video_id}'

        if host == 'youtu.be':
            video_id = path.lstrip('/')
            if video_id:
                return f'https://www.youtube.com/embed/{video_id}'

        if host == 'bilibili.com' or host.endswith('.bilibili.com'):
            match = re.search(r'/video/([^/?]+)', path)
            if match:
                bvid = match.group(1)
                page = query.get('p', ['1'])[0]
                return f'https://player.bilibili.com/player.html?bvid={bvid}&page={page}'

        return ''

    @staticmethod
    def strip_html_tags(text):
        """移除 HTML 标签，保留纯文本说明"""
        return re.sub(r'<[^>]+>', '', html.unescape(text or '')).strip()

    def replace_link_only_paragraph_with_embed(self, match):
        """将仅包含一个视频链接的段落转成内嵌播放器"""
        href = html.unescape(match.group('href')).strip()
        text = self.strip_html_tags(match.group('text'))
        caption = text if text and text != href else ''

        if self.is_video_file_url(href):
            normalized_src = html.escape(self.normalize_media_src(href), quote=True)
            mime_type = html.escape(self.get_video_mime_type(href), quote=True)
            caption_html = (
                f'<figcaption>{html.escape(caption)}</figcaption>'
                if caption else ''
            )
            return (
                '<figure class="post-embed post-embed-video">'
                f'<video controls playsinline preload="metadata">'
                f'<source src="{normalized_src}" type="{mime_type}">'
                '当前浏览器不支持 video 标签播放该视频。'
                '</video>'
                f'{caption_html}'
                '</figure>'
            )

        embed_url = self.get_video_embed_url(href)
        if embed_url:
            title = caption or 'Video embed'
            return (
                '<div class="post-embed post-embed-iframe">'
                f'<iframe src="{html.escape(embed_url, quote=True)}" '
                f'title="{html.escape(title, quote=True)}" '
                'loading="lazy" '
                'referrerpolicy="strict-origin-when-cross-origin" '
                'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                'allowfullscreen></iframe>'
                '</div>'
            )

        return match.group(0)

    def optimize_content_html(self, html_content):
        """优化文章内容中的资源标签"""
        html_content = re.sub(
            r'<p>\s*<a\b[^>]*\bhref=(["\'])(?P<href>.*?)\1[^>]*>(?P<text>.*?)</a>\s*</p>',
            self.replace_link_only_paragraph_with_embed,
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        html_content = re.sub(r'<img\b[^>]*>', self.optimize_image_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<source\b[^>]*>', self.optimize_source_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<video\b[^>]*>', self.optimize_video_tag, html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<iframe\b[^>]*>', self.optimize_iframe_tag, html_content, flags=re.IGNORECASE)
        return html_content

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
                except yaml.YAMLError as e:
                    print(f"警告: YAML frontmatter 解析失败 ({filepath}): {e}")
        
        # 渲染 markdown
        html_content = self.md.convert(body)
        toc_html = getattr(self.md, 'toc', '')
        self.md.reset()
        html_content = self.optimize_content_html(html_content)

        # 阅读时间估算：中文约 400 字/分钟
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        plain_text = html.unescape(plain_text)
        char_count = len(re.sub(r'\s+', '', plain_text))
        reading_minutes = max(1, round(char_count / 400))
        
        # 提取元数据
        filename = os.path.basename(filepath)
        default_title = os.path.splitext(filename)[0]
        title = self.resolve_frontmatter_value(frontmatter, 'title', default_title)
        title = str(title).strip() or default_title
        aliases = self.resolve_frontmatter_value(frontmatter, 'aliases', title)
        if isinstance(aliases, str):
            aliases = [aliases.strip()] if aliases.strip() else [title]
        elif isinstance(aliases, list):
            aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]
            if not aliases:
                aliases = [title]
        else:
            alias_text = str(aliases).strip()
            aliases = [alias_text] if alias_text else [title]
        slug = self.resolve_frontmatter_value(frontmatter, 'slug', title)
        slug = str(slug).strip() or title
        category = frontmatter.get('category', '未分类')
        tags = frontmatter.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        description = frontmatter.get('description', '')
        draft = frontmatter.get('draft', False)
        created_at = self.resolve_post_created_at(frontmatter)
        updated_at = self.resolve_post_updated_at(frontmatter)

        # 展示用日期：优先显式 date，否则回退到创建时间
        explicit_date = self.parse_timestamp_value(frontmatter.get('date'))
        display_dt = explicit_date if explicit_date is not None else created_at
        if display_dt is not None:
            post_date = display_dt.strftime('%Y-%m-%d')
        else:
            post_date = None
        date_display = post_date

        post = {
            'title': title,
            'aliases': aliases,
            'slug': slug,
            'date': post_date,
            'date_display': date_display,
            'created_at': created_at,
            'updated_at': updated_at,
            'category': category,
            'tags': tags,
            'description': description,
            'content': html_content,
            'toc': toc_html,
            'reading_time': reading_minutes,
            'search_entries': self.extract_search_paragraphs(html_content),
            'search_paragraphs': [],
            'draft': draft,
            'filepath': filepath,
            'filename': filename
        }

        post['search_paragraphs'] = [entry['text'] for entry in post['search_entries'] if entry.get('text')]
        
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
        
        for md_file in sorted(posts_path.rglob('*.md')):
            post = self.parse_markdown(str(md_file))
            if not post['draft']:  # 跳过草稿
                self.posts.append(post)

        # 按创建时间倒序排序，缺失时回退到 date
        self.posts.sort(
            key=lambda x: (
                x['created_at'] is not None,
                x['created_at'] or datetime.min,
                x['date'] or '',
            ),
            reverse=True
        )
        
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
            self.version_static_assets(Path(dist_static))
            print("静态资源已复制")

    def version_static_assets(self, dist_static):
        """为 CSS 与字体资源追加构建版本，避免 immutable 缓存命中过期文件"""
        css_path = dist_static / 'css' / 'style.css'
        if css_path.exists():
            css_content = css_path.read_text(encoding='utf-8')
            css_content = css_content.replace(
                "../fonts/lxgwwenkai-regular/result.css",
                f"../fonts/lxgwwenkai-regular/result.css?v={self.build_version}"
            )
            css_content = css_content.replace(
                "../fonts/lxgwwenkai-medium/result.css",
                f"../fonts/lxgwwenkai-medium/result.css?v={self.build_version}"
            )
            css_content = css_content.replace(
                "./jinkai.css",
                f"./jinkai.css?v={self.build_version}"
            )
            css_path.write_text(css_content, encoding='utf-8')

        for font_css_path in dist_static.rglob('result.css'):
            font_css = font_css_path.read_text(encoding='utf-8')
            font_css = re.sub(
                r'url\((["\']?)(\./[^)"\']+\.woff2)\1\)',
                lambda match: f'url({match.group(1)}{match.group(2)}?v={self.build_version}{match.group(1)})',
                font_css
            )
            font_css_path.write_text(font_css, encoding='utf-8')

        for legacy_font_css_path in (dist_static / 'css').glob('*.css'):
            if legacy_font_css_path.name == 'style.css':
                continue
            legacy_css = legacy_font_css_path.read_text(encoding='utf-8')
            legacy_css = re.sub(
                r'url\((["\']?)(\.\./[^)"\']+\.woff2)\1\)',
                lambda match: f'url({match.group(1)}{match.group(2)}?v={self.build_version}{match.group(1)})',
                legacy_css
            )
            legacy_font_css_path.write_text(legacy_css, encoding='utf-8')
    
    def render_template(self, template_name, context, output_path):
        """渲染模板并保存"""
        template = self.env.get_template(template_name)
        html = template.render(**context)
        
        full_path = os.path.join(DIST_DIR, output_path)
        os.makedirs(os.path.dirname(full_path) if '/' in output_path else DIST_DIR, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(html)

    @staticmethod
    def build_index_page_url(page_number):
        """返回首页分页 URL"""
        if page_number <= 1:
            return '/'
        return f'/page/{page_number}/'

    def build_pagination_context(self, current_page, total_pages):
        """构建模板可直接使用的分页上下文"""
        page_numbers = list(range(1, total_pages + 1))

        return {
            'current_page': current_page,
            'total_pages': total_pages,
            'page_numbers': page_numbers,
            'has_prev': current_page > 1,
            'has_next': current_page < total_pages,
            'prev_url': self.build_index_page_url(current_page - 1) if current_page > 1 else None,
            'next_url': self.build_index_page_url(current_page + 1) if current_page < total_pages else None,
            'page_url': self.build_index_page_url,
        }
    
    def generate_index(self):
        """生成首页"""
        posts_per_page = self.config.get('posts_per_page', 10)
        total_posts = len(self.posts)
        total_pages = max(1, math.ceil(total_posts / posts_per_page)) if posts_per_page > 0 else 1

        for page_number in range(1, total_pages + 1):
            start = (page_number - 1) * posts_per_page
            end = start + posts_per_page
            output_path = 'index.html' if page_number == 1 else f'page/{page_number}/index.html'

            self.render_template('index.html', {
                'config': self.config,
                'posts': self.posts[start:end],
                'categories': self.categories,
                'tags': self.tags,
                'pagination': self.build_pagination_context(page_number, total_pages)
            }, output_path)

        print(f"首页已生成，共 {total_pages} 页")
    
    def generate_posts(self):
        """生成文章页面"""
        for i, post in enumerate(self.posts):
            prev_post = self.posts[i - 1] if i > 0 else None
            next_post = self.posts[i + 1] if i < len(self.posts) - 1 else None
            output_path = f"posts/{post['slug']}/index.html"
            self.render_template('post.html', {
                'config': self.config,
                'post': post,
                'prev_post': prev_post,
                'next_post': next_post,
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
                'aliases': post.get('aliases', []),
                'slug': post['slug'],
                'description': post['description'],
                'search_paragraphs': post.get('search_paragraphs', []),
                'search_entries': post.get('search_entries', []),
                'category': post['category'],
                'tags': post['tags'],
                'date': date_str
            })
        
        output_path = os.path.join(DIST_DIR, 'search.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
        print("搜索数据已生成")

    def generate_sitemap(self):
        """生成 sitemap.xml"""
        base_url = self.config.get('url', '').rstrip('/')
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S+00:00')

        urls = [{'loc': f'{base_url}/', 'lastmod': now, 'priority': '1.0'}]

        for post in self.posts:
            lastmod = now
            if post.get('created_at'):
                lastmod = post['created_at'].strftime('%Y-%m-%dT%H:%M:%S+00:00')
            urls.append({
                'loc': f"{base_url}/posts/{post['slug']}/",
                'lastmod': lastmod,
                'priority': '0.8'
            })

        for category in self.categories:
            slug = self.slugify(category)
            urls.append({'loc': f'{base_url}/category/{slug}/', 'lastmod': now, 'priority': '0.5'})

        for tag in self.tags:
            slug = self.slugify(tag)
            urls.append({'loc': f'{base_url}/tag/{slug}/', 'lastmod': now, 'priority': '0.4'})

        urls.append({'loc': f'{base_url}/categories/', 'lastmod': now, 'priority': '0.5'})
        urls.append({'loc': f'{base_url}/tags/', 'lastmod': now, 'priority': '0.4'})
        urls.append({'loc': f'{base_url}/archives/', 'lastmod': now, 'priority': '0.5'})

        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for url in urls:
            lines.append('  <url>')
            lines.append(f'    <loc>{html.escape(url["loc"])}</loc>')
            lines.append(f'    <lastmod>{url["lastmod"]}</lastmod>')
            lines.append(f'    <priority>{url["priority"]}</priority>')
            lines.append('  </url>')
        lines.append('</urlset>')

        output_path = os.path.join(DIST_DIR, 'sitemap.xml')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("sitemap.xml 已生成")

    def generate_robots_txt(self):
        """生成 robots.txt"""
        base_url = self.config.get('url', '').rstrip('/')
        content = f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n"

        output_path = os.path.join(DIST_DIR, 'robots.txt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("robots.txt 已生成")

    def generate_rss_feed(self):
        """生成 Atom feed"""
        base_url = self.config.get('url', '').rstrip('/')
        title = self.config.get('title', 'Blog')
        description = self.config.get('description', '')
        author = self.config.get('author', '')
        now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')

        def atom_txt(s: str) -> str:
            return html.escape(_xml_10_safe_text(s))

        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<feed xmlns="http://www.w3.org/2005/Atom">')
        lines.append(f'  <title>{atom_txt(title)}</title>')
        lines.append(f'  <subtitle>{atom_txt(description)}</subtitle>')
        lines.append(f'  <link href="{atom_txt(base_url)}/feed.xml" rel="self" type="application/atom+xml"/>')
        lines.append(f'  <link href="{atom_txt(base_url)}/" rel="alternate" type="text/html"/>')
        lines.append(f'  <id>{atom_txt(base_url)}/</id>')
        lines.append(f'  <updated>{now}</updated>')
        if author:
            lines.append(f'  <author><name>{atom_txt(author)}</name></author>')

        for post in self.posts[:20]:
            post_url = f"{base_url}/posts/{post['slug']}/"
            updated = now
            if post.get('created_at'):
                updated = post['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ')

            lines.append('  <entry>')
            lines.append(f'    <title>{atom_txt(post["title"])}</title>')
            lines.append(f'    <link href="{atom_txt(post_url)}" rel="alternate" type="text/html"/>')
            lines.append(f'    <id>{atom_txt(post_url)}</id>')
            lines.append(f'    <updated>{updated}</updated>')
            if post.get('description'):
                lines.append(f'    <summary>{atom_txt(post["description"])}</summary>')
            lines.append(f'    <content type="html">{atom_txt(post["content"])}</content>')
            for tag in post.get('tags', []):
                lines.append(f'    <category term="{atom_txt(tag)}"/>')
            lines.append('  </entry>')

        lines.append('</feed>')

        output_path = os.path.join(DIST_DIR, 'feed.xml')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("Atom feed 已生成")

    @staticmethod
    def post_archive_year(post):
        """归档分组用年份：优先 created_at，其次 date_display / date 字符串"""
        if post.get('created_at'):
            return post['created_at'].year
        for key in ('date_display', 'date'):
            val = post.get(key)
            if not val:
                continue
            try:
                return int(str(val)[:4])
            except (ValueError, IndexError):
                continue
        return None

    def generate_archive(self):
        """生成按年份归档页面"""
        archive = {}
        for post in self.posts:
            year = self.post_archive_year(post)
            if year is None:
                year = 0
            archive.setdefault(year, []).append(post)

        sorted_years = sorted(archive.keys(), reverse=True)
        archive_sorted = [(y, archive[y]) for y in sorted_years]

        self.render_template('archive.html', {
            'config': self.config,
            'archive': archive_sorted,
            'total_posts': len(self.posts),
        }, 'archives/index.html')
        print("归档页面已生成")

    def generate_about(self):
        """生成关于页面"""
        about_content = ''
        about_md = Path('about.md')
        if about_md.exists():
            with open(about_md, 'r', encoding='utf-8') as f:
                about_content = self.md.convert(f.read())
                self.md.reset()

        self.render_template('about.html', {
            'config': self.config,
            'about_content': about_content,
        }, 'about/index.html')
        print("关于页面已生成")

    def generate_404(self):
        """生成 404 页面"""
        self.render_template('404.html', {
            'config': self.config,
        }, '404.html')
        print("404 页面已生成")
    
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
        self.generate_sitemap()
        self.generate_robots_txt()
        self.generate_rss_feed()
        self.generate_archive()
        self.generate_about()
        self.generate_404()
        
        print("=" * 50)
        print(f"构建完成！输出目录: {DIST_DIR}")
        print("=" * 50)


def main():
    builder = BlogBuilder()
    builder.build()


if __name__ == '__main__':
    main()
