# /bin/bash
# 启动所有中间件：Mineru
# 启动Mineru容器

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

check_port() {
    local port=$1
    local name=$2
    if ss -tuln | grep -q ":$port "; then
        log_info "端口 $port ($name) 正在被占用 (服务已启动)."
    else
        log_warn "端口 $port ($name) 未被占用 (可能启动失败或还在启动中)."
    fi
}
# 第一步构建镜像，列出当前docker 镜像列表，如果mineru:latest存在，就直接运行
if docker images | grep  "mineru_source_code"; then
    log_info "镜像 mineru:latest 已存在，直接运行."
    docker compose -f compose.yaml --profile api up -d
else
    log_info "镜像 mineru_source_code:latest 不存在，开始构建."
    docker build -t mineru_source_code:latest -f Dockerfile .
    log_info "镜像 mineru_source_code:latest 构建完成."
    docker compose -f compose.yaml --profile api up -d
fi

check_port 8000 "Mineru API"

