#!/bin/bash

# 配置部分
# --------------------------------------------------
# 模型挂载目录（宿主机路径），建议改为你存放模型的实际路径
MODEL_VOLUME="/home/m1881/hf_models"

# 容器内模型路径前缀 (TEI 默认会把 /data 映射为 storage)
# 如果你本地路径是 /home/m1881/hf_models/BAAI/bge-reranker-v2-m3
# 映射到容器内通常是 /data/BAAI/bge-reranker-v2-m3
# 但 TEI 也可以自动下载模型，如果本地有模型，请确保路径映射正确

# Embedding 模型配置
EMBEDDING_MODEL_ID="BAAI/bge-m3"  # 或者本地路径，如 /data/bge-m3
EMBEDDING_PORT=8081
EMBEDDING_CONTAINER_NAME="tei-embedding-server"

# Reranker 模型配置
RERANKER_MODEL_ID="BAAI/bge-reranker-v2-m3" # 或者本地路径，如 /data/bge-reranker-v2-m3
RERANKER_PORT=8082
RERANKER_CONTAINER_NAME="tei-reranker-server"

# 显卡配置 (all 或 device=0,1)
GPU_CONFIG="all"
# --------------------------------------------------

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到 Docker，请先安装 Docker。"
    exit 1
fi

echo "=================================================="
echo "准备启动 Text Embeddings Inference (TEI) 服务..."
echo "模型挂载目录: $MODEL_VOLUME"
echo "=================================================="

# 1. 启动 Embedding 服务
echo ""
echo "[1/2] 启动 Embedding 服务 ($EMBEDDING_MODEL_ID)..."

# 检查并删除旧容器
if [ "$(docker ps -aq -f name=$EMBEDDING_CONTAINER_NAME)" ]; then
    echo "发现旧容器 $EMBEDDING_CONTAINER_NAME，正在删除..."
    docker rm -f $EMBEDDING_CONTAINER_NAME
fi

docker run -d \
    --gpus "$GPU_CONFIG" \
    -p $EMBEDDING_PORT:80 \
    -v $MODEL_VOLUME:/data \
    --name $EMBEDDING_CONTAINER_NAME \
    --pull always \
    ghcr.io/huggingface/text-embeddings-inference:1.5 \
    --model-id $EMBEDDING_MODEL_ID \
    --auto-truncate

if [ $? -eq 0 ]; then
    echo "✅ Embedding 服务启动成功！"
    echo "   地址: http://localhost:$EMBEDDING_PORT"
else
    echo "❌ Embedding 服务启动失败，请检查日志: docker logs $EMBEDDING_CONTAINER_NAME"
fi

# 2. 启动 Reranker 服务
echo ""
echo "[2/2] 启动 Reranker 服务 ($RERANKER_MODEL_ID)..."

# 检查并删除旧容器
if [ "$(docker ps -aq -f name=$RERANKER_CONTAINER_NAME)" ]; then
    echo "发现旧容器 $RERANKER_CONTAINER_NAME，正在删除..."
    docker rm -f $RERANKER_CONTAINER_NAME
fi

docker run -d \
    --gpus "$GPU_CONFIG" \
    -p $RERANKER_PORT:80 \
    -v $MODEL_VOLUME:/data \
    --name $RERANKER_CONTAINER_NAME \
    --pull always \
    ghcr.io/huggingface/text-embeddings-inference:1.5 \
    --model-id $RERANKER_MODEL_ID \
    --auto-truncate

if [ $? -eq 0 ]; then
    echo "✅ Reranker 服务启动成功！"
    echo "   地址: http://localhost:$RERANKER_PORT"
else
    echo "❌ Reranker 服务启动失败，请检查日志: docker logs $RERANKER_CONTAINER_NAME"
fi

echo ""
echo "=================================================="
echo "服务状态概览:"
docker ps -f name=tei-
echo "=================================================="
