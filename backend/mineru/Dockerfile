# FROM docker.m.daocloud.io/python:3.12-slim
# RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
FROM docker.m.daocloud.io/vllm/vllm-openai:v0.10.1.1
# FROM docker.m.daocloud.io/vllm/vllm-openai:v0.10.2

# Install uv for faster pip installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
# RUN pip install uv -i https://mirrors.aliyun.com/pypi/simple

RUN apt-get update && \
    apt-get install -y \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy only pyproject.toml first to cache dependencies
COPY pyproject.toml /Mineru/pyproject.toml
# Copy version file as it is needed for setup
COPY mineru/version.py /Mineru/mineru/version.py
WORKDIR /Mineru

# Install dependencies using uv
# Use --system to install into the system python environment, matching the behavior of the original Dockerfile
# Use --no-cache-dir to keep the image size small
# Use -e .[core] to install the package in editable mode with 'core' optional dependencies
RUN uv pip install --system --no-cache-dir -e .'[core]' --index-url https://mirrors.aliyun.com/pypi/simple

# Copy the rest of the source code
COPY . /Mineru

# Re-install package to include source code changes (fast because dependencies are already installed)
RUN uv pip install --system --no-cache-dir -e .'[core]' --index-url https://mirrors.aliyun.com/pypi/simple

# 下载模型并更新配置文件，该命令会将模型下载到本地，后面直接使用本地模型
RUN /bin/bash -c "mineru-models-download -s modelscope -m all"

# Set the entry point to activate the virtual environment and run the command line tool
ENTRYPOINT ["/bin/bash", "-c", "export MINERU_MODEL_SOURCE=local && exec \"$@\"", "--"]
