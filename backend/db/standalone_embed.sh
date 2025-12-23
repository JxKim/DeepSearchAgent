#!/bin/bash

# 获取脚本所在目录的上级目录（backend）
BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
ENV_FILE="$BACKEND_DIR/.env"
# --- 数据目录配置 ---
DB_DATA_DIR="$BACKEND_DIR/../data/db_data"
mkdir -p "$DB_DATA_DIR"

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

# Milvus 数据目录
MILVUS_DATA_DIR="$DB_DATA_DIR/milvus"
MILVUS_CONFIG_DIR="$DB_DATA_DIR/milvus_config"
mkdir -p "$MILVUS_DATA_DIR"
mkdir -p "$MILVUS_CONFIG_DIR"

run_embed() {
    log_info "正在将相关配置写入到 $MILVUS_CONFIG_DIR 目录..."
    cat << EOF > "$MILVUS_CONFIG_DIR"/embedEtcd.yaml
listen-client-urls: http://0.0.0.0:2379
advertise-client-urls: http://0.0.0.0:2379
quota-backend-bytes: 4294967296
auto-compaction-mode: revision
auto-compaction-retention: '1000'
EOF

    cat << EOF > "$MILVUS_CONFIG_DIR"/user.yaml
# Extra config to override default milvus.yaml
EOF
    log_info "将相关配置写入到 $MILVUS_CONFIG_DIR 目录 完成"
    if [ ! -f "$MILVUS_CONFIG_DIR/embedEtcd.yaml" ]
    then
        log_error "embedEtcd.yaml file does not exist. Please try to create it in the current directory."
        exit 1
    fi

    if [ ! -f "$MILVUS_CONFIG_DIR/user.yaml" ]
    then
        log_error "user.yaml file does not exist. Please try to create it in the current directory."
        exit 1
    fi
    
    sudo docker run -d \
        --name milvus-standalone \
        --security-opt seccomp:unconfined \
        -e ETCD_USE_EMBED=true \
        -e ETCD_DATA_DIR=/var/lib/milvus/etcd \
        -e ETCD_CONFIG_PATH=/milvus/configs/embedEtcd.yaml \
        -e COMMON_STORAGETYPE=local \
        -e DEPLOY_MODE=STANDALONE \
        -v "$MILVUS_DATA_DIR":/var/lib/milvus \
        -v "$MILVUS_CONFIG_DIR"/embedEtcd.yaml:/milvus/configs/embedEtcd.yaml \
        -v "$MILVUS_CONFIG_DIR"/user.yaml:/milvus/configs/user.yaml \
        -p 19530:19530 \
        -p 9091:9091 \
        -p 2379:2379 \
        --health-cmd="curl -f http://localhost:9091/healthz" \
        --health-interval=30s \
        --health-start-period=90s \
        --health-timeout=20s \
        --health-retries=3 \
        milvusdb/milvus:v2.6.7 \
        milvus run standalone  1> /dev/null
}

wait_for_milvus_running() {
    log_info "等待Milvus启动中..."
    local max_retries=60
    local count=0
    while [ $count -lt $max_retries ]
    do
        # 检查容器是否还在运行
        if ! sudo docker ps | grep -q milvus-standalone; then
             log_error "Milvus 容器已停止运行，启动失败。"
             log_error "请使用 'docker logs milvus-standalone' 查看日志。"
             return 1
        fi

        res=`sudo docker ps|grep milvus-standalone|grep healthy|wc -l`
        if [ $res -eq 1 ]
        then
            log_info "Milvus 启动成功"
            # log_info "To change the default Milvus configuration, add your settings to the user.yaml file and then restart the service."
            return 0
        fi
        sleep 2
        count=$((count+1))
        log_info "正在等待 Milvus 就绪... ($count/$max_retries)"
    done
    
    log_error "Milvus 启动超时 (120秒)."
    log_error "当前状态: $(sudo docker inspect --format='{{.State.Health.Status}}' milvus-standalone 2>/dev/null)"
    return 1
}

start() {
    res=`sudo docker ps|grep milvus-standalone|grep healthy|wc -l`
    if [ $res -eq 1 ]
    then
        log_info "Milvus 正在运行中."
        exit 0
    fi

    res=`sudo docker ps -a|grep milvus-standalone|wc -l`
    if [ $res -eq 1 ]
    then
        sudo docker start milvus-standalone 1> /dev/null
    else
        run_embed
    fi

    if [ $? -ne 0 ]
    then
        log_error "启动失败."
        exit 1
    fi

    wait_for_milvus_running
    if [ $? -ne 0 ]; then
        exit 1
    fi
}

stop() {
    sudo docker stop milvus-standalone 1> /dev/null

    if [ $? -ne 0 ]
    then
        log_error "停止Milvus失败."
        exit 1
    fi
    log_info "Milvus 停止成功."

}

delete_container() {
    res=`sudo docker ps|grep milvus-standalone|wc -l`
    if [ $res -eq 1 ]
    then
        log_warn "请先停止Milvus服务再删除."
        exit 1
    fi
    sudo docker rm milvus-standalone 1> /dev/null
    if [ $? -ne 0 ]
    then
        log_error "删除Milvus容器失败."
        exit 1
    fi
    log_info "Milvus 容器删除成功."
}

delete() {
    read -p "请确认是否继续删除Milvus容器和数据. 这将删除容器和数据. 确认请输入 'y' 或 'n'. > " check
    if [ "$check" == "y" ] ||[ "$check" == "Y" ];then
        delete_container
        sudo rm -rf $(pwd)/volumes
        sudo rm -rf $(pwd)/embedEtcd.yaml
        sudo rm -rf $(pwd)/user.yaml
        log_info "Milvus 数据删除成功."
    else
        log_info "Exit delete"
        exit 0
    fi
}

upgrade() {
    read -p "Please confirm if you'd like to proceed with the upgrade. The default will be to the latest version. Confirm with 'y' for yes or 'n' for no. > " check
    if [ "$check" == "y" ] ||[ "$check" == "Y" ];then
        res=`sudo docker ps -a|grep milvus-standalone|wc -l`
        if [ $res -eq 1 ]
        then
            stop
            delete_container
        fi

        curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed_latest.sh && \
        bash standalone_embed_latest.sh start 1> /dev/null && \
        log_info "Upgrade successfully."
    else
        log_info "Exit upgrade"
        exit 0
    fi
}

case $1 in
    restart)
        stop
        start
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    upgrade)
        upgrade
        ;;
    delete)
        delete
        ;;
    *)
        log_info "请使用 bash standalone_embed.sh restart|start|stop|upgrade|delete"
        ;;
esac
