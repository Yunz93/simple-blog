/**
 * Simple Blog - 前端交互
 * 包含性能优化和安全性增强
 */

// 防抖函数 - 性能优化
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 图片懒加载 - 性能优化
class LazyLoadImages {
    constructor() {
        this.images = document.querySelectorAll('img[data-src]');
        this.init();
    }
    
    init() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.01
            });
            
            this.images.forEach(img => imageObserver.observe(img));
        } else {
            // 降级处理
            this.images.forEach(img => {
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
            });
        }
    }
}

// 搜索功能
class Search {
    constructor() {
        this.modal = document.getElementById('searchModal');
        this.input = document.getElementById('searchInput');
        this.results = document.getElementById('searchResults');
        this.closeBtn = document.getElementById('searchClose');
        this.trigger = document.querySelector('.search-trigger');
        
        this.data = [];
        this.isSearchDataLoaded = false;
        this.loadError = null;
        this.init();
    }
    
    async init() {
        // 绑定事件
        this.trigger?.addEventListener('click', (e) => {
            e.preventDefault();
            this.open();
        });
        
        this.closeBtn?.addEventListener('click', () => this.close());
        
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });

        this.results?.addEventListener('click', (e) => {
            if (e.target.closest('.search-result-item')) {
                this.close();
            }
        });
        
        // 使用防抖优化搜索输入性能
        const debouncedSearch = debounce((value) => this.search(value), 200);
        this.input?.addEventListener('input', (e) => debouncedSearch(e.target.value));
        
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K 打开搜索
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.open();
            }
            // ESC 关闭搜索
            if (e.key === 'Escape' && this.modal?.classList.contains('active')) {
                this.close();
            }
        });

        await this.loadSearchData();
    }

    getSearchDataUrl() {
        const url = new URL('/search.json', window.location.origin);
        if (window.__BUILD_VERSION__) {
            url.searchParams.set('v', window.__BUILD_VERSION__);
        }
        return url.toString();
    }

    async loadSearchData() {
        try {
            const response = await fetch(this.getSearchDataUrl(), {
                cache: 'no-store'
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            this.data = await response.json();
            this.isSearchDataLoaded = true;
            this.loadError = null;

            if (this.input?.value.trim()) {
                this.search(this.input.value);
            }
        } catch (e) {
            this.loadError = e;
            this.isSearchDataLoaded = false;
            console.error('加载搜索数据失败:', e);
        }
    }
    
    open() {
        this.modal?.classList.add('active');
        this.input?.focus();
        this.input.value = '';
        this.results.innerHTML = '';

        if (!this.isSearchDataLoaded && !this.loadError) {
            this.results.innerHTML = '<div class="search-result-item"><div class="search-result-meta">搜索索引加载中...</div></div>';
        }
    }
    
    close() {
        this.modal?.classList.remove('active');
    }
    
    search(query) {
        if (!query.trim()) {
            this.results.innerHTML = '';
            return;
        }

        if (this.loadError) {
            this.results.innerHTML = '<div class="search-result-item"><div class="search-result-meta">搜索索引加载失败，请刷新页面后重试</div></div>';
            return;
        }

        if (!this.isSearchDataLoaded) {
            this.results.innerHTML = '<div class="search-result-item"><div class="search-result-meta">搜索索引加载中...</div></div>';
            return;
        }

        const keywords = this.tokenizeQuery(query);
        const matches = this.data
            .map(item => this.buildSearchResult(item, keywords))
            .filter(Boolean)
            .sort((a, b) => b.score - a.score)
            .slice(0, 10);

        this.renderResults(matches, keywords);
    }

    renderResults(matches, keywords) {
        if (matches.length === 0) {
            this.results.innerHTML = '<div class="search-result-item"><div class="search-result-meta">未找到相关文章</div></div>';
            return;
        }

        this.results.innerHTML = matches.map(({ item, excerpt, sectionTitle, targetPath }) => `
            <a class="search-result-item" href="${this.escapeHtml(targetPath)}">
                <div class="search-result-title">${this.highlightText(item.title, keywords)}</div>
                <div class="search-result-meta">
                    ${item.date || ''} ${item.category ? `· ${this.escapeHtml(item.category)}` : ''}
                </div>
                ${sectionTitle ? `<div class="search-result-section">章节 · ${this.highlightText(sectionTitle, keywords)}</div>` : ''}
                ${excerpt ? `<div class="search-result-excerpt">${this.highlightText(excerpt, keywords)}</div>` : ''}
                ${item.tags?.length ? `
                    <div class="search-result-tags">
                        ${item.tags.map(tag => `<span class="search-result-tag">${this.highlightText(tag, keywords)}</span>`).join('')}
                    </div>
                ` : ''}
            </a>
        `).join('');
    }

    buildSearchResult(item, keywords) {
        const titleScore = this.getMatchScore(item.title, keywords);
        const aliasScore = (item.aliases || []).reduce((score, alias) => score + this.getMatchScore(alias, keywords), 0);
        const descriptionScore = this.getMatchScore(item.description, keywords);
        const categoryScore = this.getMatchScore(item.category, keywords);
        const tagScore = (item.tags || []).reduce((score, tag) => score + this.getMatchScore(tag, keywords), 0);
        const searchEntries = item.search_entries || item.search_paragraphs || [];
        const paragraphMatch = this.findBestParagraph(searchEntries, keywords);

        const score = titleScore * 5 + aliasScore * 4 + descriptionScore * 3 + categoryScore * 2 + tagScore * 2 + paragraphMatch.score * 4;
        if (score === 0) {
            return null;
        }

        const excerptSource = paragraphMatch.text || item.description || '';
        const excerpt = excerptSource ? this.truncateAroundMatch(excerptSource, keywords) : '';

        return {
            item,
            score,
            excerpt,
            sectionTitle: paragraphMatch.sectionTitle,
            targetPath: paragraphMatch.sectionAnchor
                ? `/posts/${item.slug}/#${paragraphMatch.sectionAnchor}`
                : `/posts/${item.slug}/`
        };
    }

    findBestParagraph(paragraphs, keywords) {
        let best = { score: 0, text: '', sectionTitle: '', sectionAnchor: '' };

        paragraphs.forEach((paragraph) => {
            const entry = this.normalizeSearchEntry(paragraph);
            const textScore = this.getMatchScore(entry.text, keywords);
            const sectionScore = this.getMatchScore(entry.sectionTitle, keywords);
            const score = textScore * 2 + sectionScore * 3;

            if (score > best.score) {
                best = {
                    score,
                    text: entry.text,
                    sectionTitle: entry.sectionTitle,
                    sectionAnchor: entry.sectionAnchor
                };
            }
        });

        return best;
    }

    normalizeSearchEntry(entry) {
        if (typeof entry === 'string') {
            return {
                text: entry,
                sectionTitle: '',
                sectionAnchor: ''
            };
        }

        return {
            text: entry?.text || '',
            sectionTitle: entry?.section_title || '',
            sectionAnchor: entry?.section_anchor || ''
        };
    }

    tokenizeQuery(query) {
        const trimmed = query.trim();
        if (!trimmed) {
            return [];
        }

        const parts = trimmed.split(/\s+/).filter(Boolean);
        return parts.length ? parts : [trimmed];
    }

    getMatchScore(text, keywords) {
        if (!text || keywords.length === 0) {
            return 0;
        }

        const lowerText = text.toLowerCase();
        let matchedCount = 0;

        keywords.forEach(keyword => {
            if (lowerText.includes(keyword.toLowerCase())) {
                matchedCount += 1;
            }
        });

        if (matchedCount === 0) {
            return 0;
        }

        return matchedCount === keywords.length ? matchedCount + 1 : matchedCount;
    }

    truncateAroundMatch(text, keywords, radius = 70) {
        if (!text) {
            return '';
        }

        const lowerText = text.toLowerCase();
        const positions = keywords
            .map(keyword => lowerText.indexOf(keyword.toLowerCase()))
            .filter(index => index >= 0);

        if (positions.length === 0 || text.length <= radius * 2) {
            return text;
        }

        const firstMatch = Math.min(...positions);
        const start = Math.max(0, firstMatch - radius);
        const end = Math.min(text.length, firstMatch + radius);

        return `${start > 0 ? '...' : ''}${text.slice(start, end).trim()}${end < text.length ? '...' : ''}`;
    }

    highlightText(text, keywords) {
        if (!text) {
            return '';
        }

        const escapedKeywords = [...new Set(keywords)]
            .filter(Boolean)
            .sort((a, b) => b.length - a.length)
            .map(keyword => keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

        if (escapedKeywords.length === 0) {
            return this.escapeHtml(text);
        }

        const pattern = new RegExp(`(${escapedKeywords.join('|')})`, 'giu');
        let lastIndex = 0;
        let html = '';

        for (const match of text.matchAll(pattern)) {
            const index = match.index ?? 0;
            const matchedText = match[0];
            html += this.escapeHtml(text.slice(lastIndex, index));
            html += `<mark class="search-highlight">${this.escapeHtml(matchedText)}</mark>`;
            lastIndex = index + matchedText.length;
        }

        html += this.escapeHtml(text.slice(lastIndex));
        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// 移动端菜单
class MobileMenu {
    constructor() {
        this.toggle = document.querySelector('.menu-toggle');
        this.nav = document.querySelector('.nav-links');
        this.init();
    }
    
    init() {
        this.toggle?.addEventListener('click', () => {
            this.nav?.classList.toggle('active');
        });
        
        // 点击导航链接后关闭菜单
        this.nav?.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                this.nav?.classList.remove('active');
            });
        });
    }
}

// 代码复制功能
class CodeCopy {
    constructor() {
        this.init();
    }
    
    init() {
        document.querySelectorAll('pre').forEach(pre => {
            const button = document.createElement('button');
            button.className = 'copy-button';
            button.textContent = '复制';
            button.style.cssText = `
                position: absolute;
                top: 8px;
                right: 8px;
                padding: 4px 12px;
                font-size: 12px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                color: #e2e8f0;
                cursor: pointer;
                opacity: 0;
                transition: opacity 0.2s ease;
            `;
            
            pre.style.position = 'relative';
            pre.appendChild(button);
            
            pre.addEventListener('mouseenter', () => button.style.opacity = '1');
            pre.addEventListener('mouseleave', () => button.style.opacity = '0');
            
            button.addEventListener('click', async () => {
                const code = pre.querySelector('code')?.textContent || pre.textContent;
                try {
                    await navigator.clipboard.writeText(code);
                    button.textContent = '已复制!';
                    button.style.background = 'rgba(74, 222, 128, 0.2)';
                    setTimeout(() => {
                        button.textContent = '复制';
                        button.style.background = 'rgba(255,255,255,0.1)';
                    }, 2000);
                } catch (e) {
                    console.error('复制失败:', e);
                }
            });
        });
    }
}

// 平滑滚动
class SmoothScroll {
    constructor() {
        this.init();
    }
    
    init() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const targetId = anchor.getAttribute('href');
                if (targetId === '#') return;
                
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }
}

// 主题切换
class ThemeToggle {
    constructor() {
        this.btn = document.getElementById('themeToggle');
        this.init();
    }

    getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    getEffectiveTheme() {
        return localStorage.getItem('theme') || this.getSystemTheme();
    }

    apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    init() {
        const saved = localStorage.getItem('theme');
        if (saved) {
            document.documentElement.setAttribute('data-theme', saved);
        }

        this.btn?.addEventListener('click', () => {
            const next = this.getEffectiveTheme() === 'dark' ? 'light' : 'dark';
            this.apply(next);
        });
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new Search();
    new MobileMenu();
    new CodeCopy();
    new SmoothScroll();
    new LazyLoadImages();
    new ThemeToggle();
});
