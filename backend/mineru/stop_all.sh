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
    # 端口没有被占用，且查找不到当前容器，则表示停止成功
    if ! ss -tuln | grep -q ":$port "; then
        if ! docker container ls | grep "$name"; then
            log_info "端口 $port ($name) 未被占用，且容器 $name 不存在，停止成功."
        else
            log_error "端口 $port ($name) 未被占用，但容器 $name 存在，停止失败."
        fi
    else
        log_info "端口 $port ($name) 正在被占用，停止失败."
    fi
}

# 启动Mineru容器
docker container stop mineru-api

check_port 8000 "mineru-api"

