FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 复制源码
COPY src/ src/
COPY .agent.yaml .

# 创建工作区挂载点
RUN mkdir -p /workspace

WORKDIR /workspace

ENTRYPOINT ["python", "-m", "agent"]
