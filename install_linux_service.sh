#!/bin/bash

# MangaBot Linux系统服务安装脚本
# 此脚本将在Ubuntu系统中安装MangaBot作为系统服务

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 检查是否以root权限运行
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        log_info "请使用: sudo $0"
        exit 1
    fi
}

# 检查系统兼容性
check_system() {
    log_info "检查系统兼容性..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        log_error "无法检测操作系统类型"
        exit 1
    fi
    
    source /etc/os-release
    
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        log_warn "此脚本主要针对Ubuntu/Debian系统，其他系统可能需要调整"
    fi
    
    # 检查Python版本
    if ! command -v python3 &> /dev/null; then
        log_error "未找到Python3，请先安装Python3"
        log_info "运行: apt update && apt install -y python3 python3-pip"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    log_info "检测到Python版本: $python_version"
    
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)"; then
        log_success "Python版本满足要求 (>= 3.7)"
    else
        log_error "Python版本过低，需要3.7或更高版本"
        exit 1
    fi
}

# 创建系统用户和组
create_user() {
    log_info "创建系统用户和组..."
    
    if ! id "mangabot" &>/dev/null; then
        useradd -r -s /bin/false -d /opt/mangabot mangabot
        log_success "创建用户'mangabot'"
    else
        log_info "用户'mangabot'已存在"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    # 创建安装目录
    mkdir -p /opt/mangabot
    
    # 创建数据目录
    mkdir -p /var/lib/mangabot/downloads
    mkdir -p /var/log/mangabot
    
    # 设置权限
    chown -R mangabot:mangabot /opt/mangabot
    chown -R mangabot:mangabot /var/lib/mangabot
    chown -R mangabot:mangabot /var/log/mangabot
    
    chmod 755 /opt/mangabot
    chmod 755 /var/lib/mangabot
    chmod 755 /var/log/mangabot
    
    log_success "目录结构创建完成"
}

# 复制文件到安装目录
copy_files() {
    log_info "复制文件到安装目录..."
    
    # 获取当前脚本所在目录
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # 复制必要文件
    cp "$SCRIPT_DIR/bot.py" /opt/mangabot/
    cp "$SCRIPT_DIR/requirements.txt" /opt/mangabot/
    cp "$SCRIPT_DIR/.env.example" /opt/mangabot/.env 2>/dev/null || true
    
    # 复制插件目录（如果存在）
    if [[ -d "$SCRIPT_DIR/plugins" ]]; then
        cp -r "$SCRIPT_DIR/plugins" /opt/mangabot/
    fi
    
    # 设置文件权限
    chown -R mangabot:mangabot /opt/mangabot
    chmod 644 /opt/mangabot/*.py
    chmod 644 /opt/mangabot/*.txt
    chmod 600 /opt/mangabot/.env 2>/dev/null || true
    
    log_success "文件复制完成"
}

# 安装Python依赖
install_dependencies() {
    log_info "安装Python依赖..."
    
    # 切换到安装目录
    cd /opt/mangabot
    
    # 安装pip依赖
    if python3 -m pip install --upgrade pip; then
        log_success "pip升级完成"
    else
        log_warn "pip升级失败，尝试继续安装"
    fi
    
    if python3 -m pip install -r requirements.txt; then
        log_success "Python依赖安装完成"
    else
        log_error "Python依赖安装失败"
        exit 1
    fi
}

# 安装系统服务
install_service() {
    log_info "安装系统服务..."
    
    # 复制服务文件
    cp mangabot.service /etc/systemd/system/
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用服务
    systemctl enable mangabot.service
    
    log_success "系统服务安装完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    # 检查.env文件是否存在
    if [[ ! -f "/opt/mangabot/.env" ]]; then
        log_warn "未找到.env文件，创建示例配置"
        cat > /opt/mangabot/.env << EOF
# MangaBot 配置
# 请根据实际情况修改以下配置

# NapCat WebSocket地址
NAPCAT_WS_URL=ws://localhost:8080/qq

# Flask服务器配置
FLASK_HOST=0.0.0.0
FLASK_PORT=20010

# API令牌（可选，用于安全验证）
API_TOKEN=your_secret_token_here

# 下载路径
MANGA_DOWNLOAD_PATH=/var/lib/mangabot/downloads

# 日志级别
LOG_LEVEL=INFO

# 其他配置...
EOF
        
        chown mangabot:mangabot /opt/mangabot/.env
        chmod 600 /opt/mangabot/.env
    fi
    
    log_success "环境变量配置完成"
}

# 显示安装完成信息
show_completion() {
    log_success "MangaBot Linux系统服务安装完成!"
    echo ""
    echo "=== 安装摘要 ==="
    echo "• 安装目录: /opt/mangabot"
    echo "• 数据目录: /var/lib/mangabot"
    echo "• 日志目录: /var/log/mangabot"
    echo "• 系统用户: mangabot"
    echo "• 服务文件: /etc/systemd/system/mangabot.service"
    echo ""
    echo "=== 使用方法 ==="
    echo "启动服务: systemctl start mangabot"
    echo "停止服务: systemctl stop mangabot"
    echo "重启服务: systemctl restart mangabot"
    echo "查看状态: systemctl status mangabot"
    echo "查看日志: journalctl -u mangabot -f"
    echo ""
    echo "=== 重要提醒 ==="
    echo "1. 请编辑 /opt/mangabot/.env 文件配置正确的参数"
    echo "2. 确保NapCat服务正在运行并配置正确的WebSocket地址"
    echo "3. 检查防火墙设置，确保端口20010可访问"
    echo ""
}

# 主安装函数
main() {
    log_info "开始安装MangaBot Linux系统服务..."
    
    check_root
    check_system
    create_user
    create_directories
    copy_files
    install_dependencies
    install_service
    setup_environment
    show_completion
    
    log_success "安装过程完成!"
}

# 运行主函数
main "$@"