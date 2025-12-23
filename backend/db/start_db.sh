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

check_port_occupied() {
    local port=$1
    if ss -tuln | grep -q ":$port "; then
        return 0
    else
        return 1
    fi
}

# --- 数据目录配置 ---
DB_DATA_DIR="$BACKEND_DIR/../data/db_data"
mkdir -p "$DB_DATA_DIR"

# PostgreSQL 数据目录
PG_DATA_DIR="$DB_DATA_DIR/postgres"
mkdir -p "$PG_DATA_DIR"

# Milvus 数据目录
MILVUS_DATA_DIR="$DB_DATA_DIR/milvus"
mkdir -p "$MILVUS_DATA_DIR"

# --- PostgreSQL 配置 ---
# 直接使用 .env 中的变量
PG_HOST=${POSTGRES_HOST:-localhost}
PG_PORT=${POSTGRES_PORT:-5432}
PG_USER=${POSTGRES_USER:-postgres}
PG_PASS=${POSTGRES_PASSWORD}
PG_DB=${POSTGRES_DB:-postgres}

# 如果 localhost，则尝试启动 Docker
if [ "$PG_HOST" == "localhost" ] || [ "$PG_HOST" == "127.0.0.1" ]; then
    CONTAINER_NAME="smartagent_postgres"
    
    if check_port_occupied "$PG_PORT"; then
        log_info "PostgreSQL 端口 $PG_PORT 已被占用，跳过启动."
    else
        log_info "正在检查 PostgreSQL 容器 ($CONTAINER_NAME)..."
        
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                 log_info "PostgreSQL 容器正在运行."
            else
                 log_info "启动现有的 PostgreSQL 容器..."
                 docker start $CONTAINER_NAME
            fi
        else
            log_info "创建并启动新的 PostgreSQL 容器..."
            # 默认使用 postgres:15
            # 挂载数据目录
            docker run -d \
                --name $CONTAINER_NAME \
                -p $PG_PORT:5432 \
                -e POSTGRES_USER=$PG_USER \
                -e POSTGRES_PASSWORD=$PG_PASS \
                -e POSTGRES_DB=$PG_DB \
                -v "$PG_DATA_DIR:/var/lib/postgresql/data" \
                postgres:15
        fi
    fi
else
    log_info "PostgreSQL 配置为远程主机 ($PG_HOST)，跳过本地 Docker 启动."
fi


# --- Milvus 配置 ---
# 使用同目录下的 standalone_embed.sh 启动 Milvus
# 该脚本封装了 Milvus Standalone (Embedded Etcd) 的 docker run 逻辑

# 从 .env 读取 MILVUS_URI
MILVUS_URI=${MILVUS_URI:-http://localhost:19530}
# 提取端口，例如 http://localhost:19530 -> 19530
MILVUS_PORT=$(echo $MILVUS_URI | sed -e 's/.*:\([0-9]*\).*/\1/')

if [[ "$MILVUS_URI" == *"localhost"* ]] || [[ "$MILVUS_URI" == *"127.0.0.1"* ]]; then
    
    if check_port_occupied "$MILVUS_PORT"; then
         log_info "Milvus 端口 $MILVUS_PORT 已被占用，跳过启动."
    else
        # 检查 standalone_embed.sh 是否存在
        MILVUS_SCRIPT="$BACKEND_DIR/db/standalone_embed.sh"
        
        if [ ! -f "$MILVUS_SCRIPT" ]; then
            log_error "Milvus 启动脚本未找到: $MILVUS_SCRIPT"
            # 尝试在当前目录查找 (如果在 db 目录下运行)
            if [ -f "./standalone_embed.sh" ]; then
                 MILVUS_SCRIPT="./standalone_embed.sh"
            else
                 log_warn "尝试跳过 Milvus 自动启动..."
            fi
        fi

        if [ -f "$MILVUS_SCRIPT" ]; then
            log_info "正在启动 Milvus..."
            
            # 确保脚本有执行权限
            chmod +x "$MILVUS_SCRIPT"
            
            (
                cd "$(dirname "$MILVUS_SCRIPT")"
                # 注意：standalone_embed.sh 内部使用了 sudo，如果用户非 root 且无 sudo 权限可能会失败
                # 如果当前已经是 root 或者有免密 sudo，则没问题
                # 这里直接调用 bash 运行
                bash standalone_embed.sh start
            )
            
            if [ $? -eq 0 ]; then
                 log_info "Milvus 启动命令执行成功."
            else
                 log_error "Milvus 启动命令执行失败."
            fi
        fi
    fi
else
    log_info "Milvus 配置为远程 URI ($MILVUS_URI)，跳过本地 Docker 启动."
fi

# ----Redis配置-------
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
if [ "$REDIS_HOST" == "localhost" ] || [ "$REDIS_HOST" == "127.0.0.1" ]; then
    CONTAINER_NAME="smartagent_redis"
    
    if check_port_occupied "$REDIS_PORT"; then
        log_info "Redis 端口 $REDIS_PORT 已被占用，跳过启动."
    else
        log_info "正在检查 Redis 容器 ($CONTAINER_NAME)..."
        
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
                 log_info "Redis 容器正在运行."
            else
                 log_info "启动现有的 Redis 容器..."
                 docker start $CONTAINER_NAME
            fi
        else
            log_info "创建并启动新的 Redis 容器..."
            # 默认使用 redis:6
            # 挂载数据目录
            docker run -d \
                --name $CONTAINER_NAME \
                -p $PG_PORT:5432 \
                -e POSTGRES_USER=$PG_USER \
                -e POSTGRES_PASSWORD=$PG_PASS \
                -e POSTGRES_DB=$PG_DB \
                -v "$PG_DATA_DIR:/var/lib/postgresql/data" \
                postgres:15
        fi
    fi
else
    log_info "PostgreSQL 配置为远程主机 ($PG_HOST)，跳过本地 Docker 启动."
fi



# --- 端口检测 ---
log_info "等待几秒钟让服务启动..."
sleep 5

log_info "--- 端口占用检测 ---"
check_port() {
    local port=$1
    local name=$2
    if ss -tuln | grep -q ":$port "; then
        log_info "端口 $port ($name) 正在被占用 (服务已启动)."
    else
        log_warn "端口 $port ($name) 未被占用 (可能启动失败或还在启动中)."
    fi
}

check_port "$PG_PORT" "PostgreSQL"
check_port "$MILVUS_PORT" "Milvus"

# --- 执行 DDL ---
# 如果 PostgreSQL 启动成功（或已运行），执行 table_ddl.sql
DDL_FILE="$BACKEND_DIR/db/table_ddl.sql"

if [ -f "$DDL_FILE" ]; then
    log_info "正在检查 PostgreSQL 是否就绪以执行 DDL..."
    
    # 尝试连接 PostgreSQL 并执行 SQL
    # 需要安装 postgresql-client (psql) 或者使用 docker exec
    
    if [ "$PG_HOST" == "localhost" ] || [ "$PG_HOST" == "127.0.0.1" ]; then
        CONTAINER_NAME="smartagent_postgres"
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
             log_info "在容器 $CONTAINER_NAME 中执行 table_ddl.sql..."
             
             # 等待 PostgreSQL 完全启动
             RETRIES=10
             while [ $RETRIES -gt 0 ]; do
                 if docker exec $CONTAINER_NAME pg_isready -U "$PG_USER" > /dev/null 2>&1; then
                     break
                 fi
                 log_info "等待 PostgreSQL 就绪... ($RETRIES)"
                 sleep 2
                 RETRIES=$((RETRIES-1))
             done
             
             if [ $RETRIES -eq 0 ]; then
                 log_error "PostgreSQL 未能及时就绪，跳过 DDL 执行."
             else
                 # 将 SQL 文件内容传递给 docker exec psql
                 # 注意：这里假设 table_ddl.sql 的语法是兼容的 (create table if not exists)
                 cat "$DDL_FILE" | docker exec -i $CONTAINER_NAME psql -U "$PG_USER" -d "$PG_DB"
                 
                 if [ $? -eq 0 ]; then
                     log_info "DDL 执行成功."
                 else
                     log_error "DDL 执行失败."
                 fi
             fi
        else
             log_warn "PostgreSQL 容器未运行，跳过 DDL 执行."
        fi
    else
        # 远程主机，如果本地有 psql 命令则尝试执行
        if command -v psql >/dev/null 2>&1; then
             log_info "正在远程主机 $PG_HOST 上执行 table_ddl.sql..."
             PGPASSWORD="$PG_PASS" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -f "$DDL_FILE"
             if [ $? -eq 0 ]; then
                 log_info "DDL 执行成功."
             else
                 log_error "DDL 执行失败."
             fi
        else
             log_warn "未找到 psql 命令且配置为远程主机，跳过 DDL 执行."
        fi
    fi
else
    log_warn "未找到 DDL 文件: $DDL_FILE"
fi

log_info "数据库服务启动脚本执行完成."
