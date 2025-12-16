#!/bin/bash

# 获取脚本所在目录的上级目录（backend）
BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
ENV_FILE="$BACKEND_DIR/.env"

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

# 检查 .env 是否存在
if [ ! -f "$ENV_FILE" ]; then
    log_error "配置文件 .env 未找到: $ENV_FILE"
    exit 1
fi

# 从 .env 文件加载环境变量
# 使用 set -a 和 source 自动导出变量
set -a
source "$ENV_FILE"
set +a

# --- 停止 PostgreSQL ---
CONTAINER_NAME="smartagent_postgres"
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_info "正在停止 PostgreSQL 容器 ($CONTAINER_NAME)..."
        docker stop $CONTAINER_NAME
        log_info "PostgreSQL 容器已停止."
    else
        log_info "PostgreSQL 容器未运行."
    fi
else
    log_warn "PostgreSQL 容器 ($CONTAINER_NAME) 不存在."
fi

# --- 停止 Milvus ---
# 尝试使用 standalone_embed.sh 停止 Milvus
MILVUS_SCRIPT="$BACKEND_DIR/db/standalone_embed.sh"

if [ -f "$MILVUS_SCRIPT" ]; then
    log_info "正在停止 Milvus..."
    
    # 确保脚本有执行权限
    chmod +x "$MILVUS_SCRIPT"
    
    # 切换到脚本所在目录执行
    (
        cd "$(dirname "$MILVUS_SCRIPT")"
        # 直接调用 bash 运行 stop 命令
        bash standalone_embed.sh stop
    )
    
    if [ $? -eq 0 ]; then
            log_info "Milvus 停止命令执行成功."
    else
            log_error "Milvus 停止命令执行失败."
    fi
else
    log_warn "Milvus 启动脚本未找到 ($MILVUS_SCRIPT)，尝试直接停止容器..."
    # 尝试直接停止可能存在的 Milvus 容器
    MILVUS_CONTAINER="milvus-standalone"
    if docker ps --format '{{.Names}}' | grep -q "^${MILVUS_CONTAINER}$"; then
        docker stop $MILVUS_CONTAINER
        log_info "Milvus 容器 ($MILVUS_CONTAINER) 已停止."
    else
        log_info "Milvus 容器 ($MILVUS_CONTAINER) 未运行."
    fi
    
    # 同时停止 etcd 和 minio 如果它们是独立启动的 (对于 milvus-standalone 脚本，它可能只管理 milvus-standalone 容器)
    # 注意：standalone_embed.sh 启动的是 embedded etcd，所以只有一个容器
fi

log_info "数据库停止脚本执行完成."
