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

// 节流函数 - 性能优化
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
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
        this.init();
    }
    
    async init() {
        // 加载搜索数据
        try {
            const response = await fetch('/search.json');
            this.data = await response.json();
        } catch (e) {
            console.error('加载搜索数据失败:', e);
        }
        
        // 绑定事件
        this.trigger?.addEventListener('click', (e) => {
            e.preventDefault();
            this.open();
        });
        
        this.closeBtn?.addEventListener('click', () => this.close());
        
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
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
    }
    
    open() {
        this.modal?.classList.add('active');
        this.input?.focus();
        this.input.value = '';
        this.results.innerHTML = '';
    }
    
    close() {
        this.modal?.classList.remove('active');
    }
    
    search(query) {
        if (!query.trim()) {
            this.results.innerHTML = '';
            return;
        }
        
        const keyword = query.toLowerCase();
        const matches = this.data.filter(item => {
            return item.title.toLowerCase().includes(keyword) ||
                   (item.description && item.description.toLowerCase().includes(keyword)) ||
                   (item.tags && item.tags.some(tag => tag.toLowerCase().includes(keyword)));
        }).slice(0, 10);
        
        this.renderResults(matches);
    }
    
    renderResults(matches) {
        if (matches.length === 0) {
            this.results.innerHTML = '<div class="search-result-item"><div class="search-result-meta">未找到相关文章</div></div>';
            return;
        }
        
        this.results.innerHTML = matches.map(item => `
            <div class="search-result-item" onclick="window.location.href='/posts/${item.slug}/'">
                <div class="search-result-title">${this.escapeHtml(item.title)}</div>
                <div class="search-result-meta">
                    ${item.date || ''} ${item.category ? `· ${item.category}` : ''}
                </div>
            </div>
        `).join('');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
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

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    new Search();
    new MobileMenu();
    new CodeCopy();
    new SmoothScroll();
    new LazyLoadImages();
});
