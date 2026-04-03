#!/bin/bash
#
# Simple Blog - Vercel 一键部署脚本
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Simple Blog - Vercel 部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Vercel CLI
if ! command -v vercel &> /dev/null; then
    echo -e "${YELLOW}▶ 安装 Vercel CLI...${NC}"
    npm install -g vercel
fi

# 检查是否已登录
if ! vercel whoami &> /dev/null; then
    echo -e "${YELLOW}▶ 请先登录 Vercel${NC}"
    vercel login
fi

# 检查项目是否已关联
if [ ! -d ".vercel" ]; then
    echo -e "${YELLOW}▶ 初始化 Vercel 项目...${NC}"
    echo -e "${BLUE}提示: 按提示选择或创建项目${NC}"
    vercel
fi

# 同步 markdown-press 文章（如果存在）
echo ""
echo -e "${YELLOW}▶ 检查文章源...${NC}"

MARKDOWN_PRESS_DIRS=(
    "../posts"
    "../content"
    "../markdown-press/posts"
    "markdown-press/posts"
)

for dir in "${MARKDOWN_PRESS_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓ 发现文章目录: $dir${NC}"
        mkdir -p posts
        cp -r "$dir/"* posts/ 2>/dev/null || true
        echo -e "${GREEN}✓ 文章已同步${NC}"
        break
    fi
done

# 构建
echo ""
echo -e "${YELLOW}▶ 构建博客...${NC}"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r build-requirements.txt
python build.py

if [ ! -d "dist" ] || [ ! -f "dist/index.html" ]; then
    echo -e "${RED}✗ 构建失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 构建成功${NC}"

# 部署到 Vercel
echo ""
echo -e "${YELLOW}▶ 部署到 Vercel...${NC}"
echo ""

# 询问是否生产部署
read -p "是否部署到生产环境? (Y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}▶ 部署到预览环境...${NC}"
    vercel --yes
else
    echo -e "${YELLOW}▶ 部署到生产环境...${NC}"
    vercel --prod --yes
fi

echo ""
echo -e "${GREEN}✓ 部署完成!${NC}"
